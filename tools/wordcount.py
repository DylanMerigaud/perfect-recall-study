#!/usr/bin/env python3
"""Count a manuscript against a venue's word, abstract and reference limits.

Usage: wordcount.py OUT [--limit N] [--abstract N] [--max-refs N]

Body count: whitespace-separated tokens of everything before the "## References" heading,
excluding the "About the author" section, excluding markdown pipe table rows (lines that start
and end with "|") and figure image lines (a line that is only a markdown image), excluding table
and figure caption lines (a line starting with "**Table n." or "**Figure n."), then adding a flat
250 words for every such caption found: the venue's own per-exhibit word charge, applied instead
of counting the caption's or the table's or the figure's own words.

Abstract count: whitespace tokens of the "## Abstract" section if the manuscript has one,
otherwise of the first paragraph following the document's title (its first "# " heading).

Reference count: the number of "[n]" entries in the "## References" section.

HTML comments (<!-- ... -->) are removed before any count: the rendered page does not show them.

Prints all three counts (each against its limit) and exits 1 if any of them is exceeded, 0
otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _mdutil  # noqa: E402

CAPTION_RE = re.compile(r"^\*\*(?:Table|Figure)\s+\d+\.")
IMAGE_LINE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
REFERENCE_ENTRY_RE = re.compile(r"^\[\d+\]")
TITLE_LINE_RE = re.compile(r"^#\s+\S")
TABLE_FIGURE_WORD_CHARGE = 250


def _body_text(text):
    refs = _mdutil.find_section(text, "References")
    body = text[: refs[0]] if refs is not None else text
    return _mdutil.strip_section(body, "About the author")


def body_word_count(text):
    """Return (total_words, caption_count)."""
    body = _body_text(_mdutil.strip_comments(text))
    words = 0
    captions = 0
    for line in body.splitlines():
        if TABLE_LINE_RE.match(line) or IMAGE_LINE_RE.match(line):
            continue
        if CAPTION_RE.match(line.strip()):
            captions += 1
            continue
        words += len(line.split())
    return words + captions * TABLE_FIGURE_WORD_CHARGE, captions


def _first_paragraph_after_title(text):
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if TITLE_LINE_RE.match(line):
            start = i + 1
            break
    i = start
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    para = []
    while i < len(lines) and lines[i].strip() != "" and not lines[i].lstrip().startswith("#"):
        para.append(lines[i])
        i += 1
    return "\n".join(para)


def abstract_word_count(text):
    text = _mdutil.strip_comments(text)
    abstract = _mdutil.section_body(text, "Abstract")
    if abstract is None:
        abstract = _first_paragraph_after_title(text)
    return len(abstract.split())


def reference_count(text):
    text = _mdutil.strip_comments(text)
    refs_body = _mdutil.section_body(text, "References")
    if refs_body is None:
        return 0
    return sum(1 for line in refs_body.splitlines() if REFERENCE_ENTRY_RE.match(line.strip()))


def main(argv):
    parser = argparse.ArgumentParser(prog="wordcount.py")
    parser.add_argument("manuscript")
    parser.add_argument("--limit", type=int, default=4200)
    parser.add_argument("--abstract", type=int, default=150)
    parser.add_argument("--max-refs", type=int, default=15)
    args = parser.parse_args(argv[1:])

    text = Path(args.manuscript).read_text(encoding="utf-8")
    body_words, captions = body_word_count(text)
    abstract_words = abstract_word_count(text)
    refs = reference_count(text)

    print(
        "body: %d words (limit %d), %d table/figure caption(s) charged at %d words each"
        % (body_words, args.limit, captions, TABLE_FIGURE_WORD_CHARGE)
    )
    print("abstract: %d words (limit %d)" % (abstract_words, args.abstract))
    print("references: %d (limit %d)" % (refs, args.max_refs))

    exceeded = body_words > args.limit or abstract_words > args.abstract or refs > args.max_refs
    return 1 if exceeded else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
