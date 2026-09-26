"""The decision rules of hypotheses.py, on toy inputs: each verdict follows PREREG.md 4.1."""
import json

from analysis import hypotheses as H
from analysis import x2 as x2mod


def audit_row(process, check, effect, on, known):
    return {"process": process, "check": check, "predicted_effect": effect,
            "predicted_below_0.90_on": on, "known": "true" if known else "false"}


AUDIT = [audit_row("ink", "required_field", "miss", "A3", True),
         audit_row("shadow", "required_checkbox", "miss", "A3", False),
         audit_row("stroke", "signature", "miss", "both", True),
         audit_row("loss", "forbidden_value", "miss", "A3", False),
         audit_row("curl", "required_field", "miss", "X2", False),
         audit_row("dpi", "resolution", "false_alarm", "A3", False)]


def cells(**recalls):
    return {c: {"recall": r, "n": 0 if r is None else 10, "false_alarm_rate": 0.2}
            for c, r in recalls.items()}


def test_named_cells_primary_and_strict():
    assert H.named_cells(AUDIT, "A3", strict=False) == {"required_checkbox", "signature",
                                                        "forbidden_value"}
    assert H.named_cells(AUDIT, "A3", strict=True) == {"required_checkbox", "forbidden_value"}
    assert H.named_cells(AUDIT, "X2", strict=False) == {"signature", "required_field"}


def test_h6_hits_over_failures():
    c = cells(required_field=0.5, required_checkbox=0.95, signature=0.8, forbidden_value=0.1,
              rotated_page=0.5, expiry=None)
    s = H.score_h6(c, AUDIT, "A3", strict=False)
    assert s["observed_failing"] == ["forbidden_value", "required_field", "rotated_page",
                                     "signature"]
    assert s["hits"] == ["forbidden_value", "signature"]
    assert s["hits_over_failures"] == [2, 4]
    assert s["false_predictions_over_predictions"] == [1, 3]
    assert s["verdict"] == "supported"          # 2 / 4 >= 0.5
    assert s["dropped_no_positive"] == ["expiry"]


def test_h6_no_failure_is_not_tested():
    s = H.score_h6(cells(required_field=0.99, signature=0.95), AUDIT, "A3", strict=False)
    assert s["verdict"] == "not tested"


def test_h6_without_x2_is_not_tested_yet(monkeypatch):
    monkeypatch.setattr(H, "read_audit", lambda: AUDIT)
    c = cells(required_field=0.5, signature=0.8)
    for v in c.values():
        v["recall_unscored_as_miss"], v["positives_unscored"] = v["recall"], 0
    r = H.h6(c, None)
    assert r["verdict"] == H.NOT_YET and r["X2_part"] == H.NOT_YET
    assert r["verdict_A3_part"] == "supported"


def test_false_alarm_rows_are_descriptive():
    rows = H.false_alarm_rows(cells(resolution=1.0), AUDIT, "A3")
    assert rows == [{"process": "dpi", "check": "resolution", "rate": 0.2, "correct": True}]


def protocols_with(p1_ink, p5_ink):
    def fold(ink):
        return {"folds": [{"status": "run", "rules": {"shipped": {
            "required_field_ink_crowned": ink,
            "required_field_crowned": "ink" if ink else "page"}}}]}
    return {"protocols": {"P1": fold(p1_ink), "P5": fold(p5_ink)}}


def test_h5_verdicts():
    assert H.h5(protocols_with(True, False))["verdict"] == "supported"
    assert H.h5(protocols_with(True, True))["verdict"] == "not supported"
    assert H.h5(protocols_with(False, False))["verdict"] == "not supported"
    missing = {"protocols": {"P1": protocols_with(True, False)["protocols"]["P1"]}}
    assert H.h5(missing)["verdict"] == H.NOT_YET


def test_x2_hypotheses_wait_for_x2():
    for fn in (lambda: H.h2(None, {}), lambda: H.h3(None, {}, {}), lambda: H.h4(None, {})):
        assert fn()["verdict"] == H.NOT_YET


def test_mean_abs_error_over_check_condition_pairs():
    rows = {"required_field": [
        {"positive": True, "fires": True, "condition": "phone|300dpi"},
        {"positive": True, "fires": False, "condition": "phone|300dpi"},
        {"positive": True, "fires": False, "condition": "phone|mark2"},
        {"positive": False, "fires": True, "condition": "phone|mark2"}],
        "signature": [{"positive": True, "fires": True, "condition": "phone|300dpi"}]}
    # required_field: |1 - 0.5| and |1 - 0|; signature: |1 - 1|
    assert x2mod.mean_abs_error(rows, {"required_field": 1.0, "signature": 1.0}) == 0.5


def test_p_naf_follows_the_validity_object():
    r = H.p_naf()
    d = json.load(open(H.os.path.join(H.data.RESULTS, "naf.json"), encoding="utf-8"))
    assert r["verdict"] == d["validity"]["p_naf_reported_as"] == "not interpretable"
    assert r["band_as_preregistered"] == d["p_naf"]["band"]
    hl = r["human_label_exploratory_lower_bound"]
    assert (hl["k"], hl["n"]) == (159, 5550)
