# SECURITY AND DATA-GOVERNANCE SCAN

> **Note added at release v1.1.0 packaging.** This scan is a **snapshot taken while the
> release was being assembled**, against the then-current tree. Its findings and its
> verdict still stand, but some *filenames* it mentions have since changed, and it is
> re-published here unedited rather than silently rewritten:
>
> | the scan says | the file is now |
> |---|---|
> | the audit implementation note under `docs/` | `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` -- same basename, moved into `docs/audit/`; see row 21 of `PUBLIC_CODE_RELEASE_MANIFEST.md` |
> | `src/validation/hierarchical_calibration.py` | removed; the rejected implementation is archived at `archive/nonproduction/hierarchical_calibration_rejected_historical.py` and the retained analyses are in `src/validation/hospital_analysis_and_recalibration.py` |
> | the release directory `project1_cirrhosis_transportability_code_release/` | this directory, `project1_cirrhosis_transportability_code_release_v1.1.0/` |
> | the internal assembler `build_code_release.py` | an internal packaging script; not shipped |
>
> The counts below (files scanned, lines, hits) describe that snapshot. For the **current**
> state, run `verify_public_release.py`, which re-checks checksums, required files,
> compilation, restricted-data absence and documentation references against the tree as
> shipped, and reports its own counts.

**Scope:** every file in `project1_cirrhosis_transportability_code_release/`.

**Files scanned:** 42 text files (4 binary or skipped).

## How findings are classified

A scan that flags every occurrence of the word `password` produces noise and teaches the reader to ignore it. This scan separates three kinds of hit:

| kind | meaning | fatal? |
|---|---|---|
| **VALUE** | an actual secret or identifier value | **YES** |
| **PATH** | a local filesystem path, username or network address | **YES** |
| **NAME** | a column name, an environment-variable reference, or the word in prose | no, recorded |

`subject_id` is a legitimate column name in extraction code. It becomes a leak only when a numeric value is assigned to it, which is what the VALUE patterns look for.

## Findings

