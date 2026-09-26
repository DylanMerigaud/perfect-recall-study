# Preregistration

Written on 2026-09-25, before any reading of the arms A1, A2, A3, A4, X2 or X3 exists. This file
and `coverage-audit.csv` are committed together and tagged `prereg-v1`. Every readings file
written later carries a `ts` field (UTC, ISO 8601); a row of A3, X2 or X3 whose `ts` is earlier
than the commit time of `prereg-v1` (`git log -1 --format=%ct prereg-v1`) invalidates the claim
that this preregistration came first, and the final audit checks it.

Any change to this file after the tag is a dated amendment appended at the end, in its own
commit, with the reason. An amendment that touches the design of an arm is committed BEFORE any
reading of that arm is scored.

## 1. Research questions

- **RQ1.** When a document checker's thresholds are calibrated on a parametric synthetic
  generator and validated on a held-out seed, how far do the validated scores diverge from the
  scores measured under an independent third-party generator and on real captures of the same
  forms, and how common is the condition the generator omitted (foreign ink in a blank field) in
  real archival forms?
- **RQ2.** Which validation protocol (seed holdout, jittered seed holdout, level holdout,
  leave-one-factor-out, cross-generator, pooled generators) best predicts the real-capture scores,
  and does the choice of protocol change which sensor the selection rule crowns?
- **RQ3.** Across the author's public tools that carry both a self-generated score and an
  independent check, how often did the independent check contradict the score, and through which
  mechanisms?

The system under study is dossier-preflight (github.com/DylanMerigaud/dossier-preflight). Its
generator is called G0 below: fictional dossiers rendered from four public blank forms (IRS W-9,
its Spanish edition, USCIS I-9, Cerfa 14011), degraded by rotation, dpi, JPEG quality and Gaussian
noise (`preflight/degradation.py`), with one defect injected per variant
(`preflight/fixtures.py`).

## 2. The thresholds used "as shipped"

"As shipped" means the values of `thresholds.json` at the tag `v0.2.0` of dossier-preflight.
v0.2.0 is not tagged at the time of writing. The values below were read on 2026-09-25 from
`thresholds.json` at the root of dossier-preflight on `origin/main`, commit
`2235d50abf39d0b0e952fedd082672d7003f25b9` (file sha256
`184351f68dacc89118f22efce0a052f6b596e07b7a24f93b0bdfdf1a7e4fe4a5`). The file is byte-identical
to the one at `v0.1.0` (commit 42732f0): the domain-rule fix of commit 2235d50 changed no value.
v0.2.0 is tagged from this state or from a later one whose `thresholds` values are identical; the
final audit checks that equality. If any value differs at v0.2.0, a dated amendment records the
new values before any A1 to A3 or X2 reading is scored, and those values are the ones used.

Each check fires when its score is above its value (scores are oriented so that higher means more
reason to reject). False-positive budget 0.002, thresholds measured on 2026-08-21.

| Check | Value | Origin | Sensor and settings |
|---|---|---|---|
| required_field | -0.345 | grid | ink added in the field against the blank, ink level 128 (fires below 0.345% of the zone) |
| required_checkbox | -14.375 | grid | ink added in a central disc, radius 0.30 of the side, ink level 128 |
| signature | -342.05 | grid | largest added connected component, ink level 128 (fires when its diagonal is below 342.05 canonical px) |
| expiry | 0.0 | definition | page OCR, min_conf 0 (fires when the date is past on the filing clock) |
| consistency | 0.3939 | grid | zone OCR, min_conf 0 |
| forbidden_value | 0.7214 | grid | page OCR, min_conf 0 |
| resolution | -148.5 | 150 dpi floor minus 1% | source dpi estimated from registration |
| cropped_page | 0.0879 | grid | coverage of the registered frame |
| rotated_page | 0.3585 | grid | orientation margin |

## 3. Sources and arms, with their exact sizes

