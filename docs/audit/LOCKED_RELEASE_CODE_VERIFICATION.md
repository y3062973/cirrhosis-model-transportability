# LOCKED RELEASE CODE VERIFICATION

**Compared against:** `PROJECT1_FINAL_MANUSCRIPT_v1.0.0` (the frozen analytical release)
**Publication / code release:** `PROJECT1_FINAL_MANUSCRIPT_v1.1.0`
**Frozen primary-analysis configuration:** `FINAL_v1.0.0` -- **unchanged**. The primary
model was not changed, so its configuration version string was deliberately **not**
edited; editing it would change the frozen configuration hash and invalidate every
output stamped with it. See the "Version strings" section of `CHANGELOG.md`.

Each published script is compared to its content at the frozen analytical release.
Differences are reported, never silently reconciled.

## Verdict, in one paragraph

**The original hierarchical calibration implementation contained a defect. It was
independently verified. The model was judged insufficiently reliable. The hierarchical
analysis was REMOVED from the manuscript. No hierarchical numerical result is part of
v1.1.0. Every primary result is unchanged.**

## The hierarchical calibration analysis -- final state

This is the sequence of what happened, in order, and it is the thing most easily
misreported. Wording that implies the multi-start custom fit is the final reported model
is wrong.

| # | stage | outcome |
|---|---|---|
| 1 | **Original implementation defect identified** | The published run returned the common calibration slope at the optimiser's **starting value of 1.0** after a single iteration, with every random intercept also at zero, so the optimiser satisfied its convergence tests immediately. The reported slope was an accepted initialisation, not a located maximum, and its bootstrap interval was degenerate at (1, 1). |
| 2 | **Repair attempted under author authorisation** | The fit was changed to a multi-start optimisation so the slope would be located rather than assumed. This is the state described in `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md`. |
| 3 | **Independent verification performed** | A mathematical audit found that the custom Laplace criterion omitted the Gaussian prior normalisation `-(J/2) log(2 pi tau^2)`. That term is **not constant in tau** -- it diverges as `tau` approaches zero -- so the variance component was not selected by the approximation it was reported as. An independent, mature implementation (`lme4::glmer`, R 4.6.0, lme4 2.0.6) converged cleanly with no singular fit and estimated `tau = 0.1088`, against the custom fit's `1e-06` with all 85 random intercepts exactly zero. |
| 4 | **Model judged insufficiently reliable** | The two implementations disagreed materially about the quantity of interest. The decision rule required only one sufficient condition; three were met (a confirmed mathematical error in the custom likelihood, material disagreement with the independent fit, and a variance component on the boundary of the parameter space). |
| 5 | **Hierarchical analysis removed from the manuscript** | The model was withdrawn rather than repaired further. The manuscript reports the hospital-level evidence descriptively, as observed-to-expected ratios per hospital. |
| 6 | **No hierarchical numerical result is part of v1.1.0** | No value of alpha, beta or tau from any version of that model appears in the manuscript, the released tables, the figures or any document in this repository. Table 4 no longer carries a `hierarchical_calibration` or `random_intercepts` sheet. |
| 7 | **Primary results unchanged** | Cohorts, `FINAL_MODEL_V2` and all 15 coefficients, the external validation metrics, the hospital-level discrimination meta-analysis, the leave-one-hospital-out recalibration, the clinical-score comparison and every prespecified sensitivity analysis are identical to v1.0.0. The frozen configuration hash is unchanged. |

**What may be claimed, and what may not.** Hospital-specific calibration estimates
varied **descriptively**. No formal hierarchical calibration-heterogeneity conclusion is
reported. Because the model was removed, do **not** claim that all hospitals shared the
same calibration shift, and do **not** claim that significant calibration heterogeneity
was proven: neither statement is established by a retained analysis.

The audit trail is shipped in `docs/audit/`:
`HIERARCHICAL_LAPLACE_MATH_AUDIT.md` (the mathematics),
`HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` (the comparison and the decision rule),
`HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` (the first defect, historical), and
`PUBLICATION_LOCK_v1.1.0.md` (the release-level record).

