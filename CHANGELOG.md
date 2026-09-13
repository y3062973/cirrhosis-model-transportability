# Changelog

## 1.1.0

Second release of the analysis code and reproducibility materials, accompanying
manuscript v3.2.

### Version strings -- read this before comparing versions

Two version numbers appear in this repository and they are **supposed to differ**:

| what | version | why |
|---|---|---|
| the frozen primary-analysis configuration inside `config/final_analysis_config.py` | `FINAL_v1.0.0` | the primary model and its configuration were **not changed**. Editing that string would change the frozen configuration hash and invalidate every stamped output. |
| this publication / code release | `1.1.0` | v1.1.0 **removes an unreliable secondary hierarchical analysis**. It does not change the primary analysis. |

So: the primary model and its frozen configuration are unchanged from v1.0.0; the
publication is v1.1.0; and v1.1.0's only analytical change is a **removal**. A reader
who sees `FINAL_v1.0.0` inside `final_analysis_config.py` is seeing the correct,
deliberately preserved value, not a stale string. See `REPRODUCIBILITY.md`.

### Changed -- the hierarchical calibration model was removed

A mixed-effects logistic calibration model with a random intercept per hospital had
been used to estimate a common calibration slope and a between-hospital variance
component. An audit found that the custom Laplace criterion omitted the Gaussian
prior normalisation `-(J/2) log(2 pi tau^2)`. That term is NOT constant in tau -- it
diverges as tau approaches zero -- so the variance component was not selected by the
approximation it was reported as. An independent implementation (`lme4::glmer`,
R 4.6.0, lme4 2.0.6) converged cleanly and estimated `tau = 0.109`, against the
custom fit's `1e-06` with all 85 random intercepts exactly zero.

Because the independent fit materially disagreed about the variance component, the
model was removed from the manuscript rather than repaired further.

**No hierarchical numerical result is part of v1.1.0.** No value of alpha, beta or
tau from that model appears in the manuscript, the released tables, the figures or
any document in this repository.

**What is reported instead, and what may not be claimed.** The hospital-level
calibration evidence is reported **descriptively**, as observed-to-expected ratios
per hospital. Hospital-specific calibration estimates varied descriptively. No formal
hierarchical calibration-heterogeneity conclusion is reported. Because the model was
removed, do **not** claim that all hospitals shared the same calibration shift, and do
**not** claim that significant calibration heterogeneity was proven -- neither
statement is established by a retained analysis.

**The executable pipeline no longer contains the model.** The retained analyses now
live in `src/validation/hospital_analysis_and_recalibration.py`, which contains
per-hospital descriptive performance, the random-effects AUROC meta-analysis, valid
hospital-level descriptive summaries and the leave-one-hospital-out recalibration,
and performs no mixed-effects fitting. The rejected implementation is preserved for
audit only under `archive/nonproduction/`, behind a refusal guard, and is not a reproduction
step.

**Removed outputs.** Table 4 no longer carries the `hierarchical_calibration` or
`random_intercepts` sheets; its sheets are `all_hospitals`, `primary_N20`,
`sensitivity_N30` and `meta_analysis_AUROC`. Figure 5 panel B is now the
observed-to-expected ratio per hospital rather than a caterpillar plot of shrunken
random intercepts.

**Audit record (in this repository, no restricted data).** The reasoning, the
mathematics and the comparison are shipped so a reader can check the removal rather
than take it on trust:

  * `docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md` -- the derivation and the defect
  * `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` -- the three-way
    comparison and the decision rule that removed the model
  * `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` -- how the slope was
    estimated and what went wrong
  * `docs/audit/PUBLICATION_LOCK_v1.1.0.md` -- the release-level record of the change
  * `archive/nonproduction/hierarchical_calibration_rejected_historical.py` -- the rejected
    code itself, marked **HISTORICAL IMPLEMENTATION -- NOT USED IN THE FINAL
    MANUSCRIPT -- DO NOT USE FOR INFERENCE**

### Unchanged, and verified so

Every primary result is identical to release v1.0.0: the cohorts, `FINAL_MODEL_V2` and
all 15 coefficients, the external validation metrics, the hospital-level discrimination
meta-analysis, the leave-one-hospital-out recalibration, the clinical-score comparison
and every prespecified sensitivity analysis. The frozen configuration hash is
unchanged.

### Fixed

* **`import db` placement.** The credential sanitiser inserted the shared database import
  before `from __future__ import annotations`, producing a `SyntaxError` in every
  sanitised file; future imports must precede all other imports. The insertion point now
  skips the docstring and any future imports, and `python -m compileall` is a required
  gate in the release health check.
* **UTF-8 BOM.** Sources were read as plain UTF-8, decoding the BOM into a literal
  `U+FEFF` that was re-written into the output and made the file unparseable. Sources are
  now read with `utf-8-sig`, and the release ships clean UTF-8 without a BOM.
