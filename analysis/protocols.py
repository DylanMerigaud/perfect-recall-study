#!/usr/bin/env python3
"""RQ2: the six validation protocols and the three baselines of PREREG.md section 5.

    python analysis/protocols.py            # writes results/protocols.json

A protocol is (the rows thresholds and sensor settings are chosen on, the rows the scores are
reported on), written as the two holdout predicates of dossier-preflight's grid/predicates.py
over the key grid/analyze.py builds. The choice under the shipped rule is analyze.py's own code
path, the one its main() runs: choose_domain() over the calibration rows, analyze_check() per
check on clean in-domain pages, expiry frozen at its definition, resolution at the domain floor
(operational_floor()). Nothing here re-implements a choice the tool makes.

Two things are this study's, and are said so:

1. THE BASELINES. analyze.py has one rule (highest recall at most FP_BUDGET false positives per
   target, then the middle of the plateau). B1 (Youden's J), B2 (the midpoint between the class
   means) and the budget sensitivity (0.1% and 0.5%) are choose_check() below, which walks the
   same sweep in the same order as analyze_check() and swaps only the point rule and the rank
   that picks the winning setting: for B1 and B2 the winning setting is the one with the highest
   J at its own point (ties: lower false-positive rate, then sweep order); for the budgets it is
   analyze_check()'s own rank (recall, then lower false-positive rate). With the shipped rule,
   choose_check() returns exactly what analyze_check() returns (tests/test_protocols.py). The
   domain, expiry and resolution are taken from the shipped rule's run of the same fold under
   every baseline: they are definitions, not curve choices (PREREG.md section 5).
   B3 combines, for required_field, the ink setting and the best OCR setting each chosen by the
   shipped rule within its own family, and flags a field empty when both say empty (AND) or
   when either does (OR).

2. THE RESOLUTION MARGIN. analyze.main() computes operational_floor() on every retained dossier,
   calibration and report rows alike. Under a protocol whose report set is another source (P4,
   P5), that lets the report rows move the margin, so here the margin is computed on the
   calibration rows alone; the margin main() would have used is recorded next to it
   (`resolution_margin_all_rows`).

TARGETS. Every choice is scored on A3 seed 37 (the secondary target of P1 to P3 and P6, the
report set of P4) and on X2 when x2/readings.jsonl exists (the primary target; until then every
X2 field says "not tested yet"). Scores on a target are raw sensors (abstention off), the same
measure the validated numbers are; the shipped-rule choice of each fold is ALSO scored through
analyze.frozen_rows() with a thresholds file holding that choice, abstention off and on, and
the abstention-off frozen recall must equal the sweep-derived one (checked at run time).
"""
import argparse
import collections
import copy
import json
import os
import sys
import tempfile
import time

# Run as a script, this folder is sys.path[0], and numbers.py would shadow the standard
# library module of the same name that numpy imports: drop it, put the study root instead.
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import data  # noqa: E402

G0 = 'source == "g0" and jitter == False'
G0J = 'source == "g0" and jitter == True'
G1 = 'source == "g1"'
CAL_SEEDS = "seed in (11, 23)"
REP_SEED = "seed == 37"
A3_SEED37 = f"{G1} and {REP_SEED}"
IDENTITIES = ("id01", "id02", "id03", "id04", "id05", "id06")
# PREREG.md section 5, after the cap cut: the P3 folds are angle 2, dpi 150, sigma 6.
P3_FOLDS = (("angle", "2.0"), ("dpi", "150"), ("sigma", "6.0"))
BUDGETS = (0.001, 0.005)
RELEASE_GATE = 0.90


def fold(name, protocol, calibrate, report, arms):
    return {"name": name, "protocol": protocol, "calibrate_on": calibrate, "report_on": report,
            "arms": tuple(arms)}