**One item is open, and it is a manuscript item, not a code item.** Five sentences in
the final manuscripts still assert or presuppose the removed model's uniform-shift
claim. Those manuscripts are not part of this repository and were not modified here.
The exact sentences, line numbers and minimal replacements are in
`AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`.

## File-by-file comparison

| published file | internal origin | relation to the frozen release |
|---|---|---|
| `config/final_analysis_config.py` | `final_analysis_config.py` | **identical** (including `VERSION = "FINAL_v1.0.0"`, deliberately preserved) |
| `src/phenotype/phenotype_audit.py` | `phase_0a_phenotype.py` | **identical** |
| `src/phenotype/build_cohorts.py` | `phase_2_cohorts.py` | **identical** |
| `src/phenotype/cohort_composition.py` | `phase_2b_composition.py` | **identical** |
| `src/clinical_scores/meld_component_audit.py` | `phase_0b_meld_audit.py` | **identical** |
| `src/preprocessing/build_dataset_and_model.py` | `phase_3_4_dataset_model.py` | **identical** |
| `src/clinical_scores/clinical_scores.py` | `phase_5_6_7_scores.py` | **identical** |
| `src/validation/validation_and_sensitivity.py` | `phase_8_9_12_13.py` | **identical** |
| `tests/fault_injection/fault_injection_suite.py` | `phase_13_fault_injection.py` | **identical** |
| `tests/metric_validation/independent_metrics_and_verification.py` | `phase_14_17_golden_independent.py` | **identical** |
| `src/validation/primary_validation.py` | `publock_03_04_05.py` | **identical** |
| `src/clinical_scores/paired_score_comparison.py` | `publock_08b_selection_paired.py` | **identical** |
| `src/validation/hospital_analysis_and_recalibration.py` | `publock_06_07_hospital.py` | **REPLACES it: the removed 6C section is gone; only retained analyses remain** |
| `src/reporting/tables_and_figures.py` | `publock_08_12_13_tables_figures.py` | differs -- reporting only |
| `src/provenance.py` | `provenance.py` | differs -- manuscript tooling only |
| `src/reporting/final_release_check.py` | `final_release_check.py` | differs -- verification gate only |
| `src/reporting/release_verification.py` | `verify_release.py` | **identical** (internal audit script; see below) |
| `src/validation/publication_lock.py` | `publock_03_publication_lock.py` | **identical** (internal audit script; see below) |
| `src/manuscript_qa/number_audit.py` | `manuscript_number_audit.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/semantic_unit_audit.py` | `semantic_unit_audit.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/claim_compliance.py` | `manuscript_claim_compliance.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/language_pass.py` | `language_pass.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/reference_audit.py` | `reference_final_audit.py` | added after the frozen release; not analytical |

## Assessment of the differences

### `src/validation/hospital_analysis_and_recalibration.py` (replaces `publock_06_07_hospital.py`)

**Analytical difference: a removal.** The internal script carried a third section, 6C
(`SECTION 6C -- HIERARCHICAL CALIBRATION`), implementing the custom mixed-effects
calibration fit. It is gone. The published script contains sections 6A (per-hospital
descriptive performance), 6B (random-effects meta-analysis of per-hospital AUROC) and 7
(leave-one-hospital-out recalibration), and it performs **no mixed-effects fitting at
all**: the only regressions in it are unpenalised logistic fits for per-hospital
calibration slopes and for the recalibration updates.

What was **not** changed: the data selection, the hospital eligibility thresholds, the
AUROC estimator and its Hanley standard error, the DerSimonian-Laird meta-analysis, the
leave-one-hospital-out fold construction, the recalibration model forms, the bootstrap
seeds and replicate counts, and the table and figure sheet names other than the removed
ones. Sections 6A and 6B were computed **before** section 6C in the original script and
were entirely independent of it, so their values cannot have been affected by its
removal.

### `src/reporting/tables_and_figures.py`

**Reporting difference only.** The `hierarchical_calibration` and `random_intercepts`
sheets are no longer written into Table 4, and Figure 5 panel B no longer shows the
caterpillar plot of shrunken random intercepts; it shows the observed-to-expected ratio
per hospital instead, which is a direct ratio of observed to expected deaths within each
centre and involves no mixed-effects fitting. No other table or figure changes.

