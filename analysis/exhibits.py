#!/usr/bin/env python3
"""The tables and the one figure, from the analysis outputs.

    python analysis/exhibits.py

Writes results/tables/protocols.md, results/tables/hypotheses.md, results/tables/quarter_turns.md
and results/figure1.png / figure1.svg plus the points it plots (results/figure1.json).

THE FIGURE: recall of the shipped required_field sensor (ink added in the field at level 128,
fires below 0.345% of the zone) against the ink share in the emptied field, one line per source.
- G0: the published targeted run, whose raw rows A4 re-created (the A0 grid itself never lays ink
  ON the emptied field, so it has no point on this axis but zero); x is the run's nominal ink
  level. Scored here through preflight.checks.evaluate(), abstention off.
- G1 (A3): pages binned by their measured field_ink_share; x is the median share of the bin.
- X2: emptied mark sheets by their measured mark_ink_share, once x2/readings.jsonl exists.
Error bars are Wilson 95% intervals. The x axis is logarithmic; a share of zero is drawn at the
left edge (0.01%) and labelled so.
"""
import json
import os
import sys

# Run as a script, this folder is sys.path[0], and numbers.py would shadow the standard
# library module of the same name that numpy imports: drop it, put the study root instead.
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from statistics import median  # noqa: E402 (after the sys.path fix: statistics imports numbers)

from analysis import data, stats  # noqa: E402

TABLES = os.path.join(data.RESULTS, "tables")
BINS = (0.0, 0.0005, 0.002, 0.00345, 0.005, 0.01, 0.04, float("inf"))
ZERO_AT = 0.0001
COLORS = {"G0": "#2a78d6", "G1": "#eb6834", "X2": "#1baf7a"}   # validated categorical 1..3
MARKERS = {"G0": "o", "G1": "s", "X2": "^"}


def fmt(v, d=3):
    return "n/a" if v is None else (f"{v:.{d}f}" if isinstance(v, float) else str(v))


def ci_text(iv):
    return "n/a" if not iv or iv[0] is None else f"[{iv[0]:.3f}, {iv[1]:.3f}]"


# ------------------------------------------------------------------------------------------

def table_hypotheses(H):
    lines = ["# Preregistered hypotheses", "",
             "Verdicts by the criteria of prereg/PREREG.md. \"not tested yet\": the source (X2) "
             "does not exist yet.", "",
             "| Hypothesis | Estimate | k / n | Wilson 95% | Cluster bootstrap 95% | Verdict |",
             "|---|---|---|---|---|---|"]
    for name, r in H["hypotheses"].items():
        iv = r.get("interval") or {}
        kn = f"{r['k']} / {r['n']}" if r.get("n") else "n/a"
        est = r.get("estimate")
        if name == "P-NAF":
            hl = r["human_label_exploratory_lower_bound"]
            lines.append(f"| P-NAF | pixel {fmt(r['pixel_share'])} (invalid); human-label lower "
                         f"bound {fmt(hl['share'], 4)} | {hl['k']} / {hl['n']} | "
                         f"{ci_text(hl['wilson_95'])} | {ci_text(hl['cluster_bootstrap_95'])} | "
                         f"{r['verdict']} (preregistered band on record: "
                         f"{r['band_as_preregistered']}) |")
            continue
        if name == "H5":
            lines.append(f"| H5 | P1 crowns `{r.get('P1_crowned')}`, P5 crowns "
                         f"`{r.get('P5_crowned')}` | n/a | n/a | n/a | {r['verdict']} |")
            continue
        if name == "H6":
            p = r["A3_part"]["primary"]
            s = r["A3_part"]["strict"]
            lines.append(f"| H6 (A3 part) | hits {p['hits_over_failures'][0]} of "
                         f"{p['hits_over_failures'][1]} failing cells (strict "
                         f"{s['hits_over_failures'][0]} of {s['hits_over_failures'][1]}); false "
                         f"predictions {p['false_predictions_over_predictions'][0]} of "
                         f"{p['false_predictions_over_predictions'][1]} | n/a | n/a | n/a | "
                         f"A3 part: {r['verdict_A3_part']}; H6: {r['verdict']} |")
            continue
        lines.append(f"| {name} | {fmt(est)} | {kn} | {ci_text(iv.get('wilson_95'))} | "
                     f"{ci_text(iv.get('cluster_bootstrap_95'))} | {r['verdict']} |")
    cells = H["a3_cells_at_shipped_thresholds"]
    lines += ["", "## A3 at the shipped thresholds (the cells H6 scores)", "",
              "| Check | Recall | k / n | Wilson 95% | Identity bootstrap 95% | False alarms per "
              "target |", "|---|---|---|---|---|---|"]
    for c, v in cells.items():
        iv = v.get("interval") or {}
        lines.append(f"| {c} | {fmt(v['recall'])} | {v['k']} / {v['n']} | "
                     f"{ci_text(iv.get('wilson_95'))} | {ci_text(iv.get('cluster_bootstrap_95'))}"
                     f" | {fmt(v['false_alarm_rate'], 4)} ({v['fp']} / {v['n_neg']}) |")
    return "\n".join(lines) + "\n"


