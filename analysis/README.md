# analysis

The statistics, the protocol comparison (RQ2), the preregistered hypotheses, the numbers
registry, and the tables and figure. Every threshold choice and every score goes through
dossier-preflight's own `grid/analyze.py` (its sweep, its choice rule, its holdout predicates,
its `--frozen` scoring), imported as a module and never re-implemented.

## Environment

Run everything in this folder with **dossier-preflight's virtual environment**, since the code
imports dossier-preflight (and its Tesseract-free analysis path: numpy, PyYAML, Pillow,
matplotlib):

```
DP=../dossier-preflight
PY=$DP/.venv/bin/python
```

Two environment variables locate the inputs, with sibling-directory defaults:
`DOSSIER_PREFLIGHT` (default `../dossier-preflight`) and `PR_ARCHIVE` (default
`../perfect-recall-archive`, the local staging of the raw readings that the Zenodo record will
hold: `a1/readings.jsonl`, `a2/readings.jsonl`, `a3/readings.jsonl`, `a4/readings.jsonl.gz`,
later `x2/readings.jsonl`). Sweeps are cached under `$PR_ARCHIVE/analysis-cache/`, keyed by the
readings file's sha256 and the dossier-preflight commit.

## Commands, in order

```
$PY analysis/protocols.py     # results/protocols.json
$PY analysis/hypotheses.py    # results/hypotheses.json (reads protocols.json)
$PY analysis/exhibits.py      # results/tables/*.md, results/figure1.{png,svg,json}
$PY analysis/numbers.py       # results/numbers.json (reads the three above, census/, naf.json)
$PY -m pytest analysis/tests -q
```

`numbers.py` is deterministic: two runs give byte-identical `numbers.json`.

## What each file does

- `stats.py`: Wilson 95% interval, cluster bootstrap (10,000 resamples, numpy
  `default_rng(20260925)`, percentile), its vectorised twin for a pooled ratio, exact McNemar,
  Cohen's kappa with a bootstrap interval. Known-answer tests in `tests/test_stats.py`.
- `data.py`: paths, which arms exist (an arm whose file is shorter than its declared size is
  still being written and counts as absent), loading an arm into `analyze.load()`'s index,
  dossier assembly, the sweep cache, and `fast_curve()` (the same points as `analyze.curve()`,
  counted by binary search; tested equal).
- `protocols.py`: P1 to P6 as holdout predicates, the shipped rule through `analyze.py`'s own
  sequence, the baselines B1 (Youden), B2 (class-mean midpoint), B3 (ink AND / OR the best OCR
  sensor) and the budget sensitivity (0.1%, 0.5%), each choice scored on A3 seed 37 and on X2.
  Its docstring states the two places this study adds to `analyze.py`.
- `hypotheses.py`: H1 to H6 and P-NAF by the criteria of `prereg/PREREG.md`, and the
  exploratory readings (the product view of H1, the wrong-quarter-turn rate on A3).
- `x2.py`: the real captures as a target. It plugs in by path: until `x2/readings.jsonl`
  exists, every X2 result reads "not tested yet", and the next run after it lands scores it
  with no code change.
- `exhibits.py`: the tables and the one figure.
- `numbers.py`: the registry the manuscript's `{{key}}` placeholders are rendered from.

## Verdict vocabulary

"supported", "not supported", "not tested" (the source is absent for good), "not tested yet"
(the source is still to come: X2), and "not interpretable" (P-NAF, amendment A1 of the
preregistration).
