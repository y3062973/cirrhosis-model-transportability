# Pipeline

Scripts are listed in the order they must run. Each stage reads what the previous one
wrote, resolved through **one repository root** defined in `src/repo.py`. Run from the
repository root; path resolution does not depend on the current working directory, so a
script may also be run by absolute path from anywhere.

**Access column.** `PUBLIC` = runs on this repository alone. `DB` = needs authorised
read-only access to MIMIC-IV, eICU-CRD and/or nwICU (and, from step 4 onward, the
restricted analysis dataset derived from them). Nothing in this repository pretends that
a `DB` step runs in a clean clone; see the table in `README.md`.

## Where things are written

| location | contents | shipped? |
|---|---|---|
| `data/` | source extracts, cohort tables, the analysis dataset, predictions, derived CSV outputs | **no** -- restricted; the user installs it |
| `outputs/tables/` | generated tables and workbooks (`.xlsx`) | no |
| `outputs/figures/` | generated figures (`.png`, `.pdf`) | no |
| `outputs/logs/` | generated run logs | no |

`outputs/` is created automatically by `repo.ensure_writable_dirs()`. `data/` is **not**
created automatically: an empty `data/` would only make a missing install look like a
successful one. Every stage resolves these four locations identically, which is what makes
the hand-off between stages work; `python pipeline_path_audit.py` verifies it.

| # | script | access | consumes | produces |
|---|---|---|---|---|
| 1 | `src/phenotype/build_cohorts.py` | DB | the three source databases | the per-centre cohort tables |
| 2 | `src/phenotype/phenotype_audit.py` | DB | the source databases | the strict phenotype code audit |
| 3 | `src/phenotype/cohort_composition.py` | DB | the source databases | cohort code composition and the strict-versus-broad sensitivity |
| 4 | `src/preprocessing/build_dataset_and_model.py` | DB | the cohort tables | the analysis dataset and `FINAL_MODEL_V2` |
| 5 | `src/clinical_scores/clinical_scores.py` | DB | the analysis dataset | MELD, MELD-Na, ALBI, FIB-4 |
| 6 | `src/validation/validation_and_sensitivity.py` | DB | the analysis dataset and predictions | external validation, window, landmark and sensitivity results |
| 7 | `tests/fault_injection/fault_injection_suite.py` | DB | the restricted analysis dataset | the fault-injection results |
| 8 | `tests/metric_validation/independent_metrics_and_verification.py` | DB | the restricted analysis dataset, the predictions, the three source databases | the independent metric check and the raw-to-derived verification |
| 9 | `src/validation/primary_validation.py` | DB | predictions | primary metrics, bootstrap optimism, recalibration |
| 10 | `src/validation/hospital_analysis_and_recalibration.py` | DB | predictions | per-hospital descriptive performance, the random-effects AUROC meta-analysis, hospital-level descriptive summaries, and leave-one-hospital-out recalibration |
| 11 | `src/clinical_scores/paired_score_comparison.py` | DB | scores and predictions | the paired score comparison |
| 12 | `src/reporting/tables_and_figures.py` | DB | all of the above | the released tables and figures |
| -- | `verify_public_release.py` | PUBLIC | this repository | checksums, required files, compilation, restricted-data and reference checks |

The independent metric verification in step 8 is the second implementation of every
performance metric. It imports none of the primary metric code and is compared against it
on synthetic data with fixed expected values. Note that it is **not** self-contained:
alongside the synthetic comparison it performs a raw-to-derived trace that reads the
restricted analysis dataset and opens read-only connections to the three databases. The
fault-injection suite in step 7 also reads the restricted analysis dataset, because it
samples real ICU stays from it. Only `verify_public_release.py` runs in a clean
clone.

## Notes on running

**Every step except the verifier needs database access or restricted derived data.**
Steps 1-3 query the source databases directly; the rest operate on the restricted analysis
dataset and predictions that step 4 produces, and steps 7 and 8 additionally read that
dataset (step 8 also queries the databases). `verify_public_release.py` needs
neither.

**Nothing writes to the databases.** Every connection is opened read-only, and the shared
helper is `src/db.py`, which reads credentials from the environment.

**Step 10 is the slowest step that runs on data.** The leave-one-hospital-out
recalibration refits the recalibration updates once per hospital and then runs a
hospital-cluster bootstrap over the paired differences (2,000 replicates by default, from
the frozen configuration).

**Step 10 performs no mixed-effects fitting.** In release v1.0.0 this slot held
`src/validation/hierarchical_calibration.py`, which additionally fitted a custom
hierarchical calibration model with a random intercept per hospital. That model was
audited and **removed from the manuscript as unreliable**, and the file is no longer part
of the pipeline. Step 10 now contains only the retained analyses: the per-hospital AUROC
analysis, the random-effects AUROC meta-analysis, valid hospital-level descriptive
summaries and the leave-one-hospital-out recalibration. **No hierarchical numerical
result is part of this release**, and no user should attempt to reproduce that model from
this pipeline.

The rejected implementation is preserved for transparency only at
`archive/nonproduction/hierarchical_calibration_rejected_historical.py`. It is disabled, it
refuses to run, and it must not be used for inference. The audit record is in
`docs/audit/`.

**Do not treat the figures as a step-10 detail.** Figure 5 panel B is generated from the
per-hospital observed-to-expected ratios computed in step 10; it is not a caterpillar plot
of random intercepts, and it involves no mixed-effects fitting.

**The analysis dataset is restricted.** It is derived from credentialed databases and
carries patient identifiers. It must not be committed; `.gitignore` blocks the common
paths. All intermediate artefacts listed in the "produces" column live under `data/`,
`tables/`, `figures/` and `logs/`, none of which is shipped in this repository.

**Internal release-audit scripts are not steps in this pipeline.**
`src/reporting/final_release_check.py`, `src/reporting/release_verification.py` and
`src/validation/publication_lock.py` are provenance and release-verification tooling.
They depend on restricted internal artefacts, internal checksum files and historical Git
tags that are not shipped, so they cannot run here. They are kept in place and labelled
as internal; `README.md` and their module docstrings both say so.

## Provenance

Every output carries a sidecar recording the configuration version and hash, the dataset
hash, the producing script and the package versions, written by `src/provenance.py`. The
frozen configuration reports its version as `FINAL_v1.0.0` while the publication is
v1.1.0: the primary model was not changed, so that string was deliberately left alone.
See the "Version strings" section of `README.md` and of `CHANGELOG.md`.

## Grouping note

The stage directories (`phenotype/`, `preprocessing/`, `clinical_scores/`, `validation/`,
`reporting/`) group the scripts by role. In the internal working tree several stages
shared a single numbered script; the mapping from each published filename to its internal
origin is recorded in `docs/audit/CODE_INVENTORY.md` so that a reader can trace a
published file back to its provenance. The internal working tree is not published; what
was excluded from it and why is in `docs/audit/EXCLUDED_FILES_REVIEW.md`.

## Verifying a clone

```bash
python verify_public_release.py
```

It runs 20 checks across 8 groups: checksums, required and forbidden paths, compilation,
the absence of restricted data, that every file path referenced by the documentation
resolves, that this release's manifest agrees with the checksum manifest and the tree, and
that `CITATION.cff` is structurally valid with no fake DOI or URL. It needs no database and
no patient-level data, and it exits non-zero if anything is inconsistent.