def table_protocols(P):
    lines = ["# Validation protocols (RQ2)", "",
             "Shipped choice rule unless the rule column says otherwise. Validated recall is on "
             "the protocol's own report set; A3 seed 37 is the secondary target (the report set "
             "itself for P4); X2, the primary target, is not tested yet. MAE: mean over checks "
             "of the absolute recall error on A3 seed 37.", "",
             "| Fold | Rule | required_field crowned | Validated recall (required_field) | "
             "A3 seed 37 recall (required_field) | Gate 0.90 blocks | MAE on A3 seed 37 |",
             "|---|---|---|---|---|---|---|"]
    for pid, p in P["protocols"].items():
        for f in p["folds"]:
            if f.get("status") != "run":
                lines.append(f"| {f['fold']} | all | {f['status']} | | | | |")
                continue
            for rule, r in f["rules"].items():
                if rule.startswith("B3_"):
                    v, t = r["validation"], (r["targets"] or {}).get("A3_seed37") or {}
                    lines.append(f"| {f['fold']} | {rule} | `{r['ink_component']}` "
                                 f"{rule[3:].upper()} `{r['ocr_component']}` | "
                                 f"{fmt(v['recall'])} ({v['tp']}/{v['n_pos']}) | "
                                 f"{fmt(t.get('recall'))} ({t.get('tp')}/{t.get('n_pos')}) | | |")
                    continue
                rf = r["checks"].get("required_field", {})
                v = rf.get("validation") or {}
                t = (rf.get("targets") or {}).get("A3_seed37") or {}
                e = (r.get("errors_A3_seed37") or {}).get("mean_recall_abs_error")
                gate = r.get("release_gate_0.90_blocks_required_field")
                lines.append(f"| {f['fold']} | {rule} | `{rf.get('settings')}` | "
                             f"{fmt(v.get('recall'))} ({v.get('tp')}/{v.get('n_pos')}) | "
                             f"{fmt(t.get('recall'))} ({t.get('tp')}/{t.get('n_pos')}) | "
                             f"{'yes' if gate else 'no'} | {fmt(e)} |")
    return "\n".join(lines) + "\n"


