#!/usr/bin/env python3
"""The numbers registry: every number the manuscript may quote, from one script.

    python analysis/numbers.py             # writes results/numbers.json

Each key is {"value", "text", "source", "how"}. `text` is what tools/render.py puts in place of
{{key}}; `value` is the raw number (or verdict string); `source` is the file the value was read
from; `how` says how it was derived. The output is deterministic: no clock, no environment, keys
sorted, so two runs on the same inputs give the same bytes (tests/test_numbers.py, and the
audit's `git diff --exit-code results/numbers.json`).

Inputs: results/hypotheses.json, results/protocols.json, results/naf.json, census/*.csv, and
dossier-preflight's COMMITTED results for the v0 numbers the paper keeps (the checks of the v0
prototype's verify_numbers.py), read with `git show` at the tag v0.2.0 when it exists, else at
the commit the preregistration fixes the shipped thresholds at.
"""
import argparse
import ast
import csv
import json
import math
import os
import subprocess
import sys
from collections import Counter

# Run as a script, this folder is sys.path[0], and numbers.py would shadow the standard
# library module of the same name that numpy imports: drop it, put the study root instead.
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import data, stats  # noqa: E402

PREREG_DP_COMMIT = "2235d50abf39d0b0e952fedd082672d7003f25b9"
NOT_YET = "not tested yet"


# ------------------------------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------------------------------

def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (
        isinstance(v, float) and math.isnan(v))


def f3(v):
    return f"{v:.3f}" if is_num(v) else str(v)


def f4(v):
    return f"{v:.4f}" if is_num(v) else str(v)


def count(v):
    return f"{v:,}" if is_num(v) else str(v)


def pct(v, digits=1):
    return f"{100 * v:.{digits}f}%" if is_num(v) else str(v)


def ci(lo, hi, fmt=f3):
    return f"[{fmt(lo)}, {fmt(hi)}]"


def clean(v):
    """A value JSON can hold deterministically: floats rounded to 10 significant decimals."""
    if isinstance(v, float):
        return None if math.isnan(v) else float(f"{v:.10g}")
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    return v


class Registry:
    def __init__(self):
        self.d = {}

    def put(self, key, value, text, source, how):
        if key in self.d:
            raise SystemExit(f"duplicate number key {key}")
        self.d[key] = {"value": clean(value), "text": text, "source": source, "how": how}

    def rate(self, prefix, k, n, source, how, lo=None, hi=None, fmt=f3):
        """A proportion: its value, k, n, and its Wilson interval (or the one given)."""
        if n:
            v = k / n
            wl, wh = stats.wilson(k, n) if lo is None else (lo, hi)
            self.put(prefix, v, fmt(v), source, how)
            self.put(prefix + ".k", k, count(k), source, "numerator of " + prefix)
            self.put(prefix + ".n", n, count(n), source, "denominator of " + prefix)
            self.put(prefix + ".ci", [wl, wh], ci(wl, wh, fmt), source,
                     "Wilson 95% score interval" if lo is None else "interval as given")
        else:
            self.put(prefix, None, "n/a", source, how + " (empty denominator)")


# ------------------------------------------------------------------------------------------
# v0: dossier-preflight's committed results
# ------------------------------------------------------------------------------------------

def dp_ref():
    tags = subprocess.run(["git", "-C", data.DP, "tag", "-l", "v0.2.0"], capture_output=True,
                          text=True, check=True).stdout.split()
    return "v0.2.0" if tags else PREREG_DP_COMMIT


def dp_show(ref, path):
    return subprocess.run(["git", "-C", data.DP, "show", f"{ref}:{path}"], capture_output=True,
                          text=True, check=True).stdout


def constants(text, names):
    out = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id in names:
                out[t.id] = ast.literal_eval(node.value)
    return out


