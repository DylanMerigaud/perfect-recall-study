#!/usr/bin/env python3
"""Check a manuscript's [n] citations against its refs.jsonl evidence file.

Usage: check_refs.py OUT REFS

OUT is the rendered manuscript. REFS is a JSON-lines file with one entry per reference, in the
same order as the manuscript's "## References" section (entry 1 describes reference [1], entry 2
describes [2], and so on); each entry is expected to carry "citation" (the IEEE-style string,
matched against the manuscript's own printed reference line), "supports" (a verbatim quote from
the source backing the claim it is cited for), "read_by", and exactly one identifier among "doi",
"arxiv", "url" or "isbn".

Checked, all without any network call:
- every "[n]" citation marker in the body has a matching numbered entry in the References
  section, and every References entry is cited at least once in the body;
- citation numbers are assigned in the order references are first cited (the manuscript may not
  cite [2] before [1] has appeared);
- refs.jsonl has exactly as many entries as the manuscript has references;
- every refs.jsonl entry has a non-empty "supports" quote, a non-empty "read_by", and at least
  one of doi, arxiv, url or isbn.

Checked with a network call, one per identifier type:
- a "doi" is looked up on Crossref (https://api.crossref.org/works/<doi>); the paper's title,
  year and first author's surname, parsed from the manuscript's own printed citation text, must
  match Crossref's record (title by token-set similarity at least 0.9, year exactly, surname
  case- and accent-insensitively);
- an "arxiv" id is looked up on arXiv's API; its title must match by the same similarity
  threshold;
- a "url" must answer with HTTP status 200.
- an "isbn" is checked for presence only: no isbn lookup API is used here.

All network access goes through urllib and through a single injectable `opener` argument on
every lookup function, so tests can substitute a fake opener and never touch the network.

Exits 1 and prints every problem found (never just the first) if any check fails. Exits 0
otherwise.
"""
import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _mdutil  # noqa: E402

CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")
REFERENCE_ENTRY_RE = re.compile(r"^\[(\d+)\]\s*(.*)$")
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
SIMILARITY_THRESHOLD = 0.9


def _default_opener(request, timeout=15):
    return urllib.request.urlopen(request, timeout=timeout)


def token_set_similarity(a, b):
    """Jaccard similarity of the two strings' lowercased alphanumeric token sets."""

    def tokens(s):
        return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _normalize_name(name):
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_only.strip().lower()


def parse_citation_text(text):
    """Heuristically pull a title, a year and a first-author surname out of an IEEE-style
    citation string, e.g. 'D. Merigaud, "A title," Venue, 2026.'."""
    title_m = re.search(r'"([^"]+)"', text)
    title = title_m.group(1).rstrip(",.").strip() if title_m else None
    years = re.findall(r"(?:19|20)\d\d", text)
    year = int(years[-1]) if years else None
    before_comma = text.split(",", 1)[0].strip()
    tokens = before_comma.split()
    surname = tokens[-1].rstrip(".") if tokens else None
    return {"title": title, "year": year, "surname": surname}


def body_citation_order(text):
    """Distinct citation numbers in the order they are first cited in the body (before
    References)."""
    refs = _mdutil.find_section(text, "References")
    body = text[: refs[0]] if refs is not None else text
    seen = []
    for m in CITATION_MARKER_RE.finditer(body):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def references_list(text):
    """[(number, citation_text), ...] as printed in the manuscript's References section."""
    refs_body = _mdutil.section_body(text, "References")
    entries = []
    if refs_body is None:
        return entries
    for line in refs_body.splitlines():
        m = REFERENCE_ENTRY_RE.match(line.strip())
        if m:
            entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def load_refs_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("refs.jsonl line %d is not valid JSON: %s" % (line_no, e))
    return entries


def crossref_lookup(doi, opener=None):
    opener = opener or _default_opener
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    with opener(url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    message = data.get("message", {})
    titles = message.get("title") or []
    title = titles[0] if titles else None
    year = None
    for key in ("published-print", "published-online", "published", "issued"):
        block = message.get(key)
        if block and block.get("date-parts"):
            parts = block["date-parts"][0]
            if parts and parts[0]:
                year = int(parts[0])
                break
    authors = message.get("author") or []
    surname = authors[0].get("family") if authors else None
    return {"title": title, "year": year, "surname": surname}


def arxiv_lookup(arxiv_id, opener=None):
    opener = opener or _default_opener
    url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arxiv_id)
    with opener(url) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    entry = root.find("atom:entry", ATOM_NS)
    if entry is None:
        return {"title": None}
    title_el = entry.find("atom:title", ATOM_NS)
    title = title_el.text.strip() if title_el is not None and title_el.text else None
    if title:
        title = re.sub(r"\s+", " ", title)
    return {"title": title}


