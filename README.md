# perfect-recall-study

Replication package for a study of dossier-preflight (a document-checking tool): how far a
perfect recall measured by held-out validation on a synthetic generator diverges from scores on
an independent generator and on real document captures, plus a census of other public tools whose
self-generated score was checked against an independent source.

## Status

The generator arms (A0 to A4) and the archival forms arm (X3) have run, and their results are in `results/`. The real-capture arm (X2) was not run: every result that depends on it reads "not tested yet", and a manuscript built on this study states that limit. The second census coder is still pending.

The raw readings of A0 to A4 and the X3 field measures are on Zenodo, with their checksums: https://doi.org/10.5281/zenodo.23312819 . Images are not deposited; every image is regenerated from the seeds and the pinned commits.

## What is on GitHub, and what is on Zenodo

This repository (MIT for code, CC BY 4.0 for data, see License below) carries the code, the
preregistration and its coverage audit, the census evidence and coding sheets, and the results
this study's scripts computed (`results/`, small tables, figures and the numbers registry): every
file `git ls-files` lists here. It does not carry the raw readings, the capture images or the
other large inputs those scripts read: `experiments/README.md` and `env/README.md` say so at
each path that is still empty for exactly that reason. The raw readings are in the Zenodo record
above, whose README.md says where each file goes for `analysis/` to read it.

## dossier-preflight's two tags

- `v0.1.0` is applied retroactively: the annotated tag was created on 2026-09-25, pointing at
  commit `42732f0`, dated 2026-08-22, the state dossier-preflight was already in when it was
  described in the blog post
  [`recall-1000-blind-to-dust`](https://dylan.merigaud.com/blog/recall-1000-blind-to-dust)
  (published 2026-08-27) and in the query sent to IEEE Software's editor in chief on
  2026-09-25. The blog post is independent evidence that this was the published state before
  this study started measuring it: it is dated and hosted outside this repository, and it was
  written before the tag existed.
- `v0.2.0` is the state this study measures: the thresholds and checks as shipped after the
  all-shapes failure metric and the independent-generator recall (T02 to T13 of the study
  design). `v0.2.1` carries hygiene fixes found in round 1 review, with every threshold value
  unchanged from `v0.1.0` (dossier-preflight's `JOURNAL.md` and `tests/test_failure_metric.py`
  hold that proof).

## What each folder will reproduce

- `prereg/` : the preregistration written before any new reading is taken (research questions,
  hypotheses, validation protocols, the census inclusion rule and codebook, the statistics plan),
  tagged in git so its commit time can be checked against every later reading.
- `experiments/` : the code that produces each experimental arm: additional fictional identities
  and defect instances for the base generator, a jittered variant of the same generator, an
  independent third-party generator run on the rendered pages, a targeted foreign-ink run with its
  raw rows kept, and the scripts that build, print and ingest a real-paper capture kit. Raw
  readings from these scripts are large and are not committed here; they ship through the Zenodo
  record.
- `census/` : the script that lists the population of candidate public repositories, the sheet of
  evidence quotes pinned to exact commits, the coding sheets from each coder and the agreement
  script.
- `naf/` : the pipeline that reads a public archival forms dataset and measures how often ink not
  produced by any generator in this study sits inside a field a human labeller marked blank.
- `analysis/` : the statistics used throughout (interval estimation, a cluster bootstrap, paired
  tests, inter-rater agreement), the script that compares validation protocols, the script that
  scores each preregistered hypothesis, and the script that writes the single numbers registry
  every manuscript figure is read from.
- `tools/` : checks a manuscript draft must pass before submission: substituting numbers from the
  registry, catching a stray hand-typed digit, counting words against a venue's limits, and
  verifying every citation resolves and is actually cited. See below.
- `results/` : tables, figures and the numbers registry the analysis scripts write
  (`analysis/README.md` has the commands; run them with dossier-preflight's virtual environment).
- `env/` : the pinned package and tool versions the measurements run under, so a reader can rebuild
  the same environment.

## The manuscript tools

Four small command-line tools, Python 3 standard library only, each with tests under
`tools/tests/`.

- `tools/render.py SRC NUMBERS OUT` substitutes every `{{key}}` placeholder in a manuscript source
  file with the value from a numbers registry (a JSON file), so no number in the manuscript is
  hand-typed. Exits with an error on an unknown key or a placeholder left unresolved.
- `tools/check_numbers.py SRC` fails if a digit appears in the manuscript's prose outside a
  `{{key}}` placeholder, outside inline code, outside the References and About the author
  sections, and outside a short allowlist of expected literal digits (years, form names, section
  and hypothesis labels, version numbers, commit hashes). It prints every offending line.
- `tools/wordcount.py OUT` counts the manuscript against a venue's word, abstract and reference
  limits, charging a fixed word cost per table and per figure, and prints each count.
- `tools/check_refs.py OUT REFS` checks that every citation marker has a matching reference entry
  and vice versa, that references are numbered in the order they are first cited, and that every
  reference entry carries an identifier (a DOI, an arXiv id, a URL or an ISBN), a supporting quote
  and who read it. A DOI, arXiv id or URL is checked against its own registry.

Usage is exact commands, not paraphrase; see each tool's `--help` and its test file for the
expected inputs and failure modes.

## License

Code is MIT (see `LICENSE`). Data produced by this study is CC BY 4.0, except where a source
carries its own terms; see `LICENSE-DATA.md`.

## Status, 2026-10-12

The study stopped before its real-capture arm (X2) on 2026-09-30. On 2026-10-12 the raw readings of the arms that ran were deposited on Zenodo (https://doi.org/10.5281/zenodo.23312819), and an article built on these results is being prepared, with the absence of real captures stated as a limit.
