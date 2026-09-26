#!/usr/bin/env python3
"""H1 to H6 and P-NAF, each by its criterion in prereg/PREREG.md (section 4 and 4.1, and the
amendment A1 for P-NAF), plus the exploratory readings labelled as such.

    python analysis/hypotheses.py          # needs results/protocols.json (H5, H3, H4)

Verdicts: "supported", "not supported", "not tested" (PREREG 4.1: the source is absent for
good, for example X2 if the scan session is declined), "not tested yet" (the source is still to
come: X2 before its readings exist), and for P-NAF the amendment's "not interpretable". A
criterion is met on the point estimate; its intervals are reported next to it.

Scores at the shipped thresholds are raw sensors (abstention off), the measure the shipped
held-out estimate (1.000) was taken with; the product view (abstention on) is reported next to
H1 as a sensitivity.
"""
import argparse
import collections
import csv
import json
import os
import sys

# Run as a script, this folder is sys.path[0], and numbers.py would shadow the standard
# library module of the same name that numpy imports: drop it, put the study root instead.
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import data, stats  # noqa: E402
from analysis import x2 as x2mod  # noqa: E402

H1_INK_MIN = 0.005        # PREREG 4.1: field_ink_share >= 0.5% of the field
H6_NO_INK_MAX = 0.0005    # PREREG 4.1: required_field cells on field_ink_share < 0.05%
H3_MARK_MIN = 0.01
FAIL_BELOW = 0.90
H1_BELOW = 0.50
H2_RECALL_MIN, H2_FA_MAX = 0.90, 0.10
H3_INK_BELOW, H3_OCR_MIN = 0.50, 0.60
FALSE_ALARM_ABOVE = 0.10
NOT_YET = "not tested yet"


def interval(k, n, clusters_k, clusters_n):
    w = stats.wilson(k, n)
    b = stats.cluster_bootstrap_ratio(clusters_k, clusters_n)
    return {"wilson_95": list(w), "cluster_bootstrap_95": [b["lower"], b["upper"]],
            "n_clusters": b["n_clusters"], "n_resamples": b["n_resamples"], "seed": b["seed"]}


def shipped():
    a = data.analyze()
    return a.frozen_settings(data.shipped_thresholds_path())


class A3:
    """A3's dossiers, sweeps and per-page metadata (field_ink_share, orientation)."""

    def __init__(self):
        a = data.analyze()
        data.install_fast_curve()
        self.dossiers, self.info = data.load_arm("A3")
        if self.dossiers is None:
            return
        self.sweeps = {c: data.sweep_arm(self.dossiers, self.info, c) for c in a.CHECKS}
        self.pages = {}
        for line in data.load_lines(os.path.join(data.AR, self.info["path"])):
            self.pages[(line["identity"], line["variant"], line["piece"], line["dpi"],
                        line["seed"])] = {"field_ink_share": line.get("field_ink_share"),
                                          "orientation": line["orientation"]}

    def page_of(self, key, variant, piece):
        a = data.analyze()
        return self.pages.get((key[a.IDENTITY_INDEX], variant, piece, key[1], key[4]))

    def positives(self, check, reg, threshold):
        """[(key, variant, piece, target, score, fires)] for every positive target."""
        out = []
        for key, v in sorted(self.sweeps[check][reg].items(), key=lambda kv: repr(kv[0])):
            for (variant, piece, target), s in sorted(v["pos"].items(), key=repr):
                out.append((key, variant, piece, target, s, s > threshold))
        return out


# ------------------------------------------------------------------------------------------