def protocol_folds():
    out = collections.OrderedDict()
    out["P1"] = [fold("P1", "P1", f"{G0} and {CAL_SEEDS}", f"{G0} and {REP_SEED}", ["A1"])]
    out["P2"] = [fold("P2", "P2", f"{G0J} and {CAL_SEEDS}", f"{G0J} and {REP_SEED}", ["A2"])]
    out["P3"] = [fold(f"P3/{f}={v}", "P3", f"{G0} and {f} != {v}", f"{G0} and {f} == {v}",
                      ["A1"]) for f, v in P3_FOLDS]
    out["P4"] = [fold("P4", "P4", f"{G0} and {CAL_SEEDS}", A3_SEED37, ["A1", "A3"])]
    out["P5"] = [fold("P5", "P5", f"({G0} or {G1}) and {CAL_SEEDS}",
                      f"({G0} or {G1}) and {REP_SEED}", ["A1", "A3"])]
    out["P6"] = [fold(f"P6/identity={i}", "P6", f'{G0} and identity != "{i}"',
                      f'{G0} and identity == "{i}"', ["A1"]) for i in IDENTITIES]
    return out


# ------------------------------------------------------------------------------------------
# Point rules and ranks
# ------------------------------------------------------------------------------------------

def rule_budget(budget):
    a = data.analyze()

    def point(pts, pos, neg):
        return a.chosen_point(pts, budget)

    def rank(pt):
        return (pt["recall"], -pt["fpr"])
    return {"name": f"budget_{budget}", "point": point, "rank": rank}


