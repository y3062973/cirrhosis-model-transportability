# EXCLUDED FILES REVIEW

**Scope: the internal working tree.** Every file that was considered and **excluded**
from the public code release, with the reason. Uncertainty resolves to exclusion: if it
could not be shown to be free of patient-level data, it is not in the release.

Names below are the *internal working-tree* names. They are recorded so that a reader
can understand what was withheld and why; the excluded files themselves are not
shipped, and several are referenced only as categories.

| file or directory | reason for exclusion |
|---|---|
| `data/` | the derived analysis dataset, per-centre cohort tables and the predictions file. These carry `subject_id`, `hadm_id`, `stay_id` and admission dates. **The single most important exclusion.** |
| `data/analysis_dataset.csv` | one row per ICU stay, with patient identifiers and admission/discharge/death timestamps. Restricted. |
| `data/predictions.csv` | per-stay model predictions joined to identifiers. Restricted. |
| `data/cohort_*.csv` | per-centre cohort extracts with identifiers. Restricted. |
| `data/recalibration_cv_predictions.csv` | per-stay held-out predictions. Restricted. |
| `data/publock_*.csv` | derived analysis outputs at hospital or stay level. Restricted. |
| `logs/` | run logs. Checked: they contain counts and statistics, not patient identifiers. Excluded anyway, because a log is generated and adds nothing a reader needs, and because a future log could contain more. |
| `tables/` | the released tables as `.xlsx`. Aggregate and publishable in principle, but they are publication artefacts rather than code, and the manuscript already carries them. |
| `figures/` | generated figures and their provenance sidecars. Publication artefacts, not code. |
| `01_transportability/` | superseded analyses. Shipping code that reproduces numbers other than the published ones invites confusion. |
| development notebooks and scratch | superseded by the `phase_*` pipeline scripts that were kept. |
| diagnostic scratch scripts | not part of the locked workflow. |
| packaging-task scratch scripts (one-off diffs, tag comparisons, progress and timing helpers) | scaffolding created while assembling this release. Not part of the study. |
| the historical patcher `apply_hierarchical_beta_fix.py` (also named `fix_hierarchical_beta.py`) | it edited a file at a path that does not exist in this repository, so shipping it would have given a reader a script that fails on a missing target. Its effect is visible in the archived implementation and described in `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md`. |
| database-version provenance scripts | they carried hardcoded local credentials; superseded by `docs/DATABASE_SETUP.md`. |
| journal-targeting and submission tooling | not analysis code. |
| manuscript assembly and correction machinery | not needed to reproduce the analysis. Five manuscript-QA scripts are kept because they document how the numbers were traced. |
| readiness reports and release bookkeeping | internal process artefacts. |
| cached HTML from journal websites | fetched while checking submission guidelines. |
| `__pycache__/` | compiled bytecode. |
| any `.env`, key or credential file | none was found in the tree; the `.gitignore` blocks them prospectively. |

## Non-sensitive audit documents: included, not excluded

The following were previously excluded from the code release and are **now shipped**
under `docs/audit/`, because they contain no restricted data (checked: no
individual-level records, no hospital identifiers, no absolute filesystem paths, no
credentials, no third-party URLs) and because a reader must be able to check the
decision to remove the hierarchical calibration analysis rather than take it on trust:

| document | why it is safe to publish |
|---|---|
| `HIERARCHICAL_LAPLACE_MATH_AUDIT.md` | mathematical derivation and fit-level scalars only |
| `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` | aggregate model-level comparison statistics only |
| `HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` | code-level description and aggregate numbers only |
| `PUBLICATION_LOCK_v1.1.0.md` | release-level aggregate results only; names no patient, hospital, date or path |

## Note on the manuscript and table files

The tables are aggregate and could be published without breaching any data-use
agreement. They are excluded because this repository is a **code** release: the tables
belong with the manuscript, and including a second copy creates two sources of truth
that can drift apart.

For the same reason the **manuscripts themselves are not in this repository**. The one
place where that matters is recorded in
`AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`: the manuscripts still contain wording whose
only support was the removed model, and since the manuscripts are not shipped here, the
code release cannot fix it. That file records what the authors need to change.
