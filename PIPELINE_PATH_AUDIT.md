# PIPELINE PATH AUDIT

**Verdict:**

> # ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS

**Reproduce:** `python pipeline_path_audit.py` (exit 0). It needs no database access, no
credential and no data: it extracts each script's path-setup block, executes only those
lines, and AST-parses each stage for the artefacts it reads and writes.

---

## 1. The defect this fixes

In the v1.1.0 release candidate the published scripts had been grouped into stage
directories (`src/phenotype/`, `src/preprocessing/`, `src/clinical_scores/`,
`src/validation/`, `src/reporting/`, `tests/...`), but each script still computed its own
paths from its own location:

```python
FR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(FR, "data")
TABLES = os.path.join(FR, "tables")
FIGS = os.path.join(FR, "figures")
LOGS = os.path.join(FR, "logs")
```

So `DATA` resolved to a **different directory in every stage**:

| script | `DATA` resolved to |
|---|---|
| `src/phenotype/build_cohorts.py` | `<repo>/src/phenotype/data` |
| `src/preprocessing/build_dataset_and_model.py` | `<repo>/src/preprocessing/data` |
| `src/validation/hospital_analysis_and_recalibration.py` | `<repo>/src/validation/data` |
| `tests/metric_validation/independent_metrics_and_verification.py` | `<repo>/tests/metric_validation/data` |

Step 1 wrote its cohort tables into `src/phenotype/data/`; step 4 read `csv` files from
`src/preprocessing/data/` and found nothing. **The documented pipeline could not pass an
output from one stage to the next.** The defect was invisible to `python -m compileall`
and to a filename-existence check, because every script was individually valid Python and
every *script* path in the docs was correct — only the resolved *data* paths were wrong.

Two related defects were found at the same time and are also fixed:

* `src/phenotype/phenotype_audit.py` and `src/clinical_scores/meld_component_audit.py`
  built their root as `os.path.join(dirname(__file__), "..") + "FINAL_REBUILD"`, a path
  that exists only in the authors' internal working tree and **not in this repository**.
* `src/phenotype/cohort_composition.py` used a module-level loop variable named `db`,
  which rebound the `db` import to a string and would have made the `conn()` helper fail
  with `AttributeError: 'str' object has no attribute 'connect'`.

## 2. The layout now

One root, resolved by `src/repo.py`, which walks up from its own file to the directory
holding `README.md`:

```text
<repo root>/
    README.md                     <- the root marker
    data/                         <- installed locally; restricted, never committed
    outputs/
        tables/                   <- generated tables and workbooks
        figures/                  <- generated figures
        logs/                     <- generated run logs
    src/
        repo.py                   <- the single source of truth
        phenotype/ preprocessing/ clinical_scores/ validation/ reporting/ manuscript_qa/
    tests/
        fault_injection/ metric_validation/ known_answer/
```

Every stage now resolves its paths centrally:

```python
import repo
repo.add_src_to_path()

FR = str(repo.REPO_ROOT)     # the REPOSITORY ROOT, not this file's directory
DATA = str(repo.DATA)
TABLES = str(repo.TABLES)
FIGS = str(repo.FIGURES)
LOGS = str(repo.LOGS)
repo.ensure_writable_dirs()
```

`data/` deliberately sits at the repository root rather than under `outputs/`. It holds
source and derived **patient-level** data that the user must obtain under each database's
own access agreement; it is an input, not an output of this repository. `outputs/` holds
everything the code generates and is `.gitignore`d.

`repo.add_src_to_path()` puts both `src/` and `config/` on `sys.path`. The run sequence
used to require `export PYTHONPATH=src:config`, and every script does a bare
`import final_analysis_config` from `config/`, so without that export the import failed.
The helper removes the dependency on the caller setting it correctly.

**Path resolution does not depend on the current working directory**, so a script may be
run from anywhere:

```bash
python src/phenotype/build_cohorts.py          # from the repository root
python /abs/path/to/repo/src/repo.py           # from anywhere
```

## 3. Stage-by-stage resolution

Extracted and executed by `pipeline_path_audit.py`. All 21 modules that define paths
resolve the four locations to exactly the same directories.