def _plateau_middle(best, candidates, same):
    plateau = [p for p in candidates if same(p, best)]
    return plateau[len(plateau) // 2]


def rule_youden():
    def point(pts, pos, neg):
        if not pts:
            return None
        best = max(pts, key=lambda p: (p["recall"] - p["fpr"], -p["fpr"]))
        return _plateau_middle(best, pts, lambda p, b: p["recall"] == b["recall"]
                               and p["fpr"] == b["fpr"])

    def rank(pt):
        return (pt["recall"] - pt["fpr"], -pt["fpr"])
    return {"name": "B1", "point": point, "rank": rank}


def rule_midpoint():
    a = data.analyze()

    def point(pts, pos, neg):
        p = [x for x in pos if x > a.MINUS_INF]
        n = [x for x in neg if x > a.MINUS_INF]
        if not p or not n:
            return None
        t = (sum(p) / len(p) + sum(n) / len(n)) / 2
        tp = sum(1 for x in pos if x > t)
        fp = sum(1 for x in neg if x > t)
        return {"threshold": t, "recall": tp / len(pos), "fpr": fp / len(neg), "tp": tp,
                "fp": fp, "n_pos": len(pos), "n_neg": len(neg)}

    def rank(pt):
        return (pt["recall"] - pt["fpr"], -pt["fpr"])
    return {"name": "B2", "point": point, "rank": rank}


def choose_check(by_settings, check, holdout, rule):
    """analyze_check()'s walk over the sweep, with the point rule and the rank swapped.

    Returns (settings, threshold, calibration measure, validation measure) or None."""
    a = data.analyze()
    best = None
    for reg, pc in by_settings.items():
        if not pc:
            continue
        cal, _ = a.split_by(pc, holdout)
        pos, neg = a.flatten(cal)
        pts = a.curve(pos, neg)
        pt = rule["point"](pts, pos, neg)
        if pt is None:
            continue
        r = rule["rank"](pt)
        if best is None or r > best[0]:
            best = (r, reg, pc, pt)
    if best is None:
        return None
    _, reg, pc, pt = best
    cal, val = a.split_by(pc, holdout)
    return {"settings": reg, "threshold": pt["threshold"],
            "calibration": a.measure(cal, pt["threshold"]),
            "validation": a.measure(val, pt["threshold"])}


# ------------------------------------------------------------------------------------------
# One fold under the shipped rule: analyze.main()'s own sequence
# ------------------------------------------------------------------------------------------

def keep(by_settings, pred):
    return {reg: {k: v for k, v in pc.items() if pred(k)} for reg, pc in by_settings.items()}


def run_shipped(sweeps, dossiers, holdout):
    a = data.analyze()
    kept = {c: keep(s, holdout.keeps) for c, s in sweeps.items()}
    domain, attempts = a.choose_domain(kept, list(kept), holdout)
    results = {}
    for check in kept:
        in_domain = a.subgrid(kept[check], lambda k: k[1] >= domain)
        r = a.analyze_check(a.clean_pages(in_domain, holdout), check, None, holdout)
        if r is not None:
            results[check] = r
    margins = {}
    if "resolution" in results:
        retained_cal = {k: v for k, v in dossiers.items()
                        if holdout.calibrate(k) and k[1] >= domain}
        retained_all = {k: v for k, v in dossiers.items()
                        if holdout.keeps(k) and k[1] >= domain}
        margins["all_rows"] = max(0.01, 10 * a.dpi_estimator_error(retained_all))
        results["resolution"].update(a.operational_floor(results, domain, retained_cal))
        r = a.remeasure(results["resolution"], results["resolution"]["threshold"], holdout)
        r["point"] = dict(r["validation"], threshold=r["threshold"])
    return domain, attempts, results, margins


def is_ink(check, reg):
    return check == "required_field" and reg.text_sensor == "ink"


def summarize_measure(m):
    if m is None:
        return None
    keys = ("recall", "recall_ci", "tp", "n_pos", "fpr", "fp", "n_neg", "dossier_fpr",
            "n_dossiers", "threshold")
    out = data.jsonable({k: m[k] for k in keys if k in m})
    # analyze.measure() writes recall 0.0 on an empty positive set; an empty set has no
    # recall (a P3 fold whose held-out level falls outside the chosen domain, for example).
    if not out.get("n_pos"):
        out["recall"], out["recall_ci"] = None, None
    if not out.get("n_neg"):
        out["fpr"] = None
    if not out.get("n_dossiers"):
        out["dossier_fpr"] = None
    return out


def choice_record(check, reg, threshold, cal, val):
    a = data.analyze()
    return {"settings": a.settings_name(reg, check),
            "measured_settings": data.jsonable(a._useful_settings(reg, check)),
            "ink_sensor": is_ink(check, reg), "threshold": threshold,
            "calibration": summarize_measure(cal), "validation": summarize_measure(val)}


# ------------------------------------------------------------------------------------------
# Scoring a choice on a target
# ------------------------------------------------------------------------------------------

def score_on(sweep_check, reg, threshold, pred):
    """measure() of one chosen (settings, threshold) on the rows `pred` keeps (raw sensors)."""
    a = data.analyze()
    pc = {k: v for k, v in sweep_check.get(reg, {}).items() if pred(k)}
    if not pc:
        return None
    return a.measure(pc, threshold)


def combined_measure(pc_ink, pc_ocr, thr_ink, thr_ocr, op):
    """B3: per target, the field is flagged empty when both sensors fire (AND) or either (OR).
    Only targets both sensors scored enter. Returns measure()'s fields that apply."""
    a = data.analyze()
    stats = {"tp": 0, "n_pos": 0, "fp": 0, "n_neg": 0, "hit": 0, "n_dossiers": 0}
    for key in sorted(set(pc_ink) & set(pc_ocr), key=repr):
        vi, vo = pc_ink[key], pc_ocr[key]
        any_neg = False
        for side in ("pos", "neg"):
            for t in sorted(set(vi[side]) & set(vo[side]), key=repr):
                fi, fo = vi[side][t] > thr_ink, vo[side][t] > thr_ocr
                fired = (fi and fo) if op == "and" else (fi or fo)
                if side == "pos":
                    stats["n_pos"] += 1
                    stats["tp"] += fired
                else:
                    stats["n_neg"] += 1
                    stats["fp"] += fired
                    any_neg = any_neg or fired
        stats["n_dossiers"] += 1
        stats["hit"] += any_neg
    n = stats
    return {"recall": n["tp"] / n["n_pos"] if n["n_pos"] else None,
            "recall_ci": a.wilson(n["tp"], n["n_pos"]) if n["n_pos"] else None,
            "tp": n["tp"], "n_pos": n["n_pos"],
            "fpr": n["fp"] / n["n_neg"] if n["n_neg"] else None, "fp": n["fp"],
            "n_neg": n["n_neg"],
            "dossier_fpr": n["hit"] / n["n_dossiers"] if n["n_dossiers"] else None,
            "n_dossiers": n["n_dossiers"]}


def errors(checks, target_key):
    """Per check |validated recall - observed recall| and |validated dossier_fpr - observed|,
    and their means over the checks with positives on both sides."""
    per = {}
    for c, rec in sorted(checks.items()):
        v, o = rec.get("validation"), (rec.get("targets") or {}).get(target_key)
        if not v or not o or not v.get("n_pos") or not o.get("n_pos"):
            continue
        per[c] = {"recall_abs_error": abs(v["recall"] - o["recall"]),
                  "dossier_fpr_abs_error": abs(v["dossier_fpr"] - o["dossier_fpr"])}
    if not per:
        return {"per_check": {}, "mean_recall_abs_error": None,
                "mean_dossier_fpr_abs_error": None, "n_checks": 0}
    return {"per_check": per,
            "mean_recall_abs_error": sum(x["recall_abs_error"] for x in per.values()) / len(per),
            "mean_dossier_fpr_abs_error": sum(x["dossier_fpr_abs_error"]
                                              for x in per.values()) / len(per),
            "n_checks": len(per)}


def write_thresholds_file(choices, path):
    """A thresholds.json-shaped file holding a fold's choice, for analyze.frozen_rows()."""
    body = {"thresholds": {c: {"value": ch["threshold"], "origin": "protocol",
                               "measured_settings": ch["measured_settings"]}
                           for c, ch in choices.items()}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, sort_keys=True)


def frozen_on_target(choices, dossiers, pred, tmpdir, tag):
    """analyze.frozen_rows()/frozen_report() on the target rows, abstention off and on."""
    a = data.analyze()
    path = os.path.join(tmpdir, f"thresholds-{tag}.json")
    write_thresholds_file(choices, path)
    target = {k: v for k, v in dossiers.items() if pred(k)}
    if not target:
        return None
    refs = data.identities()
    out = {}
    for label, abstention in (("abstention_off", False), ("abstention_on", True)):
        rows = a.frozen_rows(target, refs["reference"], path, list(choices),
                             catalog=data.catalog(), ref_of=refs.__getitem__,
                             abstention=abstention)
        rep = a.frozen_report(rows, path, list(choices))
        out[label] = {c: {k: data.jsonable(m[k]) for k in
                          ("recall", "tp", "n_pos", "fpr", "dossier_fpr", "n_pos_abstained",
                           "n_neg_abstained", "recall_abstention_as_miss")}
                      for c, m in rep.items()}
    return out


# ------------------------------------------------------------------------------------------
# The run
# ------------------------------------------------------------------------------------------

def load_everything(checks):
    a = data.analyze()
    data.install_fast_curve()
    arms, infos, sweeps_by_arm = {}, {}, {}
    for arm in ("A1", "A2", "A3"):
        d, info = data.load_arm(arm)
        infos[arm] = info
        if d is None:
            continue
        arms[arm] = d
        sweeps_by_arm[arm] = {}
        for check in checks:
            t = time.perf_counter()
            sweeps_by_arm[arm][check] = data.sweep_arm(d, info, check)
            print(f"  sweep {arm} {check:17s} {time.perf_counter() - t:6.1f}s", flush=True)
    return arms, infos, sweeps_by_arm


def run_fold(fd, arms, sweeps_by_arm, checks, tmpdir, x2=None):
    from grid.predicates import Holdout, Predicate
    a = data.analyze()
    missing = [x for x in fd["arms"] if x not in arms]
    base = {"calibrate_on": fd["calibrate_on"], "report_on": fd["report_on"],
            "arms": list(fd["arms"])}
    if missing:
        base["status"] = "not run yet: arm(s) " + ", ".join(missing) + " not complete"
        return base
    holdout = Holdout(fd["calibrate_on"], fd["report_on"])
    dossiers = {}
    for x in fd["arms"]:
        dossiers.update(arms[x])
    sweeps = {c: data.merge_sweeps(*(sweeps_by_arm[x][c] for x in fd["arms"])) for c in checks}
    domain, attempts, shipped, margins = run_shipped(sweeps, dossiers, holdout)
    base.update(status="run", domain=domain,
                domain_attempts=[[d, r] for d, r in attempts],
                resolution_margin_all_rows=margins.get("all_rows"))
    target_pred = Predicate(A3_SEED37)
    a3_sweeps = sweeps_by_arm.get("A3")
    rules = collections.OrderedDict()

    # The shipped rule.
    choices = {}
    for check, r in shipped.items():
        choices[check] = choice_record(check, r["settings"], r["threshold"], r["calibration"],
                                       r["validation"])
    if "resolution" in shipped:
        choices["resolution"]["resolution_margin"] = shipped["resolution"]["estimator_margin"]
        choices["resolution"]["floor_dpi"] = shipped["resolution"]["floor_dpi"]
    rules["shipped"] = choices

    # B1, B2 and the budget sensitivity: every check except the definitions.
    kept = {c: keep(s, holdout.keeps) for c, s in sweeps.items()}
    fixed = {"expiry", "resolution"}
    for rule in (rule_youden(), rule_midpoint()) + tuple(rule_budget(b) for b in BUDGETS):
        ch = {}
        for check in checks:
            if check in fixed and check in choices:
                ch[check] = copy.deepcopy(choices[check])
                continue
            in_domain = a.clean_pages(a.subgrid(kept[check], lambda k: k[1] >= domain), holdout)
            got = choose_check(in_domain, check, holdout, rule)
            if got is None:
                continue
            ch[check] = choice_record(check, got["settings"], got["threshold"],
                                      got["calibration"], got["validation"])
        rules[rule["name"]] = ch

    # Score every rule's choices on A3 seed 37 (raw sensors) and, when present, on X2.
    for name, ch in rules.items():
        for check, rec in ch.items():
            reg = _settings_of(rec, check)
            rec["targets"] = {}
            if a3_sweeps is not None:
                m = score_on(a3_sweeps[check], reg, rec["threshold"], target_pred)
                rec["targets"]["A3_seed37"] = summarize_measure(m)
            rec["targets"]["X2"] = (x2.score_choice(check, reg, rec["threshold"])
                                    if x2 is not None else "not tested yet")
        ch_out = {"checks": ch,
                  "errors_A3_seed37": errors(ch, "A3_seed37") if a3_sweeps else None,
                  "errors_X2": (x2.errors(ch) if x2 is not None else "not tested yet")}
        rf = ch.get("required_field")
        if rf:
            ch_out["required_field_crowned"] = rf["settings"]
            ch_out["required_field_ink_crowned"] = rf["ink_sensor"]
            ch_out["release_gate_0.90_blocks_required_field"] = (
                rf["validation"]["n_pos"] > 0 and rf["validation"]["recall"] < RELEASE_GATE)
        if name == "shipped" and "required_field" in shipped:
            # Every required_field setting's own point under the shipped rule (H3 reads the
            # thresholds P1 chooses for the three OCR sensors from here).
            ch_out["required_field_per_setting"] = {
                a.settings_name(r, "required_field"): pt["threshold"]
                for r, _, _, pt in shipped["required_field"]["_ranking"] if pt is not None}
        rules[name] = ch_out

    # The frozen cross-check of the shipped rule's choice on A3 seed 37.
    if "A3" in arms:
        frozen = frozen_on_target(rules["shipped"]["checks"], arms["A3"], target_pred, tmpdir,
                                  fd["name"].replace("/", "_").replace("=", "-"))
        rules["shipped"]["frozen_A3_seed37"] = frozen
        for check, rec in rules["shipped"]["checks"].items():
            t = rec["targets"].get("A3_seed37")
            f = (frozen or {}).get("abstention_off", {}).get(check)
            if t and f and (t["tp"], t["n_pos"]) != (f["tp"], f["n_pos"]):
                raise SystemExit(f"{fd['name']} {check}: sweep and frozen disagree on A3 "
                                 f"seed 37: {t['tp']}/{t['n_pos']} vs {f['tp']}/{f['n_pos']}")

    # B3: required_field, ink AND / OR the best OCR setting, each chosen by the shipped rule.
    if "required_field" in checks:
        rf_dom = a.clean_pages(a.subgrid(kept["required_field"], lambda k: k[1] >= domain),
                               holdout)
        ink = {r: pc for r, pc in rf_dom.items() if r.text_sensor == "ink"}
        ocr = {r: pc for r, pc in rf_dom.items() if r.text_sensor != "ink"}
        ci = choose_check(ink, "required_field", holdout, rule_budget(a.FP_BUDGET))
        co = choose_check(ocr, "required_field", holdout, rule_budget(a.FP_BUDGET))
        for op in ("and", "or"):
            rec = {"ink_component": a.settings_name(ci["settings"], "required_field"),
                   "ink_threshold_value": ci["threshold"],
                   "ocr_component": a.settings_name(co["settings"], "required_field"),
                   "ocr_threshold_value": co["threshold"], "targets": {}}
            for side, pred in (("calibration", holdout.calibrate), ("validation", holdout.report)):
                pi = {k: v for k, v in rf_dom[ci["settings"]].items() if pred(k)}
                po = {k: v for k, v in rf_dom[co["settings"]].items() if pred(k)}
                rec[side] = data.jsonable(combined_measure(pi, po, ci["threshold"],
                                                           co["threshold"], op))
            if a3_sweeps is not None:
                s = a3_sweeps["required_field"]
                pi = {k: v for k, v in s[ci["settings"]].items() if target_pred(k)}
                po = {k: v for k, v in s[co["settings"]].items() if target_pred(k)}
                rec["targets"]["A3_seed37"] = data.jsonable(
                    combined_measure(pi, po, ci["threshold"], co["threshold"], op))
            rec["targets"]["X2"] = (x2.score_combined(ci, co, op) if x2 is not None
                                    else "not tested yet")
            rules[f"B3_{op}"] = rec
    base["rules"] = rules
    return base


def _settings_of(rec, check):
    from preflight.checks import Settings
    return Settings(**{k: v for k, v in rec["measured_settings"].items()})


def pooled(folds):
    """P3 and P6: validation pooled over folds (each fold at its own threshold), and the mean of
    the per-fold absolute errors on A3 seed 37."""
    run = [f for f in folds if f.get("status") == "run"]
    if not run:
        return None
    out = {}
    for rule in run[0]["rules"]:
        if rule.startswith("B3_"):
            continue
        checks = sorted({c for f in run for c in f["rules"][rule]["checks"]})
        per = {}
        for c in checks:
            recs = [f["rules"][rule]["checks"][c] for f in run if c in f["rules"][rule]["checks"]]
            tp = sum(r["validation"]["tp"] for r in recs if r["validation"])
            n = sum(r["validation"]["n_pos"] for r in recs if r["validation"])
            per[c] = {"validation_recall": tp / n if n else None, "tp": tp, "n_pos": n,
                      "crowned": sorted({r["settings"] for r in recs})}
        errs = [f["rules"][rule]["errors_A3_seed37"]["mean_recall_abs_error"] for f in run
                if f["rules"][rule].get("errors_A3_seed37")
                and f["rules"][rule]["errors_A3_seed37"]["mean_recall_abs_error"] is not None]
        out[rule] = {"checks": per,
                     "mean_over_folds_of_mean_recall_abs_error_A3_seed37":
                         sum(errs) / len(errs) if errs else None,
                     "folds_required_field_ink_crowned": [
                         f["rules"][rule].get("required_field_ink_crowned") for f in run]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(data.RESULTS, "protocols.json"))
    ap.add_argument("--only", nargs="*", default=None, help="protocol ids, e.g. P1 P5")
    a_ = ap.parse_args(argv)
    a = data.analyze()
    checks = list(a.CHECKS)
    t0 = time.perf_counter()
    arms, infos, sweeps_by_arm = load_everything(checks)
    from analysis import x2 as x2mod
    x2 = x2mod.X2.load(sweeps_by_arm, checks)
    out = {"meta": {"dossier_preflight_commit": data.dp_commit(),
                    "arms": {k: {f: v for f, v in i.items() if f not in ("variants_missing",)}
                             | {"n_variants_missing": len(i.get("variants_missing", []))}
                             for k, i in infos.items()},
                    "a3_variants_missing": infos.get("A3", {}).get("variants_missing", []),
                    "x2": x2.info if x2 is not None else {"status": x2mod.status()},
                    "fp_budget": a.FP_BUDGET, "budgets_sensitivity": list(BUDGETS),
                    "release_gate_recall": RELEASE_GATE,
                    "target_a3": A3_SEED37},
           "protocols": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for pid, folds in protocol_folds().items():
            if a_.only and pid not in a_.only:
                continue
            res = []
            for fd in folds:
                t = time.perf_counter()
                res.append(dict(run_fold(fd, arms, sweeps_by_arm, checks, tmp, x2),
                                fold=fd["name"]))
                print(f"{fd['name']:18s} {res[-1]['status']} "
                      f"{time.perf_counter() - t:6.1f}s", flush=True)
            entry = {"folds": res}
            if len(folds) > 1:
                entry["pooled"] = pooled(res)
            out["protocols"][pid] = entry
    data.write_json(a_.out, data.jsonable(out))
    print(f"-> {a_.out} ({time.perf_counter() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
