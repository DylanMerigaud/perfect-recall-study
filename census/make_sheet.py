#!/usr/bin/env python3
"""Build census/sheet.csv from census/cases.yaml.

One row per episode. Columns: episode_id, repo, pinned_sha, tier, who,
self_generated_claim, independent_finding, note, code1, code2.

self_generated_claim and independent_finding hold the exact evidence quotes
from cases.yaml, each tagged with its file and line, or with "external" and
no line for a live fact outside the repository (fintech-roast-02); multiple
entries for the same episode are joined with " | ". The episode's own prose
"claim" field in cases.yaml is deliberately left out: coders see the raw
quotes only, not the narrative framing built around them.

note carries the episode's note field verbatim when cases.yaml has one, and
is empty otherwise. code1 and code2 start empty, for a coder to fill.

Run: python3 census/make_sheet.py
"""
import csv
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent
CASES = ROOT / "cases.yaml"
SHEET = ROOT / "sheet.csv"

FIELDS = [
    "episode_id",
    "repo",
    "pinned_sha",
    "tier",
    "who",
    "self_generated_claim",
    "independent_finding",
    "note",
    "code1",
    "code2",
]


def format_entries(entries):
    parts = []
    for entry in entries:
        quote = entry["quote"]
        if entry.get("file") is not None:
            loc = f"{entry['file']}:{entry['line']}"
        else:
            loc = f"external:{entry['external']}"
        parts.append(f"{quote} ({loc})")
    return " | ".join(parts)


def build_rows(data):
    rows = []
    for repo in data["repos"]:
        for ep in repo["episodes"]:
            rows.append(
                {
                    "episode_id": ep["id"],
                    "repo": repo["repo"],
                    "pinned_sha": repo["sha"],
                    "tier": ep["tier"],
                    "who": ep["who"],
                    "self_generated_claim": format_entries(ep["self_generated"]),
                    "independent_finding": format_entries(ep["independent_check"]),
                    "note": ep.get("note") or "",
                    "code1": "",
                    "code2": "",
                }
            )
    return rows


def main():
    data = yaml.safe_load(CASES.read_text())
    rows = build_rows(data)
    with SHEET.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {SHEET}")


if __name__ == "__main__":
    main()
