"""Wilson interval and cluster bootstrap for the NAF prevalence measures.

Kept local to naf/ rather than shared with analysis/stats.py (T16, written after this pipeline
runs): the preregistration fixes the method (Wilson score interval, cluster bootstrap over
images, 10,000 resamples, numpy default_rng(20260925), percentile interval) independently of
which module ends up owning the code, so this module implements exactly that method and nothing
more.
"""
import numpy as np

Z95 = 1.959963984540054  # scipy.stats.norm.ppf(0.975), written as a literal so this module has
                          # no scipy dependency


def wilson(k, n, z=Z95):
    """Wilson score interval (lower, upper) for k successes out of n trials."""
    if n <= 0:
        return (float("nan"), float("nan"))
    phat = k / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * ((phat * (1 - phat) / n + z * z / (4 * n * n)) ** 0.5)
    lower = (center - margin) / denom
    upper = (center + margin) / denom
    return max(0.0, lower), min(1.0, upper)


def cluster_bootstrap(rows, cluster_key, stat, n=10000, seed=20260925):
    """Percentile 95% interval of stat(rows) under resampling clusters with replacement.

    rows: a list of dicts (or any indexable records) already grouped conceptually by
    cluster_key; stat(rows_subset) -> a float, computed by pooling every row of every
    resampled cluster (not by resampling rows directly, which would break the correlation
    within a cluster that clustering exists to model).

    Returns (lower, upper, point_estimate, n_clusters).
    """
    clusters = {}
    for row in rows:
        clusters.setdefault(row[cluster_key], []).append(row)
    cluster_ids = sorted(clusters)
    n_clusters = len(cluster_ids)
    point = stat(rows)
    if n_clusters == 0:
        return (float("nan"), float("nan"), point, 0)

    rng = np.random.default_rng(seed)
    draws = np.empty(n, dtype=float)
    idx = np.arange(n_clusters)
    for i in range(n):
        picked = rng.choice(idx, size=n_clusters, replace=True)
        resampled_rows = []
        for j in picked:
            resampled_rows.extend(clusters[cluster_ids[j]])
        draws[i] = stat(resampled_rows)
    lower, upper = np.percentile(draws, [2.5, 97.5])
    return float(lower), float(upper), point, n_clusters


def pooled_share(rows, positive_key="positive"):
    """stat() helper: pooled share of rows[positive_key] truthy, over len(rows)."""
    if not rows:
        return float("nan")
    return sum(1 for r in rows if r[positive_key]) / len(rows)
