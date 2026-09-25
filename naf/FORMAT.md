# NAF annotation format, and the decisions this pipeline makes on top of it

NAF (github.com/herobd/NAF_dataset, CDLA-Permissive-1.0) ships one JSON file per scanned form
image, plus a `groups/<group>/` directory per form type. This file documents the dataset's own
schema (from its README, verified against the data) and every place this pipeline had to choose
an interpretation the dataset's README leaves open.

## The dataset's own schema

Each `groups/<group>/<image_id>.json` has, among other keys:

- `fieldBBs`: a list of boxes. Each has `poly_points` (four [x, y] corners, top-left, top-right,
  bottom-right, bottom-left, not restricted to a rectangle), `type`, `id`, and, only meaningful
  for response-area types, `isBlank`: `0` text, `1` handwriting, `2` print or stamp, `3` blank,
  `4` signature.
- `type` values seen in `fieldBBs`: `field`, `fieldP` (a blank inside a prose/fill-in-the-blank
  area), `fieldRow`, `fieldCol` (a whole table row or column), `fieldCheckBox`, `fieldCircle`
  (text meant to be circled or struck through), `fieldRegion` (separates multiple documents
  scanned in one image), `graphic` (an image or photograph), and `comment`: "any added writing or
  text which is not in a field", NAF's own definition, independent of this study.
- `textBBs`: pre-printed text, instructions and labels. No `comment` boxes were found there
  (checked over the whole dataset, 2026-09-25): every `comment` box lives in `fieldBBs`.
- Per group, a `template<n>.json` with no `imageFilename`, `width` or `height`: an
  annotation-only template, not a blank image. This is exactly what the plan's dataset table
  means by "no blank templates": there is no scanned or synthetic blank page to register
  against, which is why this pipeline builds its own consensus blank (registration.py) instead
  of reading one.
- Images are not committed (`.gitignore`: `**/*.jpg`); they ship as a separate GitHub release
  asset per the dataset's README, fetched by `fetch.py`.

Checked over the whole dataset (2026-09-25, 865 non-template annotation files):
`fieldBBs` types and counts: field 10,420; fieldRow 10,217; fieldP 6,920; fieldCol 5,815;
comment 3,009; fieldCircle 579; fieldCheckBox 265; graphic 104; fieldRegion 92. Of these,
`isBlank == 3` occurs on: field 2,832; fieldP 1,476; fieldRow 1,092; fieldCheckBox 91;
fieldCol 56; comment 24; graphic 4; fieldCircle 3; never on fieldRegion.

## Decisions this pipeline makes

**Which types count as a "field" for the isBlank == 3 population** (`annotations.FIELD_TYPES`):
`field`, `fieldP`, `fieldRow`, `fieldCol`, `fieldCheckBox`, `fieldCircle`. Excluded: `comment`
(it is the added-writing layer itself, never a response area a filer left blank, whatever its
own `isBlank` happens to read: 24 comment boxes carry `isBlank == 3`, a labelling side effect,
not a blank field); `graphic` (an image or photograph, not a field); `fieldRegion` (never carries
`isBlank == 3` in this dataset, so excluding it is a documented no-op, not a live filter).

**The human-label measure** (`human_label.py`, needs no image, no registration): for every field
in the population above with `isBlank == 3`, the share of its rasterised area covered by the
union of that image's `comment` polygons (any `isBlank` value on the comment: a comment box marks
that something was added there, not what kind). Positive at a share >= 1%, per the plan and the
preregistration.

**Polygon rasterisation** (`geometry.py`): PIL's `ImageDraw.polygon(fill=1)` fills the pixel AT
an integer vertex coordinate (an inclusive edge). A canvas sized to the naive ceiling of a
polygon's own extent therefore clips that last row or column exactly when the canvas is as tight
as the polygon's own bounding box, while the same polygon drawn on a larger, shared canvas (as
happens for every "other polygon" compared against a field) is not clipped: the SAME polygon
would rasterise to a different area depending on which canvas it happened to be drawn on.
`polygon_bbox` pads one pixel past the ceiling so every canvas is always large enough to hold
the inclusive edge, making area stable regardless of canvas size; `is_degenerate` separately
catches a truly zero-width or zero-height input (a point, a repeated vertex) so it is excluded
rather than measured as a spurious 1x1 field once the pad is applied. Neither case occurred in
the real dataset (0 fields excluded as degenerate, checked 2026-09-25); both are covered by
`naf/tests/test_geometry.py`.

**Form-type grouping for the pixel measure**: NAF's own `groups/<group>/` directories ARE the
form-type grouping the plan asks for ("group images by form type"); the dataset's README states
groups hold "images of the same form type", so no separate clustering is performed. Seven groups
reach the plan's 10-image floor (2026-09-25): `1`, `104_1`, `106`, `107`, `108`, `131`, `132`,
each with exactly 10 images (the dataset appears to cap labelled images per group near 10; no
group has more).

