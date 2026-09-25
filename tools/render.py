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

Every problem is printed on its own line before exiting.
"""
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([^{}]*)\}\}")


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

    rendered = PLACEHOLDER_RE.sub(replace, src_text)

    if "{{" in rendered or "}}" in rendered:
        for line_no, line in enumerate(rendered.splitlines(), start=1):
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