def url_status(url, opener=None):
    opener = opener or _default_opener
    request = urllib.request.Request(url, method="HEAD")
    try:
        with opener(request) as resp:
            return getattr(resp, "status", None) or resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code


def check_entry(number, manuscript_citation, entry, opener=None):
    opener = opener or _default_opener
    errors = []
    if not entry.get("supports"):
        errors.append("reference %d: refs.jsonl entry has no supports quote" % number)
    if not entry.get("read_by"):
        errors.append("reference %d: refs.jsonl entry has no read_by" % number)

    identifiers = [k for k in ("doi", "arxiv", "url", "isbn") if entry.get(k)]
    if not identifiers:
        errors.append("reference %d: refs.jsonl entry has no doi, arxiv, url or isbn" % number)
        return errors

    claimed = parse_citation_text(manuscript_citation)

    if entry.get("doi"):
        try:
            found = crossref_lookup(entry["doi"], opener=opener)
        except Exception as e:
            errors.append(
                "reference %d: crossref lookup for %s failed: %s" % (number, entry["doi"], e)
            )
        else:
            if token_set_similarity(claimed["title"], found["title"]) < SIMILARITY_THRESHOLD:
                errors.append(
                    "reference %d: crossref title does not match (manuscript %r vs crossref %r)"
                    % (number, claimed["title"], found["title"])
                )
            if (
                claimed["year"] is not None
                and found["year"] is not None
                and claimed["year"] != found["year"]
            ):
                errors.append(
                    "reference %d: crossref year does not match (manuscript %s vs crossref %s)"
                    % (number, claimed["year"], found["year"])
                )
            if _normalize_name(claimed["surname"]) != _normalize_name(found["surname"]):
                errors.append(
                    "reference %d: crossref first author does not match "
                    "(manuscript %r vs crossref %r)" % (number, claimed["surname"], found["surname"])
                )
    elif entry.get("arxiv"):
        try:
            found = arxiv_lookup(entry["arxiv"], opener=opener)
        except Exception as e:
            errors.append(
                "reference %d: arxiv lookup for %s failed: %s" % (number, entry["arxiv"], e)
            )
        else:
            if token_set_similarity(claimed["title"], found["title"]) < SIMILARITY_THRESHOLD:
                errors.append(
                    "reference %d: arxiv title does not match (manuscript %r vs arxiv %r)"
                    % (number, claimed["title"], found["title"])
                )
    elif entry.get("url"):
        try:
            status = url_status(entry["url"], opener=opener)
        except Exception as e:
            errors.append("reference %d: url check for %s failed: %s" % (number, entry["url"], e))
        else:
            if status != 200:
                errors.append(
                    "reference %d: url %s answered %s, not 200" % (number, entry["url"], status)
                )
    # isbn: presence only, no lookup API used here.

    return errors


def check(manuscript_text, refs_entries, opener=None):
    opener = opener or _default_opener
    errors = []

    cited_order = body_citation_order(manuscript_text)
    expected_order = list(range(1, len(cited_order) + 1))
    if cited_order != expected_order:
        errors.append(
            "citations are not numbered in order of first citation: found %r, expected %r"
            % (cited_order, expected_order)
        )

    listed = references_list(manuscript_text)
    listed_numbers = [n for n, _text in listed]
    if listed_numbers != list(range(1, len(listed_numbers) + 1)):
        errors.append(
            "References section entries are not numbered 1..N in order: %r" % listed_numbers
        )

    cited_set = set(cited_order)
    listed_set = set(listed_numbers)
    for n in sorted(cited_set - listed_set):
        errors.append("citation [%d] has no entry in the References section" % n)
    for n in sorted(listed_set - cited_set):
        errors.append("References entry [%d] is never cited in the text" % n)

    if len(refs_entries) != len(listed):
        errors.append(
            "refs.jsonl has %d entries but the manuscript lists %d references"
            % (len(refs_entries), len(listed))
        )

    for (number, citation_text), entry in zip(listed, refs_entries):
        errors.extend(check_entry(number, citation_text, entry, opener=opener))

    return errors


def main(argv):
    parser = argparse.ArgumentParser(prog="check_refs.py")
    parser.add_argument("manuscript")
    parser.add_argument("refs")
    args = parser.parse_args(argv[1:])

    manuscript_text = Path(args.manuscript).read_text(encoding="utf-8")
    try:
        refs_entries = load_refs_jsonl(args.refs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    errors = check(manuscript_text, refs_entries)
    if errors:
        for e in errors:
            print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
