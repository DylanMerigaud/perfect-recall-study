# naf

The pipeline that reads NAF (github.com/herobd/NAF_dataset, CDLA-Permissive-1.0, real United
States National Archives form scans with human field and comment labels) and measures how often
ink not produced by any generator in this study sits inside a field a human labeller marked
blank: the prevalence check T15 of the plan uses as a real-world bound independent of every
generator this study built.

See `FORMAT.md` for NAF's own annotation schema and every methodological decision this pipeline
makes on top of it (which box types count as a field, how polygons are rasterised, the
registration method and its stated scope limits).

## Layout

- `annotations.py`: reads one NAF image's JSON into the fields (isBlank == 3, a response-area
  type) and comments (added writing) this study measures.
- `geometry.py`: polygon rasterisation, area and overlap share, used by both measures below.
- `stats.py`: Wilson score interval and a cluster bootstrap over images, exactly as the
  preregistration specifies (10,000 resamples, `numpy.random.default_rng(20260925)`, percentile
  interval). Kept local rather than imported from `analysis/stats.py` (T16, written after this
  pipeline runs).
- `human_label.py`: the human-label measure. Needs no image pixels and no registration.
- `registration.py`: the pixel measure. Imports dossier-preflight's own
  `preflight.deskew.register` and `build_frame`, so it only runs under dossier-preflight's own
  venv.
- `fetch.py`: downloads and places NAF's images (a plain HTTPS release asset, no account, no
  browser), per NAF's own README.
- `measure.py`: the orchestrator, three explicit stages (see below).
- `tests/`: pytest, toy arrays and toy JSON fixtures only, no network and no real NAF data
  required. Runs fully under plain `python3`; the handful of functions that need
  dossier-preflight are pure coordinate math with no image involved, so they are tested the same
  way.

## How to rerun this

Three environment variables, matching the plan's own naming:

```
AR=/Users/dylanmerigaud/Code/perfect-recall-archive   # local archive staging, not in git
DP=/Users/dylanmerigaud/Code/dossier-preflight         # dossier-preflight's own checkout
PY=$DP/.venv/bin/python
```

1. Clone NAF and check its licence (done once; the clone lives under `$AR/x3/NAF`, not in this
   repo):

   ```
   git clone https://github.com/herobd/NAF_dataset $AR/x3/NAF
   git -C $AR/x3/NAF rev-parse HEAD   # record this sha in results/naf.json's meta.naf_commit
   cat $AR/x3/NAF/LICENSE             # must read Community Data License Agreement - Permissive 1.0
   ```

2. Fetch the images (idempotent; skips a tarball or an already-placed image it finds):

   ```
   python3 -m naf.fetch --naf-dir $AR/x3/NAF
   ```

3. Run the tests (either Python works for these; only the pixel stage itself needs `$PY`):

   ```
   python3 -m pytest naf/tests -q
   ```

4. Human-label measure (plain `python3`, no dossier-preflight needed):

   ```
   python3 naf/measure.py human-label --naf-dir $AR/x3/NAF --out $AR/x3
   ```

5. Pixel measure (must be `$PY`, dossier-preflight's own venv: it imports
   `preflight.deskew.register` and `build_frame` directly):

   ```
   $PY naf/measure.py pixel --naf-dir $AR/x3/NAF --out $AR/x3
   ```

6. Combine into the study's numbers (plain `python3`; requires both partials above to already
   exist, and refuses with a clear message otherwise):

   ```
   python3 naf/measure.py combine --naf-dir $AR/x3/NAF --archive $AR/x3 \
       --results results/naf.json --naf-commit <sha from step 1>
   ```

   Prints the reconciliation (fields in = fields measured + fields excluded, for both measures)
   and the P-NAF band, and writes `results/naf.json`.

Per-field CSVs and the per-group consensus PNGs are written under `$AR/x3/` (an archive staging
directory outside every repo, per the plan): `naf_fields_human_label.csv`,
`naf_fields_pixel.csv`, `consensus/<group>.png`. `results/naf.json` in this repo is the only
output committed to git.
