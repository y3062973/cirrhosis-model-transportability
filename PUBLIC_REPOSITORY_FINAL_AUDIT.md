# PUBLIC REPOSITORY FINAL AUDIT

**Release:** `project1_cirrhosis_transportability_code_release_v1.1.0-rc2`
**Analytical / publication version:** **v1.1.0** (unchanged; this pass is repository
packaging only)
**Repository root:** `project1_cirrhosis_transportability_code_release_v1.1.0/`
**Archive:** `project1_cirrhosis_transportability_code_release_v1.1.0-rc2.zip` --
62 entries under a single top-level directory, no `__pycache__`, no `data/`, no `outputs/`,
`testzip()` clean. The exact byte size is deliberately not quoted here: stating the size of
the archive inside a file that the archive contains would change it.

> # VERDICT: READY FOR PRIVATE GITHUB UPLOAD

Every gate below passes. Reproduce with:

```bash
python verify_public_release.py      # 20 checks, exit 0
python pipeline_path_audit.py        # path and stage hand-off audit, exit 0
python -m compileall -q .            # exit 0
```

All three were re-run **on the extracted archive in a clean temporary directory**, with no
`data/`, no `outputs/`, no `.git`, no credentials and no `PYTHONPATH` set. Results are in
section 3.5.

No database was queried, no statistical analysis was run, no model was refitted, and no
cohort, phenotype, predictor, coefficient or reported number was changed.

---

## 1. Gate results

| # | gate | requirement | result |
|---|---|---|---|
| 1 | shared path design fixed | all production stages resolve one repository-root `data/` + `outputs/` | **PASS** |
| 2 | rejected hierarchical model absent from the production pipeline | no fit, read or write of `fit_hier`, alpha/beta/tau, or the removed sheets | **PASS** |
| 3 | broken repository references | 0 referenced-but-missing repository files | **PASS** (0 broken of 381 checked) |
| 4 | fake CFF DOI / date values | 0 fake or placeholder values in `CITATION.cff` | **PASS** |
| 5 | checksum audit | 0 mismatches | **PASS** (61/61) |
| 6 | `python -m compileall` | PASS | **PASS** |
| 7 | public-safe verifier | PASS, with no data and no database | **PASS** (20/20 checks) |
| 8 | security scan | 0 credentials, 0 tokens, 0 patient identifier values, 0 patient/stay-level data, 0 private addresses, 0 author home paths | **PASS** |
| 9 | dry-run path test | every stage resolves DATA / TABLES / FIGURES / LOGS to the same locations | **PASS** |

## 2. What was wrong, and what was done

### 2.1 The broken shared working-directory design

The scripts had been grouped into stage directories, but each still computed its own paths
from its own location:

```python
FR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(FR, "data")
```

`DATA` therefore resolved to `src/phenotype/data`, `src/preprocessing/data`,
`src/validation/data`, `tests/metric_validation/data` … **a different directory in every
stage.** Step 1 wrote its cohort tables to one place and step 4 looked for them in another,
so the documented pipeline could not pass an output from one stage to the next.

**Fixed** by introducing `src/repo.py` as the single source of truth and rewriting the path
block of 21 modules. One repository root; the layout is now:

```text
<repo root>/
    data/                  installed locally; restricted, never committed
    outputs/tables/        generated tables and workbooks
    outputs/figures/       generated figures
    outputs/logs/          generated run logs
```

Every stage parses, imports and resolves identically. Full detail, including the
stage-by-stage table and the hand-off verification, is in `PIPELINE_PATH_AUDIT.md`, which is
regenerated from the code by `pipeline_path_audit.py` on every run.

Three related defects were found and fixed at the same time:

* `src/phenotype/phenotype_audit.py` and `src/clinical_scores/meld_component_audit.py`
  built their root as `.. + "FINAL_REBUILD"`, a path that exists only in the authors'
  internal working tree and not in this repository.
* `src/phenotype/cohort_composition.py` used a module-level loop variable named `db`, which
  rebound the `db` import and would have made its connection helper fail with
  `AttributeError: 'str' object has no attribute 'connect'`.
* Every script does a bare `import final_analysis_config` while the file lives in
  `config/`, so the documented sequence required `export PYTHONPATH=src:config`.
  `repo.add_src_to_path()` now puts both `src/` and `config/` on the path, removing the
  dependency on the caller setting it correctly.

### 2.2 The rejected hierarchical model

The final manuscript does **not** report the hierarchical calibration mixed-effects model.
It was removed as unreliable. The release now reflects that everywhere:

* `src/validation/hospital_analysis_and_recalibration.py` contains **only** the retained
  analyses: per-hospital descriptive performance, per-hospital AUROC, the random-effects
  AUROC meta-analysis, descriptive hospital observed-to-expected ratios, and
  leave-one-hospital-out recalibration. It performs **no mixed-effects fitting**.
