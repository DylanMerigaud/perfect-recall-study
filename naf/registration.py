"""The pixel measure (T15 step 3): must run under dossier-preflight's own venv.

This module imports dossier-preflight's registration code directly (`preflight.deskew`), so it
only works with `$DP/.venv/bin/python` on `sys.path` reaching dossier-preflight's package (the
study's plan variable `PY`, see naf/README.md). Plain `python3` does not have `preflight`
installed and every function here raises ImportError before doing anything, which naf/measure.py
uses to skip this half of the pipeline with a clear message rather than a stack trace.

Method (see FORMAT.md for the full write-up and its stated limits):

1. NAF's own `groups/<id>/` folders ARE the form-type grouping the plan asks for: the dataset's
   README states groups hold "images of the same form type", so no separate clustering is done.
2. Within a group, the MEDOID is the image whose small thumbnail has the least total absolute
   difference to every other thumbnail in the group (a cheap proxy, not itself a use of
   dossier-preflight's registration).
3. Every image in the group, including the medoid, is registered against the medoid with
   dossier-preflight's `preflight.deskew.register`, restricted to quarter turns 0 and 180
   (`quarters=(0, 2)`): a scan fed upside down is common, a scan fed sideways is not attempted,
   because undoing a 90 degree turn swaps width and height and this pipeline does not carry that
   swap through the field-polygon coordinates. This is a stated scope limit, not an oversight.
   Each of the two quarter turns is searched INDEPENDENTLY (`_register_best_of`) and the higher
   final peak wins: passing both quarters to a single `register()` call lets its coarse-then-
   refine search lock onto the wrong one (see `_register_best_of`'s docstring for the real image
   that exposed this).
4. Each image is warped into the medoid's own pixel frame (an affine built from the registration
   answer: scale and translate for quarter_turns == 0, scale, translate and a point reflection
   for quarter_turns == 2). The per-group CONSENSUS is the majority vote, pixel by pixel, of
   "dark at level 128" across every successfully registered image of the group: this is the
   printed template ink (rule lines, pre-printed labels) common to the group, not any one scan.
5. For every isBlank == 3 field of every image, dossier-preflight's own `build_frame` warps the
   consensus BACK into that image's native pixel frame (the direction dossier-preflight already
   provides, used exactly as dossier-preflight uses it elsewhere). A pixel counts as ADDED ink
   when it is dark (level 128) in the image and NOT dark in the consensus at the same native
   location.

Each image's dark mask is DILATED by CONSENSUS_DILATE_RADIUS pixels before it enters the
majority vote (step 4). Registration here is translate and uniform scale only (no sub-degree
rotation, no local or non-rigid correction), so a few pixels of residual misalignment are
expected even at a good correlation peak. Measured 2026-09-25 on a real field (group 132,
007540939_00045, field f46, a "No........." dotted line): the per-pixel vote fraction across the
field peaked at 0.70 and averaged 0.24, with NO pixel undilated reaching the 0.5 majority needed
to be called template, even though the dotted line is printed on every form of this group. See
FORMAT.md for the radius sweep that picked 3 pixels: small relative to the smallest real mark
this study places on a real capture (about 8 px, a 1 mm pencil dot at 200 dpi), so a genuine
added mark is not dilated away, while genuine fine template ink (dotted lines, small printed
text) recovers enough votes to be recognised as template.
"""
import numpy as np
from PIL import Image

from .annotations import iter_images, read_image_annotation, image_path
from .geometry import is_degenerate, polygon_bbox, rasterize_at

try:
    from preflight.deskew import register, build_frame
except ImportError as exc:  # pragma: no cover, exercised only under plain python3
    _IMPORT_ERROR = exc
    register = None
    build_frame = None
else:
    _IMPORT_ERROR = None

QUARTERS = (0, 2)
MIN_PEAK = 0.4  # below this the correlation found no usable correspondence; see FORMAT.md
DARK_LEVEL = 128
CONSENSUS_DILATE_RADIUS = 3  # pixels; see the module docstring and FORMAT.md for the sweep
DILATE_STRUCTURE = np.ones((2 * CONSENSUS_DILATE_RADIUS + 1, 2 * CONSENSUS_DILATE_RADIUS + 1),
                            dtype=bool)
THUMB_SIZE = (128, 128)


def require_preflight():
    if register is None:
        raise ImportError(
            "preflight is not importable: rerun this module with $DP/.venv/bin/python "
            "(dossier-preflight's own venv), not plain python3"
        ) from _IMPORT_ERROR


