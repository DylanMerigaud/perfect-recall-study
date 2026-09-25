#!/usr/bin/env python3
"""Verify every quote in cases.yaml is real: present in the cited repo, at its
pinned sha, within 3 lines of the cited line number.

For each repo in cases.yaml, shallow-clones it at its recorded sha into a temp
directory, then for every episode's self_generated and independent_check
entries, opens the cited file and asserts the quote string appears on a line
within +/-3 of the cited line number. An "external" entry (a fact outside the
repository, such as a live GitHub issue or PR) is skipped and reported, never
silently passed: this script does not re-verify a live API fact, only a
committed file at a pinned commit.

Exits 1 on any miss (missing repo, missing sha, missing file, or a quote not
found near its cited line). Exits 0 only when every non-external quote in
every episode of every repo was found.

Usage: python3 census/verify.py [cases.yaml]
"""

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("verify.py: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

LINE_TOLERANCE = 3


def shallow_clone(repo: str, sha: str, dest: Path) -> bool:
    url = f"https://github.com/DylanMerigaud/{repo}.git"
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(
        ["git", "-C", str(dest), "remote", "add", "origin", url],
        check=True,
    )
    fetch = subprocess.run(
        ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", sha],
        capture_output=True,
        text=True,
    )
    if fetch.returncode != 0:
        # Some servers refuse a fetch by raw sha when it is not advertised; fall
        # back to a full clone and checkout, still shallow of history depth.
        clone = subprocess.run(
            ["git", "clone", "-q", url, str(dest / "_full")],
            capture_output=True,
            text=True,
        )
        if clone.returncode != 0:
            print(f"  clone failed: {clone.stderr.strip()}", file=sys.stderr)
            return False
        checkout = subprocess.run(
            ["git", "-C", str(dest / "_full"), "checkout", "-q", sha],
            capture_output=True,
            text=True,
        )
        if checkout.returncode != 0:
            print(f"  checkout failed: {checkout.stderr.strip()}", file=sys.stderr)
            return False
        for item in (dest / "_full").iterdir():
            item.rename(dest / item.name)
        return True
    checkout = subprocess.run(
        ["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"],
        capture_output=True,
        text=True,
    )
    if checkout.returncode != 0:
        print(f"  checkout failed: {checkout.stderr.strip()}", file=sys.stderr)
        return False
    return True


def check_quote(repo_dir: Path, entry: dict) -> tuple[bool, str]:
    if "external" in entry:
        return True, f"SKIPPED (external fact: {entry['external']})"
    file_rel = entry["file"]
    line_no = entry["line"]
    quote = entry["quote"]
    target = repo_dir / file_rel
    if not target.exists():
        return False, f"file not found: {file_rel}"
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return False, f"could not read {file_rel}: {e}"
    lo = max(1, line_no - LINE_TOLERANCE)
    hi = min(len(lines), line_no + LINE_TOLERANCE)
    window = lines[lo - 1 : hi]
    for offset, text in enumerate(window, start=lo):
        if quote in text:
            return True, f"found at {file_rel}:{offset} (cited {line_no})"
    return False, f"quote not found within {LINE_TOLERANCE} lines of {file_rel}:{line_no}"


def main() -> int:
    cases_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "cases.yaml"
    if not cases_path.exists():
        print(f"verify.py: {cases_path} does not exist", file=sys.stderr)
        return 1

    data = yaml.safe_load(cases_path.read_text(encoding="utf-8"))
    repos = data.get("repos", [])
    if not repos:
        print("verify.py: no repos in cases.yaml", file=sys.stderr)
        return 1

    total = 0
    failed = 0
    skipped = 0

    with tempfile.TemporaryDirectory(prefix="census-verify-") as tmp:
        tmp_path = Path(tmp)
        for repo_entry in repos:
            repo = repo_entry["repo"]
            sha = repo_entry["sha"]
            dest = tmp_path / repo
            dest.mkdir(parents=True, exist_ok=True)
            print(f"== {repo} @ {sha}")
            ok = shallow_clone(repo, sha, dest)
            if not ok:
                print(f"  FAIL: could not check out {repo}@{sha}", file=sys.stderr)
                failed += 1
                continue
            for episode in repo_entry.get("episodes", []):
                eid = episode["id"]
                for kind in ("self_generated", "independent_check"):
                    for entry in episode.get(kind, []):
                        total += 1
                        passed, detail = check_quote(dest, entry)
                        if "SKIPPED" in detail:
                            skipped += 1
                            print(f"  [{eid}] {kind}: {detail}")
                            continue
                        if passed:
                            print(f"  [{eid}] {kind}: OK, {detail}")
                        else:
                            failed += 1
                            print(f"  [{eid}] {kind}: MISS, {detail}", file=sys.stderr)

    print(f"\n{total} quotes checked, {skipped} skipped (external), {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