def v0_numbers(R):
    ref = dp_ref()
    src = f"dossier-preflight@{ref}"
    run = constants(dp_show(ref, "grid/run.py"),
                    {"ANGLES", "DPIS", "JPEGS", "SIGMAS", "SEEDS", "PARASITE_LEVELS",
                     "SUB_ANGLES", "SUB_DPIS", "SUB_JPEGS", "SUB_SIGMAS"})
    cells = len(run["ANGLES"]) * len(run["DPIS"]) * len(run["JPEGS"]) * len(run["SIGMAS"])
    R.put("v0.grid.cells", cells, count(cells), f"{src}:grid/run.py", "product of the four "
          "factor level counts")
    R.put("v0.grid.seeds", len(run["SEEDS"]), count(len(run["SEEDS"])), f"{src}:grid/run.py",
          "len(SEEDS)")
    R.put("v0.grid.readings", cells * 3 * 13, count(cells * 3 * 13), f"{src}:grid/run.py",
          "cells x 3 seeds x 13 readings")
    dom = len(run["ANGLES"]) * len([d for d in run["DPIS"] if d >= 150]) * len(run["JPEGS"]) \
        * len(run["SIGMAS"])
    R.put("v0.grid.domain_cells", dom, count(dom), f"{src}:grid/run.py", "cells at dpi >= 150")
    sub = len(run["SUB_ANGLES"]) * len(run["SUB_DPIS"]) * len(run["SUB_JPEGS"]) \
        * len(run["SUB_SIGMAS"])
    R.put("v0.grid.parasite_readings", sub * 3 * 3 * 13, count(sub * 3 * 3 * 13),
          f"{src}:grid/run.py", "sub-grid cells x 3 seeds x 3 levels x 13 readings")
    an = constants(dp_show(ref, "grid/analyze.py"), {"FP_BUDGET", "RECALL_FLOOR",
                                                     "VALIDATION_SEED"})
    R.put("v0.fp_budget", an["FP_BUDGET"], pct(an["FP_BUDGET"]), f"{src}:grid/analyze.py",
          "FP_BUDGET, false positives per target")
    R.put("v0.recall_floor", an["RECALL_FLOOR"], pct(an["RECALL_FLOOR"], 0),
          f"{src}:grid/analyze.py", "RECALL_FLOOR")
    res = json.loads(dp_show(ref, "grid/results/resume.json"))
    rs = f"{src}:grid/results/resume.json"
    R.put("v0.checks", len(res), count(len(res)), rs, "checks in resume.json")
    perfect = [c for c, r in res.items() if r["validation"]["tp"] == r["validation"]["n_pos"]
               and r["validation"]["fp"] == 0]
    R.put("v0.checks_perfect", len(perfect), count(len(perfect)), rs,
          "checks at full recall and zero false positives on seed 37")
    rf = res["required_field"]["validation"]
    R.rate("v0.required_field.validation_recall", rf["tp"], rf["n_pos"], rs,
           "shipped required_field, seed 37", fmt=f3)
    fv = res["forbidden_value"]["validation"]
    R.rate("v0.forbidden_value.validation_recall", fv["tp"], fv["n_pos"], rs,
           "forbidden_value, seed 37")
    thr = json.loads(dp_show(ref, "thresholds.json"))["thresholds"]
    R.put("v0.required_field.threshold_pct", -thr["required_field"]["value"],
          f"{-thr['required_field']['value']:.3f}%", f"{src}:thresholds.json",
          "added ink share below which the field is called empty")
    R.put("v0.resolution.threshold_dpi", -thr["resolution"]["value"],
          f"{-thr['resolution']['value']:.1f}", f"{src}:thresholds.json", "dpi floor")
    probe = [json.loads(x) for x in dp_show(ref, "parasitic-ink-probe/results.jsonl")
             .splitlines() if x.strip()]
    ps = f"{src}:parasitic-ink-probe/results.jsonl"
    R.put("v0.probe.readings", len(probe), count(len(probe)), ps, "lines")
    empty = [r for r in probe if r["shape"] and r["variant"] == "empty_required_field"
             and (r["added_ink"] or 0) >= 0.5]
    for s in ("ink", "union", "page", "zone"):
        k = sum(not r[s]["fires"] for r in empty)
        R.rate(f"v0.probe.false_negative_rate.{s}", k, len(empty), ps,
               f"emptied field with >= 0.5% foreign ink read as filled by the {s} sensor")
    tp = json.loads(dp_show(ref, "grid/results/target_parasite.json"))
    s = tp["checks"]["required_field"]["sensors"]["ink"]["0.01"]["variant"]
    R.rate("v0.targeted.ink_recall_at_1pct", s["fired"], s["n"],
           f"{src}:grid/results/target_parasite.json",
           "targeted run: ink sensor recall with 1% foreign ink on the emptied field", fmt=f4)
    R.put("v0.source_ref", ref, ref, src, "the dossier-preflight ref the v0 numbers are read at")


# ------------------------------------------------------------------------------------------
# This study
# ------------------------------------------------------------------------------------------

def interval_pair(iv, which):
    x = (iv or {}).get(which)
    return (x[0], x[1]) if x else (None, None)