def h1(a3, ship):
    reg, thr = ship["required_field"]
    inst = collections.OrderedDict()
    for key, variant, piece, target, s, fires in a3.positives("required_field", reg, thr):
        page = a3.page_of(key, variant, piece)
        share = page["field_ink_share"] if page else None
        k = (key, variant, piece)
        rec = inst.setdefault(k, {"share": share, "fires": False, "targets": 0, "tp": 0,
                                  "wrong_turn": bool(page and page["orientation"]
                                                     ["wrong_quarter_turn"])})
        rec["fires"] = rec["fires"] or fires
        rec["targets"] += 1
        rec["tp"] += fires
    a = data.analyze()
    idx = a.IDENTITY_INDEX
    measured = {k: r for k, r in inst.items() if r["share"] is not None}
    inked = {k: r for k, r in measured.items() if r["share"] >= H1_INK_MIN}
    clean = {k: r for k, r in measured.items() if r["share"] < H6_NO_INK_MAX}
    kc, nc = collections.Counter(), collections.Counter()
    for k, r in inked.items():
        nc[k[0][idx]] += 1
        kc[k[0][idx]] += r["fires"]
    n = len(inked)
    k_ = sum(r["fires"] for r in inked.values())
    est = k_ / n if n else None
    by_dpi = {}
    for d in sorted({k[0][1] for k in inked}):
        sub = [r for kk, r in inked.items() if kk[0][1] == d]
        by_dpi[str(d)] = {"k": sum(r["fires"] for r in sub), "n": len(sub)}
    t_n = sum(r["targets"] for r in inked.values())
    t_k = sum(r["tp"] for r in inked.values())
    return {
        "criterion": "on A3 pages with field_ink_share >= 0.005 in the emptied required field, "
                     "the shipped required_field sensor's recall is below 0.50",
        "unit": "an (identity, instance, dpi, seed) page; detected when the check fires on at "
                "least one field id of the emptied role (a role can span several ids: the W-9 "
                "tax_id is three comb boxes)",
        "estimate": est, "k": k_, "n": n,
        "interval": interval(k_, n, kc, nc) if n else None,
        "verdict": ("supported" if est < H1_BELOW else "not supported") if n else "not tested",
        "shipped_settings": a.settings_name(reg, "required_field"), "threshold": thr,
        "instances_total": len(inst), "instances_share_not_measured": len(inst) - len(measured),
        "by_dpi": by_dpi,
        "per_target_recall": {"k": t_k, "n": t_n, "estimate": t_k / t_n if t_n else None},
        "exploratory_by_quarter_turn": {
            side: {"k": sum(r["fires"] for r in inked.values() if r["wrong_turn"] == w),
                   "n": sum(1 for r in inked.values() if r["wrong_turn"] == w)}
            for side, w in (("right_turn", False), ("wrong_turn", True))},
        "context_no_ink": {"k": sum(r["fires"] for r in clean.values()), "n": len(clean),
                           "note": "same sensor, pages with field_ink_share < 0.0005"},
        "source": "A3 readings (a3/readings.jsonl), a3/manifest.csv field_ink_share",
    }


def h1_product_view(a3, ship):
    """Sensitivity: the same pages through analyze.frozen_rows() with abstention ON."""
    a = data.analyze()
    refs = data.identities()
    rows = a.frozen_rows(a3.dossiers, refs["reference"], data.shipped_thresholds_path(),
                         ["required_field"], catalog=data.catalog(), ref_of=refs.__getitem__,
                         abstention=True)
    inst = {}
    for r in rows:
        if not r["positive"]:
            continue
        page = a3.page_of(r["key"], r["variant"], r["piece"])
        share = page["field_ink_share"] if page else None
        if share is None or share < H1_INK_MIN:
            continue
        rec = inst.setdefault((r["key"], r["variant"]), {"fires": False, "all_abstained": True})
        rec["fires"] = rec["fires"] or r["fires"]
        rec["all_abstained"] = rec["all_abstained"] and r["abstained"]
    judged = [r for r in inst.values() if not r["all_abstained"]]
    k = sum(r["fires"] for r in judged)
    return {"label": "exploratory sensitivity: abstention on (the product), same pages as H1",
            "n_pages": len(inst), "n_abstained": len(inst) - len(judged), "k": k,
            "n_judged": len(judged), "recall_judged": k / len(judged) if judged else None,
            "recall_abstention_as_miss": k / len(inst) if inst else None}


# ------------------------------------------------------------------------------------------

