"""Polygon rasterisation used by the human-label and pixel measures.

Every polygon in the NAF dataset is a list of [x, y] pairs and is not guaranteed to be a
rectangle or even convex, so area and intersection are both computed by rasterising the polygon
with PIL rather than by a closed-form formula: the same rasteriser is used for "the field's area"
and for "the overlap area", so the two numbers are always consistent with each other.

Rasterisation happens on a LOCAL canvas sized to the polygons involved, never on the full page:
a page can be tens of megapixels and most polygon pairs never overlap.
"""
import math

import numpy as np
from PIL import Image, ImageDraw


def polygon_bbox(points):
    """Integer bounding box (x0, y0, x1, y1), x1/y1 exclusive, covering every vertex.

    Padded one pixel past the ceiling of the max coordinate: PIL's ImageDraw.polygon fills the
    pixel AT an integer vertex coordinate (an inclusive edge), so a canvas sized to the naive
    ceil(max) clips that last row or column whenever the canvas happens to be exactly as tight
    as the polygon's own bbox, while the same polygon drawn on a larger, shared canvas (as
    happens for every "other polygon" in overlap_share) does not get clipped. Without this pad,
    the SAME polygon's rasterised area would differ depending on which canvas it happened to be
    drawn on. Measured 2026-09-25: a 6x6 axis-aligned box rasterised on its own tight bbox gave
    36 px, the identical box rasterised on a larger canvas gave 49 px, until this pad made both
    give 49 px.
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = math.floor(min(xs)), math.floor(min(ys))
    x1, y1 = math.ceil(max(xs)) + 1, math.ceil(max(ys)) + 1
    return int(x0), int(y0), int(x1), int(y1)


def is_degenerate(points):
    """True when the polygon has zero width or zero height (a point, a line, a repeated vertex).

    Uses the UNPADDED extent on purpose: polygon_bbox's +1 pad exists to give a real polygon a
    stable rasterised area regardless of canvas size, not to turn a genuinely zero-area input
    into a 1x1 measured field.
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    width = math.ceil(max(xs)) - math.floor(min(xs))
    height = math.ceil(max(ys)) - math.floor(min(ys))
    return width <= 0 or height <= 0


def _bboxes_overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def rasterize_at(points, x0, y0, w, h):
    """Boolean mask of shape (h, w): True where the polygon covers that LOCAL pixel.

    (x0, y0) is the offset of the local canvas in the polygon's own coordinate system.
    """
    if w <= 0 or h <= 0:
        return np.zeros((max(h, 0), max(w, 0)), dtype=bool)
    local = [(px - x0, py - y0) for px, py in points]
    img = Image.new("1", (w, h), 0)
    if len(local) >= 3:
        ImageDraw.Draw(img).polygon(local, fill=1, outline=1)
    return np.asarray(img, dtype=bool)


def polygon_area(points):
    """Rasterised area of a polygon, in pixels, on its own bounding box. 0 if degenerate."""
    if is_degenerate(points):
        return 0
    x0, y0, x1, y1 = polygon_bbox(points)
    mask = rasterize_at(points, x0, y0, x1 - x0, y1 - y0)
    return int(mask.sum())


def overlap_share(field_points, other_polygons):
    """(share, field_area): the field's area covered by the UNION of other_polygons.

    share is overlap_area / field_area, 0.0 when the field has no pixels or nothing overlaps.
    other_polygons already outside the field's bounding box are rejected without rasterising.
    """
    if is_degenerate(field_points):
        return 0.0, 0

    fbbox = polygon_bbox(field_points)
    fx0, fy0, fx1, fy1 = fbbox
    fw, fh = fx1 - fx0, fy1 - fy0
    if fw <= 0 or fh <= 0:
        return 0.0, 0

    relevant = [p for p in other_polygons if not is_degenerate(p)
                and _bboxes_overlap(fbbox, polygon_bbox(p))]
    field_mask = rasterize_at(field_points, fx0, fy0, fw, fh)
    field_area = int(field_mask.sum())
    if field_area == 0:
        return 0.0, 0
    if not relevant:
        return 0.0, field_area

    union = np.zeros((fh, fw), dtype=bool)
    for p in relevant:
        union |= rasterize_at(p, fx0, fy0, fw, fh)
    overlap = int(np.logical_and(field_mask, union).sum())
    return overlap / field_area, field_area