**Registration** (`registration.py`, dossier-preflight's own `preflight.deskew.register` and
`build_frame`, run under `$DP/.venv/bin/python`): within a group, the medoid is the image whose
downsampled thumbnail has the least total absolute difference to every other thumbnail (a cheap
proxy; not itself a use of dossier-preflight's code). Every image, including the medoid, is
registered against the medoid with `quarters=(0, 2)`: a scan fed upside down (180 degrees) is
common enough to check and cheap to handle exactly (a point reflection); a scan fed sideways (90
or 270 degrees) is not attempted, because undoing it swaps width and height and this pipeline
does not carry that swap through the field-polygon coordinates. This is a stated scope limit.
Probed on real images from all seven groups (2026-09-25) before this was written, each image
against its group's first image as a stand-in reference: restricting to `quarters=(0,)` already
finds correlation peaks of 0.53 to 0.96 on every one of the 63 non-reference images tried. The two
skipped orientations (90 and 270 degrees) are a small, disclosed loss, not a missing majority
case.

**Each of the two quarters searched (0 and 180 degrees) is registered INDEPENDENTLY**
(`_register_best_of`), not by a single `register(grey, medoid, quarters=(0, 2))` call, and the
higher of the two final peaks wins: `register`'s own coarse-then-refine search can otherwise lock
onto the wrong quarter. The real case that caught this, and its measured effect, is written up
below under "A second, independent bug", next to the dilation fix it was found alongside.

A registration is treated as failed, and the image excluded from the pixel measure (all its
fields excluded with it), when its correlation peak is below `MIN_PEAK = 0.4`. Chosen because
every real registration probed (2026-09-25) scored at least 0.53; a true failure to find any
correspondence at all reads far lower (near 0), so 0.4 is a floor well under the observed
working range, not a threshold expected to bite often.

**The consensus blank**: each successfully registered image is warped into the medoid's own pixel
frame (an affine built from the registration answer: scale and translate for `quarter_turns ==
0`; scale, translate and a point reflection for `quarter_turns == 2`), binarised at a fixed level
128 (not Otsu: the plan's own wording, "the share of pixels dark in the image (level 128)", and
matching it on both sides of the comparison), each image's dark mask is DILATED by
`CONSENSUS_DILATE_RADIUS = 3` pixels (see below), and the consensus is the majority vote (at
least half of the group's registered images dark, after dilation) at each pixel: the printed
template ink common to the group, not any one scan.

**Two problems were found and fixed the same day, in this order, both before any number here was
treated as a result**, on the same real field the first pixel-measure run flagged as its most
extreme outlier (group 132, field `f46`, image `007540939_00045`, a "No........." dotted line):

1. **The quarter-turn coarse-round trap.** `preflight.deskew.register` picks ONE coarse winner
   across every quarter turn it is given and only refines that one candidate; refinement never
   runs on a quarter that lost the coarse round, even when it would have refined to a higher
   final peak than the quarter that won. Group 132's image `007540939_00111` is upright
   (confirmed by eye against the medoid), yet `register(grey, medoid, quarters=(0, 2))` picked
   `quarter_turns=2` at peak 0.604, while `register(grey, medoid, quarters=(0,))` alone found the
   correct `quarter_turns=0` at a HIGHER peak of 0.619. Left uncaught, this rotated two of group
   132's ten images 180 degrees into the consensus (visible as a garbled, upside-down ghost of
   the form's own text at the bottom of the first, unfixed `consensus/132.png`).
   `_register_best_of` (`registration.py`) now searches each quarter independently and keeps the
   higher final peak; after this fix alone, only 1 of 165 fields in the whole pixel measure comes
   from a `quarter_turns == 2` registration, against several before it. This fix alone barely
   moved the pooled pixel-measure share (0.345% threshold: 0.491 to 0.485 over 165 fields): the
   outlier field itself was never one of the misrotated images, so the next problem was still
   open.
2. **Registration jitter smears fine template ink.** Registration here is translate and uniform
   scale only, refined to a modest sub-pixel precision, never a sub-degree rotation or a local
   correction. Even after fix 1, field `f46`'s per-pixel vote fraction across the field peaked at
   0.70 and averaged 0.24, with NO pixel reaching the 0.5 majority needed to count as template,
   even though the dotted line is printed on every form of that group (confirmed by warping the
   consensus back into this image's own frame both ways: see `warp_to_canonical`'s cross-check
   against dossier-preflight's own `build_frame`, which round-trips to under 1.3% pixel mismatch
   on a synthetic pattern for both supported quarter turns). A radius sweep on that field (0 to
   5 px of binary dilation on each image's dark mask before the majority vote) showed coverage
   rising monotonically (4%, 21%, 32%, 42%, 52%, 62% of the field at radius 0 to 5);
   `CONSENSUS_DILATE_RADIUS = 3` was chosen because it is small relative to the smallest real
   mark this study places on a real capture (about 8 px, a 1 mm pencil dot at 200 dpi: T14, X2),
   so a genuine added mark is not dilated away, while genuine fine template ink recovers enough
   votes to be recognised. This fix changed the pooled pixel-measure share at the shipped
   threshold from 0.485 to 0.400 over the same 165 fields, group 132's mean field share from
   0.090 to 0.036 and its maximum (still field `f46`) from 0.963 to 0.567: a real, disclosed, and
   only PARTIAL correction, not a claim that the pixel measure is now free of registration noise.
   Applied inside `register_group`, never at the per-field comparison step, so it only affects
   which pixels are treated as template, not which pixels are treated as the image's own ink.

Neither fix is a post-hoc adjustment to a result already read: both were found while inspecting
the first run's most extreme value, before that run's numbers were combined into
`results/naf.json`, and both are in the code the committed numbers were produced from.

**Per-field added-ink share**: dossier-preflight's own `build_frame` warps the consensus back
into each image's native pixel frame (the direction dossier-preflight already provides). A pixel
counts as added ink when it is dark (level 128) in the image and NOT dark in the consensus at the
same native location; the field's share is added-ink pixels over the field's own rasterised area,
in image i's own native resolution, not the medoid's.

**Registration failures and excluded fields are both counted**, never silently dropped: see
`results/naf.json`'s `counts.pixel` block and `naf/measure.py`'s printed reconciliation
(images in = measured + excluded; fields in = measured + excluded), matching T15's Verify step.