def unscored_positives(a3):
    """Per check, the damaged targets the shipped sensor returned NO score for (an expiry date
    it could not read, for instance). analyze.measure() leaves them out of the recall, as the
    published grid did; they are counted here, through analyze.frozen_rows() with abstention
    off, so a sensitivity can count them as misses. required_field: pages with
    field_ink_share < 0.0005 only, as in the cell itself."""
    a = data.analyze()
    refs = data.identities()
    rows = a.frozen_rows(a3.dossiers, refs["reference"], data.shipped_thresholds_path(),
                         list(a.CHECKS), catalog=data.catalog(), ref_of=refs.__getitem__,
                         abstention=False)
    out = collections.Counter()
    for r in rows:
        if not r["positive"] or r["score"] is not None:
            continue
        if r["check"] == "required_field":
            page = a3.page_of(r["key"], r["variant"], r["piece"])
            share = page["field_ink_share"] if page else None
            if share is None or share >= H6_NO_INK_MAX:
                continue
        out[r["check"]] += 1
    return out


def a3_cells(a3, ship):
    """Per check, pooled recall and per-target false-alarm rate at the shipped thresholds over
    all of A3; required_field positives restricted to field_ink_share < 0.0005 (PREREG 4.1)."""
    a = data.analyze()
    out = {}
    unscored = unscored_positives(a3)
    for check in a.CHECKS:
        reg, thr = ship[check]
        pc = a3.sweeps[check].get(reg)
        if pc is None:
            raise SystemExit(f"shipped settings of {check} not in the A3 sweep: {reg}")
        kc, nc = collections.Counter(), collections.Counter()
        excluded = 0
        for key, variant, piece, target, s, fires in a3.positives(check, reg, thr):
            if check == "required_field":
                page = a3.page_of(key, variant, piece)
                share = page["field_ink_share"] if page else None
                if share is None or share >= H6_NO_INK_MAX:
                    excluded += 1
                    continue
            nc[key[a.IDENTITY_INDEX]] += 1
            kc[key[a.IDENTITY_INDEX]] += fires
        neg = [x for v in pc.values() for x in v["neg"].values()]
        fp = sum(1 for x in neg if x > thr)
        k, n = sum(kc.values()), sum(nc.values())
        un = unscored.get(check, 0)
        out[check] = {"recall": k / n if n else None, "k": k, "n": n,
                      "positives_unscored": un,
                      "recall_unscored_as_miss": k / (n + un) if (n + un) else None,
                      "interval": interval(k, n, kc, nc) if n else None,
                      "positives_excluded_for_ink": excluded,
                      "false_alarm_rate": fp / len(neg) if neg else None, "fp": fp,
                      "n_neg": len(neg), "false_alarm_wilson_95": list(stats.wilson(fp, len(neg))),
                      "settings": a.settings_name(reg, check), "threshold": thr}
    return out


