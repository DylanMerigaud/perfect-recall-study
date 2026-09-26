# Preregistered hypotheses

Verdicts by the criteria of prereg/PREREG.md. "not tested yet": the source (X2) does not exist yet.

| Hypothesis | Estimate | k / n | Wilson 95% | Cluster bootstrap 95% | Verdict |
|---|---|---|---|---|---|
| H1 | 0.396 | 204 / 515 | [0.355, 0.439] | [0.368, 0.426] | supported |
| H2 | n/a | n/a | n/a | n/a | not tested yet |
| H3 | n/a | n/a | n/a | n/a | not tested yet |
| H4 | n/a | n/a | n/a | n/a | not tested yet |
| H5 | P1 crowns `text_sensor=ink, ink_threshold=190`, P5 crowns `text_sensor=ink, ink_threshold=160` | n/a | n/a | n/a | not supported |
| H6 (A3 part) | hits 1 of 4 failing cells (strict 1 of 4); false predictions 3 of 4 | n/a | n/a | n/a | A3 part: not supported; H6: not tested yet |
| P-NAF | pixel 0.400 (invalid); human-label lower bound 0.0286 | 159 / 5550 | [0.025, 0.033] | [0.019, 0.040] | not interpretable (preregistered band on record: common) |

## A3 at the shipped thresholds (the cells H6 scores)

| Check | Recall | k / n | Wilson 95% | Identity bootstrap 95% | False alarms per target |
|---|---|---|---|---|---|
| consistency | 0.963 | 52 / 54 | [0.875, 0.990] | [0.926, 1.000] | 0.8889 (48 / 54) |
| cropped_page | 0.812 | 173 / 213 | [0.754, 0.859] | [0.794, 0.828] | 0.2963 (64 / 216) |
| expiry | 1.000 | 2 / 2 | [0.342, 1.000] | [1.000, 1.000] | 0.0000 (0 / 4) |
| forbidden_value | 0.099 | 16 / 162 | [0.062, 0.154] | [0.068, 0.136] | 0.0000 (0 / 432) |
| required_checkbox | 0.944 | 204 / 216 | [0.905, 0.968] | [0.931, 0.958] | 0.7361 (159 / 216) |
| required_field | 0.826 | 422 / 511 | [0.791, 0.856] | [0.809, 0.844] | 0.3177 (446 / 1404) |
| resolution | 1.000 | 216 / 216 | [0.983, 1.000] | [1.000, 1.000] | 0.0093 (2 / 216) |
| rotated_page | 0.528 | 114 / 216 | [0.461, 0.593] | [0.491, 0.574] | 0.0000 (0 / 216) |
| signature | 1.000 | 54 / 54 | [0.934, 1.000] | [1.000, 1.000] | 0.3519 (19 / 54) |