* The rejected implementation is archived at
  `archive/nonproduction/hierarchical_calibration_rejected_historical.py`, carrying the
  banner **HISTORICAL IMPLEMENTATION. NOT USED IN THE FINAL MANUSCRIPT. DO NOT USE FOR
  INFERENCE.** All of its executable code sits in an uncalled function; running it prints a
  refusal and exits non-zero.
* `publication_lock.py`, `final_release_check.py` and `tables_and_figures.py` were all
  adapted. **No production check requires `hierarchical_calibration`, `random_intercepts`
  or any hierarchical alpha/beta/tau.** `final_release_check.py` now *fails* if either
  removed sheet reappears, so the gate is stronger than before rather than merely neutral.

### 2.3 Broken document paths

a script under `src/validation/` that does not exist did not exist. The independent metric
verification is `tests/metric_validation/independent_metrics_and_verification.py`, and every
document now names it correctly.

All repository-relative paths in `README.md`, `docs/PIPELINE.md`, `CHANGELOG.md` and
`REPRODUCIBILITY.md` resolve. The documents the CHANGELOG referenced —
`HIERARCHICAL_LAPLACE_MATH_AUDIT.md`, `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`,
`PUBLICATION_LOCK_v1.1.0.md`, `CODE_INVENTORY.md`, `EXCLUDED_FILES_REVIEW.md` — are all
**included** under `docs/audit/`, so option A was taken: the safe documents ship rather than
the references being deleted. **0 broken references.**

### 2.4 CITATION.cff

The file is strictly valid against the Citation File Format 1.2.0 schema, and the fictional
values are gone:

| field | before | now |
|---|---|---|
| `repository-code` | a placeholder GitHub URL | **absent** |
| `identifiers` (DOI) | a placeholder Zenodo DOI | **absent** |
| `date-released` | `REPLACE_WITH_RELEASE_DATE` | **absent** |
| `license` | `LicenseRef-Proprietary-Until-Licence-Chosen` (schema-invalid) | **absent** |

`version: "1.1.0"`, the title, all ten authors and the keywords are retained. No ORCID iD
was invented. The four omitted fields are documented in comments explaining exactly what to
add and in what form once the licence is chosen, the repository exists and Zenodo has minted
a DOI. A file cannot record its own hash, and the same is true of these facts: absence is
honest where a placeholder would be silently accepted and then propagate as a dead link.

### 2.5 Checksum / manifest self-reference

The manifest previously recorded its own SHA-256, which is stale by definition because
writing the row changes the file. The design is now:

| file | hashes itself? | notes |
|---|---|---|
| `PUBLIC_CODE_RELEASE_MANIFEST.md` | **no — records `SELF`** | its own row carries the literal marker `SELF`, and the verifier accepts only a real SHA-256 or `SELF` |
| `RELEASE_CHECKSUMS_SHA256.txt` | **no** | a file cannot contain its own hash |
| every other shipped file | **yes** | covered by the checksum file |

The arithmetic, stated exactly: **62 files make up the release; 61 of them are covered by
`RELEASE_CHECKSUMS_SHA256.txt`, because the checksum file cannot hash itself.** The
manifest lists all 62 rows, of which **2** record the marker `SELF`: its own row and the
checksum file's row. Verified: **61/61 checksums match, 0 mismatches, 0 missing, 0 files
unlisted, and the manifest agrees with the tree.**

### 2.6 Internal-only release scripts

`src/validation/publication_lock.py`, `src/reporting/final_release_check.py`,
`src/reporting/release_verification.py` and the `src/manuscript_qa/` directory depend on restricted
artefacts, internal checksum files and historical Git tags. They are **not** advertised as
public reproduction steps. They are kept in place — so a reader of the internal working tree
finds them where they were — with their module docstrings, `README.md` and
`internal_audit/README.md` all labelling them, and they are removed from the documented run
sequence. Where they referenced the removed model or the superseded
`PROJECT1_FINAL_MANUSCRIPT_v1.0.0` state, they were adapted to v1.1.0.

### 2.7 Version strings — a deliberate mismatch

| what | version |
|---|---|
| frozen primary-analysis configuration (`config/final_analysis_config.py`) | **`FINAL_v1.0.0`** |
| publication / code release | **`v1.1.0`** |

The frozen configuration was **not** altered and its hash is **unchanged**. Editing that
string to match the release number would change the configuration hash and invalidate every
output stamped with it. The primary model did not change; v1.1.0's only analytical change is
the **removal** of an unreliable secondary analysis. `README.md`, `CHANGELOG.md` and
`internal_audit/README.md` all state this explicitly so no reader mistakes it for staleness.

## 3. Evidence

### 3.1 Dry-run path test

```text
python pipeline_path_audit.py
[2] do all stages agree on the same four locations?
  PASS: all 21 modules that define paths agree exactly
        DATA    = <repo>/data
        TABLES  = <repo>/outputs/tables
        FIGURES = <repo>/outputs/figures
        LOGS    = <repo>/outputs/logs
[3] no module points inside src/ or tests/                             PASS
[4] stage hand-off: artefacts written vs artefacts read (AST-parsed)   PASS
[5] rejected hierarchical model must be absent from production code    PASS
VERDICT: ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS
```

