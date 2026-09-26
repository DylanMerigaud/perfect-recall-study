"""Where the readings live, and how they reach dossier-preflight's own analysis code.

Every choice and every score in this folder goes through dossier-preflight's `grid/analyze.py`
(its sweep, its choice rule, its holdout predicates of `grid/predicates.py`, its `--frozen`
scoring) imported as a module, never re-implemented. What this module adds is plumbing:

- the paths, from two environment variables with sibling-directory defaults:
  DOSSIER_PREFLIGHT (default ../dossier-preflight) and PR_ARCHIVE (default
  ../perfect-recall-archive), the local staging of the raw readings (the Zenodo record once
  published);
- which arms exist on disk right now (X2 plugs in by path: `x2/readings.jsonl` appears, and the
  next run uses it);
- loading an arm into analyze.load()'s index (a gzipped file is decompressed to the cache
  first, since analyze.load() opens a plain path);
- assembling dossiers the way analyze.complete_dossiers() does, except that a variant missing
  from a key is COUNTED and skipped rather than dropping the whole dossier (three A3 images
  failed to read; dropping their dossiers would throw away 3 x 48 good readings);
- a disk cache of analyze.sweep() per (arm file sha256, check, dossier-preflight commit);
- fast_curve(): analyze.curve() with numpy counting, byte-for-byte the same points (tested),
  because the pure-Python curve is quadratic and the protocols call it thousands of times.
"""
import gzip
import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
from functools import lru_cache

import numpy as np

STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DP = os.path.abspath(os.environ.get("DOSSIER_PREFLIGHT",
                                    os.path.join(STUDY, "..", "dossier-preflight")))
AR = os.path.abspath(os.environ.get("PR_ARCHIVE",
                                    os.path.join(STUDY, "..", "perfect-recall-archive")))
CACHE = os.path.join(AR, "analysis-cache")
RESULTS = os.path.join(STUDY, "results")

# The thresholds "as shipped" (PREREG.md section 2): thresholds.json of dossier-preflight, whose
# sha256 the preregistration records. Any other file is refused.
SHIPPED_SHA256 = "184351f68dacc89118f22efce0a052f6b596e07b7a24f93b0bdfdf1a7e4fe4a5"

ARMS = {
    "A0": ("a0/measurements.jsonl.gz",),
    "A1": ("a1/readings.jsonl", "a1/readings.jsonl.gz"),
    "A2": ("a2/readings.jsonl", "a2/readings.jsonl.gz"),
    "A3": ("a3/readings.jsonl", "a3/readings.jsonl.gz"),
    "A4": ("a4/readings.jsonl.gz", "a4/readings.jsonl"),
    "X2": ("x2/readings.jsonl", "x2/readings.jsonl.gz"),
}
# The line counts the preregistration declares (section 3.3). An arm whose file holds fewer
# lines is still being written and is treated as absent.
DECLARED_LINES = {"A1": 15876, "A2": 15876, "A3": 2646, "A4": 2592}


if DP not in sys.path:
    sys.path.insert(0, DP)


def analyze():
    """dossier-preflight's grid.analyze, imported from DP."""
    import grid.analyze as a
    return a


def arm_path(arm):
    for rel in ARMS[arm]:
        p = os.path.join(AR, rel)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None


def count_lines(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def arm_status(arm):
    """(path or None, status): 'present', 'absent' or 'incomplete (n of N lines)'.

    A3 counts its read errors (OUT.errors.jsonl of grid/read_images.py) toward completion: a
    row that raised is a row the arm attempted, reported as an exclusion, not a row still due.
    """
    p = arm_path(arm)
    if p is None:
        return None, "absent"
    want = DECLARED_LINES.get(arm)
    if want is None:
        return p, "present"
    n = count_lines(p)
    errors = p + ".errors.jsonl"
    if os.path.exists(errors):
        n += count_lines(errors)
    if n < want:
        return None, f"incomplete ({n} of {want} lines)"
    return p, "present"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=None)
