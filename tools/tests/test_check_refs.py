import json
import urllib.error
import urllib.request

import pytest

import check_refs


class FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    def read(self):
        return self._data

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def crossref_response(title, year, surname):
    payload = {
        "message": {
            "title": [title],
            "published-print": {"date-parts": [[year]]},
            "author": [{"family": surname, "given": "X"}],
        }
    }
    return FakeResponse(json.dumps(payload).encode("utf-8"))


def arxiv_response(title):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        "<entry><title>%s</title></entry>"
        "</feed>" % title
    )
    return FakeResponse(xml.encode("utf-8"))


def make_opener(responses, forbid_network=True):
    """responses: dict of a substring of the requested url -> FakeResponse or Exception."""

    def opener(request):
        url = request if isinstance(request, str) else request.full_url
        for key, value in responses.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError("no fake response configured for %s (this would hit the network)" % url)

    return opener


DOI_CITATION = '[1] D. Merigaud, "A title about detectors," Venue, 2020.'
ARXIV_CITATION = '[2] A. Author, "An arxiv paper," arXiv, 2021.'
URL_CITATION = '[3] B. Other, "A web reference," Somewhere, 2022.'

MANUSCRIPT = (
    "# Title\n\n"
    "## Abstract\n\nAn abstract.\n\n"
    "## Body\n\n"
    "We build on prior findings [1]. Later work confirms it [2] and points to related "
    "tooling [3].\n\n"
    "## References\n\n"
    + DOI_CITATION
    + "\n"
    + ARXIV_CITATION
    + "\n"
    + URL_CITATION
    + "\n"
)


def make_refs_entries(overrides=None):
    entries = [
        {
            "key": "merigaud2020",
            "doi": "10.1234/abc",
            "citation": DOI_CITATION[4:],
            "supports": "a quoted passage",
            "read_by": "Dylan",
        },
        {
            "key": "author2021",
            "arxiv": "2101.00001",
            "citation": ARXIV_CITATION[4:],
            "supports": "a quoted passage",
            "read_by": "Dylan",
        },
        {
            "key": "other2022",
            "url": "https://example.com/ref3",
            "citation": URL_CITATION[4:],
            "supports": "a quoted passage",
            "read_by": "Dylan",
        },
    ]
    if overrides:
        for i, patch in overrides.items():
            entries[i].update(patch)
    return entries


def default_opener():
    return make_opener(
        {
            "api.crossref.org": crossref_response("A title about detectors", 2020, "Merigaud"),
            "export.arxiv.org": arxiv_response("An arxiv paper"),
            "example.com/ref3": FakeResponse(b"", status=200),
        }
    )


def test_success_all_checks_pass():
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=default_opener())
    assert errors == []


def test_citations_out_of_order_fails():
    bad_manuscript = MANUSCRIPT.replace(
        "We build on prior findings [1]. Later work confirms it [2] and points to related "
        "tooling [3].",
        "We build on prior findings [2]. Later work confirms it [1] and points to related "
        "tooling [3].",
    )
    errors = check_refs.check(bad_manuscript, make_refs_entries(), opener=default_opener())
    assert any("not numbered in order of first citation" in e for e in errors)


def test_citation_with_no_reference_entry_fails():
    manuscript = MANUSCRIPT.replace("tooling [3].", "tooling [4].")
    errors = check_refs.check(manuscript, make_refs_entries(), opener=default_opener())
    assert any("citation [4] has no entry" in e for e in errors)


def test_reference_never_cited_fails():
    manuscript = MANUSCRIPT.replace(
        "We build on prior findings [1]. Later work confirms it [2] and points to related "
        "tooling [3].",
        "We build on prior findings [1]. Later work confirms it [2].",
    )
    errors = check_refs.check(manuscript, make_refs_entries(), opener=default_opener())
    assert any("[3] is never cited" in e for e in errors)


def test_refs_jsonl_count_mismatch_fails():
    entries = make_refs_entries()
    entries.pop()
    errors = check_refs.check(MANUSCRIPT, entries, opener=default_opener())
    assert any("has 2 entries but the manuscript lists 3" in e for e in errors)


def test_missing_supports_fails():
    entries = make_refs_entries({0: {"supports": ""}})
    errors = check_refs.check(MANUSCRIPT, entries, opener=default_opener())
    assert any("has no supports quote" in e for e in errors)


def test_missing_read_by_fails():
    entries = make_refs_entries({0: {"read_by": ""}})
    errors = check_refs.check(MANUSCRIPT, entries, opener=default_opener())
    assert any("has no read_by" in e for e in errors)


def test_entry_with_no_identifier_fails():
    entries = make_refs_entries({0: {"doi": None}})
    errors = check_refs.check(MANUSCRIPT, entries, opener=default_opener())
    assert any("has no doi, arxiv, url or isbn" in e for e in errors)


def test_isbn_only_entry_needs_no_network_call():
    manuscript = (
        "# Title\n\nCites one work [1].\n\n## References\n\n"
        '[1] C. Author, "A book about detectors," Publisher, 2020.\n'
    )
    entries = [
        {
            "key": "book2020",
            "isbn": "978-1-234-56789-0",
            "citation": 'C. Author, "A book about detectors," Publisher, 2020.',
            "supports": "a quoted passage",
            "read_by": "Dylan",
        }
    ]

    def opener(_request):
        raise AssertionError("isbn entries must not trigger a network call")

    errors = check_refs.check(manuscript, entries, opener=opener)
    assert errors == []