### `src/provenance.py`

**Manuscript-tooling addition only.** Two module-level helpers (`CITATION_RE` and
`citations()`) were added so the manuscript assembler and the reference auditor share
one citation pattern. They are not called by any analytical path. The metric primitives
in this module -- the functions that compute the reported performance metrics -- are
unchanged.

This is stated explicitly because `provenance.py` computes the numbers. A reader is
entitled to know that the change here cannot affect a result.

### `src/reporting/final_release_check.py`

**Verification gate only, and now strictly stronger.** The script previously *required*
the `hierarchical_calibration` and `random_intercepts` sheets to be present in Table 4
and asserted that they carried `alpha`, `beta` and `tau`. Those checks have been
**replaced** by an assertion that the sheets are **absent**, so the check now fails if
the removed model's output ever reappears. It computes no result.

## Latent defect corrected in v1.1.0 -- the `conn` helper shadowed the `db` module

In nine published files the shared database-connection helper read:

```python
def conn(db):
    c = db.connect(db)  # credentials from the environment
```

Inside that function `db` is the **parameter**, so `db.connect` resolved against the
caller's argument (for example the string `"eicu"`) rather than against the `src/db.py`
module. Any call to `conn(...)` would therefore have raised, and the database steps could
not have run as published. The parameter is renamed to `dbname` so the module reference
resolves.

Affected files: `src/phenotype/build_cohorts.py`, `src/phenotype/phenotype_audit.py`,
`src/phenotype/cohort_composition.py`, `src/preprocessing/build_dataset_and_model.py`,
`src/clinical_scores/clinical_scores.py`, `src/clinical_scores/meld_component_audit.py`,
`src/clinical_scores/paired_score_comparison.py`,
`src/validation/validation_and_sensitivity.py`,
`tests/metric_validation/independent_metrics_and_verification.py`.

**Scope of the change.** It is a name-resolution repair inside a connection helper. It
touches no query, no cohort definition, no eligibility rule, no predictor, no aggregation,
no imputation rule, no model, no configuration object and no reported number. The frozen
configuration and its hash are unchanged. It is listed here rather than in the analytical
differences because it cannot affect a result: it only makes the documented pipeline
executable.

## Internal release-audit scripts -- not part of normal reproduction

Three shipped scripts are provenance and release-verification tooling written against
the internal working tree. They are **not** reproduction steps, they are **not**
runnable in a clean clone of this repository, and they depend on restricted artefacts
and historical Git tags that are not shipped:

| script | why it cannot run here |
|---|---|
| `src/validation/publication_lock.py` | reads `data/*.csv`, `tables/*.xlsx` and `PUBLICATION_RELEASE_MANIFEST.json`; it also opens a read-only eICU database connection to recover the patient count, which requires authorised access |
| `src/reporting/final_release_check.py` | reads the restricted analysis dataset and predictions, the `PUBLICATION_ARTIFACT_CHECKSUMS.txt` file, and the historical analytical tag |
| `src/reporting/release_verification.py` | reads `PUBLICATION_ARTIFACT_CHECKSUMS.txt`, an internal artefact-checksum file that is not part of this repository |

They are kept **in place** rather than moved, so that their provenance is obvious and so
that a reader of the internal working tree finds them where they were. Their module
docstrings and `README.md` both label them for what they are. They are retained for
transparency about how the release was checked, not as instructions.

**For a public reader there is a supported alternative.** `verify_public_release.py`
at the repository root verifies the things that *can* be verified without any restricted
input: that the shipped file checksums match, that every required file is present, that
every Python file compiles, that no restricted data file is present, and that every
repository file path referenced by the documentation resolves. It requires no database
access and no patient-level data. See `README.md`.

## Conclusion

- identical to the frozen release: **12** published files
- differ, with the difference documented above: **4** published files
- replaces a frozen-release file with its retained-analyses-only subset: **1** file
- added after the frozen release (manuscript QA, not analytical): **5** files

The published code corresponds to the locked primary analysis. The single analytical
difference is the declared **removal** of the hierarchical calibration model, recorded
in `CHANGELOG.md`, in the retaining script's own docstring, in `docs/audit/`, and here.
No primary result is affected.
