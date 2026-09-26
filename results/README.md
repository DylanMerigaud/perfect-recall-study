# results

Tables, figures and the numbers registry (`numbers.json`) that the analysis scripts write. Every
number the manuscript quotes is read from a file in this folder, never typed by hand.

- `naf.json` is the X3 result (T15); `naf-reading.md` is its reading, which marks the pixel
  measure invalid and P-NAF "not interpretable".
- `protocols.json` (analysis/protocols.py): every protocol's choices, validated scores and scores
  on the targets.
- `hypotheses.json` (analysis/hypotheses.py): H1 to H6 and P-NAF with estimate, intervals, n and
  verdict, plus the exploratory readings.
- `tables/*.md`, `figure1.png`, `figure1.svg`, `figure1.json` (analysis/exhibits.py).
- `numbers.json` (analysis/numbers.py).

See the root README for how this folder fits the rest of the study.