def table_quarter_turns(H):
    q = H["exploratory"]["quarter_turns_A3"]
    o = q["overall"]
    lines = ["# Wrong quarter turn on A3 (exploratory, not preregistered)", "",
             "The production reading path of dossier-preflight settles on a quarter turn per "
             "page; grid/read_images.py records it against the expected one.", "",
             f"All pages: {o['k']} of {o['n']} = {o['rate']:.3f}, Wilson 95% "
             f"{ci_text(o['interval']['wilson_95'])}, identity bootstrap 95% "
             f"{ci_text(o['interval']['cluster_bootstrap_95'])}.", "",
             "| Piece | Wrong turn | k / n | Wilson 95% |", "|---|---|---|---|"]
    for piece, p in q["by_piece"].items():
        lines.append(f"| {piece} | {p['rate']:.3f} | {p['k']} / {p['n']} | "
                     f"{ci_text(p['wilson_95'])} |")
    t = q["all_checks"]
    lines += ["", "Do the wrong-turn pages carry the misses? Positives of every check at the "
              "shipped thresholds:", "",
              f"- recall on wrong-turn pages {fmt(t['recall_wrong_turn'])} "
              f"{ci_text(t['wilson_recall_wrong_turn'])} over {t['pos_wrong']} positives; on "
              f"right-turn pages {fmt(t['recall_right_turn'])} "
              f"{ci_text(t['wilson_recall_right_turn'])} over {t['pos_right']};",
              f"- wrong-turn pages hold {fmt(t['share_of_positives_on_wrong_turn'])} of the "
              f"positives and {fmt(t['share_of_misses_on_wrong_turn'])} of the misses.", "",
              "| Check | Recall, wrong turn | positives | Recall, right turn | positives |",
              "|---|---|---|---|---|"]
    for c, m in q["misses_by_check"].items():
        lines.append(f"| {c} | {fmt(m['recall_wrong_turn'])} | {m['pos_wrong']} | "
                     f"{fmt(m['recall_right_turn'])} | {m['pos_right']} |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------

def points_g0(ship):
    """A4's targeted rows, emptied field, variant side, scored with the shipped sensor."""
    path, st = data.arm_status("A4")
    if path is None:
        return []
    from preflight.checks import evaluate
    from preflight.reading import Reading
    reg, thr = ship["required_field"]
    thresholds = data.analyze().frozen_settings  # noqa: F841 (documents the source)
    from preflight.thresholds import load_thresholds
    th = load_thresholds(data.shipped_thresholds_path())
    ref = data.identities()[data.analyze().DEFAULT_IDENTITY]
    by = {}
    for r in data.load_lines(path):
        if r["variant"] != "empty_required_field" or r["side"] != "variant":
            continue
        found = evaluate({r["piece"]: Reading.from_dict(r["reading"])}, ref, "filing", reg, th,
                         checks=["required_field"], abstention=False)
        fired = any(c.fires for c in found if str(c.target) == r["zone"])
        k, n = by.get(r["parasite"], (0, 0))
        by[r["parasite"]] = (k + fired, n + 1)
    return [{"x": lv, "k": k, "n": n} for lv, (k, n) in sorted(by.items())]


def points_binned(pairs):
    out = []
    for lo, hi in zip(BINS, BINS[1:]):
        sub = [(s, f) for s, f in pairs if lo <= s < hi]
        if not sub:
            continue
        out.append({"x": median(s for s, _ in sub), "k": sum(f for _, f in sub), "n": len(sub),
                    "bin": [lo, hi if hi != float("inf") else None]})
    return out


def points_g1(ship):
    from analysis.hypotheses import A3
    a3 = A3()
    reg, thr = ship["required_field"]
    inst = {}
    for key, variant, piece, target, s, fires in a3.positives("required_field", reg, thr):
        page = a3.page_of(key, variant, piece)
        share = page["field_ink_share"] if page else None
        if share is None:
            continue
        k = (key, variant)
        inst[k] = (share, inst.get(k, (share, False))[1] or fires)
    return points_binned(list(inst.values()))


def points_x2(ship):
    from analysis import x2 as x2mod
    x2 = x2mod.X2.load()
    if x2 is None:
        return None
    reg, thr = ship["required_field"]
    pairs = {}
    for m, found, damaged in x2.mark_scores(reg):
        if not damaged or m["mark_ink_share"] is None:
            continue
        k = (m["identity"], m["piece"], m["capture"], m["mark_step"])
        pairs[k] = (float(m["mark_ink_share"]),
                    any(found.get(t, float("-inf")) > thr for t in damaged))
    return points_binned(list(pairs.values()))


def figure(series, path_png, path_svg):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "perfect-recall-study"
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.set_facecolor("#fcfcfb")
    fig.patch.set_facecolor("#fcfcfb")
    labels = {"G0": "G0, targeted ink on the emptied field (A4; x = nominal level)",
              "G1": "G1, Augraphy default pipeline (A3; x = measured share)",
              "X2": "X2, real captures (x = measured mark share)"}
    for name, pts in series.items():
        if not pts:
            continue
        xs = [max(p["x"], ZERO_AT) for p in pts]
        ys = [p["k"] / p["n"] for p in pts]
        lo = [y - stats.wilson(p["k"], p["n"])[0] for y, p in zip(ys, pts)]
        hi = [stats.wilson(p["k"], p["n"])[1] - y for y, p in zip(ys, pts)]
        ax.errorbar(xs, ys, yerr=[lo, hi], color=COLORS[name], marker=MARKERS[name],
                    markersize=6, linewidth=2, capsize=0, elinewidth=1, label=labels[name])
    ax.axvline(0.00345, color="#52514e", linewidth=1, linestyle=":")
    ax.text(0.00345, 1.04, " shipped threshold 0.345%", color="#52514e", fontsize=8,
            va="bottom", ha="left")
    ax.set_xscale("log")
    ax.set_xlim(ZERO_AT * 0.7, 0.2)
    ax.set_ylim(-0.03, 1.12)
    ax.set_xticks([ZERO_AT, 0.001, 0.01, 0.1])
    ax.set_xticklabels(["0", "0.1%", "1%", "10%"])
    ax.set_xlabel("ink share in the emptied required field", color="#0b0b0b")
    ax.set_ylabel("recall of the shipped sensor", color="#0b0b0b")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b5b4ae")
    ax.tick_params(colors="#52514e", labelsize=8)
    ax.grid(axis="y", color="#e7e6e2", linewidth=0.8)
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(path_png, dpi=200, metadata={"Software": None})
    fig.savefig(path_svg, metadata={"Date": None, "Creator": None})
    plt.close(fig)


def main():
    from analysis.hypotheses import shipped
    H = json.load(open(os.path.join(data.RESULTS, "hypotheses.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(data.RESULTS, "protocols.json"), encoding="utf-8"))
    os.makedirs(TABLES, exist_ok=True)
    for name, text in (("hypotheses.md", table_hypotheses(H)),
                       ("protocols.md", table_protocols(P)),
                       ("quarter_turns.md", table_quarter_turns(H))):
        with open(os.path.join(TABLES, name), "w", encoding="utf-8") as f:
            f.write(text)
    ship = shipped()
    data.install_fast_curve()
    series = {"G0": points_g0(ship), "G1": points_g1(ship), "X2": points_x2(ship)}
    data.write_json(os.path.join(data.RESULTS, "figure1.json"),
                    data.jsonable({k: (v if v is not None else "not tested yet")
                                   for k, v in series.items()}))
    figure(series, os.path.join(data.RESULTS, "figure1.png"),
           os.path.join(data.RESULTS, "figure1.svg"))
    print("-> results/tables/*.md, results/figure1.png, results/figure1.svg, results/figure1.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
