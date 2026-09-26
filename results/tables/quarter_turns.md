# Wrong quarter turn on A3 (exploratory, not preregistered)

The production reading path of dossier-preflight settles on a quarter turn per page; grid/read_images.py records it against the expected one.

All pages: 500 of 2643 = 0.189, Wilson 95% [0.175, 0.205], identity bootstrap 95% [0.183, 0.195].

| Piece | Wrong turn | k / n | Wilson 95% |
|---|---|---|---|
| employment | 0.326 | 282 / 864 | [0.296, 0.358] |
| identity | 0.110 | 77 / 702 | [0.089, 0.135] |
| tax | 0.124 | 67 / 540 | [0.099, 0.155] |
| tax_es | 0.138 | 74 / 537 | [0.111, 0.170] |

Do the wrong-turn pages carry the misses? Positives of every check at the shipped thresholds:

- recall on wrong-turn pages 0.707 [0.664, 0.746] over 474 positives; on right-turn pages 0.663 [0.642, 0.683] over 2063;
- wrong-turn pages hold 0.187 of the positives and 0.167 of the misses.

| Check | Recall, wrong turn | positives | Recall, right turn | positives |
|---|---|---|---|---|
| consistency | 1.000 | 3 | 0.961 | 51 |
| cropped_page | 0.941 | 34 | 0.788 | 179 |
| expiry | n/a | 0 | 1.000 | 2 |
| forbidden_value | 0.000 | 28 | 0.119 | 134 |
| required_checkbox | 1.000 | 31 | 0.935 | 185 |
| required_field | 0.800 | 275 | 0.578 | 1129 |
| resolution | 1.000 | 36 | 1.000 | 180 |
| rotated_page | 0.000 | 54 | 0.704 | 162 |
| signature | 1.000 | 13 | 1.000 | 41 |