def test_doi_title_mismatch_fails():
    opener = make_opener(
        {
            "api.crossref.org": crossref_response("A completely different title", 2020, "Merigaud"),
            "export.arxiv.org": arxiv_response("An arxiv paper"),
            "example.com/ref3": FakeResponse(b"", status=200),
        }
    )
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("crossref title does not match" in e for e in errors)


def test_doi_year_mismatch_fails():
    opener = make_opener(
        {
            "api.crossref.org": crossref_response("A title about detectors", 1999, "Merigaud"),
            "export.arxiv.org": arxiv_response("An arxiv paper"),
            "example.com/ref3": FakeResponse(b"", status=200),
        }
    )
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("crossref year does not match" in e for e in errors)


def test_doi_surname_mismatch_fails():
    opener = make_opener(
        {
            "api.crossref.org": crossref_response("A title about detectors", 2020, "SomeoneElse"),
            "export.arxiv.org": arxiv_response("An arxiv paper"),
            "example.com/ref3": FakeResponse(b"", status=200),
        }
    )
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("crossref first author does not match" in e for e in errors)


def test_arxiv_title_mismatch_fails():
    opener = make_opener(
        {
            "api.crossref.org": crossref_response("A title about detectors", 2020, "Merigaud"),
            "export.arxiv.org": arxiv_response("A totally unrelated arxiv title"),
            "example.com/ref3": FakeResponse(b"", status=200),
        }
    )
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("arxiv title does not match" in e for e in errors)


def test_url_not_200_fails():
    opener = make_opener(
        {
            "api.crossref.org": crossref_response("A title about detectors", 2020, "Merigaud"),
            "export.arxiv.org": arxiv_response("An arxiv paper"),
            "example.com/ref3": FakeResponse(b"", status=404),
        }
    )
    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("answered 404, not 200" in e for e in errors)


def test_url_http_error_is_reported_by_status_code():
    def opener(request):
        url = request if isinstance(request, str) else request.full_url
        if "api.crossref.org" in url:
            return crossref_response("A title about detectors", 2020, "Merigaud")
        if "export.arxiv.org" in url:
            return arxiv_response("An arxiv paper")
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("answered 404, not 200" in e for e in errors)


def test_lookup_exception_is_reported_not_raised():
    def opener(request):
        url = request if isinstance(request, str) else request.full_url
        if "api.crossref.org" in url:
            raise OSError("network unreachable")
        if "export.arxiv.org" in url:
            return arxiv_response("An arxiv paper")
        return FakeResponse(b"", status=200)

    errors = check_refs.check(MANUSCRIPT, make_refs_entries(), opener=opener)
    assert any("crossref lookup for" in e and "failed" in e for e in errors)


def test_token_set_similarity_exact_match():
    assert check_refs.token_set_similarity("A Title", "a title") == 1.0


def test_token_set_similarity_no_overlap():
    assert check_refs.token_set_similarity("A Title", "Something Else") == 0.0


def test_parse_citation_text_extracts_title_year_surname():
    parsed = check_refs.parse_citation_text(
        'D. Merigaud, "A title about detectors," Venue, 2020.'
    )
    assert parsed["title"] == "A title about detectors"
    assert parsed["year"] == 2020
    assert parsed["surname"] == "Merigaud"


def test_main_end_to_end_with_network_forbidden(tmp_path, monkeypatch):
    manuscript_path = tmp_path / "manuscript.md"
    manuscript_path.write_text(MANUSCRIPT, encoding="utf-8")
    refs_path = tmp_path / "refs.jsonl"
    refs_path.write_text(
        "\n".join(json.dumps(e) for e in make_refs_entries()) + "\n", encoding="utf-8"
    )

    monkeypatch.setattr(check_refs, "_default_opener", default_opener())

    def forbidden(*args, **kwargs):
        raise AssertionError("urlopen must not be called directly in tests")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)

    rc = check_refs.main(["check_refs.py", str(manuscript_path), str(refs_path)])
    assert rc == 0


def test_main_reports_multiple_failures_at_once(tmp_path, monkeypatch, capsys):
    manuscript_path = tmp_path / "manuscript.md"
    manuscript_path.write_text(MANUSCRIPT, encoding="utf-8")
    refs_path = tmp_path / "refs.jsonl"
    entries = make_refs_entries({0: {"supports": ""}, 1: {"read_by": ""}})
    refs_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    monkeypatch.setattr(check_refs, "_default_opener", default_opener())

    rc = check_refs.main(["check_refs.py", str(manuscript_path), str(refs_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "has no supports quote" in out
    assert "has no read_by" in out


def test_refs_jsonl_with_invalid_json_line_fails(tmp_path, capsys):
    manuscript_path = tmp_path / "manuscript.md"
    manuscript_path.write_text(MANUSCRIPT, encoding="utf-8")
    refs_path = tmp_path / "refs.jsonl"
    refs_path.write_text("{not valid json\n", encoding="utf-8")

    rc = check_refs.main(["check_refs.py", str(manuscript_path), str(refs_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "not valid JSON" in captured.err