def hypotheses_numbers(R, H):
    src = "results/hypotheses.json"
    h = H["hypotheses"]
    for name, r in h.items():
        key = name.lower().replace("-", "_")
        R.put(f"{key}.verdict", r["verdict"], r["verdict"], src, "by the PREREG criterion")
    h1 = h["H1"]
    if h1.get("n"):
        lo, hi = interval_pair(h1["interval"], "wilson_95")
        R.rate("h1.recall", h1["k"], h1["n"], src, "shipped required_field recall on A3 pages "
               "with >= 0.5% Augraphy ink in the emptied field")
        blo, bhi = interval_pair(h1["interval"], "cluster_bootstrap_95")
        R.put("h1.recall.boot", [blo, bhi], ci(blo, bhi), src,
              "identity-cluster bootstrap, 10,000 resamples, seed 20260925")
        R.put("h1.pages_not_measured", h1["instances_share_not_measured"],
              count(h1["instances_share_not_measured"]), src,
              "required_field pages whose field_ink_share could not be registered")
        c = h1["context_no_ink"]
        R.rate("h1.recall_no_ink", c["k"], c["n"], src,
               "same sensor on A3 pages with < 0.05% ink in the emptied field")
    h5 = h["H5"]
    R.put("h5.p1_crowned", h5.get("P1_crowned"), str(h5.get("P1_crowned")), src,
          "required_field setting the shipped rule retains under P1")
    R.put("h5.p5_crowned", h5.get("P5_crowned"), str(h5.get("P5_crowned")), src,
          "required_field setting the shipped rule retains under P5")
    h6 = h["H6"]["A3_part"]
    for scoring in ("primary", "strict"):
        p = h6[scoring]
        hk, hn = p["hits_over_failures"]
        fk, fn = p["false_predictions_over_predictions"]
        R.put(f"h6.a3.{scoring}.hits", [hk, hn], f"{hk} of {hn}", src,
              "observed failing A3 cells the audit named, over observed failing cells")
        R.put(f"h6.a3.{scoring}.false_predictions", [fk, fn], f"{fk} of {fn}", src,
              "named A3 cells not observed failing, over named cells")
        R.put(f"h6.a3.{scoring}.verdict", p["verdict"], p["verdict"], src,
              "H6 criterion on the A3 part only")
    for name in ("H2", "H3", "H4"):
        r = h[name]
        if r["verdict"] == NOT_YET or not is_num(r.get("estimate")):
            continue
        R.put(f"{name.lower()}.estimate", r["estimate"], f3(r["estimate"]), src,
              "point estimate by the PREREG criterion")
    pn = h["P-NAF"]
    R.put("pnaf.band_as_preregistered", pn["band_as_preregistered"], pn["band_as_preregistered"],
          src, "the preregistered band applied to the pixel measure, kept on record")
    R.put("pnaf.pixel_share", pn["pixel_share"], pct(pn["pixel_share"]), src,
          "pixel measure, invalid (template residue)")
    hl = pn["human_label_exploratory_lower_bound"]
    R.rate("pnaf.human_label_share", hl["k"], hl["n"], src,
           "exploratory lower bound: NAF comment polygon on >= 1% of a blank field",
           lo=hl["wilson_95"][0], hi=hl["wilson_95"][1], fmt=lambda v: pct(v, 2))
    R.put("pnaf.human_label_share.boot", hl["cluster_bootstrap_95"],
          ci(*hl["cluster_bootstrap_95"], fmt=lambda v: pct(v, 2)), src,
          "image-cluster bootstrap")
    R.put("pnaf.human_label_images", hl["n_images"], count(hl["n_images"]), src, "images")

    cells = H["a3_cells_at_shipped_thresholds"]
    for check, c in cells.items():
        if c["n"]:
            R.rate(f"a3.shipped.{check}.recall", c["k"], c["n"], src,
                   "pooled recall at the shipped thresholds over A3 (required_field: pages "
                   "with < 0.05% ink in the emptied field)")
        R.rate(f"a3.shipped.{check}.false_alarm", c["fp"], c["n_neg"], src,
               "per-target false-alarm rate on A3 clean pieces", fmt=f4)

    q = H["exploratory"]["quarter_turns_A3"]
    o = q["overall"]
    R.rate("explore.quarter_turn.wrong", o["k"], o["n"], src,
           "exploratory: A3 pages read at the wrong quarter turn")
    lo, hi = o["interval"]["cluster_bootstrap_95"]
    R.put("explore.quarter_turn.wrong.boot", [lo, hi], ci(lo, hi), src, "identity bootstrap")
    for piece, p in q["by_piece"].items():
        R.rate(f"explore.quarter_turn.wrong.{piece}", p["k"], p["n"], src,
               f"exploratory: {piece} pages read at the wrong quarter turn")
    t = q["all_checks"]
    R.put("explore.quarter_turn.share_of_misses", t["share_of_misses_on_wrong_turn"],
          f3(t["share_of_misses_on_wrong_turn"]), src,
          "exploratory: misses (all checks, shipped thresholds) on wrong-turn pages, over misses")
    R.put("explore.quarter_turn.share_of_positives", t["share_of_positives_on_wrong_turn"],
          f3(t["share_of_positives_on_wrong_turn"]), src,
          "exploratory: positives on wrong-turn pages, over positives")
    for side in ("wrong", "right"):
        k = t[f"pos_{side}"] - t[f"miss_{side}"]
        R.rate(f"explore.quarter_turn.recall_{side}_turn", k, t[f"pos_{side}"], src,
               f"exploratory: recall over every check's positives on {side}-turn pages")
    pv = H["exploratory"]["h1_product_view"]
    R.put("explore.h1_product.abstained", pv["n_abstained"], count(pv["n_abstained"]), src,
          "H1 pages the product refuses to judge (abstention on)")


