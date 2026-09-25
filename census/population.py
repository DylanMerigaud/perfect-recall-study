#!/usr/bin/env python3
"""Compute the census population from the account, never from memory.

Runs `gh repo list DylanMerigaud --limit 300 --json name,visibility,isFork,createdAt`,
filters to public, non-fork repositories created on or after 2026-01-01 (the population
rule of PREREG.md, section "The census design"), then applies the inclusion rule: a repo
is IN if it holds (a) a self-generated score (tests passing, a synthetic or planted
benchmark, an LLM-judged or script-graded suite) AND (b) an independent check of the same
system (a real-world input the author did not generate, a human judgment, an arithmetic
or specification oracle, a third party's verdict), with numbers of both present in files
committed at a pinned commit.

Whether a given repository satisfies that rule cannot be read off the `gh repo list`
metadata: it requires reading the repository's own files at a pinned commit. That reading
was done by hand for every candidate this script lists (shallow clone, grep, line-level
verification of every cited number; see cases.yaml for the resulting evidence and
../../docs/PLAN-PAPER-2026-09-25.md T17 for the method). RESEARCHED_DECISIONS below
records that reading's outcome and its reason, keyed by repo name, so a re-run of this
script reproduces the same population.csv without re-reading every repository by hand
every time. A repository with no entry in RESEARCHED_DECISIONS is refused: this script
never guesses an inclusion, it exits with an error naming the repo that needs a manual
read first.

Usage: python3 census/population.py [--out census/population.csv]
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OWNER = "DylanMerigaud"
POPULATION_FLOOR = datetime(2026, 1, 1, tzinfo=timezone.utc)

# One entry per repository this script has already read by hand at a pinned commit.
# include=True repos also have episodes recorded in census/cases.yaml with the exact
# file, line and quote for each self-generated and independent-check number.
RESEARCHED_DECISIONS = {
    "dossier-preflight": (
        True,
        "self-generated: grid/results/resume.json (8 of 9 checks hold validation.recall "
        "1.0 on the held-out seed; forbidden_value is the exception at 0.9965277777777778). "
        "independent: parasitic-ink-probe/FINDING.md (ink sensor false negatives 1.000, "
        "n=151) and grid/results/target_parasite.json (0 of 81 fired at 1% added ink). "
        "See cases.yaml.",
    ),
    "airlock": (
        True,
        "self-generated: eval/EVAL.md per-gate table, 100% status precision and recall "
        "across the 16-asset run (10 real archival ads plus 6 synthetic assets, not 16 "
        "synthetic assets as an earlier draft table said; corrected here). independent: "
        "eval/EVAL.md brand-naming accuracy on the 10 real spots (4 of 10 named, 6 of 10 "
        "wrong company), which the coarse BLOCK status hid. See cases.yaml.",
    ),
    "fintech-roast": (
        True,
        "self-generated: eval/RESULTS.md (recall 30/35, genuine-defect precision 53/53, "
        "adversarial pass refuted 0 of 53). independent: eval/FIELD-REPORT-2.md, a scoped "
        "audit of medusajs/medusa at a pinned commit (16 findings, 4 confirmed, 2 likely, "
        "10 refuted), plus upstream medusajs/medusa#16012 labelled a bug and closed by a "
        "third-party PR #16097 merged 2026-07-22 (verified live via gh api). See cases.yaml.",
    ),
    "trimwrit": (
        True,
        "self-generated: CHANGELOG.md (an injection run reported 32 of 32 resisted) and "
        "README.md (ablation 1.00/1.00 at n=3 per arm on the em-dash case). independent: "
        "the same CHANGELOG.md passage records every regex grader was dead during that "
        "run; CHANGELOG.md separately records the baseline arm was contaminated by the "
        "global CLAUDE.md (em-dash case read 1.00 with, 0.00 without, after the fix); "
        "README.md records the LLM judge failing 4 of 4 runs the mechanical grader passed. "
        "See cases.yaml.",
    ),
    "blazonry": (
        True,
        "self-generated: README.md (59 tests, no network, all passing). independent: "
        "scripts/gate.mjs code comment records 13 of 14 marks Dylan rejected by hand still "
        "pass the `density` check and 12 of 14 pass `construction`, because the thresholds "
        "were inflated by wordmark contamination. See cases.yaml.",
    ),
    "bankfile": (
        True,
        "self-generated: README.md (551 tests, 98% coverage, 18 documented bank "
        "deviations). independent: README.md and CHANGELOG.md, arithmetic balance check "
        "on the vendored real MT940 corpus (54 real statement files per "
        "tests/fixtures/mt940/README.md, copied from wolph/mt940's own test suite) found a "
        "reversed-credit bug no test caught; CHANGELOG.md records the SWIFT spec (DFUe "
        "Abkommen Anlage 3) found a ?31 field-mapping bug on 59 transactions across 5 "
        "files. Cited only at commits after 397f922 (the redaction commit); commit 8ba571f "
        "is never cited or linked. See cases.yaml and the T17 report for the upstream "
        "check on the one statement that commit touched.",
    ),
    "nameproof": (
        True,
        "self-generated: docs/AUDIT-2026-08-25.md (test suite 60 to 93 to 109 passing, "
        "none removed). independent: README.md `doctor` calibration against live search "
        "results, 12 of 12 agreed, and re-introducing each of the six shipped wrong "
        "answers into a scratch copy makes doctor catch it (three reinsertions shown, all "
        "CAUGHT). This is the one included repo where the independent check AGREES with "
        "the self-generated score rather than contradicting it (codebook M0). See "
        "cases.yaml.",
    ),
    "dsh-internals": (
        True,
        "self-generated: METHOD.md (\"270 valid, 0 invalid\" citations; the validator only "
        "checks the file exists and the cited line is in range, an existence-only check). "
        "independent: METHOD.md, 6 load-bearing claims re-derived by hand from the "
        "session, 3 corrections applied. See cases.yaml.",
    ),
    "ai-invoice-parser": (
        False,
        "no independent check: eval/results.json reports 95/95 fields and anomaly F1 1.0 "
        "on 9 self-generated synthetic invoices only; no real-world audit, human label or "
        "external oracle with numbers is committed anywhere in the repo.",
    ),
    "ledgerloop": (
        False,
        "self-generated score only: commit 44f3174's message reports \"Live eval: 11/11\"; "
        "no independent check is committed (the eval/ directory holds only the harness "
        "that produces the self-generated score, no field report, no results file scored "
        "against a real-world or human-labelled source).",
    ),
    "approvals-ui": (
        False,
        "unit tests only; no eval, field report or independent-check artifact of any kind "
        "found in the repository.",
    ),
    "react-flow-auto-layout": (
        False,
        "unit tests only; no eval, field report or independent-check artifact of any kind "
        "found in the repository.",
    ),
    "merigaud.com": (
        False,
        "unit tests only; no eval, field report or independent-check artifact of any kind "
        "found in the repository.",
    ),
    "config": (
        False,
        "shared ESLint/Prettier/TypeScript config package; unit tests only for its own "
        "custom lint rules, no self-generated benchmark and no independent check.",
    ),
    "perfect-recall-study": (
        False,
        "this study's own repository, not a candidate tool: created 2026-09-25, after the "
        "population was drawn for this census; holds no self-generated score or "
        "independent check of a system under test.",
    ),
}


def fetch_repos() -> list[dict]:
    result = subprocess.run(
        [
            "gh",
            "repo",
            "list",
            OWNER,
            "--limit",
            "300",
            "--json",
            "name,visibility,isFork,createdAt",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def in_population(repo: dict) -> bool:
    if repo["visibility"] != "PUBLIC":
        return False
    if repo["isFork"]:
        return False
    created = datetime.strptime(repo["createdAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return created >= POPULATION_FLOOR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "population.csv"),
        help="output CSV path",
    )
    args = parser.parse_args()

    repos = fetch_repos()
    candidates = [r for r in repos if in_population(r)]
    candidates.sort(key=lambda r: r["createdAt"])

    rows = []
    missing = []
    for repo in candidates:
        name = repo["name"]
        if name not in RESEARCHED_DECISIONS:
            missing.append(name)
            continue
        include, reason = RESEARCHED_DECISIONS[name]
        rows.append(
            {
                "name": name,
                "created_at": repo["createdAt"],
                "include": "true" if include else "false",
                "reason": reason,
            }
        )

    if missing:
        print(
            "population.py: no researched decision for: " + ", ".join(missing),
            file=sys.stderr,
        )
        print(
            "Read the repository at its pinned commit and add an entry to "
            "RESEARCHED_DECISIONS before this script can include it in the population.",
            file=sys.stderr,
        )
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "created_at", "include", "reason"])
        writer.writeheader()
        writer.writerows(rows)

    included = sum(1 for r in rows if r["include"] == "true")
    print(f"wrote {len(rows)} candidates to {out_path} ({included} included)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
