"""The protocol machinery on toy sweeps: no archive needed, dossier-preflight's code is."""
import random

import pytest

from analysis import data

a = data.analyze()
from grid.predicates import Holdout  # noqa: E402
from preflight.checks import Settings  # noqa: E402

from analysis import protocols  # noqa: E402


def key(seed, identity="id01", source="g0", dpi=200):
    return (0.0, dpi, 95, 0.0, seed, 0.0, identity, source, False, None, None)


def toy_sweep(rng, shift):
    """Three settings; each cell has 4 positives and 6 negatives, scores drawn around 0."""
    out = {}
    for i, reg in enumerate((Settings(disc_ratio=0.3, ink_threshold=128),
                             Settings(disc_ratio=0.42, ink_threshold=128),
                             Settings(disc_ratio=0.55, ink_threshold=160))):
        pc = {}
        for seed in (11, 23, 37):
            for ident in ("id01", "id02"):
                pos = {("v", "p", f"t{j}"): round(rng.gauss(1.0 + shift * i, 1.0), 1)
                       for j in range(4)}
                neg = {("p", f"n{j}"): round(rng.gauss(-1.0, 1.0), 1) for j in range(6)}
                pc[key(seed, ident)] = {"pos": pos, "neg": neg}
        out[reg] = pc
    return out


def test_fast_curve_is_the_original_curve():
    rng = random.Random(3)
    for _ in range(30):
        pos = [round(rng.gauss(0, 1), 1) for _ in range(rng.randint(0, 40))]
        neg = [round(rng.gauss(-0.5, 1), 1) for _ in range(rng.randint(0, 60))]
        if rng.random() < 0.3:
            pos.append(a.MINUS_INF)
        assert data.fast_curve(pos, neg) == a.curve(pos, neg)


@pytest.mark.parametrize("shift", [0.0, 0.5, -0.5])
def test_choose_check_with_the_shipped_rule_is_analyze_check(shift):
    by_settings = toy_sweep(random.Random(7), shift)
    holdout = Holdout("seed != 37", "seed == 37")
    mine = protocols.choose_check(by_settings, "required_checkbox", holdout,
                                  protocols.rule_budget(a.FP_BUDGET))
    theirs = a.analyze_check(by_settings, "required_checkbox", None, holdout)
    assert mine["settings"] == theirs["settings"]
    assert mine["threshold"] == theirs["threshold"]
    assert mine["validation"] == theirs["validation"]
    assert mine["calibration"] == theirs["calibration"]


def test_predicates_split_by_identity():
    by_settings = toy_sweep(random.Random(1), 0.0)
    holdout = Holdout('identity != "id02"', 'identity == "id02"')
    got = protocols.choose_check(by_settings, "required_checkbox", holdout,
                                 protocols.rule_budget(a.FP_BUDGET))
    assert got["calibration"]["n_dossiers"] == 3
    assert got["validation"]["n_dossiers"] == 3


def test_youden_takes_the_point_maximising_j():
    pos = [1.0, 2.0, 3.0, 4.0]
    neg = [0.0, 0.5, 2.5, -1.0]
    pts = a.curve(pos, neg)
    pt = protocols.rule_youden()["point"](pts, pos, neg)
    best = max(p["recall"] - p["fpr"] for p in pts)
    assert pt["recall"] - pt["fpr"] == best


def test_midpoint_is_between_the_class_means():
    pos = [2.0, 4.0]
    neg = [0.0, -2.0]
    pt = protocols.rule_midpoint()["point"](a.curve(pos, neg), pos, neg)
    assert pt["threshold"] == 1.0
    assert pt["recall"] == 1.0 and pt["fpr"] == 0.0


def test_combined_and_or():
    ink = {key(37): {"pos": {"a": 1.0, "b": -1.0}, "neg": {"c": 1.0, "d": -1.0}}}
    ocr = {key(37): {"pos": {"a": -1.0, "b": 1.0}, "neg": {"c": -1.0, "d": -1.0}}}
    both = protocols.combined_measure(ink, ocr, 0.0, 0.0, "and")
    either = protocols.combined_measure(ink, ocr, 0.0, 0.0, "or")
    assert (both["tp"], both["n_pos"], both["fp"]) == (0, 2, 0)
    assert (either["tp"], either["n_pos"], either["fp"]) == (2, 2, 1)
    assert either["dossier_fpr"] == 1.0 and both["dossier_fpr"] == 0.0


def test_errors_are_absolute_and_skip_empty_checks():
    checks = {"x": {"validation": {"recall": 1.0, "n_pos": 5, "dossier_fpr": 0.0},
                    "targets": {"T": {"recall": 0.25, "n_pos": 4, "dossier_fpr": 0.5}}},
              "y": {"validation": {"recall": 0.5, "n_pos": 5, "dossier_fpr": 0.0},
                    "targets": {"T": {"recall": 0.0, "n_pos": 0, "dossier_fpr": 0.0}}}}
    e = protocols.errors(checks, "T")
    assert e["n_checks"] == 1
    assert e["mean_recall_abs_error"] == 0.75
    assert e["mean_dossier_fpr_abs_error"] == 0.5


def test_protocol_table_matches_the_preregistration():
    folds = protocols.protocol_folds()
    assert list(folds) == ["P1", "P2", "P3", "P4", "P5", "P6"]
    assert len(folds["P3"]) == 3 and len(folds["P6"]) == 6
    k37_g1 = (0.0, 200, 100, 0.0, 37, 0.0, "id01", "g1", False, None, None)
    k11_g1 = (0.0, 200, 100, 0.0, 11, 0.0, "id01", "g1", False, None, None)
    p4 = Holdout(folds["P4"][0]["calibrate_on"], folds["P4"][0]["report_on"])
    p5 = Holdout(folds["P5"][0]["calibrate_on"], folds["P5"][0]["report_on"])
    assert p4.report(k37_g1) and not p4.calibrate(k11_g1)
    assert p5.calibrate(k11_g1) and p5.report(k37_g1)
    assert p5.calibrate(key(11)) and not p5.calibrate(key(37))
    jit = (0.0, 200, 95, 0.0, 11, 0.0, "id01", "g0", True, None, None)
    p1 = Holdout(folds["P1"][0]["calibrate_on"], folds["P1"][0]["report_on"])
    p2 = Holdout(folds["P2"][0]["calibrate_on"], folds["P2"][0]["report_on"])
    assert p2.calibrate(jit) and not p1.calibrate(jit)