def protocol_numbers(R, P):
    src = "results/protocols.json"
    for pid, p in P["protocols"].items():
        for f in p["folds"]:
            tag = f["fold"].replace("/", ".").replace("=", "_")
            if f.get("status") != "run":
                R.put(f"protocol.{tag}.status", f["status"], f["status"], src, "fold status")
                continue
            for rule, r in f["rules"].items():
                base = f"protocol.{tag}.{rule}"
                if rule.startswith("B3_"):
                    v = r["validation"]
                    R.rate(base + ".required_field.validation_recall", v["tp"], v["n_pos"], src,
                           f"{rule} validated recall")
                    t = (r.get("targets") or {}).get("A3_seed37")
                    if isinstance(t, dict) and t.get("n_pos"):
                        R.rate(base + ".required_field.a3_recall", t["tp"], t["n_pos"], src,
                               f"{rule} recall on A3 seed 37")
                    continue
                rf = r["checks"].get("required_field")
                if rf:
                    R.put(base + ".required_field.crowned", rf["settings"], rf["settings"], src,
                          "setting retained for required_field")
                    v = rf["validation"]
                    if v and v["n_pos"]:
                        R.rate(base + ".required_field.validation_recall", v["tp"], v["n_pos"],
                               src, "validated recall on the protocol's report set")
                    t = rf["targets"].get("A3_seed37")
                    if isinstance(t, dict) and t.get("n_pos"):
                        R.rate(base + ".required_field.a3_recall", t["tp"], t["n_pos"], src,
                               "recall of that choice on A3 seed 37")
                e = r.get("errors_A3_seed37")
                if e and e.get("mean_recall_abs_error") is not None:
                    R.put(base + ".mae_a3", e["mean_recall_abs_error"],
                          f3(e["mean_recall_abs_error"]), src,
                          "mean over checks of |validated recall - A3 seed 37 recall|")
                if "release_gate_0.90_blocks_required_field" in r:
                    b = r["release_gate_0.90_blocks_required_field"]
                    R.put(base + ".gate_blocks_required_field", b, "yes" if b else "no", src,
                          "a release gate at recall 0.90 on the report set blocks required_field")


def census_numbers(R):
    src1 = "census/coder1.csv"
    rows = list(csv.DictReader(open(os.path.join(data.STUDY, "census", "sheet.csv"),
                                    encoding="utf-8")))
    R.put("census.episodes", len(rows), count(len(rows)), "census/sheet.csv", "episodes")
    tiers = Counter(r["tier"] for r in rows)
    for t, n in sorted(tiers.items()):
        R.put(f"census.tier.{t}", n, count(n), "census/sheet.csv", f"episodes of tier {t}")
    pop = list(csv.DictReader(open(os.path.join(data.STUDY, "census", "population.csv"),
                                   encoding="utf-8")))
    inc = sum(1 for r in pop if r["include"].strip().lower() == "true")
    R.put("census.population", len(pop), count(len(pop)), "census/population.csv", "repos")
    R.put("census.included", inc, count(inc), "census/population.csv", "repos included")
    c1 = {r["episode_id"]: r["code_first"] for r in csv.DictReader(
        open(os.path.join(data.STUDY, "census", "coder1.csv"), encoding="utf-8"))}
    for code, n in sorted(Counter(c1.values()).items()):
        R.put(f"census.coder1.{code}", n, count(n), src1,
              f"episodes coder 1 coded {code} first (coder 1 only, before agreement)")
    c2p = os.path.join(data.STUDY, "census", "coder2.csv")
    if not os.path.exists(c2p):
        R.put("census.kappa", None, "pending coder 2", src1, "Cohen's kappa needs coder 2")
        return
    c2 = {r["episode_id"]: r["code_first"] for r in csv.DictReader(open(c2p, encoding="utf-8"))}
    pairs = [(c1[e], c2[e]) for e in sorted(c1) if e in c2]
    b = stats.kappa_bootstrap(pairs)
    R.put("census.kappa", b["point"], f"{b['point']:.2f}", "census/coder1.csv, coder2.csv",
          "Cohen's kappa on the first code")
    R.put("census.kappa.boot", [b["lower"], b["upper"]],
          f"[{b['lower']:.2f}, {b['upper']:.2f}]", "census/coder1.csv, coder2.csv",
          "bootstrap over episodes")