* **The historical patcher is no longer shipped.** `apply_hierarchical_beta_fix.py` edited
  a file that does not exist in this repository, so executing it would have failed on a
  missing target. The change history it would have applied is recorded here and in
  `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md`, and the implementation it
  edited is archived (and not run) at
  `archive/nonproduction/hierarchical_calibration_rejected_historical.py`.
* **Database helper shadowed the `db` module in nine files.** The shared connection helper
  was written as `def conn(db): c = db.connect(db)`. Inside that function `db` is the
  **parameter**, so `db.connect` resolved against the caller's argument string rather than
  the `src/db.py` module, and the first database step would have failed. Affected:
  `src/phenotype/build_cohorts.py`, `src/phenotype/phenotype_audit.py`,
  `src/phenotype/cohort_composition.py`, `src/preprocessing/build_dataset_and_model.py`,
  `src/clinical_scores/clinical_scores.py`, `src/clinical_scores/meld_component_audit.py`,
  `src/clinical_scores/paired_score_comparison.py`,
  `src/validation/validation_and_sensitivity.py` and
  `tests/metric_validation/independent_metrics_and_verification.py`. The parameter is
  renamed to `dbname` so the module reference resolves. This is a latent runtime defect
  corrected in the shipped source; **no cohort, predictor, model, configuration or
  reported result is touched**, and the frozen configuration hash is unchanged.
* **Repository file references.** Every file path named in `README.md`, `docs/PIPELINE.md`
  and the other shipped documents is now checked automatically against the working tree
  by `verify_public_release.py`; the release ships with 0 broken references. Several
  stale references (a document that was never in the archive, and a script path that did
  not exist in this repository) were removed or corrected.
* **Documentation contradicted the code about what runs in a clean clone.** The README and
  the pipeline document previously implied that the two test suites were self-contained.
  They are not: both read the restricted analysis dataset, and the independent metric
  verification also opens read-only connections to the three databases. The access labels
  now say so, and only `verify_public_release.py` is labelled publicly runnable.
* **Internal release-audit scripts are labelled, not advertised.** `final_release_check.py`,
  `release_verification.py` and `publication_lock.py` depend on restricted artefacts,
  internal checksum files and a historical Git tag. They are marked as internal
  verification scripts and removed from the documented reproduction sequence.
* **Stale references to the removed model inside retained scripts.** Three shipped scripts
  still named or read the withdrawn hierarchical model, which would have been wrong even
  though none of it was a reported result:
  - `final_release_check.py` previously **required** the `hierarchical_calibration` and
    `random_intercepts` sheets to be present in Table 4. The checks are now inverted: the
    gate fails if either sheet ever reappears.
  - `publication_lock.py` still read the `hierarchical_calibration` sheet and wrote an
    alpha/beta/tau sentence into the lock document, which would now raise on a missing
    sheet. It reads the retained `primary_N20` sheet instead and states that no
    hierarchical model is reported.
  - `tables_and_figures.py`'s module docstring still described Figure 5 as "hospital
    observed vs predicted + hierarchical calibration". Figure 5 panel B has been the
    per-hospital observed-to-expected ratio since the removal.
* **Stale file path in the documented pipeline.** `docs/PIPELINE.md` named a script under
  `src/validation/` that does not exist in this repository. The independent metric
  verification is the script under `tests/metric_validation/`, and the pipeline table now
  names it.

### Version strings

MIMIC-IV is stated as **v3.1** throughout, which the authors have confirmed. The earlier
conservative "v3.x, minor version unconfirmed" wording has been removed. That version was
an open question only because v3.0 and v3.1 publish identical row counts for patients,
admissions and ICU stays and the schema stores no version string; the authors resolved it
directly.

### Scope and audience of the shipped scripts

`README.md` labels every shipped script as one of: publicly runnable without database
data; requiring authorised MIMIC-IV / eICU-CRD / nwICU access; or an internal
release-audit script that is not part of normal reproduction. Not every shipped script
runs in a clean clone, and the labelling says which.

## 1.0.0

Initial public release of the analysis code and reproducibility materials accompanying
manuscript v3.1.

### Contents

- the frozen analysis configuration
- the cohort construction and extraction pipeline
- predictor extraction, aggregation, imputation and model fitting
- clinical score construction and the paired score comparison
- external validation, sensitivity analyses and the independent metric verification
- hospital-level and meta-analytic analyses, and leave-one-hospital-out recalibration
- table and figure generation
- release verification

### Known issues at that release

**Hierarchical calibration slope.** The published run returned the common slope at the
optimiser's **starting value of 1.0** after a single iteration, because the random
intercepts all started at zero and the optimiser satisfied its convergence tests
immediately. Its reported confidence interval was degenerate at (1, 1) for the same
reason. The fit was subsequently repaired to a multi-start optimisation, and then removed
entirely -- see the 1.1.0 section above.

### Not included, by design

No source or derived data, no notebooks, no logs, no tables or figures, and no manuscript
files. The itemised exclusions and the reason for each are recorded in
`docs/audit/EXCLUDED_FILES_REVIEW.md`.
