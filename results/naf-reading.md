# X3 (NAF) reading, 2026-09-25

The reading of `results/naf.json`, done after the X3 run and after the tag `prereg-v1`. The
deviations it records and what the paper reports are fixed in `prereg/PREREG.md`, section
"Deviations and amendments, 2026-09-25, after the X3 run".

## Verdict

- The preregistered P-NAF rule, applied to the pixel measure it names, gives **"common"**:
  66 of 165 fields, 0.400, Wilson 95% [0.328, 0.476], image-cluster bootstrap 95% [0.299, 0.538].
- That measurement is **invalid as a prevalence of foreign ink**: most of its positives are
  printed template ink the consensus failed to hold. P-NAF is reported as **"not interpretable"**.
- The human-label measure is reported as an **exploratory lower bound**: 159 of 5,550 fields,
  2.86%, Wilson 95% [2.46%, 3.34%], image-cluster bootstrap 95% [1.89%, 3.98%] over 556 images.
  Its band range is "occasional" under either interval.

## The crop audit

Sample (`naf/diagnostics/audit_sample.py`): among pixel-positive fields with no comment overlap
(62), the 15 highest shares plus 10 drawn at random from the rest (`random.Random(20260925)`),
plus the 4 fields with a comment overlap. Each was rendered by `naf/diagnostics/crop_audit.py` as
three panels: the scan, the consensus warped into the scan's frame, and the added-ink pixels in
red inside the field outline. 14 of the 25 no-comment fields were read by eye, plus all 4
comment fields.

| field (group, image, field) | share | reading |
|---|---|---|
| 132, 007540939_00045, f46 | 0.567 | residue: the consensus is mostly black here, the red covers paper texture and the dotted line |
| 132, 007540939_00398, f53 | 0.149 | residue: dotted line and paper noise |
| 131, 100660788_00363, f58 | 0.093 | real (ditto marks) plus the whole dotted line as residue |
| 131, 100651536_00022, f59 | 0.078 | residue: the dotted line, absent from the consensus |
| 132, 007540939_00045, f54 | 0.069 | residue: dotted line and paper noise |
| 132, 007540939_00126, f51 | 0.058 | residue: dotted line |
| 131, 101023529_00047, f50 | 0.056 | residue: dotted line |
| 132, 007540939_00111, f56 | 0.042 | real (signature strokes entering the field) plus dotted-line residue |
| 106, 007675709_00058, f4 | 0.022 | residue: dotted line |
| 106, 007675709_00027, f4 | 0.024 | residue: dotted line |
| 131, 100651536_00024, f57 | 0.021 | residue: dotted line, partly |
| 1, 007182398_00121, f30 | 0.006 | real (a pen stroke from the label above; this is the group's medoid) |
| 131, 100651536_00020, f25 | 0.005 | real (handwriting from the row above dropping into a blank table row) plus the printed row number |
| 106, 007675709_00062, f1 | 0.007 | residue: dotted line |

**10 of 14 are residue only, 4 of 14 hold real added ink**, always mixed with residue.

Fields with a comment overlap: 131, 101023529_00081, f70 (handwritten strokes, real);
132, 007540939_00398, f51 (a handwritten "227", real); 131, 100651536_00022, f28 (a signature
stroke and an ink blot, real, plus the printed row number); 132, 007540939_00183, f47 (specks
only). The 2 x 2 table has no field that is comment-positive and pixel-negative.

Two further signs that the pixel measure reads residue:

- **The medoids.** Each group's medoid registers against itself exactly (peak 1.0), yet 7 of the
  17 medoid fields are positive: the vote drops the medoid's own printed line because the other
  scans sit several pixels off at that spot.
- **Group 132's consensus is mostly black** once the grey, noisy paper crosses level 128 after
  dilation. The measure is blind in some places there and flags in others. 27 of the 66
  positives come from this group.

## Sensitivity

Re-run under dossier-preflight's venv with `naf/diagnostics/crop_audit.py`. Radius 3 reproduces
the committed 66 of 165.

| consensus | >= 0.345% | >= 1% | >= 4% |
|---|---|---|---|
| no dilation (the preregistered median) | 80 | 61 | 31 |
| 3 px dilation (committed) | 66 | 44 | 14 |
| 3 px, each image left out of its own vote | 73 | 48 | 17 |
| 6 px dilation | 53 | 32 | 6 |
| 3 px, counting only added ink more than 8 px from any template ink | 42 | 26 | |

The count moves with a free parameter, and even at 6 px it stays above 5%.

## Why the human-label measure is a lower bound, not the prevalence

- It counts only marks NAF's annotators drew a `comment` box around. The audit found real ink
  with no comment label (the ditto marks in 100660788_00363 f58, the stray row handwriting in
  100651536_00020 f25), so it undercounts.
- It covers the whole dataset (5,550 fields, 556 images with at least one), not only the seven
  groups the pixel measure could reach.
- It was not the preregistered P-NAF measure, so it is labelled exploratory.

## Two findings on dossier-preflight's registration (exploratory)

1. **The quarter-turn trap** (`naf/diagnostics/quarter_trap.py`). `register` refines only the
   quarter that wins the coarse round. On group 132, image 007540939_00111 (upright) against
   medoid 007540939_00212: `quarters=(0, 2)` returns turn 2 at peak 0.6042, `quarters=(0,)` alone
   returns turn 0 at 0.6189, and the coarse round scores the two 0.5970 and 0.5972.
2. **The tool's own `prepare()` gets this upright page wrong**: quarter turn 3, peak 0.5650,
   orientation margin -0.0539. The margin is negative, so the rotated-page check would not fire,
   while the page would be read in the wrong frame. This is one archival image against a scanned
   medoid, not one of the tool's templates. None of the synthetic readings in the archive (A0
   measurements, control and corner; A4 readings and replay) chose a wrong turn, so real captures
   (X2) are where it could show up.

## Reproduce

```
AR=/Users/dylanmerigaud/Code/perfect-recall-archive
python3 naf/diagnostics/audit_sample.py $AR/x3
$PY naf/diagnostics/crop_audit.py OUT $(python3 naf/diagnostics/audit_sample.py $AR/x3 | awk '{print $2}')
$PY naf/diagnostics/quarter_trap.py
```
