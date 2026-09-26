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


def build():
    R = Registry()
    H = json.load(open(os.path.join(data.RESULTS, "hypotheses.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(data.RESULTS, "protocols.json"), encoding="utf-8"))
    v0_numbers(R)
    arm_numbers(R, P)
    hypotheses_numbers(R, H)
    protocol_numbers(R, P)
    census_numbers(R)
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
