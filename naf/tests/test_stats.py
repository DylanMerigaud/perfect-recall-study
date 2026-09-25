from naf.stats import cluster_bootstrap, pooled_share, wilson


def test_wilson_zero_of_81_matches_v0_table_2():
    lower, upper = wilson(0, 81)
    assert lower == 0.0
    assert abs(upper - 0.0453) < 0.0002


def test_wilson_287_of_288():
    lower, upper = wilson(287, 288)
    assert abs(lower - 0.981) < 0.0005
    assert upper <= 1.0


def test_wilson_half_of_hundred_is_centered_near_half():
    lower, upper = wilson(50, 100)
    assert lower < 0.5 < upper
    assert abs((lower + upper) / 2 - 0.5) < 0.01


def test_wilson_zero_trials_is_nan():
    lower, upper = wilson(0, 0)
    assert lower != lower  # NaN != NaN
    assert upper != upper


def test_cluster_bootstrap_constant_rows_has_zero_width_interval():
    # every row positive: pooled share is always 1.0, whatever cluster gets resampled
    rows = [{"image_id": "a", "positive": True}, {"image_id": "a", "positive": True},
            {"image_id": "b", "positive": True}, {"image_id": "c", "positive": True}]
    lower, upper, point, n_clusters = cluster_bootstrap(
        rows, "image_id", lambda r: pooled_share(r, "positive"), n=200,
    )
    assert point == 1.0
    assert lower == 1.0
    assert upper == 1.0
    assert n_clusters == 3


def test_cluster_bootstrap_is_deterministic_given_the_seed():
    rows = [
        {"image_id": "a", "positive": True}, {"image_id": "a", "positive": False},
        {"image_id": "b", "positive": True}, {"image_id": "b", "positive": True},
        {"image_id": "c", "positive": False}, {"image_id": "c", "positive": False},
        {"image_id": "d", "positive": True}, {"image_id": "d", "positive": False},
    ]
    stat = lambda r: pooled_share(r, "positive")
    a = cluster_bootstrap(rows, "image_id", stat, n=500, seed=20260925)
    b = cluster_bootstrap(rows, "image_id", stat, n=500, seed=20260925)
    assert a == b


def test_cluster_bootstrap_interval_contains_point_estimate():
    rows = [
        {"image_id": "a", "positive": True}, {"image_id": "a", "positive": False},
        {"image_id": "b", "positive": True}, {"image_id": "b", "positive": True},
        {"image_id": "c", "positive": False}, {"image_id": "c", "positive": False},
    ]
    lower, upper, point, n_clusters = cluster_bootstrap(
        rows, "image_id", lambda r: pooled_share(r, "positive"), n=2000,
    )
    assert n_clusters == 3
    assert lower <= point <= upper


def test_pooled_share_empty_is_nan():
    assert pooled_share([], "positive") != pooled_share([], "positive")
