import json

import render


def test_success_substitutes_every_key(tmp_path):
    src = tmp_path / "manuscript.src.md"
    src.write_text("Recall was {{h1.recall}} on n={{h1.n}}.\n", encoding="utf-8")
    numbers = tmp_path / "numbers.json"
    numbers.write_text(
        json.dumps({"h1.recall": {"text": "0.000"}, "h1.n": {"text": "151"}}),
        encoding="utf-8",
    )
    out = tmp_path / "manuscript.md"

    rc = render.main(["render.py", str(src), str(numbers), str(out)])

    assert rc == 0
    assert out.read_text(encoding="utf-8") == "Recall was 0.000 on n=151.\n"


def test_unknown_key_fails_and_writes_nothing(tmp_path, capsys):
    src = tmp_path / "manuscript.src.md"
    src.write_text("Recall was {{h1.recall}}.\n", encoding="utf-8")
    numbers = tmp_path / "numbers.json"
    numbers.write_text(json.dumps({}), encoding="utf-8")
    out = tmp_path / "manuscript.md"

    rc = render.main(["render.py", str(src), str(numbers), str(out)])

    assert rc == 1
    assert not out.exists()
    captured = capsys.readouterr()
    assert "unknown key: h1.recall" in captured.err


def test_entry_with_no_text_field_is_unknown(tmp_path):
    src = tmp_path / "manuscript.src.md"
    src.write_text("Value {{x}}.\n", encoding="utf-8")
    numbers = tmp_path / "numbers.json"
    numbers.write_text(json.dumps({"x": {"value": 1}}), encoding="utf-8")
    out = tmp_path / "manuscript.md"

    rc = render.main(["render.py", str(src), str(numbers), str(out)])

    assert rc == 1
    assert not out.exists()


def test_leftover_nested_brace_fails(tmp_path, capsys):
    src = tmp_path / "manuscript.src.md"
    src.write_text("Broken {{{{x}}}}.\n", encoding="utf-8")
    numbers = tmp_path / "numbers.json"
    numbers.write_text(json.dumps({"x": {"text": "1"}}), encoding="utf-8")
    out = tmp_path / "manuscript.md"

    rc = render.main(["render.py", str(src), str(numbers), str(out)])

    assert rc == 1
    assert not out.exists()
    captured = capsys.readouterr()
    assert "leftover brace" in captured.err


def test_unmatched_open_brace_fails(tmp_path):
    src = tmp_path / "manuscript.src.md"
    src.write_text("Unclosed {{x here.\n", encoding="utf-8")
    numbers = tmp_path / "numbers.json"
    numbers.write_text(json.dumps({}), encoding="utf-8")
    out = tmp_path / "manuscript.md"

    rc = render.main(["render.py", str(src), str(numbers), str(out)])

    assert rc == 1
    assert not out.exists()


def test_wrong_arg_count_fails(capsys):
    rc = render.main(["render.py", "only-one-arg"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "usage" in captured.err
