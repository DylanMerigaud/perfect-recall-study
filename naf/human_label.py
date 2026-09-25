"""The human-label measure (T15 step 2): needs no blank, no registration, no pixels.

For every field with isBlank == 3 (see annotations.FIELD_TYPES), the share of the field's
rasterised area covered by the union of that image's comment polygons ("any added writing or
text which is not in a field", NAF's own label, independent of this study). A field is positive
when that share is at least 1%. Computed over every image in the dataset: this measure needs no
image pixels and no registration, so nothing here is limited to the pixel-measure groups.
"""
from .annotations import iter_images, read_image_annotation
from .geometry import overlap_share
from .stats import cluster_bootstrap, pooled_share, wilson

THRESHOLD = 0.01


def compute(naf_dir):
    """Return (per_field_rows, per_image, excluded).

    per_field_rows: one dict per measured field: group, image_id, field_id, field_type,
    field_area, overlap_share, positive, ts (filled by the caller).
    per_image: image_id -> {group, n_fields, n_positive, share}.
    excluded: one dict per field dropped before measurement, with a reason.
    """
    per_field_rows = []
    per_image = {}
    excluded = []

    for group, image_id, json_path in iter_images(naf_dir):
        fields, comments, _w, _h = read_image_annotation(json_path)
        comment_polys = [c["poly"] for c in comments]
        n_fields = 0
        n_positive = 0
        for field in fields:
            share, area = overlap_share(field["poly"], comment_polys)
            if area == 0:
                excluded.append({
                    "group": group, "image_id": image_id, "field_id": field["id"],
                    "reason": "degenerate field polygon (zero raster area)",
                })
                continue
            positive = share >= THRESHOLD
            n_fields += 1
            n_positive += 1 if positive else 0
            per_field_rows.append({
                "group": group, "image_id": image_id, "field_id": field["id"],
                "field_type": field["type"], "field_area_px": area,
                "comment_overlap_share": share, "positive": positive,
            })
        per_image[image_id] = {
            "group": group, "n_fields": n_fields, "n_positive": n_positive,
            "share": (n_positive / n_fields) if n_fields else None,
        }

    return per_field_rows, per_image, excluded


def summarize(per_field_rows):
    """Pooled Wilson interval and cluster bootstrap over images, for the positive column."""
    k = sum(1 for r in per_field_rows if r["positive"])
    n = len(per_field_rows)
    lower, upper = wilson(k, n)
    boot_lower, boot_upper, point, n_images = cluster_bootstrap(
        per_field_rows, "image_id", lambda rows: pooled_share(rows, "positive"),
    )
    return {
        "k": k, "n": n, "share": (k / n) if n else float("nan"),
        "wilson_95": {"lower": lower, "upper": upper},
        "cluster_bootstrap_95": {
            "lower": boot_lower, "upper": boot_upper, "n_resamples": 10000,
            "seed": 20260925, "n_clusters_images": n_images,
        },
    }
