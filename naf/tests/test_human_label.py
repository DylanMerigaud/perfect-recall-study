import json
import os

from naf.human_label import THRESHOLD, compute, summarize


def _write(naf_dir, group, image_id, fields, comments):
    group_dir = os.path.join(naf_dir, "groups", group)
    os.makedirs(group_dir, exist_ok=True)
    data = {
        "imageFilename": image_id + ".jpg", "width": 100, "height": 100,
        "fieldBBs": fields + comments, "textBBs": [],
    }
    with open(os.path.join(group_dir, image_id + ".json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def _field(fid, poly, isblank=3, ftype="field"):
    return {"id": fid, "type": ftype, "isBlank": isblank, "poly_points": poly}


def _comment(cid, poly):
    return {"id": cid, "type": "comment", "isBlank": 1, "poly_points": poly}


def test_compute_flags_a_field_with_enough_comment_overlap(tmp_path):
    naf_dir = str(tmp_path)
    # a 100x100 field with a 15x15 comment fully inside: 225 / 10000 = 2.25%, above THRESHOLD
    _write(
        naf_dir, "g1", "img0",
        fields=[_field("f0", [[0, 0], [100, 0], [100, 100], [0, 100]])],
        comments=[_comment("c0", [[10, 10], [25, 10], [25, 25], [10, 25]])],
    )
    # a second field with no overlapping comment at all
    _write(
        naf_dir, "g1", "img1",
        fields=[_field("f1", [[0, 0], [100, 0], [100, 100], [0, 100]])],
        comments=[],
    )

    rows, per_image, excluded = compute(naf_dir)
    assert excluded == []
    by_field = {r["field_id"]: r for r in rows}
    assert by_field["f0"]["positive"] is True
    assert by_field["f0"]["comment_overlap_share"] >= THRESHOLD
    assert by_field["f1"]["positive"] is False

    assert per_image["img0"]["n_fields"] == 1
    assert per_image["img0"]["n_positive"] == 1
    assert per_image["img1"]["n_fields"] == 1
    assert per_image["img1"]["n_positive"] == 0

    summary = summarize(rows)
    assert summary["k"] == 1
    assert summary["n"] == 2
    assert abs(summary["share"] - 0.5) < 1e-9
    assert summary["cluster_bootstrap_95"]["n_clusters_images"] == 2


def test_compute_excludes_degenerate_field_polygon(tmp_path):
    naf_dir = str(tmp_path)
    _write(
        naf_dir, "g1", "img0",
        fields=[_field("f0", [[5, 5], [5, 5], [5, 5]])],  # zero-area sliver
        comments=[],
    )
    rows, per_image, excluded = compute(naf_dir)
    assert rows == []
    assert len(excluded) == 1
    assert excluded[0]["field_id"] == "f0"
    assert "zero raster area" in excluded[0]["reason"]
