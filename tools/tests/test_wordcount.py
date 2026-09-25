import wordcount


def test_success_reports_all_three_counts_and_exits_0(tmp_path, capsys):
    title_line = "# Title"
    abstract_heading = "## Abstract"
    abstract_para = "Short abstract paragraph with five words here."
    body_heading = "## Body"
    body_para = "Prose paragraph with exactly six words total."
    references_heading = "## References"
    ref1 = '[1] A. Author, "Title," Venue, 2020.'
    ref2 = '[2] B. Author, "Other," Venue, 2021.'

    text = (
        "\n\n".join(
            [
                title_line,
                abstract_heading,
                abstract_para,
                body_heading,
                body_para,
                references_heading,
                ref1 + "\n" + ref2,
            ]
        )
        + "\n"
    )

    expected_body_words = sum(
        len(s.split()) for s in (title_line, abstract_heading, abstract_para, body_heading, body_para)
    )
    expected_abstract_words = len(abstract_para.split())

    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "1000", "--abstract", "50", "--max-refs", "10"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "body: %d words" % expected_body_words in out
    assert "abstract: %d words" % expected_abstract_words in out
    assert "references: 2" in out


def test_body_limit_exceeded_fails(tmp_path):
    body = " ".join(["word"] * 50)
    text = "# Title\n\n%s\n\n## References\n\n[1] X.\n" % body
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "10", "--abstract", "150", "--max-refs", "15"]
    )
    assert rc == 1


def test_abstract_limit_exceeded_fails(tmp_path):
    abstract = " ".join(["word"] * 20)
    text = "# Title\n\n## Abstract\n\n%s\n\n## References\n\n[1] X.\n" % abstract
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "1000", "--abstract", "5", "--max-refs", "15"]
    )
    assert rc == 1


def test_max_refs_exceeded_fails(tmp_path):
    refs = "\n".join('[%d] Reference number %d.' % (i, i) for i in range(1, 6))
    text = "# Title\n\nSome prose.\n\n## References\n\n%s\n" % refs
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "1000", "--abstract", "150", "--max-refs", "3"]
    )
    assert rc == 1


def test_table_and_figure_blocks_are_excluded_and_captions_charged(tmp_path, capsys):
    prose = "A short sentence of prose."
    table = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    table_caption = "**Table 1. A small table.**"
    figure = "![alt text](figure1.png)"
    figure_caption = "**Figure 1. A small figure.**"

    text = (
        "# Title\n\n"
        + prose
        + "\n\n"
        + table
        + "\n\n"
        + table_caption
        + "\n\n"
        + figure
        + "\n\n"
        + figure_caption
        + "\n\n## References\n\n[1] X.\n"
    )
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    title_words = len("# Title".split())
    prose_words = len(prose.split())
    expected_body_words = title_words + prose_words + 2 * 250

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "10000", "--abstract", "150", "--max-refs", "15"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "body: %d words" % expected_body_words in out
    assert "2 table/figure caption(s)" in out


def test_about_the_author_section_excluded_from_body_count(tmp_path, capsys):
    prose = "A short sentence of prose."
    bio = " ".join(["biography"] * 40)
    text = (
        "# Title\n\n"
        + prose
        + "\n\n## About the author\n\n"
        + bio
        + "\n\n## References\n\n[1] X.\n"
    )
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    title_words = len("# Title".split())
    prose_words = len(prose.split())

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "10000", "--abstract", "150", "--max-refs", "15"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "body: %d words" % (title_words + prose_words) in out


def test_content_after_references_excluded_from_body_count(tmp_path, capsys):
    prose = "A short sentence of prose."
    text = "# Title\n\n" + prose + "\n\n## References\n\n[1] X.\n\n## About the author\n\n" + (
        " ".join(["biography"] * 40)
    )
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    title_words = len("# Title".split())
    prose_words = len(prose.split())

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "10000", "--abstract", "150", "--max-refs", "15"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "body: %d words" % (title_words + prose_words) in out


def test_abstract_fallback_is_first_paragraph_after_title(tmp_path, capsys):
    first_para = "This is the abstract by position, not by heading."
    text = "# Title\n\n" + first_para + "\n\n## Body\n\nMore prose here.\n\n## References\n\n[1] X.\n"
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")

    rc = wordcount.main(
        ["wordcount.py", str(manuscript), "--limit", "10000", "--abstract", "150", "--max-refs", "15"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "abstract: %d words" % len(first_para.split()) in out


def test_wrong_manuscript_path_raises(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        wordcount.main(["wordcount.py", str(tmp_path / "missing.md")])