def arm_numbers(R, P):
    src = "results/protocols.json"
    for arm, info in P["meta"]["arms"].items():
        R.put(f"arm.{arm}.status", info["status"], info["status"], src, "arm on disk")
        if info.get("dossiers") is not None:
            R.put(f"arm.{arm}.dossiers", info["dossiers"], count(info["dossiers"]), src,
                  "dossiers (key = cell, seed, identity) assembled")
    R.put("arm.A3.images_not_read", len(P["meta"]["a3_variants_missing"]),
          count(len(P["meta"]["a3_variants_missing"])), src,
          "A3 images whose reading raised (grid/read_images.py errors file)")
    R.put("arm.X2.status", P["meta"]["x2"].get("status"), P["meta"]["x2"].get("status"), src,
          "X2 on disk")


# ------------------------------------------------------------------------------------------
# Numbers added for the claims map (CLAIMS.md "Numbers to add", T20)
# ------------------------------------------------------------------------------------------

def a4_numbers(R, tallied=None):
    """A4 per check, per ink level, pooled and per shape (analysis/a4.py)."""
    from analysis import a4
    t = a4.compute() if tallied is None else tallied
    if t is None:
        R.put("a4.status", "absent", "absent", "a4/readings.jsonl.gz", "A4 not on disk")
        return
    src = "a4/readings.jsonl.gz (analysis/a4.py)"
    for check, c in sorted(t.items()):
        for side, name in (("variant", "recall"), ("clean", "false_alarm")):
            for lv, (k, n) in sorted(c["pooled"].get(side, {}).items()):
                R.rate(f"a4.{check}.{name}.at_{a4.level_tag(lv)}", k, n, src,
                       f"shipped {check} at the shipped threshold, abstention off, foreign ink "
                       f"at level {lv} laid on the damaged zone, every shape pooled "
                       f"({'damaged' if side == 'variant' else 'clean'} dossier)")
            for shape, d in sorted(c["by_shape"].items()):
                for lv, (k, n) in sorted(d.get(side, {}).items()):
                    R.rate(f"a4.{check}.{name}.{shape}.at_{a4.level_tag(lv)}", k, n, src,
                           f"as a4.{check}.{name}.at_<level>, {shape} shape only")


def dossier_rate(R, prefix, t, source, how):
    """A per-dossier false-alarm rate stored as (dossier_fpr, n_dossiers): k is recovered."""
    n = t["n_dossiers"]
    k = round(t["dossier_fpr"] * n)
    if abs(k - t["dossier_fpr"] * n) > 1e-6:
        raise SystemExit(f"{prefix}: dossier_fpr x n_dossiers is not an integer")
    R.rate(prefix, k, n, source, how)


def protocol_extra_numbers(R, P):
    """Domain per fold, false-alarm cost on A3 and on validation, MAE of dossier false alarms."""
    src = "results/protocols.json"
    for pid, p in P["protocols"].items():
        for f in p["folds"]:
            if f.get("status") != "run":
                continue
            tag = f["fold"].replace("/", ".").replace("=", "_")
            base = f"protocol.{tag}"
            att = f.get("domain_attempts") or []
            R.put(base + ".domain_dpi", f.get("domain"), count(f.get("domain")), src,
                  "dpi floor the dossier-level domain rule settled on (the validated figures "
                  "are over dpi at or above it)")
            R.put(base + ".domain_attempts", att,
                  ", ".join(f"{d} dpi {f3(r)}" for d, r in att), src,
                  "complete-dossier recall per candidate dpi floor, in the order tried")
            fb = bool(att) and all(r == 0 for _, r in att)
            R.put(base + ".domain_fallback", fb, "yes" if fb else "no", src,
                  "every candidate floor had complete-dossier recall 0, so the rule fell back")
            for rule, r in f["rules"].items():
                rb = f"{base}.{rule}.required_field"
                if rule.startswith("B3_"):
                    sets = {"validation": r.get("validation"),
                            "a3": (r.get("targets") or {}).get("A3_seed37")}
                else:
                    rf = r["checks"].get("required_field") or {}
                    sets = {"validation": rf.get("validation"),
                            "a3": (rf.get("targets") or {}).get("A3_seed37")}
                for where, t in sets.items():
                    if not isinstance(t, dict) or not t.get("n_neg"):
                        continue
                    label = "A3 seed 37" if where == "a3" else "the protocol's report set"
                    R.rate(f"{rb}.{where}_fpr", t["fp"], t["n_neg"], src,
                           f"{rule}: false alarms per clean required field on {label}", fmt=f3)
                    if t.get("n_dossiers"):
                        dossier_rate(R, f"{rb}.{where}_dossier_fpr", t, src,
                                     f"{rule}: clean dossiers with at least one required_field "
                                     f"false alarm on {label}")
                e = r.get("errors_A3_seed37")
                if e and e.get("mean_dossier_fpr_abs_error") is not None:
                    R.put(f"{base}.{rule}.mae_dossier_fpr_a3", e["mean_dossier_fpr_abs_error"],
                          f3(e["mean_dossier_fpr_abs_error"]), src,
                          "mean over checks of |validated - A3 seed 37 per-dossier false-alarm "
                          "rate|")


