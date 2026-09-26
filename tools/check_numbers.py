#!/usr/bin/env python3
"""Fail if a digit appears in a manuscript's prose outside the exempted regions.

Usage: check_numbers.py SRC

The manuscript's numbers are meant to be written as {{key}} placeholders (see render.py) and
substituted from a numbers registry, never typed by hand: a hand-typed digit is a number that
never went through the registry, which is exactly what this check catches.

Exempted from the check:
- text inside a {{key}} placeholder;
- inline code (`single backtick spans`) and fenced code blocks (```triple backtick blocks```);
- HTML comments (<!-- ... -->), which the rendered page does not show;
- the "References" and "About the author" sections, in full;
- any span matching a pattern in number_allowlist.txt, next to this script (years, form names
  like W-9, section and hypothesis labels like H3 or RQ1, version numbers, commit hashes, and
  similar labels that are not measurements).

Exits 1 and prints one line per offending manuscript line (in order, each line at most once) if
any digit falls outside every exemption. Exits 0 otherwise.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _mdutil  # noqa: E402

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]*\}\}")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
EXEMPT_SECTIONS = ("References", "About the author")
ALLOWLIST_PATH = Path(__file__).resolve().parent / "number_allowlist.txt"


def load_allowlist(path=None):
    path = path or ALLOWLIST_PATH
    patterns = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(re.compile(line))
    return patterns


def _mark(mask, match):
    start, end = match.span()
    for i in range(start, end):
        mask[i] = True


def excluded_mask(text, allowlist):
    mask = [False] * len(text)
    for pattern in (_mdutil.COMMENT_RE, FENCED_CODE_RE, INLINE_CODE_RE, PLACEHOLDER_RE):
        for m in pattern.finditer(text):
            _mark(mask, m)
    for pattern in allowlist:
        for m in pattern.finditer(text):
            _mark(mask, m)
    for title in EXEMPT_SECTIONS:
        found = _mdutil.find_section(text, title)
        if found is not None:
            start, end, _level = found
            for i in range(start, min(end, len(text))):
                mask[i] = True
    return mask


def find_offending_lines(text, allowlist=None):
    if allowlist is None:
        allowlist = load_allowlist()
    mask = excluded_mask(text, allowlist)

    offending = []
    seen_lines = set()
    line_no = 1
    line_start = 0
    for i, ch in enumerate(text):
        if ch == "\n":
            line_no += 1
            line_start = i + 1
            continue
        if ch.isdigit() and not mask[i] and line_no not in seen_lines:
            line_end = text.find("\n", line_start)
            if line_end == -1:
                line_end = len(text)
            offending.append((line_no, text[line_start:line_end].strip()))
            seen_lines.add(line_no)
    return offending


def main(argv):
    if len(argv) != 2:
        print("usage: check_numbers.py SRC", file=sys.stderr)
        return 1

    text = Path(argv[1]).read_text(encoding="utf-8")
    offending = find_offending_lines(text)
    if offending:
        for line_no, line in offending:
            print("line %d: %s" % (line_no, line))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