def load_grey(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("L"))


def pick_medoid(greys):
    """Index of the image whose small thumbnail is closest, in total L1 distance, to the rest."""
    thumbs = [
        np.asarray(Image.fromarray(g).resize(THUMB_SIZE, Image.BILINEAR), dtype=np.float32)
        for g in greys
    ]
    n = len(thumbs)
    totals = [0.0] * n
    for i in range(n):
        for j in range(n):
            if i != j:
                totals[i] += float(np.abs(thumbs[i] - thumbs[j]).sum())
    return int(np.argmin(totals))


def _affine_canonical_from_original(reg, orig_h, orig_w):
    """PIL AFFINE coefficients mapping a CANONICAL output pixel to an ORIGINAL input pixel."""
    s = reg.scale
    if reg.quarter_turns == 0:
        return (1.0 / s, 0.0, -reg.dx / s, 0.0, 1.0 / s, -reg.dy / s)
    if reg.quarter_turns == 2:
        return (
            -1.0 / s, 0.0, reg.dx / s + orig_w - 1,
            0.0, -1.0 / s, reg.dy / s + orig_h - 1,
        )
    raise ValueError("unsupported quarter_turns %r (only 0 and 2 are registered)"
                      % (reg.quarter_turns,))


def warp_to_canonical(grey, reg, canonical_size):
    """grey resampled into the medoid's own frame; canonical_size = (canon_w, canon_h)."""
    orig_h, orig_w = grey.shape
    coeffs = _affine_canonical_from_original(reg, orig_h, orig_w)
    warped = Image.fromarray(grey).transform(
        canonical_size, Image.AFFINE, coeffs, resample=Image.BILINEAR, fillcolor=255,
    )
    return np.asarray(warped)


def turn_point(x, y, quarter_turns, orig_w, orig_h):
    """A field-polygon vertex, in the image's own (untouched) coordinates, into the TURNED frame
    that dossier-preflight's register/build_frame operate in for this quarter_turns value."""
    if quarter_turns == 0:
        return x, y
    if quarter_turns == 2:
        return orig_w - 1 - x, orig_h - 1 - y
    raise ValueError("unsupported quarter_turns %r" % (quarter_turns,))


def _register_best_of(grey, medoid_grey):
    """The best-refined registration across QUARTERS, each quarter searched INDEPENDENTLY.

    dossier-preflight's own register() picks a single coarse winner across every quarter turn
    it is given, then refines only that one candidate (grid/../preflight/deskew.py's
    `attempt`/`best` loop): refinement never runs on a quarter that lost the coarse round, even
    if it would have refined to a higher final peak than the quarter that won. Measured
    2026-09-25 on a real NAF image (group 132, 007540939_00111, upright, not actually rotated):
    register(grey, medoid, quarters=(0, 2)) picked quarter_turns=2 at peak 0.604, while
    register(grey, medoid, quarters=(0,)) alone found quarter_turns=0 at peak 0.619, the correct
    answer and a HIGHER peak. Calling register() once per quarter turn and keeping the best
    final peak avoids this coarse-round trap.
    """
    best = None
    for qt in QUARTERS:
        candidate = register(grey, medoid_grey, quarters=(qt,))
        if best is None or candidate.peak > best.peak:
            best = candidate
    return best