def hypotheses_extra_numbers(R, H):
    src = "results/hypotheses.json"
    h1 = H["hypotheses"]["H1"]
    for side, v in sorted(h1.get("exploratory_by_quarter_turn", {}).items()):
        R.rate(f"h1.recall.{side}", v["k"], v["n"], src,
               f"exploratory: H1 recall on pages the tool read at the {side.replace('_', ' ')}")
    for dpi, v in sorted(h1.get("by_dpi", {}).items(), key=lambda kv: int(kv[0])):
        R.rate(f"h1.recall.by_dpi.{dpi}", v["k"], v["n"], src, f"H1 recall at {dpi} dpi")
    q = H["exploratory"]["quarter_turns_A3"]
    for check, m in sorted(q["misses_by_check"].items()):
        for side in ("right", "wrong"):
            n = m[f"pos_{side}"]
            if n:
                R.rate(f"explore.quarter_turn.{check}.recall_{side}_turn",
                       n - m[f"miss_{side}"], n, src,
                       f"exploratory: {check} recall at the shipped thresholds on A3 pages read "
                       f"at the {side} quarter turn")
    for dpi, v in sorted(q["by_dpi"].items(), key=lambda kv: int(kv[0])):
        R.rate(f"explore.quarter_turn.wrong.by_dpi.{dpi}", v["k"], v["n"], src,
               f"exploratory: A3 pages read at the wrong quarter turn, {dpi} dpi")
    p = H["hypotheses"]["H6"]["A3_part"]["primary"]
    for name in ("named", "observed_failing", "hits"):
        R.put(f"h6.a3.{name}", p[name], ", ".join(p[name]), src,
              f"H6 A3 part, primary scoring: {name.replace('_', ' ')} (checks, in order)")


def naf_numbers(R):
    src = "results/naf.json"
    pn = json.load(open(os.path.join(data.RESULTS, "naf.json"), encoding="utf-8"))["p_naf"]
    pix = os.path.join(data.AR, "x3", "naf_fields_pixel.csv")
    rows = list(csv.DictReader(open(pix, encoding="utf-8")))
    k = sum(r["above_0.345pct"] == "True" for r in rows)
    if abs(k / len(rows) - pn["share"]) > 1e-12:
        raise SystemExit("naf_fields_pixel.csv disagrees with results/naf.json p_naf.share")
    s = "x3/naf_fields_pixel.csv (= results/naf.json p_naf)"
    R.put("pnaf.pixel_share.k", k, count(k), s, "numerator of pnaf.pixel_share")
    R.put("pnaf.pixel_share.n", len(rows), count(len(rows)), s, "denominator of pnaf.pixel_share")
    w = pn["wilson_95"]
    R.put("pnaf.pixel_share.ci", [w["lower"], w["upper"]],
          ci(w["lower"], w["upper"], fmt=lambda v: pct(v, 1)), src, "Wilson 95% as stored")
    med = [r for r in rows if r["image_id"] == r["medoid_id"]]
    mk = sum(r["above_0.345pct"] == "True" for r in med)
    R.put("pnaf.audit.medoid_positive", [mk, len(med)], f"{mk} of {len(med)}",
          "x3/naf_fields_pixel.csv", "medoid fields (registered against themselves) the pixel "
          "measure still calls positive")
    audit = list(csv.DictReader(open(os.path.join(data.RESULTS, "naf-crop-audit.csv"),
                                     encoding="utf-8")))
    nc = [r for r in audit if r["sample"] == "no_comment"]
    for label, key in (("residue", "residue_only"), ("real_mixed", "real_mixed")):
        n = sum(r["label"] == label for r in nc)
        R.put(f"pnaf.audit.{key}", [n, len(nc)], f"{n} of {len(nc)}",
              "results/naf-crop-audit.csv", f"crop audit read by eye, no-comment fields: {label}")
    var = list(csv.DictReader(open(os.path.join(data.RESULTS, "naf-variants.csv"),
                                   encoding="utf-8")))
    variants = {"no_dilation": ("0", "False"), "dilation_3": ("3", "False"),
                "dilation_3_loo": ("3", "True"), "dilation_6": ("6", "False")}
    for tname, t in (("0.345pct", 0.00345), ("1pct", 0.01), ("4pct", 0.04)):
        for vname, (rad, loo) in variants.items():
            sub = [r for r in var if r["radius"] == rad and r["loo"] == loo]
            n = sum(float(r["share"]) >= t for r in sub)
            R.put(f"pnaf.sensitivity.{vname}.{tname}", [n, len(sub)], f"{n} of {len(sub)}",
                  "results/naf-variants.csv (naf/diagnostics/crop_audit.py)",
                  f"fields at or above {tname} added ink, consensus variant {vname}")
        sub = [r for r in var if r["radius"] == "3" and r["loo"] == "False"]
        n = sum((int(r["added"]) - int(r["near8"])) / int(r["area"]) >= t for r in sub)
        R.put(f"pnaf.sensitivity.far8.{tname}", [n, len(sub)], f"{n} of {len(sub)}",
              "results/naf-variants.csv (naf/diagnostics/crop_audit.py)",
              f"fields at or above {tname}, 3 px consensus, counting only added ink more than "
              "8 px from any template ink")


