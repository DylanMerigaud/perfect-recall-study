import math

from analysis.stats import (cluster_bootstrap, cluster_bootstrap_ratio, cohen_kappa,
                            kappa_bootstrap, mcnemar_exact, wilson)


def test_wilson_zero_of_81_upper_is_v0_table_2():
    lo, hi = wilson(0, 81)
    assert lo == 0.0
    assert round(hi, 4) == 0.0453


def test_wilson_287_of_288_lower_is_0981():
    lo, hi = wilson(287, 288)
    assert round(lo, 3) == 0.981
    assert hi <= 1.0


def test_wilson_matches_the_x3_module_to_the_last_digit():
    from naf.stats import wilson as naf_wilson
    for k, n in ((0, 81), (159, 5550), (66, 165), (287, 288), (5, 5)):
        assert wilson(k, n) == naf_wilson(k, n)


def test_wilson_empty_denominator_is_nan():
    lo, hi = wilson(0, 0)
    assert math.isnan(lo) and math.isnan(hi)


def test_mcnemar_known_answers():
    # b=1, c=6: 2 * (C(7,0) + C(7,1)) / 2^7 = 16 / 128
    assert mcnemar_exact(1, 6) == 0.125
    assert mcnemar_exact(6, 1) == 0.125
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 3) == 1.0
    # b=0, c=10: 2 / 1024
    assert mcnemar_exact(0, 10) == 2 / 1024


def test_cohen_kappa_textbook_example():
    # The two-rater yes/no example of the Wikipedia "Cohen's kappa" article: 20 yes/yes,
    # 5 yes/no, 10 no/yes, 15 no/no. po = 0.70, pe = 0.50, kappa = 0.40.
    pairs = ([("yes", "yes")] * 20 + [("yes", "no")] * 5 + [("no", "yes")] * 10
             + [("no", "no")] * 15)
    assert abs(cohen_kappa(pairs) - 0.4) < 1e-12


def test_cohen_kappa_fleiss_style_three_categories():
    # Perfect agreement is 1; systematic disagreement on a balanced table is negative.
    assert cohen_kappa([("M1", "M1"), ("M2", "M2"), ("M0", "M0")]) == 1.0
    assert cohen_kappa([("a", "b"), ("b", "a")]) == -1.0
    assert math.isnan(cohen_kappa([("M1", "M1"), ("M1", "M1")]))


def test_kappa_bootstrap_is_seeded_and_brackets_the_point():
    pairs = ([("yes", "yes")] * 20 + [("yes", "no")] * 5 + [("no", "yes")] * 10
             + [("no", "no")] * 15)
    a = kappa_bootstrap(pairs, n=500)
    b = kappa_bootstrap(pairs, n=500)
    assert a == b
    assert a["lower"] < 0.4 < a["upper"]


def test_cluster_bootstrap_equals_the_x3_module():
    from naf.stats import cluster_bootstrap as naf_cb, pooled_share
    rows = [{"c": c, "positive": p} for c, p in
            [("a", 1), ("a", 0), ("b", 1), ("c", 0), ("c", 0), ("d", 1), ("d", 1), ("e", 0)]]
    mine = cluster_bootstrap(rows, "c", pooled_share, n=2000)
    lo, hi, point, nc = naf_cb(rows, "c", pooled_share, n=2000)
    assert (mine["lower"], mine["upper"], mine["point"], mine["n_clusters"]) == (lo, hi, point, nc)


def test_ratio_bootstrap_equals_the_generic_one():
    rows = [{"c": c, "hit": h} for c, h in
            [("id01", 1), ("id01", 1), ("id02", 0), ("id03", 1), ("id03", 0), ("id04", 0),
             ("id05", 1), ("id06", 1), ("id06", 1), ("id06", 0)]]
    generic = cluster_bootstrap(rows, "c", lambda rs: sum(r["hit"] for r in rs) / len(rs),
                                n=3000)
    k, n = {}, {}
    for r in rows:
        k[r["c"]] = k.get(r["c"], 0) + r["hit"]
        n[r["c"]] = n.get(r["c"], 0) + 1
    fast = cluster_bootstrap_ratio(k, n, n=3000)
    for f in ("lower", "upper", "point", "n_clusters"):
        assert abs(generic[f] - fast[f]) < 1e-12, f


def test_constant_rows_give_a_zero_width_interval():
    k, n = {"a": 3, "b": 2}, {"a": 3, "b": 2}
    out = cluster_bootstrap_ratio(k, n, n=200)
    assert out["lower"] == out["upper"] == 1.0