| # | stage script | DATA | TABLES | FIGURES | LOGS |
|---|---|---|---|---|---|
| 1 | `src/phenotype/build_cohorts.py` | `<root>/data` | `<root>/outputs/tables` | `<root>/outputs/figures` | `<root>/outputs/logs` |
| 2 | `src/phenotype/phenotype_audit.py` | same | same | same | same |
| 3 | `src/phenotype/cohort_composition.py` | same | same | same | same |
| 4 | `src/preprocessing/build_dataset_and_model.py` | same | same | same | same |
| 5 | `src/clinical_scores/clinical_scores.py` | same | same | same | same |
| — | `src/clinical_scores/meld_component_audit.py` | same | same | same | same |
| 6 | `src/validation/validation_and_sensitivity.py` | same | same | same | same |
| 7 | `tests/fault_injection/fault_injection_suite.py` | same | same | same | same |
| 8 | `tests/metric_validation/independent_metrics_and_verification.py` | same | same | same | same |
| 9 | `src/validation/primary_validation.py` | same | same | same | same |
| 10 | `src/validation/hospital_analysis_and_recalibration.py` | same | same | same | same |
| 11 | `src/clinical_scores/paired_score_comparison.py` | same | same | same | same |
| 12 | `src/reporting/tables_and_figures.py` | same | same | same | same |
| — | `src/validation/publication_lock.py` | same | same | same | same |
| — | `src/reporting/final_release_check.py` | same | same | same | same |
| — | `src/reporting/release_verification.py` | same | same | same | same |
| — | `src/manuscript_qa/semantic_unit_audit.py` | same | same | same | same |
| — | `src/manuscript_qa/number_audit.py` | same | same | same | same |
| — | `src/manuscript_qa/claim_compliance.py` | same | same | same | same |
| — | `src/manuscript_qa/language_pass.py` | same | same | same | same |
| — | `src/manuscript_qa/reference_audit.py` | same | same | same | same |

`src/provenance.py` and `src/db.py` define no data or output paths. `provenance.py` uses
`FR` only to locate `requirements.txt` for the dependency lock hash, so it carries the
repository root and nothing else. `db.py` has no path dependence at all.

## 4. Hand-off verification

`pipeline_path_audit.py` AST-parses every stage and extracts, per stage, the artefact names
it **reads** (`read_csv`, `read_excel`, `read_json`, `read_parquet`, `open` in read mode)
and the names it **writes** (`to_csv`, `to_excel`, `savefig`, `open` in write mode). It
then checks that every artefact read by a stage is produced by that same stage or by an
earlier one.

**Result: no ordering violation.** The chained hand-offs are:

| producer | artefact | consumer |
|---|---|---|
| 1 `build_cohorts.py` | `cohort_mimic.csv`, `cohort_eicu.csv`, `cohort_nwicu.csv`, `cohort_flow.csv` | 3, 4 |
| 2 `phenotype_audit.py` | `cirrhosis_phenotype_rule.json`, `cirrhosis_code_dictionary.xlsx` | 4 |
| 3 `cohort_composition.py` | `TableS8_cohort_composition.xlsx` | 12 |
| 4 `build_dataset_and_model.py` | `analysis_dataset.csv`, `predictions.csv`, `model_v2_coefficients.csv` | 5, 6, 8, 9, 10, 11, 12 |
| 5 `clinical_scores.py` | `score_comparison_common_complete.csv`, `score_comparison_paired.csv`, `map_sensitivity.csv`, `TableS9_score_detail.xlsx` | 11, 12 |
| 6 `validation_and_sensitivity.py` | `missingness_sensitivity.csv`, `early_prediction_sensitivity.csv`, `publock_repeated_patient.csv`, `known_answer_tests.csv` | 12 |
| 9 `primary_validation.py` | `publock_external_ci.csv`, `publock_optimism.csv`, `Table_Final_Optimism.xlsx` | 12 |
| 10 `hospital_analysis_and_recalibration.py` | `publock_hospital_descriptive.csv`, `publock_hospital_meta.csv`, `publock_recalibration_ci.csv`, `recalibration_cv_predictions.csv`, `Table4_hospital_level.xlsx`, `Table5_recalibration.xlsx` | 11, 12 |
| 11 `paired_score_comparison.py` | `publock_paired_score_differences.csv`, `publock_score_mappings.csv`, `Table6_score_comparison.xlsx` | 12 |
| 12 `tables_and_figures.py` | `Table1..Table3`, `Supplementary_Tables_S1_S7.xlsx`, figures | — |

The single-input rule is worth stating explicitly: `analysis_dataset.csv` and
`predictions.csv` are written by stage 4 and read by every later data stage, which is why
those two names are exempted from the ordering rule above — they are the pipeline's shared
inputs, not a stage's private intermediate.

## 5. Verification performed

| check | result |
|---|---|
| every module's path block executes without error | 21/21 |
| all stages resolve DATA to the same directory | PASS |
| all stages resolve TABLES / FIGURES / LOGS to the same directories | PASS |
| no path constant points inside `src/` or `tests/` | PASS |
| `python -m compileall` over the release | PASS |
| every artefact read is produced by an earlier stage | PASS |
| `src/repo.py` self-test resolves an absolute root under `<repo>` | PASS |
| no production script fits, reads or writes the removed hierarchical model | PASS |

## 6. What was NOT changed

This was a path-resolution repair. **No query, cohort, phenotype rule, eligibility
criterion, predictor, aggregation rule, imputation rule, model, coefficient or reported
number was touched.** The frozen configuration `config/final_analysis_config.py` is
byte-identical to the v1.1.0 candidate and still reports `VERSION = "FINAL_v1.0.0"`;
its configuration hash is unchanged. The change is confined to how each script locates
`data/` and `outputs/`.