| Id | Source | What varies | Used for |
|---|---|---|---|
| A0 | the published grid (existing readings, v0.1.0) | 1 identity, 1 instance per defect, 384 cells (angle, dpi, JPEG, noise), seeds 11/23/37, plus the ink sub-grid | continuity; the thresholds as shipped |
| A1 | G0 re-run with 6 fictional identities and every defect instance | cell set R (below, after the cap cut), seeds 11/23/37 | P1, P3, P5, P6 data |
| A2 | G0j: G0 with a seed that also draws continuous jitter | same R, seeds 11/23/37 | P2 |
| A3 | G1: Augraphy 8.2.6 `default_augraphy_pipeline()`, unmodified, on the rendered pages | dpi 150/200/300, 3 seeded draws per page, 6 identities | P4, P5, H1, H5 |
| A4 | the targeted foreign-ink run, re-run with raw readings dumped and all three ink shapes on every seed | 27 cells, 4 levels, 3 seeds | archives the raw rows the published aggregate never kept |
| X2 | real prints of 4 identities, captured by phone and optionally by flatbed | real paper, optics, hand signatures, hand-made marks | H2, H3, H4 targets; never used to choose anything |
| X3 | NAF real archival forms | real stray ink under human labels | prevalence band (P-NAF) |

**Jitter in G0j** (seeded by the job seed, drawn once per page): angle += U(-0.1, +0.1) degrees;
translation dx, dy ~ U(-3, +3) pixels at 200 dpi, scaled to the cell dpi; blur ~ U(0.3, 0.5);
JPEG quality += integer U(-5, +5), clipped to [10, 100].

### 3.1 The anchor: what the current code reads per cell

On dossier-preflight `origin/main` (2235d50), `grid/run.py --pilot 1` printed
`1 cells x 3 seeds x 1 parasite level(s) x 13 readings = 39 readings` and wrote 39 lines in 0.8
minutes on 3 workers (about 3.7 worker-seconds per reading). The 13 readings per (cell, seed) are
the 4 clean pieces plus one reading per single-defect variant (9 variants, each touching one
piece). The published grid is 384 x 3 x 13 = 14,976 readings, which is A0.

### 3.2 Defect instances per identity (the enumeration rule of the plan, applied to the reference schema)

Every identity file has the schema of `fixtures/reference.yaml`, so the count per identity is the
reference's. The rule: every required field emptied in turn, every required checkbox unticked,
one missing signature per signed piece, expiry at 1 day and at 365 days past (on the filing
clock), one disagreement per consistency pair the reference declares, the forbidden value on each
piece that carries one, and the three page defects on each piece.

Interpretation fixed here, before any reading:

- A required-field instance is a ROLE of the template's `required` list, the unit
  `Variant.empty_fields` takes. The W-9 `tax_id` role spans three comb boxes; emptying it empties
  all three (one instance, three positive targets).
- "A piece that carries" the forbidden value is a piece with a social security or taxpayer number
  field, where the form's own example number 999-99-9999 fits: `tax_id` on both W-9 editions and
  `ssn` on the I-9. The Cerfa carries none. The second forbidden value (`A COMPLETER`) is not
  injected, as in v0.1.0.
- The one declared consistency pair (street name, W-9 address against Cerfa street name) gets
  one disagreement, placed on the Cerfa side as in v0.1.0.
- The rule applies to all four pieces, the Spanish W-9 included. In v0.1.0 that piece only ever
  appeared clean; under this enumeration it carries its own instances.

| Piece (template) | Required fields | Checkboxes | Signature | Expiry | Consistency | Forbidden value | Page defects | Total |
|---|---|---|---|---|---|---|---|---|
| tax (fw9) | 4 (name, address, city, tax_id) | 1 | 0 | 0 | 0 | 1 | 3 | 9 |
| tax_es (fw9sp) | 4 | 1 | 0 | 0 | 0 | 1 | 3 | 9 |
| employment (i9) | 7 | 1 | 1 | 2 | 0 | 1 | 3 | 15 |
| identity (cerfa14011) | 7 | 1 | 0 | 0 | 1 | 0 | 3 | 12 |
| **all** | 22 | 4 | 1 | 2 | 1 | 3 | 12 | **45** |

Readings per identity per (cell, seed): 4 clean pieces + 45 defect instances (each touches one
piece) = **49**.

### 3.3 Arm sizes and the 30,000 cap

The cell set R is angle {0, 0.5, 2} degrees x dpi {150, 200, 300} x JPEG {55, 95} x noise sigma
{0, 6} = 36 cells. Cap per arm: 30,000 readings; above it, drop JPEG 55 first, then sigma 6.

- **A1**, full R: 6 identities x 36 cells x 3 seeds x 49 = **31,752**, above the cap.
  **Cut, recorded here before running: JPEG 55 is dropped.** R becomes angle {0, 0.5, 2} x dpi
  {150, 200, 300} x JPEG {95} x sigma {0, 6} = 18 cells, and A1 = 6 x 18 x 3 x 49 = **15,876**
  readings. Sigma 6 is kept (the cap holds after the first cut).