def arm_reading_numbers(R):
    for arm, want in sorted(data.DECLARED_LINES.items()):
        path = data.arm_path(arm)
        if path is None:
            continue
        n = data.count_lines(path)
        errors = path + ".errors.jsonl"
        e = data.count_lines(errors) if os.path.exists(errors) else 0
        if n + e != want:
            raise SystemExit(f"{arm}: {n} lines + {e} errors, the preregistration declares {want}")
        R.put(f"arm.{arm}.readings", n, count(n), os.path.relpath(path, data.AR),
              "non-empty lines of the arm file (read errors excluded), asserted to add up with "
              "the error file to the declared size")


def prereg_numbers(R):
    from analysis import hypotheses
    audit = hypotheses.read_audit()
    src = "prereg/coverage-audit.csv"
    R.put("prereg.audit.rows", len(audit), count(len(audit)), src, "rows")
    below = sum(r["predicted_below_0.90_on"].strip() != "none" for r in audit)
    R.put("prereg.audit.below_090", below, count(below), src,
          "rows predicting recall below 0.90 on A3, X2 or both")
    for source in ("A3", "X2"):
        named = sorted(hypotheses.named_cells(audit, source, strict=False))
        R.put(f"prereg.audit.named_h6.{source}", named, ", ".join(named), src,
              f"checks the audit names as failing on {source}, known required_field ink excluded")


def census_tool_status(sheet, first_code, tiers=("T-A", "T-B")):
    """{repo: "contradicted" | "agree" | "no objective or human episode"} and the contradicted
    episodes. A tool is contradicted when any episode of an allowed tier has a first code other
    than M0, agrees when every such episode is M0."""
    by_tool, contra = {}, []
    for r in sheet:
        by_tool.setdefault(r["repo"], [])
        if r["tier"] not in tiers:
            continue
        code = first_code[r["episode_id"]]
        by_tool[r["repo"]].append(code)
        if code != "M0":
            contra.append(r["episode_id"])
    status = {t: ("no objective or human episode" if not c else
                  "agree" if all(x == "M0" for x in c) else "contradicted")
              for t, c in by_tool.items()}
    return status, contra