| kind | file | line | pattern | matched text | note |
|---|---|---|---|---|---|
| NAME | `CHANGELOG.md` | 40 | credential word in prose | `credential` | The word, in documentation explaining that no secret is stored. |
| NAME | `PUBLIC_CODE_RELEASE_MANIFEST.md` | 12 | credential word in prose | `credential` | The word, in documentation explaining that no secret is stored. |
| NAME | `src/clinical_scores/clinical_scores.py` | 38 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/clinical_scores/clinical_scores.py` | 166 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 168 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 168 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 169 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 174 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 175 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 177 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 178 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 179 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 180 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 183 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 184 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 185 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 201 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 202 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 205 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 206 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 220 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 222 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 222 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 223 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 229 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 230 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 234 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 235 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 283 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 283 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 421 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 422 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 428 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 429 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 430 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 430 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 430 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/clinical_scores.py` | 459 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/meld_component_audit.py` | 39 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/clinical_scores/meld_component_audit.py` | 84 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/meld_component_audit.py` | 89 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/meld_component_audit.py` | 207 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/meld_component_audit.py` | 210 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 47 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 47 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 56 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 74 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 75 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 78 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 79 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 183 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 185 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 185 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 186 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 191 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 192 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 194 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 195 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 199 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 200 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 201 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 202 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/clinical_scores/paired_score_comparison.py` | 203 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/db.py` | 4 | credential word in prose | `password` | The word, in documentation explaining that no secret is stored. |
| NAME | `src/db.py` | 9 | credential word in prose | `password` | The word, in documentation explaining that no secret is stored. |
| NAME | `src/db.py` | 24 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 42 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 43 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 45 | credential word in prose | `password` | The word, in documentation explaining that no secret is stored. |
| NAME | `src/db.py` | 47 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 57 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 61 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/db.py` | 65 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/manuscript_qa/number_audit.py` | 207 | credential word in prose | `token` | The word, in documentation explaining that no secret is stored. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 8 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 9 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 9 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 10 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 10 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 38 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 38 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 39 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 39 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 47 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 62 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 71 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 85 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 87 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 89 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 148 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 176 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/manuscript_qa/semantic_unit_audit.py` | 177 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 40 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/phenotype/build_cohorts.py` | 78 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 82 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 93 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 93 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 93 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 94 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 95 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 97 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 97 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 97 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 101 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 101 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 102 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 102 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 105 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 105 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 105 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 133 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 167 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 176 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 208 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 208 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 213 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 225 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 225 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 228 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 230 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 230 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 231 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 231 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 231 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 233 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 233 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 233 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 234 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 237 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 237 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 239 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 263 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 285 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/build_cohorts.py` | 287 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 27 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/phenotype/cohort_composition.py` | 52 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 53 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 112 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 116 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 121 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 131 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 134 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 143 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 146 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 161 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 165 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 168 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 198 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/cohort_composition.py` | 201 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/phenotype_audit.py` | 35 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/phenotype/phenotype_audit.py` | 161 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/phenotype_audit.py` | 162 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/phenotype_audit.py` | 173 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/phenotype/phenotype_audit.py` | 173 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 43 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 86 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 99 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 102 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 102 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 103 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 109 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 112 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 115 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 115 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 116 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 122 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 138 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 138 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 138 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 144 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 144 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 146 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 146 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 148 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 148 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 149 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 150 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 158 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 173 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 183 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 204 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 226 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 226 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 228 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 228 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 229 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 230 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 231 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 232 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 233 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 235 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 236 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 241 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 242 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 250 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 258 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 261 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 261 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 262 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 268 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 271 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 274 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 274 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 275 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 281 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 302 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 302 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 304 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 304 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 305 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 307 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 307 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 308 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 308 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 309 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 310 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 311 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 312 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 321 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 321 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 321 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 421 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 421 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/preprocessing/build_dataset_and_model.py` | 421 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/final_release_check.py` | 69 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/final_release_check.py` | 69 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 52 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 52 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 55 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 56 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 104 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 104 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/reporting/tables_and_figures.py` | 230 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/validation/hierarchical_calibration.py` | 78 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/hierarchical_calibration.py` | 78 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/hierarchical_calibration.py` | 502 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/hierarchical_calibration.py` | 502 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 50 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 50 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 154 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 166 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 173 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/validation/primary_validation.py` | 252 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 253 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 257 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 258 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 259 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/primary_validation.py` | 262 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 63 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 63 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 147 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 149 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 155 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 156 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 159 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 159 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 160 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 238 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 239 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 240 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 248 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 248 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 256 | identifier used as a column name | `subject_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/publication_lock.py` | 256 | identifier used as a column name | `uniquepid` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 33 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `src/validation/validation_and_sensitivity.py` | 180 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 181 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 205 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 206 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 216 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 217 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 274 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 278 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 280 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 280 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 281 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 286 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 288 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 290 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 290 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 291 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 296 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 297 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 299 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 299 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 301 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 301 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 304 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 304 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 306 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 317 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 326 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 327 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 330 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 330 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 333 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 333 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 334 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `src/validation/validation_and_sensitivity.py` | 337 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 55 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 56 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 56 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 109 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 110 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 111 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 116 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 199 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/fault_injection/fault_injection_suite.py` | 199 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 31 | environment variable reference | `os.environ` | An environment lookup: the correct pattern. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 52 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 52 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 150 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 151 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 152 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 179 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 182 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 185 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 185 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 186 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 192 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 197 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 209 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 214 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 217 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 217 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 223 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 223 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 225 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 232 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 265 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 265 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 270 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 277 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 277 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 278 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 296 | identifier used as a column name | `stay_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |
| NAME | `tests/metric_validation/independent_metrics_and_verification.py` | 296 | identifier used as a column name | `hadm_id` | A column NAME. Legitimate in extraction code; only a VALUE would be a leak. |

## Resolution of each class

**VALUE findings: 0.** None. No password, token, key or identifier value appears anywhere in the release.

**PATH findings: 0.** None. No absolute path, username or private network address appears. The sanitiser rewrites local paths to `.` and the credentials module reads the host from the environment.

**NAME findings: 337.** Permitted and expected. They are concentrated in three places, each of which is the correct pattern rather than a defect:

- `src/db.py` and `.env.example` document the environment variables and state that no credential is stored in the repository;
- the extraction scripts read identifiers such as `subject_id` as **column names** in SQL, with no values;
- `DATA_ACCESS.md` and `README.md` tell contributors not to commit credentials or data.

## Credential sanitiser

The working tree contained hardcoded local credentials in the database connection idiom used across the pipeline:

```python
PG = dict(host="127.0.0.1", port=5432, user="postgres", password="<literal>",
             connect_timeout=20)