- **A2**: the same design with jitter: **15,876** readings, same cut.
- **A3**: 6 identities x 49 pages (4 clean + 45 instances) x 3 dpi x 3 seeds = **2,646** images,
  one reading each: **2,646** readings, under the cap. The page-defect overrides (72 dpi render,
  18% crop, quarter turn) are applied to the render before the Augraphy pipeline, as G0 applies
  them before its degradation.
- **A4**: 4 targeted variants (the emptied required field on I-9 City or Town, the unticked W-9
  box, the missing I-9 signature, the expired I-9 date; `grid/target_parasite.py targeted()` on
  the current code) x 27 cells x 3 seeds x 4 levels x 2 sides (variant and clean) = **2,592**
  readings. The replay without `--all-shapes` that proves the dump changes nothing is another
  2,592 readings and is not an arm.
- Total new generator readings: 15,876 + 15,876 + 2,646 + 2,592 = 36,990.

Consequence of the cut for P3: with a single JPEG level, the JPEG fold of the level holdout does
not exist. P3 runs three folds (angle 2 degrees, dpi 150, sigma 6), reported per fold and pooled.

**If the implemented enumeration (T08) differs from 3.2**, for example if the Spanish W-9 stays
clean-only (then 40 readings per identity per cell and seed, A1 = A2 = 6 x 36 x 3 x 40 = 25,920
with R intact and no cut) or if required fields are enumerated per field id rather than per role,
a dated amendment giving the implemented count, the recomputed arm sizes and the cap decision is
committed to this file BEFORE any A1 to A3 reading is scored. The line counts of the readings
files must equal the sizes declared here or in that amendment.

- **X2** (planned by the kit, T14): for identities id01 to id04, 13 base pieces (4 clean and one
  instance of each of the 9 defect types) plus 2 mark sheets (the clean copy and the emptied copy
  of the piece that the first required-field instance empties): 60 sheets. Phone captures: each
  base sheet twice (the low-resolution variant only on the flatbed at 75 dpi, so 12 base sheets on
  the phone) and each mark sheet twice after each of 4 steps (step 0 no mark, step 1 pencil dot of
  about 1 mm, step 2 pen stroke of about 5 mm, step 3 light pencil rub of about 1 cm square), so 4
  x (12 x 2 + 2 x 4 x 2) = **160 phone captures**, one reading each. The optional flatbed adds each
  sheet at 150 and 300 dpi (mark sheets after each step) plus the low-resolution variant at 75
  dpi: at most 4 x (12 x 2 + 2 x 4 x 2 + 1) = 164 captures. The exact count is the checklist the
  kit prints; if it differs from these numbers, a dated amendment records it before any X2
  reading is scored. Captures excluded at ingest (identity mismatch) are counted and reported. If
  Dylan declines the session, X2 is dropped: H2, H3 and H4 are reported as not tested, and P4 and
  P5 are scored against A3 seed 37 only.
- **X3** (NAF, github.com/herobd/NAF_dataset, CDLA-Permissive-1.0): every image at the pinned
  commit (about 860), unit = a field with `isBlank = 3`. Its size is the dataset's; registration
  failures are excluded and counted, and fields in = fields measured + fields excluded.

## 4. Hypotheses (verbatim from the plan, section 2.2)

Each hypothesis has one pre-declared criterion. Point estimates carry 95% intervals (section 7).

- **H1 (the blind spot, independent generator).** On A3 pages where an Augraphy augmentation laid
  ink inside the emptied required field (area share >= 0.5% of the field), the shipped
  `required_field` sensor's recall is below 0.50. (The shipped held-out estimate is 1.000.)
- **H2 (the benchmark is right about what it varies).** On real captures with no added marks, the
  pooled recall over the six content checks (required_field, required_checkbox, signature, expiry,
  consistency, forbidden_value) is at least 0.90 and the per-dossier false-alarm rate at most 0.10,
  at the shipped thresholds. Failing H2 means the problem is broader than ink.
- **H3 (the mechanism on real paper).** On real captures of the emptied required field carrying a
  hand-made mark of at least 1% of the field's area, the shipped ink sensor's recall is below 0.50
  and the best OCR sensor's recall is at least 0.60.
- **H4 (which protocol predicts reality).** Over (check, real-capture condition) pairs, the mean
  absolute error between the protocol's validated recall and the real-capture recall is larger for
  P1 than for P5; the paired cluster-bootstrap 95% interval of (error P1 minus error P5) lies above
  zero.
