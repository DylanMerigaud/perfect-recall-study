# perfect-recall-study

Replication package for a study of dossier-preflight (a document-checking tool): how far a
perfect recall measured by held-out validation on a synthetic generator diverges from scores on
an independent generator and on real document captures, plus a census of other public tools whose
self-generated score was checked against an independent source.

## Status

This study is in progress. This repository holds the design, the preregistration, the code that
will produce every reading and every number, and the checks a manuscript must pass before
submission. The analysis of the generator arms and of the archival forms has run (`results/`);
the real-capture arm (X2) and the second census coder are still to come, and every result that
depends on them reads "not tested yet" or "pending coder 2". Results are provisional until the
manuscript and the Zenodo record are public.

Raw readings, capture images and other large data will be deposited in a Zenodo record with a DOI
once collection is complete. That record is not published yet. Nothing here should be read as
final until the Zenodo record and the accompanying manuscript are both public.

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
