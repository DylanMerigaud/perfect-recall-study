import check_numbers


def run(text, tmp_path):
    src = tmp_path / "manuscript.md"
    src.write_text(text, encoding="utf-8")
    return check_numbers.main(["check_numbers.py", str(src)])


def test_clean_prose_passes(tmp_path):
    text = "This is a sentence about a checker with no numbers at all in its prose.\n"
    assert run(text, tmp_path) == 0


def test_stray_digit_in_prose_fails(tmp_path, capsys):
    text = "The tool passed 68 tests before release.\n"
    rc = run(text, tmp_path)
    assert rc == 1
    captured = capsys.readouterr()
    assert "68 tests" in captured.out


def test_digit_inside_placeholder_is_exempt(tmp_path):
    text = "The recall was {{h1.recall}} on n={{h1.n123}}.\n"
    assert run(text, tmp_path) == 0


def test_digit_inside_inline_code_is_exempt(tmp_path):
    text = "Run `grid/run.py --seed 37` to reproduce.\n"
    assert run(text, tmp_path) == 0


def test_digit_inside_fenced_code_is_exempt(tmp_path):
    text = "Some prose.\n\n```\npython3 grid/run.py --seed 37 --cells 36\n```\n\nMore prose.\n"
    assert run(text, tmp_path) == 0


def test_digit_in_references_section_is_exempt(tmp_path):
    text = (
        "# Title\n\n"
        "Some prose with no numbers.\n\n"
        "## References\n\n"
        "[1] A. Author, \"A paper from 2019,\" Venue, 2019.\n"
    )
    assert run(text, tmp_path) == 0


def test_digit_in_about_the_author_section_is_exempt(tmp_path):
    text = (
        "# Title\n\n"
        "Some prose with no numbers.\n\n"
        "## About the author\n\n"
        "Dylan Merigaud has shipped 8 tools since 2026.\n"
    )
    assert run(text, tmp_path) == 0


def test_about_the_author_exemption_does_not_leak_past_its_section(tmp_path, capsys):
    text = (
        "# Title\n\n"
        "## About the author\n\n"
        "Bio text with 8 tools.\n\n"
        "## Limits\n\n"
        "This section claims 42 percent, which is not allowed.\n\n"
        "## References\n\n"
        "[1] X.\n"
    )
    rc = run(text, tmp_path)
    assert rc == 1
    captured = capsys.readouterr()
    assert "42 percent" in captured.out


def test_year_is_allowlisted(tmp_path):
    assert run("The study ran in 2026.\n", tmp_path) == 0


def test_hypothesis_and_protocol_labels_are_allowlisted(tmp_path):
    text = "H3 was supported; P5 crowned the ink sensor; see RQ1 and Table 1 and Figure 1.\n"
    assert run(text, tmp_path) == 0


def test_commit_sha_is_allowlisted(tmp_path):
    text = "The domain rule changed at commit 42732f04021ad899ab83cd760d30c54f8a1cd851.\n"
    assert run(text, tmp_path) == 0


def test_version_tag_is_allowlisted(tmp_path):
    assert run("Measured at v0.2.0.\n", tmp_path) == 0


def test_offending_line_reported_once_even_with_two_stray_digits(tmp_path, capsys):
    text = "This line has 12 and 34 stray digits.\n"
    rc = run(text, tmp_path)
    assert rc == 1
    captured = capsys.readouterr()
    assert len(captured.out.strip().splitlines()) == 1


def test_wrong_arg_count_fails(capsys):
    rc = check_numbers.main(["check_numbers.py"])
    assert rc == 1


def test_digits_inside_an_html_comment_are_exempt(tmp_path):
    text = (
        "Prose with no numbers.\n"
        "<!-- PENDING-CODER2: kappa 0.81 on 14 episodes,\n"
        "a second line with 42 in it -->\n"
        "More prose.\n"
    )
    assert run(text, tmp_path) == 0


def test_digits_after_a_closed_comment_are_still_caught(tmp_path, capsys):
    text = "<!-- slot 1 -->\nThe tool passed 68 tests.\n"
    assert run(text, tmp_path) == 1
    assert "68 tests" in capsys.readouterr().out
