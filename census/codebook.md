# Codebook

Examples naming repositories were removed from the preregistered codebook for blind coding; the
definitions are otherwise verbatim.

- **Evidence tier** per episode: T-A objective (constructed ground truth, arithmetic or
  specification oracle, a grader shown unable to match, a third party's merge); T-B human judgment
  (named or unnamed person); T-C a model's verdict. The census claims rest on T-A and T-B; T-C
  episodes are listed and never counted as "hand reads".
- **Codebook** (applied as is; "other" allowed with a free-text reason):
  - M1 coinciding blind spot: the test generator never produces a condition the winning component
    is structurally weak to;
  - M2 circular oracle: the same author or the same model wrote the fixtures or labels and the
    system under test;
  - M3 degenerate grader: the checker could not fail;
  - M4 right for the wrong reason: an aggregate verdict is correct while the reason is wrong;
  - M5 contaminated control: the comparison arm was not what it claimed;
  - M0 agreement: the independent check confirmed the score.
  An episode may carry up to two codes, ranked.
