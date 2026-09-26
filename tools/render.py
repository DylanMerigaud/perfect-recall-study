#!/usr/bin/env python3
"""Substitute {{key}} placeholders in a manuscript source with values from a numbers registry.

Usage: render.py SRC NUMBERS OUT

SRC is a manuscript source file whose numbers are written as {{key}} placeholders, never as
literal digits. NUMBERS is a JSON file mapping each key to an object carrying at least a "text"
field, the exact string to substitute (results/numbers.json in this repository). OUT is where the
rendered manuscript is written.

Exits 1 and writes nothing to OUT if:
- a {{key}} placeholder has no matching entry in NUMBERS, or the entry has no "text" field;
- a "{{" or "}}" is left in the rendered text (a malformed or unresolved placeholder, for
  example nested braces).

Text inside HTML comments (<!-- ... -->) is left exactly as written: no substitution, no
brace check. A comment holds text that is not true yet (a paragraph waiting for results whose
keys do not exist yet), and the rendered page does not show it.

Every problem is printed on its own line before exiting.
"""
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([^{}]*)\}\}")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def render(src_text, numbers):
    """Return (rendered_text, errors). errors is empty on success."""
    errors = []

    def replace(match):
        key = match.group(1).strip()
        if not key:
            errors.append("empty placeholder: {{}}")
            return match.group(0)
        entry = numbers.get(key)
        if entry is None or "text" not in entry:
            errors.append("unknown key: %s" % key)
            return match.group(0)
        return str(entry["text"])

    pieces = []
    last = 0
    for m in COMMENT_RE.finditer(src_text):
        pieces.append(PLACEHOLDER_RE.sub(replace, src_text[last:m.start()]))
        pieces.append(m.group(0))
        last = m.end()
    pieces.append(PLACEHOLDER_RE.sub(replace, src_text[last:]))
    rendered = "".join(pieces)

    visible = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), rendered)
    if "{{" in visible or "}}" in visible:
        for line_no, line in enumerate(visible.splitlines(), start=1):
            if "{{" in line or "}}" in line:
                errors.append("leftover brace on line %d: %s" % (line_no, line.strip()))

    return rendered, errors


def main(argv):
    if len(argv) != 4:
        print("usage: render.py SRC NUMBERS OUT", file=sys.stderr)
        return 1
    src_path, numbers_path, out_path = argv[1], argv[2], argv[3]

    src_text = Path(src_path).read_text(encoding="utf-8")
    numbers = json.loads(Path(numbers_path).read_text(encoding="utf-8"))

    rendered, errors = render(src_text, numbers)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    Path(out_path).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