def census_extra_numbers(R):
    base = os.path.join(data.STUDY, "census")
    sheet = list(csv.DictReader(open(os.path.join(base, "sheet.csv"), encoding="utf-8")))
    resolved = os.path.join(base, "resolved.csv")
    coder1 = list(csv.DictReader(open(os.path.join(base, "coder1.csv"), encoding="utf-8")))
    if os.path.exists(resolved):
        codes = list(csv.DictReader(open(resolved, encoding="utf-8")))
        src, who = "census/sheet.csv, census/resolved.csv", "resolved codes"
    else:
        codes = coder1
        src, who = "census/sheet.csv, census/coder1.csv", "coder 1 only, single coder, before " \
            "agreement"
    first = {r["episode_id"]: r["code_first"] for r in codes}
    status, contra = census_tool_status(sheet, first)
    tools_c = sorted(t for t, s in status.items() if s == "contradicted")
    tools_a = sorted(t for t, s in status.items() if s == "agree")
    R.put("census.tools_contradicted_ab", len(tools_c), count(len(tools_c)), src,
          f"tools with a tier T-A or T-B episode whose first code is not M0 ({who})")
    R.put("census.tools_contradicted_ab.list", tools_c, ", ".join(tools_c), src, who)
    R.put("census.tools_agree_ab", len(tools_a), count(len(tools_a)), src,
          f"tools whose every tier T-A or T-B episode is coded M0 ({who})")
    R.put("census.tools_agree_ab.list", tools_a, ", ".join(tools_a), src, who)
    R.put("census.episodes_contradicted_ab", len(contra), count(len(contra)), src,
          f"tier T-A or T-B episodes whose first code is not M0 ({who})")
    for tier in sorted({r["tier"] for r in sheet}):
        eps = [r for r in sheet if r["tier"] == tier]
        n = sum(first[r["episode_id"]] != "M0" for r in eps)
        R.put(f"census.contradicted.{tier}", [n, len(eps)], f"{n} of {len(eps)}", src,
              f"tier {tier} episodes whose first code is not M0 ({who})")
    for tool, s in sorted(status.items()):
        R.put(f"census.tool.{tool}.status_ab", s, s, src, f"on tiers T-A and T-B ({who})")
        _, c_all = census_tool_status([r for r in sheet if r["repo"] == tool], first,
                                      tiers=("T-A", "T-B", "T-C"))
        R.put(f"census.tool.{tool}.contradicted_any_tier", len(c_all), count(len(c_all)), src,
              f"episodes of any tier whose first code is not M0 ({who})")
    for tool in sorted(status):
        for tier in sorted({r["tier"] for r in sheet}):
            eps = [r for r in sheet if r["repo"] == tool and r["tier"] == tier]
            if eps:
                n = sum(first[r["episode_id"]] != "M0" for r in eps)
                R.put(f"census.tool.{tool}.contradicted.{tier}", [n, len(eps)],
                      f"{n} of {len(eps)}", src,
                      f"tier {tier} episodes of {tool} whose first code is not M0 ({who})")
    R.put("census.resolved.basis", who, who, src, "what the census.resolved.* counts rest on")
    for code, n in sorted(Counter(first.values()).items()):
        R.put(f"census.resolved.{code}", n, count(n), src, f"first codes ({who})")
    for code, n in sorted(Counter(r["code_second"] for r in coder1 if r["code_second"]).items()):
        R.put(f"census.coder1.second.{code}", n, count(n), "census/coder1.csv",
              "episodes coder 1 gave this second code (coder 1 only)")
    for r in sheet:
        e = r["episode_id"]
        R.put(f"census.{e}.claim_text", r["self_generated_claim"], r["self_generated_claim"],
              "census/sheet.csv", "the self-generated claim, quoted at the pinned commit")
        R.put(f"census.{e}.finding_text", r["independent_finding"], r["independent_finding"],
              "census/sheet.csv", "the independent finding, quoted at the pinned commit")


def shipped_failure_numbers(R):
    """The failure metric as dossier-preflight ships it in thresholds.json, per tag."""
    for tag, prefix in (("v0.1.0", "v0.shipped"), ("v0.2.0", "v020.shipped")):
        tags = subprocess.run(["git", "-C", data.DP, "tag", "-l", tag], capture_output=True,
                              text=True, check=True).stdout.split()
        if not tags:
            R.put(f"{prefix}.status", "not tagged", "not tagged", f"dossier-preflight@{tag}",
                  "tag absent")
            continue
        src = f"dossier-preflight@{tag}:thresholds.json"
        th = json.loads(dp_show(tag, "thresholds.json"))["thresholds"]
        for check, t in sorted(th.items()):
            v = t.get("recall_with_ink_on_the_damaged_field")
            if not isinstance(v, dict):
                continue
            for lv, rate in sorted(v.items(), key=lambda kv: float(kv[0])):
                R.put(f"{prefix}.{check}.recall_with_ink_on_the_damaged_field.{lv}", rate,
                      f4(rate), src, "the stored value per ink level")
            d = t.get("ink_on_the_damaged_field")
            if isinstance(d, dict):
                for shape, levels in sorted(d.get("by_shape", {}).items()):
                    for lv, c in sorted(levels.items(), key=lambda kv: float(kv[0])):
                        R.put(f"{prefix}.{check}.ink_on_the_damaged_field.{shape}.{lv}",
                              [c["k"], c["n"]], f"{c['k']} of {c['n']}", src,
                              "the stored per-shape count")


def build():
    R = Registry()
    H = json.load(open(os.path.join(data.RESULTS, "hypotheses.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(data.RESULTS, "protocols.json"), encoding="utf-8"))
    v0_numbers(R)
    arm_numbers(R, P)
    arm_reading_numbers(R)
    hypotheses_numbers(R, H)
    hypotheses_extra_numbers(R, H)
    protocol_numbers(R, P)
    protocol_extra_numbers(R, P)
    census_numbers(R)
    census_extra_numbers(R)
    a4_numbers(R)
    naf_numbers(R)
    prereg_numbers(R)
    shipped_failure_numbers(R)
    return R.d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(data.RESULTS, "numbers.json"))
    a = ap.parse_args(argv)
    d = build()
    text = json.dumps(d, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"{len(d)} numbers -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