c = psycopg2.connect(**{**PG, "dbname": db})
```

Every published file was rewritten by `build_code_release.py` so that this becomes an environment lookup through `src/db.py`:

```python
PG = dict(connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")))
c = db.connect(db)   # credentials from DB_USER / DB_PASSWORD / DB_HOST
```

The build **fails** if any credential pattern survives into an output file, so a silent partial sanitisation is impossible. `src/db.py` opens every session read-only, which also documents that no query in this release writes.

## Data files

The only tabular files in the release are the allowlisted aggregate metadata:
- `metadata/model_coefficients.csv`
- `metadata/phenotype_codes.csv`
- `metadata/predictor_definitions.csv`

These contain model coefficients, phenotype code prefixes and predictor definitions. None contains a row per patient or per stay, and none can identify an individual. **No CSV or XLSX holding patient or stay rows is present.**

## Files scanned

| file | status | chars |
|---|---|---|
| `.env.example` | scanned | 542 |
| `.gitignore` | scanned | 1,236 |
| `CHANGELOG.md` | scanned | 4,550 |
| `CITATION.cff` | scanned | 1,691 |
| `DATA_ACCESS.md` | scanned | 3,125 |
| `LICENSE_PENDING.txt` | scanned | 1,925 |
| `MODEL_SPECIFICATION.md` | scanned | 3,988 |
| `PUBLIC_CODE_RELEASE_MANIFEST.md` | scanned | 9,282 |
| `README.md` | scanned | 5,369 |
| `RELEASE_CHECKSUMS_SHA256.txt` | scanned | 4,408 |
| `REPRODUCIBILITY.md` | scanned | 2,901 |
| `SECURITY_AND_DATA_GOVERNANCE_SCAN.md` | skipped (this report) | 0 |
| `environment.yml` | scanned | 362 |
| `requirements.txt` | scanned | 339 |
| `config/final_analysis_config.py` | scanned | 12,305 |
| `docs/DATABASE_SETUP.md` | scanned | 2,005 |
| `docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` | scanned | 10,334 |
| `docs/PIPELINE.md` | scanned | 2,471 |
| `metadata/model_coefficients.csv` | binary/skipped | 0 |
| `metadata/phenotype_codes.csv` | binary/skipped | 0 |
| `metadata/predictor_definitions.csv` | binary/skipped | 0 |
| `src/db.py` | scanned | 2,320 |
| `src/provenance.py` | scanned | 8,315 |
| `src/clinical_scores/clinical_scores.py` | scanned | 25,988 |
| `src/clinical_scores/meld_component_audit.py` | scanned | 9,983 |
| `src/clinical_scores/paired_score_comparison.py` | scanned | 16,146 |
| `src/manuscript_qa/claim_compliance.py` | scanned | 9,705 |
| `src/manuscript_qa/language_pass.py` | scanned | 8,150 |
| `src/manuscript_qa/number_audit.py` | scanned | 11,364 |
| `src/manuscript_qa/reference_audit.py` | scanned | 13,654 |
| `src/manuscript_qa/semantic_unit_audit.py` | scanned | 11,929 |
| `src/phenotype/build_cohorts.py` | scanned | 14,112 |
| `src/phenotype/cohort_composition.py` | scanned | 12,606 |
| `src/phenotype/phenotype_audit.py` | scanned | 12,216 |
| `src/preprocessing/build_dataset_and_model.py` | scanned | 21,513 |
| `src/reporting/final_release_check.py` | scanned | 12,321 |
| `src/reporting/release_verification.py` | scanned | 1,626 |
| `src/reporting/tables_and_figures.py` | scanned | 26,969 |
| `src/validation/hierarchical_calibration.py` | scanned | 25,177 |
| `src/validation/primary_validation.py` | scanned | 17,258 |
| `src/validation/publication_lock.py` | scanned | 22,334 |
| `src/validation/validation_and_sensitivity.py` | scanned | 26,835 |
| `tests/fault_injection/fault_injection_suite.py` | scanned | 10,705 |
| `tests/known_answer/README.md` | scanned | 434 |
| `tests/metric_validation/README.md` | scanned | 357 |
| `tests/metric_validation/independent_metrics_and_verification.py` | scanned | 15,816 |

## Verdict

> # SAFE FOR AUTHOR REVIEW

No credential value, no identifier value, no local path, no username and no network address appears anywhere in the release. The only tabular files are aggregate metadata that cannot identify an individual. The release is safe for the author to inspect, and safe to upload to a **private** repository.

This verdict covers the RELEASE DIRECTORY only. It is not a statement that the source working tree is clean of credentials, and it is not a licence to publish the working tree.
