# CODE INVENTORY -- provenance of the published files

**Manuscript:** Transportability of a cirrhosis mortality model across health systems:
preserved discrimination but shifted calibration-in-the-large

**Publication / code release:** `PROJECT1_FINAL_MANUSCRIPT_v1.1.0`
**Frozen primary-analysis configuration:** `FINAL_v1.0.0` (unchanged; see `CHANGELOG.md`)
**Superseded analytical release:** `PROJECT1_FINAL_MANUSCRIPT_v1.0.0` (preserved, unmoved)

## What this document is, and why it is short

The internal working tree carried 91 Python files under internal names (`phase_*`,
`publock_*`, `manuscript_*`). This document records the mapping from each **published**
file back to its internal origin, so a reader can trace a file in this repository to
its provenance. It is a provenance record, not a run order -- for the run order see
`docs/PIPELINE.md`, which is authoritative.

The internal working tree itself is **not** published and is **not** obtainable from
this repository; the excluded files and the reasons for excluding each are recorded in
`EXCLUDED_FILES_REVIEW.md`.

## Mapping: published file to internal origin

| published file | internal origin | relation to the frozen release |
|---|---|---|
| `config/final_analysis_config.py` | `final_analysis_config.py` | identical |
| `src/phenotype/phenotype_audit.py` | `phase_0a_phenotype.py` | identical |
| `src/phenotype/build_cohorts.py` | `phase_2_cohorts.py` | identical |
| `src/phenotype/cohort_composition.py` | `phase_2b_composition.py` | identical |
| `src/clinical_scores/meld_component_audit.py` | `phase_0b_meld_audit.py` | identical |
| `src/preprocessing/build_dataset_and_model.py` | `phase_3_4_dataset_model.py` | identical |
| `src/clinical_scores/clinical_scores.py` | `phase_5_6_7_scores.py` | identical |
| `src/validation/validation_and_sensitivity.py` | `phase_8_9_12_13.py` | identical |
| `tests/fault_injection/fault_injection_suite.py` | `phase_13_fault_injection.py` | identical |
| `tests/metric_validation/independent_metrics_and_verification.py` | `phase_14_17_golden_independent.py` | identical |
| `src/validation/primary_validation.py` | `publock_03_04_05.py` | identical |
| `src/validation/publication_lock.py` | `publock_03_publication_lock.py` | internal audit script -- see below |
| `src/clinical_scores/paired_score_comparison.py` | `publock_08b_selection_paired.py` | identical |
| `src/reporting/tables_and_figures.py` | `publock_08_12_13_tables_figures.py` | differs -- see below |
| `src/provenance.py` | `provenance.py` | differs -- see below |
| `src/reporting/final_release_check.py` | `final_release_check.py` | internal audit script -- see below |
| `src/reporting/release_verification.py` | `verify_release.py` | internal audit script -- see below |
| `src/validation/hospital_analysis_and_recalibration.py` | `publock_06_07_hospital.py` | **replaces** it -- see below |
| `src/manuscript_qa/number_audit.py` | `manuscript_number_audit.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/semantic_unit_audit.py` | `semantic_unit_audit.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/claim_compliance.py` | `manuscript_claim_compliance.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/language_pass.py` | `language_pass.py` | added after the frozen release; not analytical |
| `src/manuscript_qa/reference_audit.py` | `reference_final_audit.py` | added after the frozen release; not analytical |

The five `src/manuscript_qa/` scripts are **not** analytical: they audit the manuscript
text against the locked numbers. They are shipped because they document how the numbers
were traced, and they require the manuscript files (not included here) to run.

## The four published files that differ from the frozen release

### `src/validation/hospital_analysis_and_recalibration.py`

**Analytical difference: a REMOVAL.** The internal file carried a third section, 6C, a
custom hierarchical mixed-effects calibration fit. That model was audited, found
unreliable, and **removed from the manuscript** -- see
`docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`. The published script
therefore contains only the retained analyses: per-hospital descriptive performance,
the random-effects AUROC meta-analysis, hospital-level descriptive summaries and the
leave-one-hospital-out recalibration. **It performs no mixed-effects fitting.** The
rejected implementation is preserved, non-executable and clearly marked, at
`archive/nonproduction/hierarchical_calibration_rejected_historical.py`.

This is the one change in v1.1.0 that touches an analysis, and it removes rather than
alters. The retained sections reproduce the v1.0.0 values exactly.

### `src/reporting/tables_and_figures.py`

**Reporting difference only.** The hierarchical calibration sheet is no longer written
into Table 4, and Figure 5 panel B was replaced with the observed-to-expected ratio per
hospital -- a direct ratio that requires no mixed-effects fitting. No other table or
figure changes.

### `src/provenance.py`

**Manuscript-tooling addition only.** Two module-level helpers (`CITATION_RE` and
`citations()`) were added so the manuscript assembler and the reference auditor share
one citation pattern. They are not called by any analytical path. The metric
primitives in this module -- the functions that compute the performance metrics -- are
unchanged.

This is stated explicitly because `provenance.py` computes the reported metrics, and a
reader is entitled to know that the change here cannot affect a number.

### `src/reporting/final_release_check.py`

**Verification gate only -- and now strictly stronger.** Two changes: an explicit
assertion that Table 4 does **not** contain the removed `hierarchical_calibration` or
`random_intercepts` sheets, and the removal of the checks that previously required
them. It computes no result.

`src/reporting/final_release_check.py`, `src/reporting/release_verification.py` and
`src/validation/publication_lock.py` are **internal release-audit scripts**, not
reproduction steps. They require restricted artefacts that this repository does not
ship. `README.md` labels them as such and they are not part of the normal run order.

## Summary

- identical to the frozen release: **12** published files
- differ, with the difference documented above: **4** published files
- added after the frozen release (manuscript QA, not analytical): **5** files
- replaces a frozen-release file with its retained-analyses-only subset: **1** file
  (`src/validation/hospital_analysis_and_recalibration.py`)

The published code corresponds to the locked primary analysis. The single analytical
difference is a declared **removal**, recorded in `CHANGELOG.md`, in the script's own
docstring, in `docs/audit/`, and here.
