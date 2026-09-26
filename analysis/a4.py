"""A4, the targeted foreign-ink run with every shape: per check, per ink level, per shape.

The published targeted run (dossier-preflight grid/target_parasite.py at v0.1.0) drew its ink
shape as `seed % 3`; over seeds 11, 23 and 37 that never drew the first sorted shape (fold). A4
re-ran it with `--all-shapes` (shape index `(seed + cell index) % 3`) and dumped every raw row
(`$AR/a4/readings.jsonl.gz`, 2,592 rows). This module scores those rows with the shipped
thresholds, the way analysis/exhibits.py points_g0 already does for required_field: each check's
shipped setting, abstention off, the check counted as firing when it fires on the row's zone.

    recall       side "variant": the damaged dossier, does the check still catch its defect
    false alarm  side "clean": the clean dossier, same ink at the same place, does it now fire

Counting is separated from scoring (`tally`), so the arithmetic is tested without images.
"""
from collections import defaultdict

LEVELS = (0.0, 0.002, 0.01, 0.04)


def level_tag(level):
    """0.0 -> '0', 0.002 -> '0.002': the suffix of an `at_<level>` key."""
    return "0" if level == 0 else f"{level:g}"


def tally(scored):
    """scored: iterable of (check, level, shape, side, fired).

    Returns {check: {"pooled": {side: {level: [k, n]}},
                     "by_shape": {shape: {side: {level: [k, n]}}}}}.
    Level 0 carries no shape (no ink was laid), so it appears in "pooled" only.
    """
    out = defaultdict(lambda: {"pooled": defaultdict(lambda: defaultdict(lambda: [0, 0])),
                               "by_shape": defaultdict(
                                   lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))})
    for check, level, shape, side, fired in scored:
        c = out[check]
        cell = c["pooled"][side][level]
        cell[0] += bool(fired)
        cell[1] += 1
        if level and shape is not None:
            cell = c["by_shape"][shape][side][level]
            cell[0] += bool(fired)
            cell[1] += 1
    return {ch: {"pooled": {s: dict(v) for s, v in c["pooled"].items()},
                 "by_shape": {sh: {s: dict(v) for s, v in d.items()}
                              for sh, d in c["by_shape"].items()}}
            for ch, c in out.items()}


def scored_rows(rows, ship, ref, thresholds):
    """(check, level, shape, side, fired) per A4 row, at the shipped thresholds."""
    from preflight.checks import evaluate
    from preflight.fixtures import VARIANTS
    from preflight.reading import Reading
    check_of = {v.name: v.check for v in VARIANTS}
    for r in rows:
        check = check_of[r["variant"]]
        reg, _thr = ship[check]
        found = evaluate({r["piece"]: Reading.from_dict(r["reading"])}, ref, "filing", reg,
                         thresholds, checks=[check], abstention=False)
        fired = any(c.fires for c in found if str(c.target) == r["zone"])
        yield check, r["parasite"], r["shape"], r["side"], fired


def compute():
    """The tally for the A4 file on disk, or None when A4 is absent."""
    from analysis import data
    from analysis.hypotheses import shipped
    from preflight.thresholds import load_thresholds
    path, _status = data.arm_status("A4")
    if path is None:
        return None
    ship = shipped()
    th = load_thresholds(data.shipped_thresholds_path())
    ref = data.identities()[data.analyze().DEFAULT_IDENTITY]
    return tally(scored_rows(data.load_lines(path), ship, ref, th))