def register_group(group_images):
    """group_images: list of (image_id, grey). Returns (medoid_id, consensus, per_image_reg).

    consensus: uint8 array, same shape as the medoid, 0 where the majority of registered images
    were dark at DARK_LEVEL after CONSENSUS_DILATE_RADIUS dilation (see the module docstring),
    255 elsewhere.
    per_image_reg: image_id -> {"ok": bool, "reason": str or None, "peak", "quarter_turns",
    "scale", "dx", "dy"} (peak/quarter_turns/... absent when a registration could not be
    attempted at all, which does not happen here since register() always returns a best guess;
    "ok" is False only when the peak is below MIN_PEAK).
    """
    require_preflight()
    from scipy import ndimage  # local: dossier-preflight's own venv has it; plain python3's
                                # system scipy fails to load on this Mac (T02's own note), and
                                # this module must still import cleanly there for the tests that
                                # need no image and no preflight.
    ids = [i for i, _ in group_images]
    greys = [g for _, g in group_images]
    medoid_idx = pick_medoid(greys)
    medoid_grey = greys[medoid_idx]
    canon_h, canon_w = medoid_grey.shape
    canonical_size = (canon_w, canon_h)

    per_image_reg = {}
    dark_stack = []
    for image_id, grey in group_images:
        reg = _register_best_of(grey, medoid_grey)
        ok = reg.peak >= MIN_PEAK
        per_image_reg[image_id] = {
            "ok": ok, "reason": None if ok else "registration peak %.3f below MIN_PEAK %.2f"
            % (reg.peak, MIN_PEAK),
            "peak": float(reg.peak), "quarter_turns": int(reg.quarter_turns),
            "scale": float(reg.scale), "dx": int(reg.dx), "dy": int(reg.dy),
        }
        if ok:
            warped = warp_to_canonical(grey, reg, canonical_size)
            dark = warped < DARK_LEVEL
            dilated = ndimage.binary_dilation(dark, structure=DILATE_STRUCTURE)
            dark_stack.append(dilated)

    if dark_stack:
        vote = np.mean(np.stack(dark_stack, axis=0), axis=0)
        consensus = np.where(vote >= 0.5, 0, 255).astype(np.uint8)
    else:
        consensus = np.full((canon_h, canon_w), 255, np.uint8)

    return ids[medoid_idx], consensus, per_image_reg


def field_ink_rows(naf_dir, group, image_id, grey, reg_info, consensus):
    """One row per isBlank == 3 field of this image: added-ink share against the consensus.

    Returns (rows, excluded): rows have field_id, field_type, field_area_px, ink_share,
    positives at 0.345%/1%/4%; excluded has field_id and a reason (registration not ok, a
    degenerate polygon, or a field polygon landing outside the registered frame).
    """
    require_preflight()
    rows = []
    excluded = []

    json_path = None
    for g, iid, path in iter_images(naf_dir):
        if g == group and iid == image_id:
            json_path = path
            break
    fields, _comments, _w, _h = read_image_annotation(json_path)

    if not reg_info["ok"]:
        for field in fields:
            excluded.append({"field_id": field["id"], "reason": reg_info["reason"]})
        return rows, excluded

    class _Reg:
        pass
    reg = _Reg()
    reg.quarter_turns = reg_info["quarter_turns"]
    reg.scale = reg_info["scale"]
    reg.dx = reg_info["dx"]
    reg.dy = reg_info["dy"]

    frame = build_frame(grey, consensus, reg)
    orig_h, orig_w = grey.shape
    frame_h, frame_w = frame.scan.shape

    for field in fields:
        turned_poly = [turn_point(x, y, reg.quarter_turns, orig_w, orig_h) for x, y in field["poly"]]
        if is_degenerate(turned_poly):
            excluded.append({"field_id": field["id"],
                              "reason": "degenerate field polygon (zero raster area)"})
            continue
        x0, y0, x1, y1 = polygon_bbox(turned_poly)
        if x0 < 0 or y0 < 0 or x1 > frame_w or y1 > frame_h or x1 <= x0 or y1 <= y0:
            excluded.append({"field_id": field["id"],
                              "reason": "field polygon outside the registered frame"})
            continue
        mask = rasterize_at(turned_poly, x0, y0, x1 - x0, y1 - y0)
        area = int(mask.sum())
        if area == 0:
            excluded.append({"field_id": field["id"],
                              "reason": "degenerate field polygon (zero raster area)"})
            continue
        scan_patch = frame.scan[y0:y1, x0:x1]
        blank_patch = frame.blank[y0:y1, x0:x1]
        dark_image = np.logical_and(mask, scan_patch < DARK_LEVEL)
        dark_template = np.logical_and(mask, blank_patch < DARK_LEVEL)
        added = np.logical_and(dark_image, np.logical_not(dark_template))
        added_count = int(added.sum())
        share = added_count / area
        rows.append({
            "group": group, "image_id": image_id, "field_id": field["id"],
            "field_type": field["type"], "field_area_px": area,
            "added_ink_share": share,
            "above_0.345pct": share >= 0.00345,
            "above_1pct": share >= 0.01,
            "above_4pct": share >= 0.04,
        })
    return rows, excluded


def load_group_images(naf_dir, group):
    """(image_id, grey) for every image in one NAF group directory, in a stable order."""
    out = []
    for g, image_id, _json_path in iter_images(naf_dir):
        if g == group:
            out.append((image_id, load_grey(image_path(naf_dir, group, image_id))))
    return out