- **H5 (selection amplifies the blind spot).** Under P5 (calibrating on G0 and G1 together), the
  selection rule does not choose the added-ink sensor for `required_field`, while under P1 it does.
- **H6 (the audit works on what was not already known).** The generator-coverage audit, committed
  before any A3, X2 or X3 reading, names at least half of the (check, source) cells where observed
  recall falls below 0.90 on A3 or X2, EXCLUDING the already-known `required_field` ink failure.
  Reported as hits over observed failures and false predictions over predictions.
- **P-NAF (a reading band, not a test).** The share of NAF blank fields carrying added ink above the
  shipped threshold (0.345% of the field) is read as "rare" if its upper 95% bound is below 0.5%,
  "occasional" from 0.5% to 5%, "common" above 5%. The paper's wording of practical consequence is
  fixed by the band before the number exists.

### 4.1 Operational definitions (fixed now, they do not change the criteria above)

- **Verdicts.** Each hypothesis is "supported", "not supported" or "not tested" (its source is
  absent). A criterion is met on the point estimate; its interval is always reported next to it.
- **H1.** `field_ink_share` is the share of the emptied field's pixels dark at level 128 in the
  augmented image and not dark in the un-augmented render of the same page, after registration
  (T11). Recall is over (identity, instance, dpi, seed) positives of `required_field` with
  `field_ink_share >= 0.005`.
- **H2.** "Real captures with no added marks" are all X2 captures except mark steps 1 to 3. The
  pooled recall is positives detected over positives across the six content checks; the
  per-dossier false-alarm rate is the share of clean captured dossiers (one identity, one capture
  round) on which any of the six checks fires.
- **H3.** The mark's area share is measured against the step 0 capture of the same sheet at level
  128. "The best OCR sensor" is the one of the three shipped text sensors (`page`, `zone`, `union`,
  each at min_conf 0 and the threshold P1 chooses for it) with the highest recall on these
  captures; the choice among three is disclosed with its recall.
- **H4.** A real-capture condition is (capture device, dpi for the flatbed) for unmarked captures
  and (device, mark step) for mark sheets. Pairs with no positive are dropped for recall. The
  cluster is the physical sheet.
- **H5.** "The added-ink sensor" is `text_sensor=ink` at any ink level; "chooses" means it is the
  setting the shipped choice rule (highest recall at a false-positive rate at most 0.002, then the
  middle of the plateau) retains for `required_field`.
- **H6, primary scoring (as written).** A (check, source) cell, source in {A3, X2}, is OBSERVED
  failing when its pooled recall at the shipped thresholds is below 0.90. To exclude the known
  `required_field` ink failure, the `required_field` cells are computed only on readings with no
  added ink in the emptied field: A3 readings with `field_ink_share < 0.0005` (0.05% of the
  field, about a seventh of the shipped 0.345%), X2 captures other than mark steps 1 to 3. A cell is NAMED by the audit when a row of `coverage-audit.csv` has that check,
  `predicted_effect = miss`, `predicted_below_0.90_on` equal to that source or `both`, and is not
  a `required_field` row with `known = true`. Hits = observed failing cells that are named;
  supported when hits / observed failures >= 0.5. False predictions = named cells not observed
  failing, over named cells. A cell with no positive in its source (for example X2 resolution
  without the flatbed) is dropped from both counts. If no cell fails, H6 is "not tested".
- **H6, strict scoring (sensitivity, reported next to the primary).** The same, but only rows with
  `known = false` name a cell. It excludes the added-ink effects on `required_checkbox`,
  `signature` and `expiry` that the published targeted run already showed (`thresholds.json`,
  `recall_with_ink_on_the_damaged_field`). With the audit as committed, both scorings name the same
  eight cells.
- **Rows predicting a false alarm** are not scored by H6. They are reported descriptively: a row
  predicting `false_alarm` below 0.90 on a source is correct when that check's per-target
  false-alarm rate on clean pieces of that source exceeds 0.10.
- **P-NAF.** The share is over NAF fields with `isBlank = 3`, the pixel measure of T15 (added ink
  against the consensus blank at level 128), Wilson interval with the cluster bootstrap over
  images; the human-label measure (a `comment` polygon on at least 1% of the field) is reported
  next to it.

## 5. Protocols and baselines (RQ2)

