"""Small markdown heading-section helpers shared by the manuscript tools.

Not a tool on its own: check_numbers.py, wordcount.py and check_refs.py import it. Every tool
script adds its own directory to sys.path before importing it, so this works whether a tool is
run directly (python3 tools/check_numbers.py ...) or imported from a test.
"""
import re

_HEADING_RE = re.compile(r"^(#+)\s+(.*?)\s*$", re.MULTILINE)


def headings(text):
    """Yield (level, title, start, end) for every ATX heading line in text.

    `start` is the index of the '#' character; `end` is the index right after the heading
    line's trailing newline (or end of text for the last line).
    """
    for m in _HEADING_RE.finditer(text):
        end = m.end()
        if end < len(text) and text[end] == "\n":
            end += 1
        yield len(m.group(1)), m.group(2).strip(), m.start(), end


def find_section(text, title, case_insensitive=True):
    """Return (start, end, level) of the section headed exactly `title`, or None.

    `start` is the index of the heading line itself. `end` is the index of the next heading at
    the same level or shallower, or len(text) if none follows: the whole section, heading
    included, is text[start:end].
    """
    target = title.strip().lower() if case_insensitive else title.strip()
    all_headings = list(headings(text))
    for i, (level, htitle, start, _hend) in enumerate(all_headings):
        compared = htitle.lower() if case_insensitive else htitle
        if compared == target:
            end = len(text)
            for later_level, _t, later_start, _e in all_headings[i + 1:]:
                if later_level <= level:
                    end = later_start
                    break
            return start, end, level
    return None


def section_body(text, title, case_insensitive=True):
    """Return the section's content, excluding its own heading line, or None if absent."""
    found = find_section(text, title, case_insensitive=case_insensitive)
    if found is None:
        return None
    start, end, _level = found
    body_start = start
    for _level2, _title2, hstart, hend in headings(text):
        if hstart == start:
            body_start = hend
            break
    return text[body_start:end]


def strip_section(text, title, case_insensitive=True):
    """Return text with the whole section (its heading included) removed."""
    found = find_section(text, title, case_insensitive=case_insensitive)
    if found is None:
        return text
    start, end, _level = found
    return text[:start] + text[end:]
