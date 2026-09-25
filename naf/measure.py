#!/usr/bin/env python3
"""Orchestrates the NAF prevalence measure (T15).

Three explicit stages, because the pixel stage needs dossier-preflight's own registration code
and therefore its own venv, while the human-label stage needs nothing but this study's own
Python:

  python3 naf/measure.py human-label --naf-dir $AR/x3/NAF --out $AR/x3
      writes $AR/x3/human_label_partial.json and $AR/x3/naf_fields_human_label.csv

  $DP/.venv/bin/python naf/measure.py pixel --naf-dir $AR/x3/NAF --out $AR/x3
      writes $AR/x3/pixel_partial.json, $AR/x3/naf_fields_pixel.csv and one consensus PNG per
      group under $AR/x3/consensus/

  python3 naf/measure.py combine --naf-dir $AR/x3/NAF --archive $AR/x3 --results results/naf.json
      reads both partials, writes the final results/naf.json, and prints the reconciliation
      (fields in = fields measured + fields excluded) this task's Verify step checks.

Each stage fails loudly (a non-zero exit and a message) rather than silently skipping: `combine`
run before `pixel` has run refuses, it does not fall back to human-label-only silently.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naf import human_label as hl
from naf.annotations import iter_images
from naf.stats import cluster_bootstrap, pooled_share, wilson

MIN_GROUPS_FOR_PIXEL = 3
GROUP_MIN_IMAGES = 10
PIXEL_THRESHOLDS = {"0.345pct": "above_0.345pct", "1pct": "above_1pct", "4pct": "above_4pct"}


def now_ts():
    return datetime.now(timezone.utc).isoformat()


def qualifying_groups(naf_dir):
    """group -> list of image_id, for every group with at least GROUP_MIN_IMAGES images."""
    groups = {}
    for group, image_id, _path in iter_images(naf_dir):
        groups.setdefault(group, []).append(image_id)
    return {g: ids for g, ids in groups.items() if len(ids) >= GROUP_MIN_IMAGES}


# ---------------------------------------------------------------------------
# Stage: human-label
# ---------------------------------------------------------------------------

def stage_human_label(naf_dir, out_dir, ts):
    per_field_rows, per_image, excluded = hl.compute(naf_dir)
    for row in per_field_rows:
        row["ts"] = ts

    csv_path = os.path.join(out_dir, "naf_fields_human_label.csv")
    fieldnames = ["group", "image_id", "field_id", "field_type", "field_area_px",
                  "comment_overlap_share", "positive", "ts"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_field_rows)

    summary = hl.summarize(per_field_rows)
    excluded_by_reason = {}
    for e in excluded:
        excluded_by_reason[e["reason"]] = excluded_by_reason.get(e["reason"], 0) + 1

    partial = {
        "ts": ts,
        "fields_in": len(per_field_rows) + len(excluded),
        "fields_measured": len(per_field_rows),
        "fields_excluded": len(excluded),
        "excluded_by_reason": excluded_by_reason,
        "pooled": summary,
        "per_image": per_image,
    }
    partial_path = os.path.join(out_dir, "human_label_partial.json")
    with open(partial_path, "w", encoding="utf-8") as fh:
        json.dump(partial, fh, indent=2, sort_keys=True)

    print("human-label: fields in %d = measured %d + excluded %d"
          % (partial["fields_in"], partial["fields_measured"], partial["fields_excluded"]))
    print("wrote", csv_path)
    print("wrote", partial_path)


# ---------------------------------------------------------------------------
# Stage: pixel (must run under $DP/.venv/bin/python)
# ---------------------------------------------------------------------------

def stage_pixel(naf_dir, out_dir, ts):
    from naf import registration as reg_mod
    from PIL import Image

    reg_mod.require_preflight()

    groups = qualifying_groups(naf_dir)
    if len(groups) < MIN_GROUPS_FOR_PIXEL:
        partial = {
            "ts": ts, "skipped": True,
            "reason": "fewer than %d groups reach %d images (%d found)"
                      % (MIN_GROUPS_FOR_PIXEL, GROUP_MIN_IMAGES, len(groups)),
            "fields_in": 0, "fields_measured": 0, "fields_excluded": 0,
            "images_in": 0, "images_measured": 0, "images_excluded": 0,
        }
        with open(os.path.join(out_dir, "pixel_partial.json"), "w", encoding="utf-8") as fh:
            json.dump(partial, fh, indent=2, sort_keys=True)
        print(partial["reason"])
        return

    consensus_dir = os.path.join(out_dir, "consensus")
    os.makedirs(consensus_dir, exist_ok=True)

    all_rows = []
    all_excluded = []  # dicts with group, image_id, field_id, reason
    images_in = 0
    images_measured = 0
    images_excluded = 0
    image_excluded_reasons = {}

    for group in sorted(groups):
        group_images = reg_mod.load_group_images(naf_dir, group)
        images_in += len(group_images)
        medoid_id, consensus, per_image_reg = reg_mod.register_group(group_images)
        Image.fromarray(consensus).save(os.path.join(consensus_dir, "%s.png" % group))

        greys_by_id = dict(group_images)
        for image_id, grey in group_images:
            reg_info = per_image_reg[image_id]
            if reg_info["ok"]:
                images_measured += 1
            else:
                images_excluded += 1
                image_excluded_reasons[reg_info["reason"]] = (
                    image_excluded_reasons.get(reg_info["reason"], 0) + 1
                )
            rows, excluded = reg_mod.field_ink_rows(
                naf_dir, group, image_id, grey, reg_info, consensus,
            )
            for row in rows:
                row["ts"] = ts
                row["medoid_id"] = medoid_id
                row["registration_peak"] = reg_info["peak"]
                row["registration_quarter_turns"] = reg_info["quarter_turns"]
            all_rows.extend(rows)
            for e in excluded:
                all_excluded.append({"group": group, "image_id": image_id,
                                      "field_id": e["field_id"], "reason": e["reason"]})

    csv_path = os.path.join(out_dir, "naf_fields_pixel.csv")
    fieldnames = ["group", "image_id", "field_id", "field_type", "field_area_px",
                  "added_ink_share", "above_0.345pct", "above_1pct", "above_4pct",
                  "medoid_id", "registration_peak", "registration_quarter_turns", "ts"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    excluded_by_reason = {}
    for e in all_excluded:
        excluded_by_reason[e["reason"]] = excluded_by_reason.get(e["reason"], 0) + 1

    thresholds = {}
    for label, key in PIXEL_THRESHOLDS.items():
        k = sum(1 for r in all_rows if r[key])
        n = len(all_rows)
        lower, upper = wilson(k, n)
        boot_lower, boot_upper, point, n_images = cluster_bootstrap(
            all_rows, "image_id", lambda rows, key=key: pooled_share(rows, key),
        )
        thresholds[label] = {
            "k": k, "n": n, "share": (k / n) if n else float("nan"),
            "wilson_95": {"lower": lower, "upper": upper},
            "cluster_bootstrap_95": {"lower": boot_lower, "upper": boot_upper,
                                      "n_resamples": 10000, "seed": 20260925,
                                      "n_clusters_images": n_images},
        }

    partial = {
        "ts": ts, "skipped": False,
        "groups": sorted(groups),
        "n_groups": len(groups),
        "images_in": images_in, "images_measured": images_measured,
        "images_excluded": images_excluded,
        "images_excluded_by_reason": image_excluded_reasons,
        "fields_in": len(all_rows) + len(all_excluded),
        "fields_measured": len(all_rows),
        "fields_excluded": len(all_excluded),
        "fields_excluded_by_reason": excluded_by_reason,
        "thresholds": thresholds,
    }
    with open(os.path.join(out_dir, "pixel_partial.json"), "w", encoding="utf-8") as fh:
        json.dump(partial, fh, indent=2, sort_keys=True)

    print("pixel: images in %d = measured %d + excluded %d"
          % (images_in, images_measured, images_excluded))
    print("pixel: fields in %d = measured %d + excluded %d"
          % (partial["fields_in"], partial["fields_measured"], partial["fields_excluded"]))
    print("wrote", csv_path)
    print("wrote", os.path.join(out_dir, "pixel_partial.json"))


# ---------------------------------------------------------------------------
# Stage: combine
# ---------------------------------------------------------------------------

def _band(upper_95):
    if upper_95 < 0.005:
        return "rare"
    if upper_95 <= 0.05:
        return "occasional"
    return "common"


def _agreement_table(pixel_csv_path, human_csv_path, pixel_threshold_key):
    human = {}
    with open(human_csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            human[(row["group"], row["image_id"], row["field_id"])] = row["positive"] == "True"

    table = {"human_pos_pixel_pos": 0, "human_pos_pixel_neg": 0,
             "human_neg_pixel_pos": 0, "human_neg_pixel_neg": 0}
    n = 0
    with open(pixel_csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["group"], row["image_id"], row["field_id"])
            if key not in human:
                continue
            h_pos = human[key]
            p_pos = row[pixel_threshold_key] == "True"
            n += 1
            if h_pos and p_pos:
                table["human_pos_pixel_pos"] += 1
            elif h_pos and not p_pos:
                table["human_pos_pixel_neg"] += 1
            elif not h_pos and p_pos:
                table["human_neg_pixel_pos"] += 1
            else:
                table["human_neg_pixel_neg"] += 1
    return table, n


def stage_combine(naf_dir, archive_dir, results_path, naf_commit, license_name, ts):
    hl_path = os.path.join(archive_dir, "human_label_partial.json")
    px_path = os.path.join(archive_dir, "pixel_partial.json")
    if not os.path.exists(hl_path):
        print("missing %s: run the human-label stage first" % hl_path, file=sys.stderr)
        return 1
    if not os.path.exists(px_path):
        print("missing %s: run the pixel stage first (under $DP/.venv/bin/python)" % px_path,
              file=sys.stderr)
        return 1

    with open(hl_path, encoding="utf-8") as fh:
        human_label = json.load(fh)
    with open(px_path, encoding="utf-8") as fh:
        pixel = json.load(fh)

    images_total = sum(1 for _ in iter_images(naf_dir))

    result = {
        "meta": {"naf_commit": naf_commit, "license": license_name, "ts": ts},
        "counts": {
            "images_total": images_total,
            "human_label": {
                "fields_in": human_label["fields_in"],
                "fields_measured": human_label["fields_measured"],
                "fields_excluded": human_label["fields_excluded"],
                "excluded_by_reason": human_label["excluded_by_reason"],
            },
            "pixel": {
                "skipped": pixel.get("skipped", False),
                "n_groups": pixel.get("n_groups", 0),
                "groups": pixel.get("groups", []),
                "images_in": pixel.get("images_in", 0),
                "images_measured": pixel.get("images_measured", 0),
                "images_excluded": pixel.get("images_excluded", 0),
                "images_excluded_by_reason": pixel.get("images_excluded_by_reason", {}),
                "fields_in": pixel.get("fields_in", 0),
                "fields_measured": pixel.get("fields_measured", 0),
                "fields_excluded": pixel.get("fields_excluded", 0),
                "fields_excluded_by_reason": pixel.get("fields_excluded_by_reason", {}),
            },
        },
        "human_label_measure": {
            "pooled": human_label["pooled"],
            "per_image": human_label["per_image"],
            "threshold": "comment polygon overlap >= 1% of the field's area",
        },
    }

    if pixel.get("skipped"):
        result["pixel_measure"] = {"skipped": True, "reason": pixel.get("reason")}
        result["agreement_2x2"] = {"skipped": True,
                                    "reason": "pixel measure not computed"}
        result["p_naf"] = {
            "measure": "human_label (pixel measure not computed: fewer than 3 groups "
                       "reached 10 images)",
            "share": human_label["pooled"]["share"],
            "wilson_95": human_label["pooled"]["wilson_95"],
            "cluster_bootstrap_95": human_label["pooled"]["cluster_bootstrap_95"],
            "band": _band(human_label["pooled"]["wilson_95"]["upper"]),
            "rule": "rare if upper 95% bound < 0.5%, occasional 0.5% to 5%, common above 5%",
        }
    else:
        result["pixel_measure"] = {"skipped": False, "thresholds": pixel["thresholds"]}

        table, n_agree = _agreement_table(
            os.path.join(archive_dir, "naf_fields_pixel.csv"),
            os.path.join(archive_dir, "naf_fields_human_label.csv"),
            "above_0.345pct",
        )
        result["agreement_2x2"] = {
            "skipped": False, "n_fields": n_agree,
            "pixel_threshold": "0.345pct", "human_threshold": "comment overlap >= 1%",
            "table": table,
        }

        primary = pixel["thresholds"]["0.345pct"]
        result["p_naf"] = {
            "measure": "pixel_at_0.345pct",
            "share": primary["share"],
            "wilson_95": primary["wilson_95"],
            "cluster_bootstrap_95": primary["cluster_bootstrap_95"],
            "band": _band(primary["wilson_95"]["upper"]),
            "rule": "rare if upper 95% bound < 0.5%, occasional 0.5% to 5%, common above 5%",
            "human_label_secondary": {
                "share": human_label["pooled"]["share"],
                "wilson_95": human_label["pooled"]["wilson_95"],
                "cluster_bootstrap_95": human_label["pooled"]["cluster_bootstrap_95"],
            },
        }

    os.makedirs(os.path.dirname(results_path) or ".", exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)

    hl_in = result["counts"]["human_label"]["fields_in"]
    hl_m = result["counts"]["human_label"]["fields_measured"]
    hl_e = result["counts"]["human_label"]["fields_excluded"]
    px_in = result["counts"]["pixel"]["fields_in"]
    px_m = result["counts"]["pixel"]["fields_measured"]
    px_e = result["counts"]["pixel"]["fields_excluded"]
    print("human-label: fields in %d = measured %d + excluded %d (%s)"
          % (hl_in, hl_m, hl_e, hl_in == hl_m + hl_e))
    print("pixel: fields in %d = measured %d + excluded %d (%s)"
          % (px_in, px_m, px_e, px_in == px_m + px_e))
    print("P-NAF band:", result["p_naf"]["band"])
    print("wrote", results_path)
    if hl_in != hl_m + hl_e or px_in != px_m + px_e:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="stage", required=True)

    p1 = sub.add_parser("human-label")
    p1.add_argument("--naf-dir", required=True)
    p1.add_argument("--out", required=True)

    p2 = sub.add_parser("pixel")
    p2.add_argument("--naf-dir", required=True)
    p2.add_argument("--out", required=True)

    p3 = sub.add_parser("combine")
    p3.add_argument("--naf-dir", required=True)
    p3.add_argument("--archive", required=True)
    p3.add_argument("--results", required=True)
    p3.add_argument("--naf-commit", required=True)
    p3.add_argument("--license", default="CDLA-Permissive-1.0")

    args = parser.parse_args()
    ts = now_ts()

    if args.stage == "human-label":
        os.makedirs(args.out, exist_ok=True)
        stage_human_label(args.naf_dir, args.out, ts)
        return 0
    if args.stage == "pixel":
        os.makedirs(args.out, exist_ok=True)
        stage_pixel(args.naf_dir, args.out, ts)
        return 0
    if args.stage == "combine":
        return stage_combine(args.naf_dir, args.archive, args.results,
                              args.naf_commit, args.license, ts)
    return 1


if __name__ == "__main__":
    sys.exit(main())