A protocol is (the data thresholds and sensor settings are chosen on, the data the scores are
reported on). The choice rule is the shipped one unless a baseline says otherwise: highest recall
with at most 0.2% false positives per checked field, then the middle of the plateau
(`grid/analyze.py` `chosen_point`, `FP_BUDGET = 0.002`). Expiry stays frozen at zero and
resolution at the domain floor under every protocol (they are definitions, not curve choices).

| Id | Choose on | Report on |
|---|---|---|
| P1 | A1 seeds 11+23 | A1 seed 37 (the published protocol, replicated with identities) |
| P2 | A2 seeds 11+23 | A2 seed 37 (a seed that means something) |
| P3 | A1 minus the most severe level of one factor | that held-out level, one fold per factor (3 folds after the cap cut: angle 2, dpi 150, sigma 6), reported per fold and pooled |
| P4 | A1 seeds 11+23 | A3 seed 37 (cross-generator) |
| P5 | A1 and A3 seeds 11+23 pooled | A1 and A3 seed 37 pooled |
| P6 | leave-one-identity-out on A1 (6 folds) | the held-out identity |

Baselines for the choice rule, run under every protocol: **B1** Youden's J (maximum of recall minus
false-positive rate); **B2** the default threshold (midpoint between the class means of the score on
the calibration data); **B3** a combined sensor for `required_field` (flag empty only when the ink
sensor AND the best OCR sensor both say empty; and separately OR). Sensitivity of the shipped rule:
false-positive budgets 0.1% and 0.5%.

Targets every protocol is scored against: X2 (primary) and, for P1 to P3 and P6, A3 seed 37
(secondary). Metrics: per (check, condition) the absolute error |validated recall minus observed
recall| and |validated per-dossier false-alarm rate minus observed|; the sensor each protocol
crowns; whether a release gate at recall 0.90 on the protocol's own report set would have blocked
`required_field`.

Stated before a reviewer does: for the ink condition, P1 to P3 and P6 cannot see ink BY
CONSTRUCTION (resampling the same generator cannot create a condition it never makes). The
empirical content of RQ2 is the size of each protocol's error on real captures that no protocol
has seen, which include everything real paper and optics add beyond ink.

## 6. The census (RQ3)

- **Population**, computed by a script, never by memory: `gh repo list DylanMerigaud --limit 300
  --json name,visibility,isFork,createdAt` filtered to public, non-fork, `createdAt` on or after
  2026-01-01. Private repositories are out of scope because their data cannot be shared.