def dp_commit():
    return subprocess.run(["git", "-C", DP, "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def shipped_thresholds_path():
    p = os.path.join(DP, "thresholds.json")
    got = sha256(p)
    if got != SHIPPED_SHA256:
        raise SystemExit(f"{p} has sha256 {got}, the preregistration fixes {SHIPPED_SHA256}")
    return p


def plain(path):
    """A plain-text path analyze.load() can open: gz files are decompressed into the cache."""
    if not path.endswith(".gz"):
        return path
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, sha256(path)[:16] + "-" + os.path.basename(path)[:-3])
    if not os.path.exists(out):
        tmp = out + ".tmp"
        with gzip.open(path, "rb") as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.replace(tmp, out)
    return out


def load_lines(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@lru_cache(maxsize=None)
def identities():
    """{identity: Reference} for fixtures/identities (A1 to A3, X2) plus the default reference
    (A0, A4), under the name analyze.DEFAULT_IDENTITY gives it."""
    from preflight.reference import load_reference
    d = os.path.join(DP, "fixtures", "identities")
    refs = {}
    for name in sorted(os.listdir(d)):
        if name.endswith(".yaml"):
            r = load_reference(os.path.join(d, name))
            refs[r.identity] = r
    refs[analyze().DEFAULT_IDENTITY] = load_reference()
    return refs


@lru_cache(maxsize=None)
def catalog():
    a = analyze()
    out = {}
    for r in identities().values():
        out.update(a.variant_catalog(r))
    return out


def expected_of_identity(identity):
    from preflight.fixtures import enumerate_variants
    ref = identities()[identity]
    return frozenset(v.name for v in enumerate_variants(ref))


def assemble(index, expected_of=expected_of_identity):
    """analyze.complete_dossiers(), with one difference stated in the module docstring: a key
    whose clean dossier is whole keeps every variant it has; a declared variant it lacks is
    recorded in `missing` instead of dropping the key. A key missing a clean piece is dropped
    and recorded in `dropped`."""
    refs = identities()
    dossiers, missing, dropped = {}, [], []
    a = analyze()
    for key in sorted(index, key=repr):
        by_variant = index[key]
        ref = refs[key[a.IDENTITY_INDEX]]
        clean = by_variant.get("clean", {})
        if len(clean) < len(ref.pieces):
            dropped.append(key)
            continue
        d = {"clean": clean}
        for name in sorted(expected_of(key[a.IDENTITY_INDEX])):
            if name == "clean":
                continue
            if name in by_variant:
                d[name] = dict(clean, **by_variant[name])
            else:
                missing.append((key, name))
        dossiers[key] = d
    return dossiers, missing, dropped


def load_arm(arm):
    """(dossiers, info) for a generator arm (A1, A2, A3) read in analyze.load()'s schema."""
    path, status = arm_status(arm)
    if path is None:
        return None, {"arm": arm, "status": status}
    index = analyze().load(plain(path))
    dossiers, missing, dropped = assemble(index)
    return dossiers, {"arm": arm, "status": status, "path": os.path.relpath(path, AR),
                      "sha256": sha256(path), "keys": len(index), "dossiers": len(dossiers),
                      "variants_missing": [[list(k), n] for k, n in missing],
                      "keys_dropped": [list(k) for k in dropped]}


def _cache_file(tag, check):
    return os.path.join(CACHE, f"sweep-{tag}-{dp_commit()[:12]}-{check}.pkl")


def sweep_arm(dossiers, info, check):
    """analyze.sweep() for one arm and one check, cached on disk by the arm file's sha256."""
    os.makedirs(CACHE, exist_ok=True)
    path = _cache_file(info["sha256"][:16], check)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    a = analyze()
    refs = identities()
    out = a.sweep(dossiers, None, check, catalog=catalog(), ref_of=refs.__getitem__)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(out, f)
    os.replace(tmp, path)
    return out


def merge_sweeps(*sweeps):
    """{settings: per_cell} unions over arms (their keys never collide: source and jitter are in
    the key)."""
    out = {}
    for s in sweeps:
        for reg, pc in s.items():
            out.setdefault(reg, {}).update(pc)
    return out


def fast_curve(pos, neg):
    """analyze.curve() with the counts done by binary search: the same list of dicts, the same
    floats (tested against the original on random data with ties)."""
    a = analyze()
    thresholds = sorted({s for s in list(pos) + list(neg) if s > a.MINUS_INF})
    if not thresholds:
        return []
    margins = [thresholds[0] - 1.0]
    margins += [(x + y) / 2 for x, y in zip(thresholds, thresholds[1:])]
    margins += [thresholds[-1] + 1.0]
    sp = np.sort(np.asarray(list(pos), dtype=float))
    sn = np.sort(np.asarray(list(neg), dtype=float))
    m = np.asarray(margins, dtype=float)
    tps = len(sp) - np.searchsorted(sp, m, side="right")
    fps = len(sn) - np.searchsorted(sn, m, side="right")
    n_pos, n_neg = len(pos), len(neg)
    prev = a.PREVALENCE
    pts = []
    for t, tp, fp in zip(margins, tps.tolist(), fps.tolist()):
        recall = tp / n_pos if n_pos else 0.0
        fpr = fp / n_neg if n_neg else 0.0
        grid_prec = tp / (tp + fp) if (tp + fp) else 1.0
        num = prev * recall
        real_prec = num / (num + (1 - prev) * fpr) if (num + (1 - prev) * fpr) else 1.0
        pts.append({"threshold": t, "recall": recall, "fpr": fpr,
                    "grid_precision": grid_prec, "prevalence_precision": real_prec,
                    "tp": tp, "fp": fp, "n_pos": n_pos, "n_neg": n_neg})
    return pts


def install_fast_curve():
    a = analyze()
    if a.curve is not fast_curve:
        a._original_curve = a.curve
        a.curve = fast_curve


def write_json(path, obj):
    """Deterministic JSON: sorted keys, two-space indent, floats as Python prints them."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=True,
                      default=str)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def jsonable(v):
    """Tuples to lists, tuple keys to strings, nan kept (json writes NaN), recursively."""
    if isinstance(v, dict):
        return {(k if isinstance(k, str) else str(k)): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v
