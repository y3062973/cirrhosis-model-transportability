# PUBLIC CODE RELEASE MANIFEST

**Release:** v1.1.0
**Publication / code release verified against:** `PROJECT1_FINAL_MANUSCRIPT_v1.1.0`
**Frozen primary-analysis configuration:** `FINAL_v1.0.0` -- unchanged. The primary model
was not changed, so its configuration version string was deliberately left alone; editing
it would change the frozen configuration hash. See the "Version strings" section of
`CHANGELOG.md`.
**Files:** 62 (including this manifest)
**Total size:** 719,175 bytes

Every file in the release is listed below with its SHA-256 and whether it contains
patient-level or stay-level data. **No file contains such data.** Aggregate model
coefficients and publication-level summary statistics are permitted and are marked
`NO (aggregate)`.

`RELEASE_CHECKSUMS_SHA256.txt` covers every file listed below except itself, which cannot
contain its own hash. It is also written inside the ZIP, so the archive is
self-verifying.

| # | path | purpose / content | contains data? | bytes | SHA-256 |
|---|---|---|---|---|---|
| 1 | `.env.example` | placeholder environment variables; no real credential | NO | 542 | `5c2251e31867389f3291439d0dd43a3bb63b02ab0e19bdbd2103405c1d87bb56` |
| 2 | `.gitignore` | blocks credentials, dumps, and any CSV/XLSX holding rows | NO | 1,236 | `344d4aae8e6aba0373f2f87390cf98dfdaa1ab6e2feb2eaca3962f4de20d3fa3` |
| 3 | `CHANGELOG.md` | version history, the removal decision, what is excluded by design | NO | 11,347 | `8a81e8108368b7589016e896aecfe4a6125a3cc0e312b96cf288f67e615c82d9` |
| 4 | `CITATION.cff` | citation metadata; CFF 1.2.0-valid; DOI and URL deliberately omitted rather than faked | NO | 3,005 | `af8e65dc6ae2e1672d731e47be557becb64bd4b0fd8ce54e017d0779c999a2f2` |
| 5 | `DATA_ACCESS.md` | how to obtain the three databases; data-governance rules | NO | 3,125 | `bedfc40c861c1e26ea866897d063fd2095cacd2eeeb521adeb3e186a6ae6dc98` |
| 6 | `LICENSE_PENDING.txt` | states that no licence has been chosen and why that matters | NO | 1,925 | `1d170c06dc45e846107227f89e3b94237801fcac6ae7f8447f088d3f0e56fcd8` |
| 7 | `MODEL_SPECIFICATION.md` | the locked model: formula, coefficients, units, aggregation | NO | 3,988 | `ca7ffc933c664ba020cb2f644c9962152b669bdec5db8aad22d68e4c3a7eabd4` |
| 8 | `PIPELINE_PATH_AUDIT.md` | the shared-path repair: the defect, the new layout, the stage-by-stage resolution table, the hand-off verification and the verdict | NO | 9,768 | `01eb9ce2f1ada0ea643c80d5e90e0c4ba9b4238609fcf6821c5571a195f12e85` |
| 9 | `PUBLIC_CODE_RELEASE_MANIFEST.md` | this manifest | NO | -- | SELF -- a file cannot record its own SHA-256 |
| 10 | `PUBLIC_REPOSITORY_FINAL_AUDIT.md` | final audit report: gate results, the shared-path repair, the security scan, the checksum arithmetic and the verdict | NO | 15,218 | `e3a2bfbb84fb5dec848e66f4399683af7e5ff1f86b0ef265c88681b385397994` |
| 11 | `README.md` | entry point: purpose, data statement, runnable-vs-restricted labels, reproduction order, governance | NO | 16,844 | `2d8437d65694e2348ea053abb686d27b4b2162f2e371d19a65adc42cc7db7622` |
| 12 | `RELEASE_CHECKSUMS_SHA256.txt` | SHA-256 of every other file in the release; does not hash itself | NO | -- | SELF -- a file cannot record its own SHA-256 |
| 13 | `REPRODUCIBILITY.md` | determinism, verification performed, the removed analysis, environment | NO | 4,724 | `afedd4dfc37670b5fde65fcca73d25b4ae815aed36484cf3a125188f728d1325` |
| 14 | `SECURITY_AND_DATA_GOVERNANCE_SCAN.md` | security and data-governance scan report, with a note where filenames have since changed | NO | 69,372 | `bd11e596cca6e578fb5c5057ce9bad32e0720504919551d97185086ecec83d3f` |
| 15 | `archive/nonproduction/README.md` | why a rejected implementation is archived, and that it must not be run | NO | 3,531 | `87982517857a4bd7f6b67334ae6c3038c66191fd6e1a34055a8d4c965264d239` |
| 16 | `archive/nonproduction/hierarchical_calibration_rejected_historical.py` | **HISTORICAL IMPLEMENTATION -- NOT USED IN THE FINAL MANUSCRIPT -- DO NOT USE FOR INFERENCE.** The rejected model, disabled and non-executable | NO | 30,490 | `e3a679c73ce4ee28a633499ff501870b63edb9cac654996896b05be2527da31d` |
| 17 | `config/final_analysis_config.py` | the frozen analysis configuration (`FINAL_v1.0.0`, unchanged) | NO | 12,305 | `e59a2e2bea4c03dbea23da4e61364a67752e5c5dfafb395be56db6816c5148e6` |
| 18 | `docs/DATABASE_SETUP.md` | expected schema and the MIMIC-IV version note | NO | 2,005 | `5657783f9cd0fb0787681fbe7159f1fd7932013c76e689d05415625a7ef81122` |
| 19 | `docs/PIPELINE.md` | run order with inputs, outputs and the access each step needs per step | NO | 8,188 | `8445ed64f953791c141a9a63ada8f2a573b6c2aabfb9dbe2f5d1fa8152e00778` |
| 20 | `docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` | **OPEN ITEM**: manuscript sentences still asserting the removed model's uniform-shift claim, with line numbers and minimal replacements | NO | 9,095 | `6dc0ec2e68c57d471da000c8dba105ca0301534c3e4a363e5ceb184751e23c4d` |
| 21 | `docs/audit/CODE_INVENTORY.md` | provenance of each published file against the internal working tree | NO | 6,819 | `db86607c09bb506cb3a17b8fd5a73d5a240e863fe4b4f3e651008511e9ff8863` |
| 22 | `docs/audit/EXCLUDED_FILES_REVIEW.md` | what was withheld from the release and why | NO | 4,924 | `24f0920733c271b0fb43fdb318b029c3dd76dee036be73bbf491b50b5b259f46` |
| 23 | `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` | the four-way comparison and the decision rule that removed the model | NO (aggregate) | 11,227 | `71cf47fcda1a4704cc41d110034f9b0c489320fd988ef51b6f4dfcd54d1877c7` |
| 24 | `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` | the first defect: the optimiser returned the slope at its starting value | NO (aggregate) | 13,729 | `8ed6899ad756fce04ed2c14b3441b8a4c419e0bd99f174f39040fa359da5bc76` |
| 25 | `docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md` | the mathematics: the omitted Gaussian prior normalisation | NO (aggregate) | 14,247 | `39ba6b0f8012676085e75d1be0c0506b31f3a80f0093b68fd90ff48457d50209` |
| 26 | `docs/audit/LOCKED_RELEASE_CODE_VERIFICATION.md` | file-by-file comparison of the published code against the frozen release | NO | 14,039 | `83a0bf53de4c7a3dad47004ef0666c817d42374986187c1392b100bf44e72d14` |
| 27 | `docs/audit/PUBLICATION_LOCK_v1.1.0.md` | release-level record: what changed, what did not, what was removed (one item OPEN) | NO (aggregate) | 7,246 | `92cacdbfccbda89b6ed0ee688476629ac07e1013c2dca1595d113030c72e5aa6` |
| 28 | `docs/audit/README.md` | how to read the audit trail, and what may and may not be concluded | NO | 6,092 | `f84913052fa476667dd7d4f173e541b404dff013a0f0194454d01ce1d31efb8a` |
| 29 | `environment.yml` | conda environment | NO | 362 | `be88f3266df8204adeec6f33223a6bccaa247cbab649be5745648e5519ebcaef` |
| 30 | `internal_audit/README.md` | why the internal release-audit scripts cannot run in a clean clone, and how they were adapted for v1.1.0 | NO | 4,046 | `ba388d790eda234a743fe1c7a6e1cdc29ffb549ab5ffe3f2f842c7db54a56d2f` |
| 31 | `metadata/model_coefficients.csv` | model coefficients (aggregate, published in the manuscript as Table 2) | NO (aggregate) | 722 | `bcabb99a5472fa8f32b6f17cc5a62e5c0a1facb978cc424eda4df505277fc1e7` |
| 32 | `metadata/phenotype_codes.csv` | ICD code prefixes and admission counts at code level (no patient rows) | NO (aggregate) | 497 | `787962df0bcd648bcbffcb43e763de069457df409decc1380310f5df1740c6bf` |
| 33 | `metadata/predictor_definitions.csv` | predictor list, aggregation rule and missing-indicator flag (definitions only) | NO (aggregate) | 41 | `b50ec0c9a28c06a3a55c1c12c55bb4d5c3db987722484dc0b6b3d39847c22bbf` |
| 34 | `pipeline_path_audit.py` | runnable audit of the above: extracts and executes each script's path block only, then AST-parses every stage for the artefacts it reads and writes | NO | 14,357 | `fdca19bad017a25d269f00c20a1653d604e34d6e016b08ae9d93bb54a4b05aa9` |
| 35 | `requirements.txt` | pinned dependency versions | NO | 339 | `0f178214b7cdcf6c545355970d2583fe247fcff5f7e16a64e6d284d1277d71b3` |
| 36 | `src/clinical_scores/clinical_scores.py` | MELD, MELD-Na, ALBI and FIB-4 construction on identical ICU stays | NO | 26,061 | `50aaeb671b4ecbb270c082095e200310c0fff4306e1ae9ff4984a8b7820f50ee` |
| 37 | `src/clinical_scores/meld_component_audit.py` | audit of the MELD component extraction against the source databases | NO | 10,609 | `6e3d9919e8909f2c189c603942dc5dcbb6642fec57494c9834dee8afe222967c` |
| 38 | `src/clinical_scores/paired_score_comparison.py` | paired score comparison with hospital-cluster bootstrap differences | NO | 16,382 | `0b0715cf2206ab72d63521918bd3bb0afe0775869b907cc8ed35b0e325165c8b` |
| 39 | `src/db.py` | environment-based, read-only database connection | NO | 2,320 | `d2b3bbf95022669859911e788a7af48b760057575058abf978924ff7643769e0` |
| 40 | `src/manuscript_qa/claim_compliance.py` | claim-lock compliance: the manuscript must not assert what the analysis does not support | NO | 10,182 | `82a5a8eba60889acd884b2ad6ba8c3e1b151ba509bb058441fa1953ccf6d2cee` |
| 41 | `src/manuscript_qa/language_pass.py` | overstatement scan, distinguishing a term used from one that is negated | NO | 8,544 | `405fa7ecead066fd1dcefe718ce06b7d9b088a69aad786f0984dbff23add19a1` |
| 42 | `src/manuscript_qa/number_audit.py` | traces every number in the manuscript narrative to a locked artefact | NO | 11,642 | `c3a2cf36030f61cdb5e21a0cb0148cf2e10fbd2d5f6ebdb26ad0e559cff5beb1` |
| 43 | `src/manuscript_qa/reference_audit.py` | reference integrity: unresolved, uncited, missing and duplicate references | NO | 14,002 | `c2075bba48ed4e480a4ce4fd265a40dfc8701253b89f4b37ec264a0ce35a5b98` |
| 44 | `src/manuscript_qa/semantic_unit_audit.py` | unit audit: ICU stays versus patients versus hospitals | NO | 12,239 | `6edba70d7d6f9a40073e9d0da4d4261573a48610b7ea28fe20e13518745187f4` |
| 45 | `src/phenotype/build_cohorts.py` | rebuild all three cohorts under the frozen phenotype, including the extraction queries | NO | 14,391 | `9ef4af5f5e393ebd93d7284162a41a4a3355992542fa1f5cba4eefcde0fba70b` |
| 46 | `src/phenotype/cohort_composition.py` | cohort code composition and the strict-versus-broad phenotype sensitivity | NO | 13,150 | `e237452097e0599b6edca6cbc9fafd679bec7382037855a9ea758a7d80abe343` |
| 47 | `src/phenotype/phenotype_audit.py` | strict cirrhosis phenotype construction and audit of the code prefixes | NO | 12,799 | `abf4881828d030ed9f1cdb4d96d71c57b2c038f7b451f8db8c1e14b1305f26eb` |
| 48 | `src/preprocessing/build_dataset_and_model.py` | 0-24 h predictor extraction, aggregation, plausibility filtering, imputation, and the fitting of `FINAL_MODEL_V2` | NO | 21,651 | `2eb216bd72f21d6f69364809f2adca27bbc80249e081044758054c36f7930dce` |
| 49 | `src/provenance.py` | provenance stamping and the primary metric primitives | NO | 8,213 | `a4054e3b106b24d82c500028fa5e7670035ec99465e7e370d716fe70660abad8` |
| 50 | `src/repo.py` | THE single source of truth for repository paths: resolves the repository root from its own location and defines DATA / OUTPUTS / TABLES / FIGURES / LOGS so that every stage shares one root | NO | 6,030 | `9dca243616cd7cf682c1483728d98bb9b9d687c1e7a6abbe9f894ae798cf3038` |
| 51 | `src/reporting/final_release_check.py` | internal release gate: asserts the removed hierarchical sheets are **absent**; needs restricted artefacts | NO | 13,668 | `341464af4b0490370245d31c3f9a05034be499fba13e0aafaae94fb6b95f0e92` |
| 52 | `src/reporting/release_verification.py` | internal checksum/manifest verification; needs an internal artefact-checksum file | NO | 2,141 | `c80dc474a4171e4dc384a7d4a5a95892d45298d92fd18ebdbd6223f4107938ba` |
| 53 | `src/reporting/tables_and_figures.py` | generation of the released tables and figures; Figure 5 panel B is the per-hospital O/E ratio | NO | 27,386 | `e5074704f5ecd9368058dcf7fbf405e311469b01fa4c7731227e245c22175fc8` |
| 54 | `src/validation/hospital_analysis_and_recalibration.py` | **retained hospital-level analyses only**: per-hospital descriptive performance, random-effects AUROC meta-analysis, descriptive hospital-level summaries, leave-one-hospital-out recalibration. No mixed-effects fitting | NO | 17,721 | `7fe726f0a8bc9cb7d98f08f5d97584655f9edf391b2e307975dbf2cb39ec05fb` |
| 55 | `src/validation/primary_validation.py` | primary validation metrics, patient-level bootstrap optimism correction, recalibration | NO | 17,452 | `dd085feed2b63ad376986a8594b635ff2cc151dd01c06bb9b151a3c22b75fb55` |
| 56 | `src/validation/publication_lock.py` | internal publication lock: primary metrics and the locked analysis record; needs restricted artefacts and a read-only eICU connection | NO | 23,518 | `1c7bc6a7fc991648ec591419926828c3c3a7c29026d1d6381f5bbfc3b7787b72` |
| 57 | `src/validation/validation_and_sensitivity.py` | external validation, the 0-6 h window, the 24-hour landmark analysis, the MAP, missing-data and first-admission sensitivities | NO | 26,890 | `121dc3bc80700432026a38c9721e039a69473d13621f0368f7ef4974889d02bd` |
| 58 | `tests/fault_injection/fault_injection_suite.py` | fault-injection suite over synthetic fixtures; needs no database | NO | 10,981 | `e0e2b1525149961cf680c7079f3754695e1accad5f0af1299ffbc520c2667533` |
| 59 | `tests/known_answer/README.md` | how the known-answer tests work and that they are synthetic | NO | 1,296 | `bda9761fbacc53a9627b66a7c7ea0b414d966351869a3d455dbe1eace02c213b` |
| 60 | `tests/metric_validation/README.md` | how the independent metric verification works, and how to run it | NO | 637 | `8bedbf7d028b517ed366760099a929e3fbbaff2129d9bc99fe7d510161f12352` |
| 61 | `tests/metric_validation/independent_metrics_and_verification.py` | second, independent implementation of every performance metric; needs no database | NO | 16,072 | `9db792f0de639369f1a5973d874d2417aa1e37199217a0aafdf37a1019d4557d` |
| 62 | `verify_public_release.py` | **public-safe verifier**: checksums, required files, compilation, restricted-data scan, documentation references. Needs no database and no patient-level data | NO | 43,640 | `68ccad6d2e9f463b9291122e3e4c07323a8063c8406be6729d24579883c73a5c` |