- **Inclusion rule**: the repo holds (a) a self-generated score (tests passing, a synthetic or
  planted benchmark, an LLM-judged or script-graded suite) AND (b) an independent check of the same
  system (a real-world input the author did not generate, a human judgment, an arithmetic or
  specification oracle, a third party's verdict), with the numbers of both present in files
  committed at a pinned commit. Everything else is listed as excluded with its reason.
- **Unit of analysis**: an episode, one pair (self-generated claim, independent finding). A tool may
  have several.
- **Evidence tier** per episode: T-A objective (constructed ground truth, arithmetic or
  specification oracle, a grader shown unable to match, a third party's merge); T-B human judgment
  (named or unnamed person); T-C a model's verdict. The census claims rest on T-A and T-B; T-C
  episodes are listed and never counted as "hand reads".
- **Codebook** (applied as is; "other" allowed with a free-text reason):
  - M1 coinciding blind spot: the test generator never produces a condition the winning component
    is structurally weak to (dossier-preflight ink; bankfile reversed credits);
  - M2 circular oracle: the same author or the same model wrote the fixtures or labels and the
    system under test;
  - M3 degenerate grader: the checker could not fail (trimwrit's dead regex graders; dsh-internals'
    existence-only validator);
  - M4 right for the wrong reason: an aggregate verdict is correct while the reason is wrong
    (airlock: an unknown brand always blocks);
  - M5 contaminated control: the comparison arm was not what it claimed (trimwrit's "without" arm);
  - M0 agreement: the independent check confirmed the score (nameproof's `doctor`).
  An episode may carry up to two codes, ranked.
- **Coders**: coder 1 is a fresh Claude Opus session given only the codebook and the evidence file;
  coder 2 is an outside reader with research experience if one has accepted by the time coding
  runs, otherwise the author. Cohen's kappa on the first code, with a bootstrap interval;
  disagreements resolved by discussion, recorded with both original codes.

## 7. Statistics

- Proportions: Wilson 95% score intervals, exact counts always printed next to them.
- Clustering: readings are nested (identity x cell x seed for generators; physical sheet x capture
  for X2; image for X3). Every interval on a difference or a pooled rate uses a cluster bootstrap
  over the top cluster (identity for A1 to A3, sheet for X2, image for X3), 10,000 resamples, numpy
  `default_rng(20260925)`, percentile intervals.
- Paired sensor comparisons on the same readings: exact McNemar, reported with the two discordant
  counts, exploratory only.
- H4: paired cluster bootstrap on the difference of mean absolute errors.
- Multiplicity: six preregistered hypotheses judged by their own criteria; everything else is
  labelled exploratory and carries intervals, no p-values.
- Census: counts per mechanism with their denominators; Cohen's kappa with a bootstrap interval
  over episodes.

## 8. What would falsify the thesis

- H1 and H3 both fail (the ink sensor keeps recall >= 0.50 under independent and real ink): the
  "blind spot" was an artifact of the probe; the paper then reports that.
- P-NAF lands in "rare": the failure is real but uncommon in the one real population measured; the
  paper then frames the lesson as reporting practice, not harm.
- H4 fails (seed holdout predicts real captures as well as pooled generators): insight 2 changes
  to "a second generator did not buy prediction accuracy here".
- H5 fails (ink still wins under pooled data): the "selection amplifies" claim is dropped.
- The census codes most included episodes M0 (agreement): the generality claim is dropped and the
  census is reported as such.

## 9. The generator-coverage audit (`coverage-audit.csv`)

Written from code reading only: `preflight/degradation.py`, `preflight/sensors.py`,
`preflight/checks.py`, `preflight/reading.py`, `preflight/deskew.py`, `grid/run.py`,
`preflight/fixtures.py`, the templates, and the Augraphy augmentations named in the plan
(Markup, Scribbles, Stains, BadPhotoCopy, DirtyRollers, DirtyDrum, Letterpress,
BindingsAndFasteners, NoisyLines, Folding, ShadowCast). No reading of any arm was consulted. One
geometric fact was measured on the blank renders alone (no degradation, no reading): how much
pre-printed line ink a shift of 2, 4 or 6 px brings into each watched zone. It is quoted in the
rows it supports (for example +2.56% at 2 px into the W-9 name field, against a 0.345% threshold).

One row per (physical process of real capture, check): 24 processes x 9 checks = 216 rows. The
23 processes of the plan plus one added, "ink loss (faded or broken print)", because Letterpress is
in the Augraphy list and G0 never removes ink. Columns: `process, check, covered_by_G0
(yes|no|partly), sensor, predicted_effect (none|miss|false_alarm), predicted_below_0.90_on
(A3|X2|both|none), known (true|false), reason`. For a `false_alarm` row, "below 0.90" refers to
one minus the per-target false-alarm rate on clean pieces. `known = true` marks the added-ink
mechanism already published: every added-ink row of `required_field` (the failure H6 excludes),
and the added-ink rows of `required_checkbox`, `signature` and `expiry` that the published targeted
run already showed below 0.90.

What the audit predicts, in one place (23 rows predict a value below 0.90: 19 misses, 7 of them
known, and 4 false alarms):

- Cells predicted to fail on recall, not already known (H6 scores these eight):
  A3 `required_checkbox` (cast shadows), A3 `signature` (shadow edges; also long lines, known),
  A3 `expiry` (ink loss; also streaks, known), A3 `forbidden_value` (ink loss);
  X2 `required_field` on unmarked captures (local misregistration from curl and residual
  perspective, and line thickening by the phone's enhancement, both bringing pre-printed line ink
  into a zone the sensor compares by counts), X2 `required_checkbox` (the box outline enters the
  6.6 px disc at a 4 to 5 px offset), X2 `signature` (the signature line enters the band as one
  long added component), X2 `cropped_page` (a covered bottom fifth leaves the frame full size, so
  coverage stays near 1.0).
- Predicted false alarms: A3 `resolution` (1% margin at 150 dpi), A3 `consistency` and A3
  `signature` (ink loss), X2 `signature` (a real hand signature broken into components under 342
  px inside a 36 px tall band).
- Predicted NOT to fail, stated so they can be wrong: highlights and the light pencil rub of step
  3 stay above grey 128 and are invisible to the ink sensor; the step 1 pencil dot is too small
  and light to cross 0.345%; rotation, translation, JPEG, dpi (for recall), bleed-through,
  binding holes and identity move no recall under 0.90.

Two of these predictions pull against H2, which is kept as written: the audit expects X2
`required_field`, `required_checkbox` and `signature` recall, and X2 signature false alarms, to
put H2 at risk on real captures even without marks.

## Amendments

None at the time of tagging.

## Deviations and amendments, 2026-09-25, after the X3 run

Written on 2026-09-25, after the tag `prereg-v1` (commit b3995e4, 15:31 +0200) and after the X3
pixel measure had been run and read. Everything in this section was decided after the tag. The
text above it is unchanged.

### D1. A 3 px dilation before the consensus vote (T15 step 3, section 3 X3)

- **What.** The plan specifies the consensus blank as the pixelwise median of the registered
  binarised images. The committed code (`naf/registration.py`, `CONSENSUS_DILATE_RADIUS = 3`)
  dilates each image's dark mask by 3 px before the majority vote.
- **Why.** Registration is translate and uniform scale only. A few pixels of residual
  misalignment kept fine printed ink (a dotted leader line) below the 50% majority on every image
  of group 132, although it is printed on all of them.
- **When.** While inspecting the first pixel run's most extreme field (group 132, image
  007540939_00045, field f46), before `results/naf.json` was first written, after the tag.
- **Measured effect** (fields at or above each threshold, out of 165; re-run by
  `naf/diagnostics/crop_audit.py`):

  | consensus | >= 0.345% | >= 1% | >= 4% |
  |---|---|---|---|
  | no dilation (the preregistered median) | 80 | 61 | 31 |
  | 3 px dilation (committed) | 66 | 44 | 14 |
  | 3 px, each image left out of its own vote | 73 | 48 | 17 |
  | 6 px dilation | 53 | 32 | 6 |

  The share at 0.345% moves from 0.485 to 0.400 with 3 px. Every variant stays above 5%.

### D2. Each quarter turn is searched separately (T15 step 3)

- **What.** The plan says to register with dossier-preflight's own `register`. The committed
  code calls `register(..., quarters=(q,))` once for q = 0 and once for q = 2 and keeps the higher
  final peak (`_register_best_of`), instead of a single `register(..., quarters=(0, 2))`.
- **Why.** `register` refines only the quarter that wins the coarse round. On group 132, image
  007540939_00111 (upright) against medoid 007540939_00212, `quarters=(0, 2)` returns turn 2 at
  peak 0.6042 while `quarters=(0,)` alone returns turn 0 at 0.6189. The coarse round scores the
  two 0.5970 and 0.5972 (`naf/diagnostics/quarter_trap.py`).
- **When.** Same inspection as D1, after the tag.
- **Measured effect.** The share at 0.345% moved from 0.491 to 0.485 (81 to 80 of 165, before
  D1).

### A1. What P-NAF is reported as

- **The preregistered rule, applied as written.** P-NAF is read on the pixel measure it names:
  66 of 165 fields, 0.400, Wilson 95% [0.328, 0.476], image-cluster bootstrap 95% [0.299,
  0.538]. The upper bound is above 5%, so the rule gives **"common"**. That result stays in
  `results/naf.json` (`p_naf.band`) and is not re-chosen.
- **Why that measurement is invalid.** A crop audit, done after the number existed
  (`results/naf-reading.md`), read the pixel-positive fields by eye. 10 of the 14 inspected
  fields with no comment label hold only template residue: the field's own printed dotted or
  rule line, or paper noise, which the consensus holds a few pixels off or not at all. 4 of the
  14 hold real added ink mixed with residue. 7 of the 17 medoid fields come out positive against
  a consensus that includes the medoid itself. As the table in D1 shows, the count depends on a
  free parameter. The pixel measure reads registration residue, not a prevalence of foreign ink.
- **What the paper reports.** P-NAF is reported as **"not interpretable"**. The human-label
  measure (a NAF `comment` polygon on at least 1% of an `isBlank = 3` field), planned as the
  measure reported next to it, is reported as an **exploratory lower bound**, labelled as such
  and not as the P-NAF reading: 159 of 5,550 fields, 2.86%, Wilson 95% [2.46%, 3.34%],
  image-cluster bootstrap 95% [1.89%, 3.98%] over 556 images. Its band range is "occasional"
  under either interval. It is a lower bound because NAF's annotators did not label every added
  mark as a comment: the audit found ditto marks and stray handwriting from a neighbouring row in
  fields with no comment label.
- **Section 8.** P-NAF is neither "rare" nor a valid "common". The falsification line on "rare"
  is therefore not tested. The paper states this.
- **Machine-readable.** `results/naf.json` carries a `validity` object with
  `pixel_measure_valid: false`, written by `naf/measure.py combine`.

## A2, 2026-09-26, before any A3b reading: a corrected Augraphy arm with one seed per page

Written on 2026-09-26, after the A3 arm had been read and scored and after round 1 of the
adversarial review, and BEFORE any image of the new arm A3b exists. It adds an arm; it changes
nothing above it and no A3 number.

- **The flaw in A3, disclosed.** `grid/augraphy_render.py` seeded `random`, `numpy.random` and
  OpenCV with the job seed (11, 23 or 37) before every page. Augraphy draws both the structure of
  its default pipeline (which augmentations run) and their parameters from that state, so every
  page sharing a (seed, dpi) cell received nearly the same draw: at seed 37, 3 to 5 distinct
  augmentation sets per dpi over 294 pages each, and ShadowCast, Letterpress, Stains,
  LightingGradient, PageBorder and Faxify fired on 0 of 2,646 pages. A3 is therefore about nine
  pipeline realizations, not 2,646 independent degradations, and its intervals (Wilson, identity
  bootstrap) understate its uncertainty. A3 stays reported as preregistered, with this flaw
  stated next to every A3 number.
- **A3b, the corrected arm.** The same design as A3 (section 3.3): 6 identities x 49 pages x dpi
  {150, 200, 300} x replicate seed {11, 23, 37} = **2,646** images, one reading each, the same
  unmodified `default_augraphy_pipeline()` of Augraphy 8.2.6, the same render and page-geometry
  overrides, the same greyscale conversion, read by the same `grid/read_images.py`. The ONE
  change: before each page, `random`, `numpy.random` and OpenCV are seeded with a per-page seed,
  the first 4 bytes (big endian) of SHA-256 of the string `identity|variant|piece|dpi|seed`
  (`seed` the replicate seed), so the pipeline structure and its draws vary independently across
  pages and each augmentation class appears near its pipeline probability. The replicate seed
  keeps its role: seeds 11 and 23 are calibration, seed 37 is the report seed. The per-page seed
  is written to the manifest (`page_seed`). The default of `grid/augraphy_render.py` keeps the old
  behaviour, so A3 stays reproducible byte for byte.
- **field_ink_share on A3b** uses the axis-locked registration that the committed A3 manifest
  already uses (axis 0, quarter turn 0), from the start; no recomputation pass.
- **What runs on A3b.** H1 (the same criterion: recall below 0.50 on pages with
  `field_ink_share >= 0.005`, the same 0.5% rule, the same shipped setting), H5 (P5 pools A1 and
  A3b seeds 11 and 23, reports on A1 and A3b seed 37), the A3 part of H6 (source A3b in place of
  A3, same primary and strict scorings), P4 (reports on A3b seed 37), P5, and the secondary target
  of Table 1 (A3b seed 37 for P1 to P3 and P6). A3b is the corrected arm and the paper's primary
  generator result; the A3 figures are reported next to it as the preregistered arm.
- **Declared sensitivities, before any A3b reading** (exploratory, intervals, no verdict): a
  cluster bootstrap over the (seed, dpi) cell, over the augmentation set, and over the field
  instance (template x role) next to the preregistered identity bootstrap; H1 bounds with the
  pages whose share cannot be measured counted as all detected and as all missed; H1 per target;
  H1 by dpi, by seed and by augmentation class (mark: Scribbles or Markup; bleed-through:
  BleedThrough; binding: BookBinding or BindingsAndFasteners; photocopy family: BadPhotoCopy,
  DirtyDrum, DirtyRollers, LowInkRandomLines, LowInkPeriodicLines); the wrong-quarter-turn rate,
  `rotated_page` and `cropped_page` recall and H6 with and without the augmentations a loose
  single sheet cannot receive (BookBinding, BindingsAndFasteners, Folding, Squish); an eye audit
  of a seeded random sample of at least 30 inked and 20 not-inked A3b fields.
- **The measured state.** A3b is rendered and read at the dossier-preflight tag `study-a3b`:
  v0.2.0 plus the per-page seed option of `grid/augraphy_render.py` and its test, with no change
  to any reading, sensor, check or threshold. Every result file of this study is regenerated at
  that tag, so the recorded commit is the one named here.