def read_audit():
    path = os.path.join(data.STUDY, "prereg", "coverage-audit.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def named_cells(audit, source, strict):
    named = set()
    for r in audit:
        if r["predicted_effect"] != "miss":
            continue
        if r["predicted_below_0.90_on"] not in (source, "both"):
            continue
        known = r["known"].strip().lower() == "true"
        if strict and known:
            continue
        if not strict and r["check"] == "required_field" and known:
            continue
        named.add(r["check"])
    return named


def score_h6(cells, audit, source, strict):
    has_pos = {c for c, v in cells.items() if v["n"]}
    failing = {c for c in has_pos if cells[c]["recall"] < FAIL_BELOW}
    named = named_cells(audit, source, strict) & has_pos
    hits = failing & named
    out = {"observed_failing": sorted(failing), "named": sorted(named), "hits": sorted(hits),
           "hits_over_failures": [len(hits), len(failing)],
           "false_predictions_over_predictions": [len(named - failing), len(named)],
           "dropped_no_positive": sorted(set(cells) - has_pos)}
    if not failing:
        out["verdict"] = "not tested"
    else:
        out["estimate"] = len(hits) / len(failing)
        out["verdict"] = "supported" if len(hits) / len(failing) >= 0.5 else "not supported"
    return out


def false_alarm_rows(cells, audit, source):
    out = []
    for r in audit:
        if r["predicted_effect"] != "false_alarm" or r["predicted_below_0.90_on"] not in (source,
                                                                                         "both"):
            continue
        c = cells.get(r["check"])
        rate = c["false_alarm_rate"] if c else None
        out.append({"process": r["process"], "check": r["check"], "rate": rate,
                    "correct": (rate is not None and rate > FALSE_ALARM_ABOVE)})
    return out


def h6(a3_cells_, x2_cells=None):
    audit = read_audit()
    unscored_as_miss = {c: dict(v, recall=v["recall_unscored_as_miss"],
                                n=v["n"] + v["positives_unscored"])
                        for c, v in a3_cells_.items()}
    part = {"primary": score_h6(a3_cells_, audit, "A3", strict=False),
            "strict": score_h6(a3_cells_, audit, "A3", strict=True),
            "sensitivity_unscored_as_miss": score_h6(unscored_as_miss, audit, "A3",
                                                     strict=False),
            "false_alarm_rows": false_alarm_rows(a3_cells_, audit, "A3")}
    res = {"criterion": "the coverage audit names at least half of the (check, source) cells "
                        "where observed recall falls below 0.90 on A3 or X2, excluding the known "
                        "required_field ink failure",
           "A3_part": part}
    if x2_cells is None:
        res["X2_part"] = NOT_YET
        res["verdict"] = NOT_YET
        res["verdict_A3_part"] = part["primary"]["verdict"]
        res["note"] = ("the X2 part waits for the real captures; the A3 part is scored now, by "
                       "the same rule restricted to source A3")
        return res
    xp = {"primary": score_h6(x2_cells, audit, "X2", strict=False),
          "strict": score_h6(x2_cells, audit, "X2", strict=True),
          "false_alarm_rows": false_alarm_rows(x2_cells, audit, "X2")}
    res["X2_part"] = xp
    for scoring in ("primary", "strict"):
        fail = part[scoring]["hits_over_failures"][1] + xp[scoring]["hits_over_failures"][1]
        hit = part[scoring]["hits_over_failures"][0] + xp[scoring]["hits_over_failures"][0]
        res[scoring] = {"hits_over_failures": [hit, fail],
                        "verdict": "not tested" if not fail else
                        ("supported" if hit / fail >= 0.5 else "not supported")}
    res["verdict"] = res["primary"]["verdict"]
    res["verdict_A3_part"] = part["primary"]["verdict"]
    return res


# ------------------------------------------------------------------------------------------

def h5(protocols):
    def crowned(pid):
        p = protocols["protocols"].get(pid)
        if not p or p["folds"][0].get("status") != "run":
            return None, None
        r = p["folds"][0]["rules"]["shipped"]
        return r.get("required_field_ink_crowned"), r.get("required_field_crowned")
    p1_ink, p1 = crowned("P1")
    p5_ink, p5 = crowned("P5")
    res = {"criterion": "under P5 the shipped selection rule does not choose the added-ink sensor "
                        "for required_field, while under P1 it does",
           "P1_crowned": p1, "P5_crowned": p5, "n": None, "estimate": None, "interval": None,
           "source": "results/protocols.json"}
    if p1_ink is None or p5_ink is None:
        res["verdict"] = NOT_YET
    else:
        res["verdict"] = "supported" if (p1_ink and not p5_ink) else "not supported"
    return res


def h2(x2, ship):
    if x2 is None:
        return {"verdict": NOT_YET, "criterion": "pooled recall >= 0.90 over the six content "
                "checks and per-dossier false-alarm rate <= 0.10 on unmarked real captures"}
    rows = []
    for check in x2mod.CONTENT_CHECKS:
        reg, thr = ship[check]
        rows += x2.rows_unmarked(check, reg, thr)
        if check == "required_field":
            rows += x2.rows_marks(reg, thr, steps=(0,))
    pos = [r for r in rows if r["positive"]]
    kc, nc = collections.Counter(), collections.Counter()
    for r in pos:
        nc[repr(r["sheet"])] += 1
        kc[repr(r["sheet"])] += r["fires"]
    k, n = sum(kc.values()), sum(nc.values())
    alarm = collections.defaultdict(bool)
    for r in rows:
        if not r["positive"] and "mark" not in r["sheet"]:
            alarm[r["key"]] = alarm[r["key"]] or r["fires"]
    fa_k, fa_n = sum(alarm.values()), len(alarm)
    recall = k / n if n else None
    fa = fa_k / fa_n if fa_n else None
    ok = recall is not None and fa is not None
    return {"criterion": "pooled recall >= 0.90 and per-dossier false-alarm rate <= 0.10",
            "estimate": recall, "k": k, "n": n, "interval": interval(k, n, kc, nc) if n else None,
            "dossier_false_alarm": {"estimate": fa, "k": fa_k, "n": fa_n,
                                    "wilson_95": list(stats.wilson(fa_k, fa_n))},
            "verdict": ("supported" if recall >= H2_RECALL_MIN and fa <= H2_FA_MAX
                        else "not supported") if ok else "not tested",
            "source": "X2 readings"}


def p1_ocr_thresholds(protocols):
    p = protocols["protocols"].get("P1")
    if not p or p["folds"][0].get("status") != "run":
        return None
    return p["folds"][0]["rules"]["shipped"].get("required_field_per_setting")


def h3(x2, ship, protocols):
    if x2 is None:
        return {"verdict": NOT_YET, "criterion": "on marked emptied fields (mark >= 1% of the "
                "field), shipped ink sensor recall < 0.50 and best OCR sensor recall >= 0.60"}
    from preflight.checks import Settings
    reg, thr = ship["required_field"]

    def recall(reg_, thr_):
        inst = {}
        for m, found, damaged in x2.mark_scores(reg_):
            if not damaged or m["mark_step"] not in (1, 2, 3):
                continue
            if m["mark_ink_share"] is None or float(m["mark_ink_share"]) < H3_MARK_MIN:
                continue
            k = (m["identity"], m["piece"], m["variant"], m["capture"], m["mark_step"])
            inst[k] = any(found.get(t, float("-inf")) > thr_ for t in damaged)
        k_ = sum(inst.values())
        return k_, len(inst)
    ki, ni = recall(reg, thr)
    per = p1_ocr_thresholds(protocols) or {}
    ocr = {}
    for sensor in ("page", "zone", "union"):
        name = f"text_sensor={sensor}, min_conf=0.0"
        if name in per:
            k, n = recall(Settings(text_sensor=sensor, min_conf=0.0), per[name])
            ocr[sensor] = {"k": k, "n": n, "recall": k / n if n else None,
                           "threshold_P1": per[name]}
    best = max(ocr.items(), key=lambda kv: (kv[1]["recall"] or -1)) if ocr else None
    ok = ni and best and best[1]["n"]
    ink_rec = ki / ni if ni else None
    return {"criterion": "shipped ink sensor recall < 0.50 and best OCR sensor recall >= 0.60",
            "ink": {"k": ki, "n": ni, "estimate": ink_rec, "wilson_95": list(stats.wilson(ki, ni))},
            "ocr": ocr, "best_ocr": best[0] if best else None,
            "verdict": ("supported" if ink_rec < H3_INK_BELOW
                        and best[1]["recall"] >= H3_OCR_MIN else "not supported")
            if ok else "not tested", "source": "X2 readings"}


def h4(x2, protocols):
    if x2 is None:
        return {"verdict": NOT_YET, "criterion": "MAE of P1 > MAE of P5 on real captures and the "
                "paired cluster-bootstrap 95% interval of (P1 - P5) lies above zero"}
    from preflight.checks import Settings

    def fold_rules(pid):
        p = protocols["protocols"].get(pid)
        if not p or p["folds"][0].get("status") != "run":
            return None
        return p["folds"][0]["rules"]["shipped"]["checks"]
    p1, p5 = fold_rules("P1"), fold_rules("P5")
    if p1 is None or p5 is None:
        return {"verdict": NOT_YET, "note": "P1 or P5 not run"}
    rows = []
    for pid, ch in (("P1", p1), ("P5", p5)):
        for check, rec in ch.items():
            reg = Settings(**rec["measured_settings"])
            for r in x2.rows(check, reg, rec["threshold"]):
                if r["positive"]:
                    rows.append({"sheet": repr(r["sheet"]), "check": check,
                                 "condition": r["condition"], "fires": r["fires"],
                                 "protocol": pid})
    validated = {pid: {c: rec["validation"]["recall"] for c, rec in ch.items()
                       if rec.get("validation") and rec["validation"].get("n_pos")}
                 for pid, ch in (("P1", p1), ("P5", p5))}

    def diff(rs):
        maes = {}
        for pid in ("P1", "P5"):
            by = collections.defaultdict(list)
            for r in rs:
                if r["protocol"] == pid:
                    by[r["check"]].append({"positive": True, "fires": r["fires"],
                                           "condition": r["condition"]})
            maes[pid] = x2mod.mean_abs_error(by, validated[pid])
        return maes["P1"] - maes["P5"]
    b = stats.cluster_bootstrap(rows, "sheet", diff)
    est = b["point"]
    return {"criterion": "MAE(P1) > MAE(P5) and the paired cluster-bootstrap 95% interval of "
                         "(P1 - P5) lies above zero",
            "estimate": est, "interval": {"cluster_bootstrap_95": [b["lower"], b["upper"]],
                                          "n_clusters": b["n_clusters"]},
            "verdict": "supported" if est > 0 and b["lower"] > 0 else "not supported",
            "source": "results/protocols.json, X2 readings"}


def p_naf():
    d = json.load(open(os.path.join(data.RESULTS, "naf.json"), encoding="utf-8"))
    p, v = d["p_naf"], d["validity"]
    h = p["human_label_secondary"]
    hl = d["human_label_measure"]
    pooled = hl.get("pooled") or {}
    return {"criterion": p["rule"], "band_as_preregistered": p["band"],
            "pixel_share": p["share"], "pixel_wilson_95": [p["wilson_95"]["lower"],
                                                           p["wilson_95"]["upper"]],
            "pixel_cluster_bootstrap_95": [p["cluster_bootstrap_95"]["lower"],
                                           p["cluster_bootstrap_95"]["upper"]],
            "pixel_n_fields": d["counts"]["pixel"]["fields_measured"],
            "verdict": v["p_naf_reported_as"], "pixel_measure_valid": v["pixel_measure_valid"],
            "why": v["reason"],
            "human_label_exploratory_lower_bound": {
                "label": v["human_label_role"], "band": v["human_label_band"],
                "share": h["share"], "k": pooled.get("k"),
                "n": d["counts"]["human_label"]["fields_measured"],
                "wilson_95": [h["wilson_95"]["lower"], h["wilson_95"]["upper"]],
                "cluster_bootstrap_95": [h["cluster_bootstrap_95"]["lower"],
                                         h["cluster_bootstrap_95"]["upper"]],
                "n_images": h["cluster_bootstrap_95"]["n_clusters_images"]},
            "source": "results/naf.json (validity object; prereg amendment A1)"}


# ------------------------------------------------------------------------------------------

def quarter_turns(a3, ship):
    """Exploratory: how often the production path settles on the wrong quarter turn on A3, by
    piece, and whether the pages it happens on carry the misses at the shipped thresholds."""
    a = data.analyze()
    by_piece = collections.defaultdict(lambda: [0, 0])
    kc, nc = collections.Counter(), collections.Counter()
    for (ident, variant, piece, dpi, seed), p in sorted(a3.pages.items(), key=repr):
        wrong = bool(p["orientation"]["wrong_quarter_turn"])
        by_piece[piece][0] += wrong
        by_piece[piece][1] += 1
        kc[ident] += wrong
        nc[ident] += 1
    pieces = {pc: {"k": k, "n": n, "rate": k / n, "wilson_95": list(stats.wilson(k, n))}
              for pc, (k, n) in sorted(by_piece.items())}
    k_all, n_all = sum(kc.values()), sum(nc.values())
    overall = {"k": k_all, "n": n_all, "rate": k_all / n_all,
               "interval": interval(k_all, n_all, kc, nc)}
    by_dpi = collections.defaultdict(lambda: [0, 0])
    for (ident, variant, piece, dpi, seed), p in a3.pages.items():
        by_dpi[str(dpi)][0] += bool(p["orientation"]["wrong_quarter_turn"])
        by_dpi[str(dpi)][1] += 1
    misses = {}
    tot = {"pos_wrong": 0, "pos_right": 0, "miss_wrong": 0, "miss_right": 0}
    for check in a.CHECKS:
        reg, thr = ship[check]
        c = {"pos_wrong": 0, "pos_right": 0, "miss_wrong": 0, "miss_right": 0, "unknown": 0}
        for key, variant, piece, target, s, fires in a3.positives(check, reg, thr):
            page_piece = piece if "+" not in piece else (data.catalog()[variant].piece or piece)
            page = a3.page_of(key, variant, page_piece)
            if page is None:
                c["unknown"] += 1
                continue
            side = "wrong" if page["orientation"]["wrong_quarter_turn"] else "right"
            c[f"pos_{side}"] += 1
            c[f"miss_{side}"] += not fires
        for k_ in tot:
            tot[k_] += c[k_]
        c["recall_wrong_turn"] = (1 - c["miss_wrong"] / c["pos_wrong"]) if c["pos_wrong"] else None
        c["recall_right_turn"] = (1 - c["miss_right"] / c["pos_right"]) if c["pos_right"] else None
        misses[check] = c
    n_miss = tot["miss_wrong"] + tot["miss_right"]
    n_pos = tot["pos_wrong"] + tot["pos_right"]
    return {"label": "exploratory, not preregistered: orientation fields recorded by "
                     "grid/read_images.py on A3",
            "overall": overall, "by_piece": pieces,
            "by_dpi": {d: {"k": k, "n": n, "rate": k / n} for d, (k, n) in sorted(by_dpi.items())},
            "misses_by_check": misses,
            "all_checks": dict(tot, share_of_misses_on_wrong_turn=(tot["miss_wrong"] / n_miss
                                                                  if n_miss else None),
                               share_of_positives_on_wrong_turn=(tot["pos_wrong"] / n_pos
                                                                 if n_pos else None),
                               recall_wrong_turn=(1 - tot["miss_wrong"] / tot["pos_wrong"])
                               if tot["pos_wrong"] else None,
                               recall_right_turn=(1 - tot["miss_right"] / tot["pos_right"])
                               if tot["pos_right"] else None,
                               wilson_recall_wrong_turn=list(stats.wilson(
                                   tot["pos_wrong"] - tot["miss_wrong"], tot["pos_wrong"])),
                               wilson_recall_right_turn=list(stats.wilson(
                                   tot["pos_right"] - tot["miss_right"], tot["pos_right"])))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(data.RESULTS, "hypotheses.json"))
    ap.add_argument("--protocols", default=os.path.join(data.RESULTS, "protocols.json"))
    a_ = ap.parse_args(argv)
    protocols = json.load(open(a_.protocols, encoding="utf-8"))
    ship = shipped()
    a3 = A3()
    if a3.dossiers is None:
        raise SystemExit(f"A3 is {a3.info['status']}")
    x2 = x2mod.X2.load()
    cells = a3_cells(a3, ship)
    x2_cells = None
    if x2 is not None:
        x2_cells = {}
        for check, (reg, thr) in ship.items():
            s = x2.score_choice(check, reg, thr)
            x2_cells[check] = {"recall": s["recall"], "k": s["tp"], "n": s["n_pos"],
                               "false_alarm_rate": s["fpr"]}
    out = {"meta": {"thresholds_sha256": data.SHIPPED_SHA256,
                    "dossier_preflight_commit": data.dp_commit(),
                    "a3": {k: v for k, v in a3.info.items() if k != "variants_missing"},
                    "a3_variants_missing": a3.info["variants_missing"],
                    "x2": x2.info if x2 is not None else {"status": x2mod.status()},
                    "verdict_vocabulary": ["supported", "not supported", "not tested",
                                           NOT_YET, "not interpretable"]},
           "hypotheses": {"H1": h1(a3, ship), "H2": h2(x2, ship), "H3": h3(x2, ship, protocols),
                          "H4": h4(x2, protocols), "H5": h5(protocols),
                          "H6": h6(cells, x2_cells), "P-NAF": p_naf()},
           "a3_cells_at_shipped_thresholds": cells,
           "x2_cells_at_shipped_thresholds": x2_cells if x2_cells is not None else NOT_YET,
           "exploratory": {"h1_product_view": h1_product_view(a3, ship),
                           "quarter_turns_A3": quarter_turns(a3, ship)}}
    data.write_json(a_.out, data.jsonable(out))
    for h, r in out["hypotheses"].items():
        print(f"{h:6s} {r['verdict']:16s} {r.get('estimate')}")
    print(f"-> {a_.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
