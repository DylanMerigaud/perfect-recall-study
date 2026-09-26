"""The statistics the preregistration fixes (prereg/PREREG.md, section 7), and nothing more.

- wilson(k, n): Wilson 95% score interval, exact counts always printed next to it by callers.
- cluster_bootstrap(rows, cluster_key, stat): percentile 95% interval under resampling the top
  cluster with replacement, 10,000 resamples, numpy default_rng(20260925).
- cluster_bootstrap_ratio(k_by_cluster, n_by_cluster): the same draws for a pooled ratio (a
  recall, a rate), vectorised; it consumes the random stream exactly as cluster_bootstrap does,
  so both give the same interval on the same data (tested).
- mcnemar_exact(b, c): exact two-sided McNemar p-value from the two discordant counts.
- cohen_kappa(pairs) and kappa_bootstrap(pairs): Cohen's kappa on the first code, and its
  percentile interval over episodes.

Standard library plus numpy. Z95 is scipy.stats.norm.ppf(0.975) written as a literal, the same
constant naf/stats.py uses, so the X3 intervals and these agree to the last digit.
"""
import math
from collections import Counter

import numpy as np

Z95 = 1.959963984540054
SEED = 20260925
N_RESAMPLES = 10000


def wilson(k, n, z=Z95):
    """Wilson score interval (lower, upper) for k successes out of n. (nan, nan) when n is 0:
    an empty denominator has no interval, and a (0, 1) placeholder would read as a measurement."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom), min(1.0, (centre + margin) / denom))


def _clusters(rows, cluster_key):
    groups = {}
    for row in rows:
        key = cluster_key(row) if callable(cluster_key) else row[cluster_key]
        groups.setdefault(key, []).append(row)
    return groups


def cluster_bootstrap(rows, cluster_key, stat, n=N_RESAMPLES, seed=SEED):
    """Percentile 95% interval of stat(rows) when whole clusters are resampled.

    rows: records; cluster_key: a field name or a function of a record; stat: a function of a
    list of records returning a float (it may return nan on an empty draw, such draws are
    dropped from the percentile and counted). Returns a dict with lower, upper, point,
    n_clusters, n_resamples, n_undefined, seed.
    """
    groups = _clusters(rows, cluster_key)
    ids = sorted(groups, key=repr)
    point = stat(rows)
    out = {"point": point, "n_clusters": len(ids), "n_resamples": n, "seed": seed}
    if not ids:
        out.update(lower=float("nan"), upper=float("nan"), n_undefined=n)
        return out
    rng = np.random.default_rng(seed)
    idx = np.arange(len(ids))
    draws = np.empty(n, dtype=float)
    for i in range(n):
        picked = rng.choice(idx, size=len(ids), replace=True)
        sample = []
        for j in picked:
            sample.extend(groups[ids[j]])
        draws[i] = stat(sample)
    return _percentile(draws, out)


def _percentile(draws, out):
    ok = draws[~np.isnan(draws)]
    out["n_undefined"] = int(len(draws) - len(ok))
    if len(ok) == 0:
        out.update(lower=float("nan"), upper=float("nan"))
    else:
        lo, hi = np.percentile(ok, [2.5, 97.5])
        out.update(lower=float(lo), upper=float(hi))
    return out


def cluster_bootstrap_ratio(k_by_cluster, n_by_cluster, n=N_RESAMPLES, seed=SEED):
    """cluster_bootstrap for a pooled ratio sum(k) / sum(n), given per-cluster counts.

    k_by_cluster and n_by_cluster are dicts keyed by cluster id. The clusters are sorted the
    way cluster_bootstrap sorts them and the random stream is drawn the same way, so the two
    functions agree exactly on the same data (tests/test_stats.py). A draw whose pooled n is 0
    is undefined and dropped.
    """
    ids = sorted(n_by_cluster, key=repr)
    total_n = sum(n_by_cluster.values())
    point = sum(k_by_cluster.get(c, 0) for c in ids) / total_n if total_n else float("nan")
    out = {"point": point, "n_clusters": len(ids), "n_resamples": n, "seed": seed}
    if not ids:
        out.update(lower=float("nan"), upper=float("nan"), n_undefined=n)
        return out
    k = np.array([k_by_cluster.get(c, 0) for c in ids], dtype=float)
    m = np.array([n_by_cluster[c] for c in ids], dtype=float)
    rng = np.random.default_rng(seed)
    idx = np.arange(len(ids))
    draws = np.empty(n, dtype=float)
    for i in range(n):
        picked = rng.choice(idx, size=len(ids), replace=True)
        den = m[picked].sum()
        draws[i] = k[picked].sum() / den if den else float("nan")
    return _percentile(draws, out)


def mcnemar_exact(b, c):
    """Exact two-sided McNemar p-value: the binomial test of b against b + c at one half."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cohen_kappa(pairs):
    """Cohen's kappa over (code of coder 1, code of coder 2) pairs.

    Returns nan when the expected agreement is 1 (every episode coded the same single label by
    both coders): kappa is undefined there, not 1.
    """
    pairs = list(pairs)
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum(ca[x] * cb[x] for x in set(ca) | set(cb)) / (n * n)
    if pe == 1:
        return float("nan")
    return (po - pe) / (1 - pe)


def kappa_bootstrap(pairs, n=N_RESAMPLES, seed=SEED):
    """Cohen's kappa with a percentile 95% interval over episodes (each pair is one cluster)."""
    pairs = list(pairs)
    rows = [{"i": i, "a": a, "b": b} for i, (a, b) in enumerate(pairs)]
    return cluster_bootstrap(rows, "i", lambda rs: cohen_kappa((r["a"], r["b"]) for r in rs),
                             n=n, seed=seed)