The test extracts each script's path block and executes **only those lines**, so the
statistical bodies are never run. It needs no data, no credential and no database.

### 3.2 Compilation

```text
python -m compileall -q .      -> exit 0, 27 Python files
```

This gate matters: it is what caught the `import db` / `from __future__` ordering defect and
the UTF-8 BOM defect in the previous candidate, neither of which a filename check can see.

### 3.3 Security scan

| requirement | result |
|---|---|
| credential values | **0** |
| API keys / tokens | **0** |
| patient identifier *values* | **0** |
| patient-level or stay-level data | **0** |
| private server addresses | **0** |
| author home paths | **0** |

Column *names* such as `subject_id` and `stay_id` appear in extraction code, which is
expected and permitted: only a value would be a leak. The only tabular files shipped are the
three aggregate metadata files under `metadata/`, all with no patient rows.

### 3.4 Public-safe verifier

```text
python verify_public_release.py
  20/20 checks passed
  PUBLIC CODE RELEASE VERIFIED
```

It runs with no MIMIC, eICU or nwICU access and runs 20 checks: checksums; required and
forbidden paths; compilation; the absence of restricted data; documentation
references; the release manifest (including that its `SELF` rows are used correctly and
that it lists exactly the shipped files); the pipeline structure, delegated to
`pipeline_path_audit.py`; and the citation metadata.

### 3.5 The extracted archive, verified independently

The ZIP was unpacked into a clean temporary directory containing nothing else, and every
gate was re-run there:

| gate | result |
|---|---|
| `python -m compileall -q .` | exit 0 |
| `python verify_public_release.py` | **20/20 checks passed** |
| `python pipeline_path_audit.py` | **ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS** |
| `python src/repo.py` | resolves an absolute root under the extracted directory; `all paths under repo root: True` |
| archive integrity | `testzip()` clean; 62 entries; 0 outside the release root; 0 `__pycache__`; 0 `data/` or `outputs/` |

No environment variable was set and no credential was present, which is the point: the
verifier and the path audit are self-contained.

## 4. Files added or changed in this pass

| path | change |
|---|---|
| `src/repo.py` | **new** — the single source of truth for repository paths |
| `pipeline_path_audit.py` | **new** — runnable path and structure audit |
| `PIPELINE_PATH_AUDIT.md` | **new** — the path repair, written up |
| `PUBLIC_REPOSITORY_FINAL_AUDIT.md` | **new** — this document |
| `verify_public_release.py` | **renamed** from the rc1 script name; 8 check groups, 20 checks |
| `internal_audit/README.md` | **new** — why the internal scripts cannot run in a clean clone |
| `archive/nonproduction/` | **moved** out of the `docs/` tree, banner restated |
| 21 pipeline modules | path block rewritten to the shared root; no analytical change |
| `src/phenotype/cohort_composition.py` | `db` loop variable renamed; connection helper fixed |
| `src/phenotype/phenotype_audit.py`, `src/clinical_scores/meld_component_audit.py` | hardcoded `FINAL_REBUILD` root removed |
| `CITATION.cff` | fake DOI, URL, date and invalid licence removed |
| `README.md`, `docs/PIPELINE.md`, `CHANGELOG.md`, `REPRODUCIBILITY.md`, `PUBLIC_CODE_RELEASE_MANIFEST.md`, `SECURITY_AND_DATA_GOVERNANCE_SCAN.md`, the `docs/audit/` directory | updated for the new layout, paths and version framing |
| `RELEASE_CHECKSUMS_SHA256.txt` | regenerated: 61 entries |

## 5. What was deliberately NOT done

* **No new analytical version.** The analytical and publication version remains **v1.1.0**.
  This pass is repository packaging only.
* No database was queried; no analysis was run; `FINAL_MODEL_V2` was not refitted.
* No cohort, phenotype rule, eligibility criterion, predictor, aggregation rule, imputation
  rule, coefficient or reported number was changed.
* `config/final_analysis_config.py` was not modified and its hash is unchanged.
* No upload to GitHub. No upload to Zenodo. No licence chosen on the authors' behalf. No
  ORCID iD invented.

## 6. Remaining author actions

1. **Close the manuscript wording item.** `docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`
   records five sentences in the manuscript pair that still assert or presuppose the removed
   model's uniform-shift claim, with line numbers and minimal replacements. The manuscripts
   are not part of this repository and were not modified here. No hierarchical *number*
   survives in them — only the qualitative claim.
2. Choose a software licence, then add `license:` to `CITATION.cff`.
3. Create the GitHub repository, then add `repository-code:`.
4. Archive a release on Zenodo, then add `identifiers:` with the bare DOI.
5. Confirm the CRediT roles and the ethics-committee statement (unchanged items).