**Note on rows 8 and 10 -- the exact arithmetic.** These two files carry the literal
marker `SELF` in the hash column, because a file cannot record its own SHA-256: writing
the hash changes the file. Therefore:

* **62 files** make up the release;
* **61 of them are covered by `RELEASE_CHECKSUMS_SHA256.txt`**, because the checksum file
  cannot hash itself;
* the manifest lists **all 62** rows, of which **2** (its own row and the checksum
  file's row) record `SELF`.

`verify_public_release.py` enforces exactly this: it re-hashes every one of the 61
covered files, asserts the two `SELF` rows are the only non-hash rows, asserts the
manifest lists every shipped file, and cross-checks the manifest against the checksum
manifest so the two cannot drift apart.

## Data-content audit

- files containing patient-level or stay-level data: **0**
- files containing aggregate, non-identifying values: 7 (3 metadata tables and 4 audit
  documents that quote model-level or aggregate statistics)
- Python files: 28 (all compile)
- documentation files: 24
- aggregate CSV files: 3
- other files (config, environment, licence notice, checksums): 7

Re-checked on every run by `verify_public_release.py`, which scans for per-row
clinical tables, patient or stay identifier columns, credential literals, `.env` files and
credentialed connection strings. It reports 0 findings.

## What is deliberately absent

- the three source databases and every extract of them
- the derived analysis dataset and the predictions file
- any CSV or XLSX holding a row per patient or per ICU stay (the only tabular files are the
  three aggregate metadata files under `metadata/`)
- notebooks, logs, cached SQL output and database dumps
- the manuscript, tables and figures as documents
- credentials, `.env` files, keys and connection strings
- superseded and development-phase analysis scripts
- **the removed hierarchical calibration model as an executable pipeline step**: the
  rejected implementation is archived, disabled and clearly marked, and no hierarchical
  numerical result is part of this release

The itemised exclusion list with a reason per file is in
`docs/audit/EXCLUDED_FILES_REVIEW.md`.

## Verification performed

Run `python verify_public_release.py` to reproduce all of this. It needs no database
access and no patient-level data.

| check | result |
|---|---|
| every file's SHA-256 matches the checksum manifest | 61/61 |
| the manifest covers every shipped file | yes |
| every required file present | 62/62 |
| every removed or restricted path absent | 8/8 |
| every Python file compiles | 28/28 |
| no UTF-8 BOM in any source | yes |
| the archived rejected implementation is inert | yes |
| no restricted data shipped | 0 findings |
| every documented repository file path resolves | **0 broken** of 381 checked |
| `PUBLIC_CODE_RELEASE_MANIFEST.md` covers the same files as the checksum manifest | yes |
| `PUBLIC_CODE_RELEASE_MANIFEST.md` lists every shipped file | 62/62 |
| `PUBLIC_CODE_RELEASE_MANIFEST.md` sizes and hashes match the tree | yes |
| `CITATION.cff` structurally valid, no fake DOI or URL | yes |

20 checks across 8 groups; the run prints each one individually and exits non-zero on any
failure, so it can gate publication in CI.

References to internal working-tree files that intentionally do not resolve (generator
scripts the audit record names, internal origin filenames, and the excluded categories) are
listed individually in the verifier's `NON_RESOLVING` map, each with a stated reason, so
that the "0 broken" figure cannot be reached by ignoring a real broken link.

## One open item, recorded here because it is not a code matter

Five sentences in the manuscript pair still assert or presuppose the removed model's
uniform-shift claim. **The manuscripts are not part of this repository** and were not
modified by this packaging pass, so the code release cannot fix them; it records them in
`docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` with line numbers and minimal
replacements. `docs/audit/PUBLICATION_LOCK_v1.1.0.md` marks the corresponding rows **OPEN**.
