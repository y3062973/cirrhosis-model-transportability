# Transportability of a cirrhosis mortality model across health systems: analysis code and reproducibility materials

Analysis code and non-restricted reproducibility materials accompanying the manuscript.

**Release:** `PROJECT1_FINAL_MANUSCRIPT_v1.1.0`
**Frozen primary-analysis configuration:** `FINAL_v1.0.0` (unchanged -- see
[Version strings](#version-strings))

## Purpose

This repository contains the analysis code, the frozen analysis configuration and the
non-restricted reproducibility materials for a study of how a cirrhosis mortality
prediction model transports between health systems.

**It contains no data.** It contains no source data, no derived patient-level or
stay-level data, and no database extracts. Everything needed to reproduce the analysis
from scratch is here except the data, which must be obtained independently under each
database's own access agreement.

The finding the code reproduces is a transportability result: discrimination and the
calibration slope transported between health systems, while calibration-in-the-large did
not. The code is published so that result can be checked, not because the model is
offered for clinical use.

## What is in this release, and what is not

Release v1.1.0 removes one analysis. A hierarchical mixed-effects calibration model was
audited, found unreliable, and **removed from the manuscript**; **no numerical result from
it is part of this release**. The retained hospital-level analyses are the per-hospital
AUROC analysis, the random-effects AUROC meta-analysis and the leave-one-hospital-out
recalibration.

**What the retained analyses support:** hospital-specific calibration estimates varied
**descriptively**.
**What they do not support, and what is therefore not claimed:** neither that all
hospitals shared the same calibration shift, nor that significant calibration
heterogeneity was proven. No formal hierarchical calibration-heterogeneity conclusion is
reported.

The audit trail is shipped in `docs/audit/`, and the rejected implementation is preserved,
non-executable, in `archive/nonproduction/`. See [Audit trail](#audit-trail).

## Version strings

Two version numbers appear here and they are **supposed to differ**:

| what | version | why |
|---|---|---|
| the frozen primary-analysis configuration in `config/final_analysis_config.py` | `FINAL_v1.0.0` | the primary model and its configuration were **not changed**. Editing that string would change the frozen configuration hash and invalidate every output stamped with it. |
| this publication / code release | `1.1.0` | v1.1.0 **removes an unreliable secondary hierarchical analysis**. It does not change the primary analysis. |

A reader who sees `FINAL_v1.0.0` inside `final_analysis_config.py` is seeing the correct,
deliberately preserved value, not a stale string.

## Data

**This repository does NOT contain MIMIC-IV, eICU-CRD or nwICU data.** All three are
third-party credentialed resources, and the authors are not permitted to redistribute
them. An independent researcher must obtain their own authorised access.

| database | version | role | where to obtain it |
|---|---|---|---|
| MIMIC-IV | **v3.1** | development cohort (4,237 ICU stays, 857 deaths) | https://physionet.org/content/mimiciv/3.1/ |
| eICU-CRD | **v2.0** | primary external validation (1,612 ICU stays, 324 deaths, 155 hospitals) | https://physionet.org/content/eicu-crd/2.0/ |
| nwICU | **v0.1.0** | secondary external validation (349 ICU stays, 75 deaths) | https://physionet.org/content/nwicu/0.1.0/ |

Access requires completion of the required training and acceptance of a data-use
agreement that prohibits redistribution. See `DATA_ACCESS.md` for the full statement,
including the MIMIC-IV version used.

## Repository layout

```text
verify_public_release.py   public-safe verifier (run this first; no data needed)
pipeline_path_audit.py     path and stage hand-off audit (no data needed)

data/                      YOU install this; restricted, never committed
outputs/                   everything the code generates
    tables/                generated tables and workbooks
    figures/               generated figures
    logs/                  generated run logs

config/                    the frozen analysis configuration
src/                       the analysis pipeline, grouped by stage
    repo.py                THE single source of truth for repository paths
metadata/                  aggregate, non-identifying metadata
tests/                     fault injection and independent metric verification
docs/                      pipeline, database setup and the audit trail
internal_audit/            why the internal release-audit scripts cannot run here
archive/nonproduction/     the rejected hierarchical implementation, audit only
```

Every stage resolves `data/` and `outputs/` through `src/repo.py`, so all stages share ONE
repository root and each stage can read what the previous one wrote. Path resolution does
not depend on the current working directory, so you can run a script from anywhere. The
full account of that repair, including the stage-by-stage table and the hand-off
verification, is in `PIPELINE_PATH_AUDIT.md`; `python pipeline_path_audit.py` regenerates
and re-checks it.

`data/` sits at the repository root rather than under `outputs/` because it holds
patient-level source and derived data that you obtain under each database's access
agreement. It is an input, not an output of this repository.

## What can actually be run

**Not every script in this repository runs in a clean clone.** Read this table before
running anything. The columns are: does it run here, and what does it need.

| script | category | needs |
|---|---|---|
| `verify_public_release.py` | **PUBLICLY RUNNABLE WITHOUT DATABASE DATA** | nothing but this repository |
| `pipeline_path_audit.py` | **PUBLICLY RUNNABLE WITHOUT DATABASE DATA** | nothing but this repository |
| `src/repo.py` | **PUBLICLY RUNNABLE WITHOUT DATABASE DATA** | nothing; prints the resolved layout |
| `src/phenotype/build_cohorts.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the three databases, read-only |
| `src/phenotype/phenotype_audit.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases |
| `src/phenotype/cohort_composition.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases |
| `src/preprocessing/build_dataset_and_model.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases and the cohorts built by step 1 |
| `src/clinical_scores/clinical_scores.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases and the analysis dataset (restricted derived data) |
| `src/clinical_scores/meld_component_audit.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases |
| `src/validation/validation_and_sensitivity.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the analysis dataset and predictions |
| `src/validation/primary_validation.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the analysis dataset and predictions |
| `src/validation/hospital_analysis_and_recalibration.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the analysis dataset and predictions |
| `src/clinical_scores/paired_score_comparison.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the source databases, the analysis dataset and predictions |
| `src/reporting/tables_and_figures.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | every artefact above |
| `tests/fault_injection/fault_injection_suite.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the restricted analysis dataset; it samples real ICU stays from it |
| `tests/metric_validation/independent_metrics_and_verification.py` | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the restricted analysis dataset, the predictions, and read-only access to all three databases for the raw-to-derived trace |
| the `src/manuscript_qa/` scripts | **REQUIRES AUTHORISED ACCESS TO MIMIC/eICU/nwICU** | the artefacts above **and** the manuscript files, which are not in this repository |
| `src/reporting/final_release_check.py` | **INTERNAL RELEASE-AUDIT SCRIPT -- NOT PART OF NORMAL REPRODUCTION** | restricted internal artefacts, internal checksum files and a historical Git tag |
| `src/reporting/release_verification.py` | **INTERNAL RELEASE-AUDIT SCRIPT -- NOT PART OF NORMAL REPRODUCTION** | an internal artefact-checksum file that is not shipped |
| `src/validation/publication_lock.py` | **INTERNAL RELEASE-AUDIT SCRIPT -- NOT PART OF NORMAL REPRODUCTION** | restricted internal artefacts, and a read-only eICU database connection |
| `archive/nonproduction/hierarchical_calibration_rejected_historical.py` | **DO NOT RUN -- HISTORICAL, NOT USED IN THE FINAL MANUSCRIPT** | refuses to execute; kept for audit history only |

**Read the table literally.** Only the verifier, the path audit and `src/repo.py` run in a
clean clone.
The two test suites are *not* self-contained: despite their names they read the restricted
analysis dataset, and the independent metric verification also opens read-only connections
to the three databases for its raw-to-derived trace. An independent researcher with their
own authorised access can run the whole analysis; someone without it can run the verifier,
and can read every number and the reasoning behind the removal. Nothing in this repository
pretends otherwise.

## Reproduction

Each stage reads what the previous one wrote, through the shared paths in `src/repo.py`.
Run them in this order from the repository root.

```bash
# 0. configure database credentials LOCALLY (never commit them)
cp .env.example .env      # then edit .env with your own values
export $(grep -v '^#' .env | xargs)     # or use python-dotenv
```

`PYTHONPATH` no longer needs to be set by hand: `src/repo.py` puts `src/` and `config/` on
the import path, so the scripts do not depend on an environment variable being exported
correctly.

```text
 0. check the layout (no data needed)
      python src/repo.py
      python pipeline_path_audit.py
```
 1. build the strict cirrhosis cohort and extract the source tables
      python src/phenotype/build_cohorts.py
 2. audit the strict phenotype codes
      python src/phenotype/phenotype_audit.py
 3. cohort code composition and the strict-versus-broad sensitivity
      python src/phenotype/cohort_composition.py
 4. extract 0-24 h predictors, apply aggregation and imputation, fit FINAL_MODEL_V2
      python src/preprocessing/build_dataset_and_model.py
 5. construct MELD, MELD-Na, ALBI and FIB-4 on identical ICU stays
      python src/clinical_scores/clinical_scores.py
 6. external validation, window and landmark analyses, sensitivity analyses
      python src/validation/validation_and_sensitivity.py
 7. fault injection and the independent metric verification
      python tests/fault_injection/fault_injection_suite.py
      python tests/metric_validation/independent_metrics_and_verification.py
 8. primary validation, bootstrap optimism, recalibration
      python src/validation/primary_validation.py
 9. per-hospital performance, random-effects AUROC meta-analysis,
    leave-one-hospital-out recalibration
      python src/validation/hospital_analysis_and_recalibration.py
10. paired score comparison
      python src/clinical_scores/paired_score_comparison.py
11. generate the tables and figures
      python src/reporting/tables_and_figures.py
```

**Step 9 replaces the former step 9.** In release v1.0.0 this step ran
`src/validation/hierarchical_calibration.py`, which also fitted a custom hierarchical
mixed-effects calibration model. That model was removed as unreliable, and the file no
longer exists in the pipeline. Step 9 above contains only the retained analyses and
performs no mixed-effects fitting. The removed implementation is archived, and must not
be run for inference.

**Verification.** After running the pipeline:

```text
python verify_public_release.py        # works in a clean clone, no data needed
```

That is the supported release check for a public reader. The three internal release-audit
scripts listed above are **not** reproduction steps and are not runnable without internal
artefacts.

`docs/PIPELINE.md` gives the same sequence with the artefacts each step consumes and
produces, and is authoritative for ordering if the two ever disagree. It also marks which
steps need database access.

## Requirements

```bash
pip install -r requirements.txt
```

Pinned to the versions actually used. `environment.yml` is provided for conda.

## Audit trail

The one analytical change in v1.1.0 is a removal, and the record of it ships with the
code so a reader can check it rather than take it on trust:

| document | what it is |
|---|---|
| `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` | the four-way comparison and the decision rule that removed the model |
| `docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md` | the mathematical audit: the omitted Gaussian prior normalisation |
| `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` | the first defect: the optimiser returned the slope at its starting value |
| `docs/audit/PUBLICATION_LOCK_v1.1.0.md` | release-level record of what changed and what did not |
| `docs/audit/LOCKED_RELEASE_CODE_VERIFICATION.md` | file-by-file comparison against the frozen analytical release |
| `docs/audit/CODE_INVENTORY.md` | provenance of each published file |
| `docs/audit/EXCLUDED_FILES_REVIEW.md` | what was withheld and why |
| `docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` | **open item for the authors** -- see below |
| `archive/nonproduction/hierarchical_calibration_rejected_historical.py` | the rejected implementation, disabled and clearly marked |

**Open item.** The manuscript files are **not** part of this repository. Five sentences
in them still assert or presuppose the removed model's uniform-shift claim.
`docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` quotes them with line numbers and
gives minimal replacements. The code release cannot fix this; it records it.

## Data governance

**Derived patient-level and stay-level data must never be committed to this
repository.** A file derived from MIMIC-IV remains governed by the MIMIC-IV data-use
agreement; deriving it does not make it the authors' to publish. This is the rule most
easily broken by accident, because a derived table feels like one's own work.

`.gitignore` blocks the common cases (`.env`, `data/`, `*.csv`, dumps, keys). It is a
backstop, not a substitute for care. `DATA_ACCESS.md` states the rules in full.
`verify_public_release.py` re-checks the shipped tree for restricted data on every
run.

## Licence

**Not yet chosen.** See `LICENSE_PENDING.txt`. The authors must select a licence before
this repository is made public; MIT is recommended as a simple permissive option. Note
that `CITATION.cff` therefore omits its `license` field: Citation File Format 1.2.0
accepts only SPDX identifiers there and has no way to express "not yet chosen".

## Citation

See `CITATION.cff`. It carries the title, version 1.1.0 and all ten authors, and
**deliberately omits** the repository URL and DOI, because no DOI has been issued and a
placeholder would be silently accepted by validators and then propagate as a dead link.
Add `repository-code` once the repository exists and `identifiers` once Zenodo has
archived a release and minted a DOI.

## Verification status of this release

`python verify_public_release.py` runs 20 checks across 8 groups, with no database
access and no patient-level data:

1. **checksums** -- every file's SHA-256 matches `RELEASE_CHECKSUMS_SHA256.txt`, and the
   manifest covers every shipped file (56/56 verified across 57 files);
2. **required files** -- every required file is present and every removed or restricted
   path is absent;
3. **compile** -- every Python file compiles (26/26), is clean UTF-8 without a BOM, and
   the archived rejected implementation is inert;
4. **restricted data** -- nothing restricted is shipped: no per-row clinical table, no
   patient or stay identifier column, no credential literal, no `.env`, no credentialed
   connection string;
5. **documentation references** -- every repository file path referenced by the shipped
   documentation resolves: **0 broken** (284 checked). References to internal
   working-tree files that intentionally do not resolve are declared individually, with
   a reason, in the verifier;
6. **release manifest** -- `PUBLIC_CODE_RELEASE_MANIFEST.md` lists all 57 shipped files,
   the same set as the checksum manifest, and its sizes and hashes match the tree, so the
   two cannot drift apart;
7. **citation metadata** -- `CITATION.cff` is structurally valid and carries no fake DOI
   or repository URL.
