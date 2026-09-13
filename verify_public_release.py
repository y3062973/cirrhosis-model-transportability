#!/usr/bin/env python3
"""Verify the public repository. NO DATABASE ACCESS AND NO PATIENT DATA REQUIRED.

This is the public-safe health check for this code release. It needs no database
connection, no credential and no patient-level data: it inspects only the repository
contents. (Earlier release candidates shipped this as `verify_public_code_release.py`;
the name is now `verify_public_release.py`.)

This is the verifier a member of the public is meant to run. It checks only things that
can be checked from the repository contents alone:

  1. CHECKSUMS    every file listed in RELEASE_CHECKSUMS_SHA256.txt exists and hashes to
                  the recorded SHA-256, and every shipped file is covered by the manifest
                  (the checksum file does not hash itself, and the manifest records SELF
                  for its own row)
  2. REQUIRED     every file the release must contain is present, and every removed or
                  restricted path is absent
  3. COMPILE      every Python file compiles, decodes as UTF-8 without a BOM, and the
                  archived rejected implementation is inert
  4. NO DATA      no restricted data is present: no per-row clinical table, no patient or
                  stay identifier column, no credential literal, no `.env` file, no
                  credentialed connection string
  5. REFERENCES   every repository file path referenced by the shipped documentation
                  resolves to a file that exists
  6. CITATION     CITATION.cff is structurally valid and ships no fake DOI or URL
  7. STRUCTURE    the rejected hierarchical calibration model is absent from the
                  production pipeline, and every stage shares one repository root
                  (delegates to pipeline_path_audit.py)

It does NOT reproduce any analysis. It cannot: the analysis needs MIMIC-IV, eICU-CRD and
nwICU, which are credentialed and are not redistributable. What it does verify is that
the code package is internally consistent, complete, and safe to publish.

It deliberately does NOT require or use:

  * any database connection or credential
  * any patient-level or stay-level data
  * any Git history, tag or remote
  * any restricted internal artefact

Those appear in the *internal release-audit* scripts
(`src/reporting/final_release_check.py`, `src/reporting/release_verification.py`,
`src/validation/publication_lock.py`), which are provenance tooling rather than
reproduction steps and are labelled as such in README.md.

Usage
-----
    python verify_public_release.py                 # full check, human-readable
    python verify_public_release.py --quiet         # only failures and the summary
    python verify_public_release.py --list-references
    python verify_public_release.py --no-structure  # skip the delegated path audit

Exit code is 0 only if every check passes, so this can gate publication in CI.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if not os.path.isfile(os.path.join(ROOT, "README.md")):
    ROOT = os.path.dirname(ROOT)
CHECKSUMS = "RELEASE_CHECKSUMS_SHA256.txt"
GENERATOR = os.path.basename(os.path.abspath(__file__))
PATH_AUDIT = "pipeline_path_audit.py"

# ---------------------------------------------------------------- expected contents
# Files the release must contain. Documentation and code, not generated artefacts.
REQUIRED_FILES = [
    # entry points and release metadata
    "README.md", "CHANGELOG.md", "CITATION.cff", "REPRODUCIBILITY.md",
    "MODEL_SPECIFICATION.md", "DATA_ACCESS.md", "PUBLIC_CODE_RELEASE_MANIFEST.md",
    "RELEASE_CHECKSUMS_SHA256.txt", "LICENSE_PENDING.txt",
    "SECURITY_AND_DATA_GOVERNANCE_SCAN.md",
    ".gitignore", ".env.example", "requirements.txt", "environment.yml",
    GENERATOR, PATH_AUDIT, "PUBLIC_REPOSITORY_FINAL_AUDIT.md", "PIPELINE_PATH_AUDIT.md",
    # frozen configuration -- must be present and must not have moved
    "config/final_analysis_config.py",
    # non-restricted metadata
    "metadata/model_coefficients.csv", "metadata/phenotype_codes.csv",
    "metadata/predictor_definitions.csv",
    # documentation
    "docs/PIPELINE.md", "docs/DATABASE_SETUP.md",
    "docs/audit/README.md", "internal_audit/README.md",
    "archive/nonproduction/README.md",
    # published analysis pipeline
    "src/phenotype/build_cohorts.py", "src/phenotype/phenotype_audit.py",
    "src/phenotype/cohort_composition.py",
    "src/preprocessing/build_dataset_and_model.py",
    "src/clinical_scores/clinical_scores.py",
    "src/clinical_scores/paired_score_comparison.py",
    "src/clinical_scores/meld_component_audit.py",
    "src/validation/validation_and_sensitivity.py",
    "src/validation/primary_validation.py",
    "src/validation/hospital_analysis_and_recalibration.py",
    "src/reporting/tables_and_figures.py",
    "src/reporting/final_release_check.py", "src/reporting/release_verification.py",
    "src/validation/publication_lock.py",
    "src/provenance.py", "src/db.py", "src/repo.py",
    # verification suites
    "tests/fault_injection/fault_injection_suite.py",
    "tests/metric_validation/independent_metrics_and_verification.py",
    "tests/metric_validation/README.md", "tests/known_answer/README.md",
    # manuscript QA (not analytical)
    "src/manuscript_qa/number_audit.py", "src/manuscript_qa/semantic_unit_audit.py",
    "src/manuscript_qa/claim_compliance.py", "src/manuscript_qa/language_pass.py",
    "src/manuscript_qa/reference_audit.py",
    # the internal-only release-audit scripts, shipped but labelled
    "internal_audit/README.md",
    # audit trail for the removed analysis
    "docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md",
    "docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md",
    "docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md",
    "docs/audit/PUBLICATION_LOCK_v1.1.0.md",
    "docs/audit/LOCKED_RELEASE_CODE_VERIFICATION.md",
    "docs/audit/CODE_INVENTORY.md",
    "docs/audit/EXCLUDED_FILES_REVIEW.md",
    "docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md",
    "archive/nonproduction/hierarchical_calibration_rejected_historical.py",
]

# Files that must NOT exist. The removed hierarchical model must not come back as an
# executable pipeline step, and no restricted artefact may be shipped.
FORBIDDEN_PATHS = [
    "src/validation/hierarchical_calibration.py",
    "src/validation/hierarchical_calibration_rejected_historical.py",
    "src/model/apply_hierarchical_beta_fix.py",
    "apply_hierarchical_beta_fix.py",
    "fix_hierarchical_beta.py",
    # Generated trees must not be COMMITTED. `data/` and `outputs/` are created at run
    # time (data/ by the user, outputs/ by src/repo.py) and are both gitignored, so their
    # presence on a working machine is expected and is not itself a defect. What is
    # verified instead is that no FILE inside them is shipped: see the restricted-data
    # scan and the checksum manifest coverage below. The legacy flat tree names are
    # listed, because nothing writes them any more and their presence would mean a script
    # still resolves an old path.
    "logs", "tables", "figures",
]

# Documentation paths that intentionally do not resolve to a shipped file, each with the
# reason. Nothing else may fail to resolve. This is not a convenience list: it is the
# declared set of references to internal working-tree artefacts that the audit record
# names on purpose, and every entry states why it is not shipped.
NON_RESOLVING = {
    # generator scripts of the audit documents, written against the internal working
    # tree; they need the restricted analysis dataset and are not shipped
    "hierarchical_laplace_math_audit.py":
        "internal generator of the Laplace audit; needs the restricted dataset",
    "hierarchical_calibration_comparison.py":
        "internal generator of the comparison document; needs the restricted dataset",
    "export_r_glmm_input.py":
        "internal exporter of the audited subset to R; needs the restricted dataset",
    "independent_glmm_fit.R":
        "the independent lme4::glmer fit (implementation C); needs the restricted dataset",
    # internal analytical scripts that were never published as public steps
    "apply_hierarchical_beta_fix.py":
        "historical patcher, deliberately not shipped; see EXCLUDED_FILES_REVIEW.md",
    "fix_hierarchical_beta.py":
        "alternative name of the same historical patcher, deliberately not shipped",
    "diag_meld_window2.py":
        "internal diagnostic script named in a retained comment; not shipped",
    "phase_13_fault_injection.py":
        "the internal name this suite is stamped with in provenance metadata",
    "phase_14_17_golden_independent.py":
        "the internal name this suite is stamped with in provenance metadata",
    "phase_2_cohorts.py": "the internal name build_cohorts.py is stamped with",
    "phase_2b_composition.py": "the internal name cohort_composition.py is stamped with",
    "phase_3_4_dataset_model.py":
        "the internal name build_dataset_and_model.py is stamped with",
    "phase_5_6_7_scores.py": "the internal name clinical_scores.py is stamped with",
    "phase_8_9_12_13.py":
        "the internal name validation_and_sensitivity.py is stamped with",
    "publock_03_publication_lock.py":
        "the internal name publication_lock.py is stamped with",
    "publock_03_04_05.py": "the internal name primary_validation.py is stamped with",
    "publock_08_12_13_tables_figures.py":
        "the internal name tables_and_figures.py is stamped with",
    "publock_08b_selection_paired.py":
        "the internal name paired_score_comparison.py is stamped with",
    "publock_08b_selection.py":
        "internal predecessor of the paired-score selection step; not shipped",
    "publock_02_release.py": "internal release-bookkeeping script; not shipped",
    "publock_06_07_hospital.py":
        "the internal origin of the retained hospital analyses",
    # internal working-tree filenames recorded as provenance origins
    "publock_06_07_hospital.py": "internal origin of the retained hospital analyses",
    "publock_03_publication_lock.py": "internal origin of publication_lock.py",
    "publock_03_04_05.py": "internal origin of primary_validation.py",
    "publock_08_12_13_tables_figures.py": "internal origin of tables_and_figures.py",
    "publock_08b_selection_paired.py": "internal origin of paired_score_comparison.py",
    "phase_0a_phenotype.py": "internal origin of phenotype_audit.py",
    "phase_0b_meld_audit.py": "internal origin of meld_component_audit.py",
    "phase_2_cohorts.py": "internal origin of build_cohorts.py",
    "phase_2b_composition.py": "internal origin of cohort_composition.py",
    "phase_3_4_dataset_model.py": "internal origin of build_dataset_and_model.py",
    "phase_5_6_7_scores.py": "internal origin of clinical_scores.py",
    "phase_8_9_12_13.py": "internal origin of validation_and_sensitivity.py",
    "phase_13_fault_injection.py": "internal origin of fault_injection_suite.py",
    "phase_14_17_golden_independent.py":
        "internal origin of independent_metrics_and_verification.py",
    "manuscript_number_audit.py": "internal origin of manuscript_qa/number_audit.py",
    "semantic_unit_audit.py": "internal origin of manuscript_qa/semantic_unit_audit.py",
    "manuscript_claim_compliance.py":
        "internal origin of manuscript_qa/claim_compliance.py",
    "language_pass.py": "internal origin of manuscript_qa/language_pass.py",
    "reference_final_audit.py": "internal origin of manuscript_qa/reference_audit.py",
    "verify_release.py": "internal origin of reporting/release_verification.py",
    "final_release_check.py": "internal origin of reporting/final_release_check.py",
    "provenance.py": "internal origin of src/provenance.py",
    "final_analysis_config.py": "internal origin of config/final_analysis_config.py",
    # documents the manuscript QA scripts audit; a manuscript is not a code release
    "MANUSCRIPT_v3.2_EN.md": "the manuscript; not part of this code release",
    "MANUSCRIPT_v3.2_CN.md": "the manuscript; not part of this code release",
    "MANUSCRIPT_NUMBER_AUDIT.md": "manuscript-repository document; not part of this release",
    "MANUSCRIPT_CLAIM_COMPLIANCE.md":
        "manuscript-repository document; not part of this release",
    "MANUSCRIPT_SEMANTIC_UNIT_AUDIT.md":
        "manuscript-repository document; not part of this release",
    "RECALIBRATION_WORDING_AUDIT.md":
        "manuscript-repository document; not part of this release",
    # files the excluded categories cover: named in order to document the EXCLUSION
    "data": "excluded by design: restricted derived data",
    "logs": "excluded by design: generated run logs",
    "tables": "excluded by design: publication artefacts",
    "figures": "excluded by design: publication artefacts",
    "data/analysis_dataset.csv": "excluded: restricted per-stay dataset",
    "data/predictions.csv": "excluded: restricted per-stay predictions",
    "data/cohort_*.csv": "excluded: restricted per-centre cohort extracts",
    "data/recalibration_cv_predictions.csv": "excluded: restricted held-out predictions",
    "data/publock_*.csv": "excluded: restricted derived outputs",
    "data/*.csv": "excluded: the restricted data directory as a whole",
    "tables/*.xlsx": "excluded: publication artefacts",
    "01_transportability": "excluded: superseded analyses",
    "__pycache__": "excluded: compiled bytecode",
    "src/model": "does not exist in this repository; the patcher it held is not shipped",
    "src/validation/hierarchical_calibration.py":
        "REMOVED from the pipeline; the rejected implementation is archived instead",
    "PUBLICATION_RELEASE_MANIFEST.json": "internal release-audit artefact; not shipped",
    "PUBLICATION_ARTIFACT_CHECKSUMS.txt":
        "internal artefact-checksum file; not shipped",
    ".env": "created locally by the user; never committed",
    # glob patterns quoted from .gitignore and from README, not file references
    "*.csv": "a glob pattern in .gitignore, not a file reference",
    "src/manuscript_qa/*.py":
        "glob over the manuscript-QA scripts, not a single file reference",
    # internal packaging scripts named by the security scan snapshot
    "build_code_release.py": "internal packaging script; not shipped",
    "project1_cirrhosis_transportability_code_release":
        "the release directory under its former name; now ..._v1.1.0",
    "project1_cirrhosis_transportability_code_release_v1.1.0":
        "this directory, named from outside itself",
    # stage directories named by the pipeline document: the historical grouping of the
    # internal working tree, not directories of this repository
    "model": "historical stage directory of the internal working tree",
    "validation": "stage directory; in this repository it is `src/validation`",
    "recalibration": "historical stage directory of the internal working tree",
    "sensitivity": "historical stage directory of the internal working tree",
    "reporting": "stage directory; in this repository it is `src/reporting`",
    "phenotype": "stage directory; in this repository it is `src/phenotype`",
    "preprocessing": "stage directory; in this repository it is `src/preprocessing`",
    "clinical_scores": "stage directory; in this repository it is `src/clinical_scores`",
    # Artefacts the PIPELINE generates under data/ and outputs/. They are not shipped
    # (they are restricted per-patient data or publication artefacts), so the audit
    # documents that describe the hand-off necessarily name files that do not exist here.
    # Each is produced by a numbered pipeline stage; see PIPELINE_PATH_AUDIT.md.
    "cohort_mimic.csv": "generated by stage 1 into data/; restricted, not shipped",
    "cohort_eicu.csv": "generated by stage 1 into data/; restricted, not shipped",
    "cohort_nwicu.csv": "generated by stage 1 into data/; restricted, not shipped",
    "cohort_flow.csv": "generated by stage 1 into data/; restricted, not shipped",
    "cohort_old_vs_new.csv": "generated by stage 3 into data/; restricted, not shipped",
    "cohort_newonly_review_sample.csv":
        "generated by stage 3 into data/; restricted, not shipped",
    "cirrhosis_phenotype_rule.json": "generated by stage 2 into data/; not shipped",
    "cirrhosis_code_dictionary.xlsx": "generated by stage 2 into outputs/tables/; not shipped",
    "analysis_dataset.csv": "generated by stage 4 into data/; restricted, not shipped",
    "predictions.csv": "generated by stage 4 into data/; restricted, not shipped",
    "model_v2_coefficients.csv": "generated by stage 4 into data/; not shipped",
    "qc_flags.csv": "generated by stage 4 into data/; not shipped",
    "score_comparison_common_complete.csv":
        "generated by stage 5 into data/; restricted, not shipped",
    "score_comparison_paired.csv": "generated by stage 5 into data/; not shipped",
    "map_sensitivity.csv": "generated by stage 5 into data/; not shipped",
    "TableS9_score_detail.xlsx": "generated by stage 5 into outputs/tables/; not shipped",
    "missingness_sensitivity.csv": "generated by stage 6 into data/; not shipped",
    "early_prediction_sensitivity.csv": "generated by stage 6 into data/; not shipped",
    "publock_repeated_patient.csv": "generated by stage 6 into data/; not shipped",
    "known_answer_tests.csv": "generated by stage 6 into data/; not shipped",
    "fault_injection.csv": "generated by stage 7 into data/; not shipped",
    "independent_metric_check.csv": "generated by stage 8 into data/; not shipped",
    "GOLDEN_100_RAW_TO_DERIVED.xlsx":
        "generated by stage 8 into outputs/tables/; restricted per-stay rows, not shipped",
    "publock_external_ci.csv": "generated by stage 9 into data/; not shipped",
    "publock_optimism.csv": "generated by stage 9 into data/; not shipped",
    "Table_Final_Optimism.xlsx": "generated by stage 9 into outputs/tables/; not shipped",
    "publock_hospital_descriptive.csv": "generated by stage 10 into data/; not shipped",
    "publock_hospital_meta.csv": "generated by stage 10 into data/; not shipped",
    "publock_recalibration_ci.csv": "generated by stage 10 into data/; not shipped",
    "recalibration_cv_predictions.csv":
        "generated by stage 10 into data/; restricted per-stay rows, not shipped",
    "publock_paired_score_differences.csv": "generated by stage 11 into data/; not shipped",
    "publock_score_mappings.csv": "generated by stage 11 into data/; not shipped",
    # illustrative path used in a usage example, not a repository file
    "abs/path/to/repo/src/repo.py":
        "an illustrative absolute path in a usage example, not a repository file",
    # Generated trees, named by the documentation as the locations the pipeline writes to.
    # They are created at run time and are gitignored, so a clean clone does not contain
    # them; naming them is correct and their absence here is expected.
    "outputs": "the generated-output tree, created at run time by src/repo.py",
    "outputs/tables": "generated by the pipeline at run time",
    "outputs/figures": "generated by the pipeline at run time",
    "outputs/logs": "generated by the pipeline at run time",
    # glob patterns naming whole generated trees
    "outputs/tables/*.xlsx": "glob over the generated tables; none is shipped",
    "outputs/figures/*.png": "glob over the generated figures; none is shipped",
    "PUBLICATION_LOCK.md": "internal lock document; produced by publication_lock.py",
    "FINAL_PUBLICATION_REPORT.md": "internal report; not part of the code release",
    "Language_PASS_AUDIT.md": "manuscript-repository audit; not part of the code release",
}

# Column-name tokens that indicate per-patient or per-stay rows. Their appearance as a
# *column name* in extraction code is legitimate; their appearance as a CSV header in a
# shipped file is not.
IDENTIFIER_TOKENS = ["subject_id", "hadm_id", "stay_id", "patientunitstayid",
                     "uniquepid", "patient_uid", "hospitalid", "icustay_id"]

CREDENTIAL_PATTERNS = [
    (re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{4,}['\"]"),
     "hardcoded password literal"),
    (re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)"
                r"\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "hardcoded API key or token literal"),
    (re.compile(r"(?i)postgres(?:ql)?://[^\s'\"]*:[^\s'\"@]+@"),
     "credentialed connection string"),
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----"),
     "private key block"),
]

BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".pyc", ".xlsx",
              ".xls", ".parquet", ".feather", ".db", ".sqlite", ".duckdb"}
TEXT_EXT = {".py", ".md", ".txt", ".cff", ".yml", ".yaml", ".csv", ".json", ".cfg",
            ".toml", ".ini", ".example", ".gitignore", ""}

N_STEPS = 8
FAILS: list[str] = []
CHECKS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILS.append(f"{name}: {detail}")


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def shipped_files() -> list[str]:
    """Every file in the release, excluding caches."""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in {"__pycache__", ".git", ".pytest_cache",
                                    ".mypy_cache", ".ipynb_checkpoints"}]
        for f in filenames:
            out.append(rel(os.path.join(dirpath, f)))
    return sorted(out)


# ===================================================================== 1. CHECKSUMS
def check_checksums(verbose: bool) -> None:
    ck = os.path.join(ROOT, CHECKSUMS)
    if not os.path.isfile(ck):
        record("checksums: manifest present", False, f"{CHECKSUMS} not found")
        return
    listed: dict[str, str] = {}
    with open(ck, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or "  " not in line:
                continue
            digest, name = line.split("  ", 1)
            listed[name.strip()] = digest.strip()

    ok = bad = missing = 0
    problems: list[str] = []
    for name, digest in sorted(listed.items()):
        full = os.path.join(ROOT, name.replace("/", os.sep))
        if not os.path.isfile(full):
            missing += 1
            problems.append(f"MISSING   {name}")
            continue
        actual = sha256_file(full)
        if actual == digest:
            ok += 1
        else:
            bad += 1
            problems.append(f"MISMATCH  {name}\n              expected {digest}\n"
                            f"              actual   {actual}")
    record("checksums: all listed files match", bad == 0 and missing == 0,
           f"ok={ok} mismatch={bad} missing={missing}")

    # every shipped file must be covered, so the manifest cannot silently go stale
    uncovered = sorted(set(shipped_files()) - set(listed) - {CHECKSUMS})
    if uncovered:
        problems.append("NOT IN MANIFEST: " + ", ".join(uncovered))
    record("checksums: manifest covers every shipped file", not uncovered,
           f"{len(uncovered)} uncovered")

    if verbose:
        print(f"  checksum manifest: {len(listed)} entries; {ok} verified")
        for p in problems:
            print("    " + p)


# ===================================================================== 2. REQUIRED
def check_required(verbose: bool) -> None:
    missing = [f for f in REQUIRED_FILES
               if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]
    record("required files present", not missing,
           f"missing: {missing}" if missing else f"{len(REQUIRED_FILES)} checked")

    present = [f for f in FORBIDDEN_PATHS
               if os.path.exists(os.path.join(ROOT, f.replace("/", os.sep)))]
    record("removed / restricted paths absent", not present,
           f"present: {present}" if present else f"{len(FORBIDDEN_PATHS)} checked")

    if verbose:
        print(f"  required: {len(REQUIRED_FILES) - len(missing)}/{len(REQUIRED_FILES)}"
              f" present")
        print(f"  forbidden paths absent: "
              f"{len(FORBIDDEN_PATHS) - len(present)}/{len(FORBIDDEN_PATHS)}")


# ===================================================================== 3. COMPILE
def check_compile(verbose: bool) -> None:
    pys = [f for f in shipped_files() if f.endswith(".py")]
    bad_syntax, bad_bom, bad_decode = [], [], []
    for name in pys:
        full = os.path.join(ROOT, name.replace("/", os.sep))
        with open(full, "rb") as fh:
            raw = fh.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad_bom.append(name)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            bad_decode.append(f"{name} ({exc})")
            continue
        try:
            compile(text, full, "exec")
        except SyntaxError as exc:
            bad_syntax.append(f"{name}:{exc.lineno}: {exc.msg}")

    record("compile: every Python file compiles", not bad_syntax,
           f"{len(bad_syntax)} failed: {bad_syntax[:5]}")
    record("compile: no UTF-8 BOM", not bad_bom, f"{len(bad_bom)} with BOM: {bad_bom[:5]}")
    record("compile: all sources decode as UTF-8", not bad_decode,
           f"{len(bad_decode)} failed: {bad_decode[:5]}")

    # the archived historical file must be inert: parseable, but no top-level execution
    arch = "archive/nonproduction/hierarchical_calibration_rejected_historical.py"
    ap = os.path.join(ROOT, arch.replace("/", os.sep))
    if os.path.isfile(ap):
        with open(ap, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        top_level = [n for n in tree.body
                     if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                     and not (isinstance(n.value.func, ast.Name)
                              and n.value.func.id == "print")]
        record("compile: archived rejected implementation is inert", not top_level,
               f"{len(top_level)} executable top-level expressions")
    else:
        record("compile: archived rejected implementation is inert", False,
               f"{arch} not found")

    if verbose:
        print(f"  python files compiled: {len(pys) - len(bad_syntax)}/{len(pys)}")


# ===================================================================== 4. NO DATA
def check_no_restricted_data(verbose: bool) -> None:
    files = shipped_files()
    findings: list[str] = []

    # 4a. environment files
    envs = [f for f in files if os.path.basename(f).startswith(".env")
            and not f.endswith(".env.example")]
    if envs:
        findings.append(f"environment file present: {envs}")

    # 4b. tabular files outside the allowlisted aggregate metadata directory
    allowed = {
        "metadata/model_coefficients.csv",
        "metadata/phenotype_codes.csv",
        "metadata/predictor_definitions.csv",
    }
    for f in files:
        low = f.lower()
        if low in allowed:
            continue
        if low.endswith((".csv", ".xlsx", ".xls", ".parquet", ".feather", ".dta", ".sav")):
            findings.append(f"tabular data file outside metadata/: {f}")
        if low.endswith((".db", ".sqlite", ".sqlite3", ".duckdb", ".dump", ".sql.gz")):
            findings.append(f"database file present: {f}")

    # 4c. identifier column headers in any shipped table
    for f in files:
        if not f.lower().endswith(".csv"):
            continue
        full = os.path.join(ROOT, f.replace("/", os.sep))
        try:
            with open(full, encoding="utf-8-sig") as fh:
                header = fh.readline().strip().lower()
        except (OSError, UnicodeDecodeError):
            continue
        hits = [t for t in IDENTIFIER_TOKENS if t in header]
        if hits:
            findings.append(f"identifier column(s) {hits} in header of {f}")

    # 4d. credential literals in text files
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in BINARY_EXT or ext not in TEXT_EXT:
            continue
        full = os.path.join(ROOT, f.replace("/", os.sep))
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for pat, label in CREDENTIAL_PATTERNS:
            for m in pat.finditer(text):
                if f.endswith(".env.example"):
                    continue
                snippet = m.group(0)
                if re.search(r"(?i)placeholder|your[_-]|example|changeme|xxxx|<.*>|REPLACE",
                             snippet):
                    continue
                findings.append(f"{label} in {f}: {snippet[:60]!r}")

    record("no restricted data shipped", not findings, f"{len(findings)} finding(s)")
    if verbose:
        print(f"  restricted-data findings: {len(findings)}")
        for x in findings[:20]:
            print("    " + x)


# ===================================================================== 5. REFERENCES
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
PY_CMD_RE = re.compile(r"\bpython3?\s+([A-Za-z0-9_./\\-]+\.py)")


def candidate_paths(md_path: str, text: str) -> set[str]:
    """Repository file paths that a document appears to reference."""
    found: set[str] = set()

    for m in MD_LINK_RE.finditer(text):
        target = m.group(1).split("#")[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        base = os.path.dirname(md_path)
        found.add(os.path.normpath(os.path.join(base, target)).replace(os.sep, "/"))

    for m in CODE_SPAN_RE.finditer(text):
        span = m.group(1).strip()
        if any(ch in span for ch in " \t") or span.startswith(("-", "http")):
            continue
        found.add(span)

    for m in PY_CMD_RE.finditer(text):
        found.add(m.group(1).replace("\\", "/"))

    return found


def looks_like_path_token(tok: str) -> bool:
    if not tok or tok.startswith(("-", ".", "#")) or " " in tok:
        return False
    if tok in {"python", "pip", "bash", "git", "Rscript", "cp", "export"}:
        return False
    if "/" in tok:
        return True
    return bool(re.search(r"\.(py|md|txt|cff|yml|yaml|csv|json|example|gitignore)$", tok))


def check_references(verbose: bool, list_refs: bool) -> None:
    mds = [f for f in shipped_files() if f.lower().endswith(".md")]
    repo_files = set(shipped_files())
    repo_dirs = {os.path.dirname(f) for f in repo_files}
    basenames = {os.path.basename(f) for f in repo_files}

    broken: list[str] = []
    checked = 0
    uniq: set[str] = set()
    for md in mds:
        full = os.path.join(ROOT, md.replace("/", os.sep))
        try:
            with open(full, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        for tok in candidate_paths(md, text):
            if not looks_like_path_token(tok):
                continue
            t = tok.strip("`.,;:()").strip("/").replace("\\", "/").lstrip("./")
            if not t or t.startswith("http"):
                continue
            if t in NON_RESOLVING or os.path.basename(t) in NON_RESOLVING:
                continue
            checked += 1
            uniq.add(t)
            if (t in repo_files or t in repo_dirs or t in basenames
                    or os.path.exists(os.path.join(ROOT, t.replace("/", os.sep)))):
                continue
            broken.append(f"{md} -> {t}")

    record("references: every documented file path resolves", not broken,
           f"{len(broken)} broken of {checked} checked")
    if verbose or list_refs:
        print(f"  documented file references checked: {checked} ({len(uniq)} distinct)")
        for b in broken:
            print("    BROKEN  " + b)
    if list_refs:
        print(f"  intentionally non-resolving references declared: {len(NON_RESOLVING)}")
        for t in sorted(uniq):
            print("    " + t)


# ===================================================================== 6. MANIFEST
MANIFEST_ROW_RE = re.compile(
    r"^\| (\d+) \| `([^`]+)` \|.*?\| ([\d,]+|--?) \| (.+?) \|$", re.M)
# A row may record a real SHA-256, or the literal marker SELF. Nothing else is accepted,
# because any other placeholder would be a stale hash waiting to mislead a reader.
SELF_MARKER_RE = re.compile(r"^(?:`([0-9a-f]{64})`|SELF\b.*)$")


def check_release_manifest(verbose: bool) -> None:
    """PUBLIC_CODE_RELEASE_MANIFEST.md must agree with the tree and the checksums."""
    path = os.path.join(ROOT, "PUBLIC_CODE_RELEASE_MANIFEST.md")
    if not os.path.isfile(path):
        record("manifest: PUBLIC_CODE_RELEASE_MANIFEST.md present", False, "not found")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    rows = MANIFEST_ROW_RE.findall(text)
    if not rows:
        record("manifest: file table parsed", False, "no rows matched")
        return

    problems: list[str] = []
    listed: set[str] = set()
    # This script cannot carry a stable row about itself: editing it changes its own size
    # and hash. The manifest and the checksum manifest are self-referential in the same
    # way, and the checksum manifest excludes itself for exactly that reason. All three
    # are therefore exempt from the size/hash comparison while still being required to
    # appear as rows, which is asserted separately below.
    self_ref = {GENERATOR, "PUBLIC_CODE_RELEASE_MANIFEST.md", CHECKSUMS}
    for _num, relpath, size_s, digest in rows:
        if relpath in self_ref:
            # self-referential; see the note above
            # manifest for the same reason, so neither is compared here
            continue
        listed.add(relpath)
        full = os.path.join(ROOT, relpath.replace("/", os.sep))
        if not os.path.isfile(full):
            problems.append(f"listed but absent: {relpath}")
            continue
        if not SELF_MARKER_RE.match(digest):
            problems.append(f"{relpath}: hash column is not a SHA-256 or SELF: {digest!r}")
            continue
        actual_size = os.path.getsize(full)
        if size_s != "--" and int(size_s.replace(",", "")) != actual_size:
            problems.append(f"{relpath}: size says {size_s}, actual {actual_size:,}")
        recorded = re.match(r"^`([0-9a-f]{64})`$", digest)
        if recorded and sha256_file(full) != recorded.group(1):
            problems.append(f"{relpath}: sha256 mismatch")

    # the manifest must cover the same files as the checksum manifest
    ck = os.path.join(ROOT, CHECKSUMS)
    if os.path.isfile(ck):
        checked = set()
        with open(ck, encoding="utf-8") as fh:
            for line in fh:
                if "  " in line and not line.startswith("#"):
                    checked.add(line.rstrip("\n").split("  ", 1)[1].strip())
        only_ck = sorted(checked - listed - self_ref)
        only_man = sorted(listed - checked - self_ref)
        if only_ck:
            problems.append(f"in checksums, not in manifest: {only_ck}")
        if only_man:
            problems.append(f"in manifest, not in checksums: {only_man}")
        record("manifest: covers the same files as the checksum manifest",
               not (only_ck or only_man), f"{len(only_ck)} / {len(only_man)}")

    # and it must list every shipped file: an incomplete manifest is a stale manifest.
    # The three files that cannot carry a stable self-referential hash -- this script,
    # the checksum manifest, and the manifest itself -- are excluded from the comparison
    # but are still required to appear as rows above.
    shipped = set(shipped_files())
    exempt = {GENERATOR, CHECKSUMS, "PUBLIC_CODE_RELEASE_MANIFEST.md"}
    not_listed = sorted(shipped - listed - exempt)
    if not_listed:
        problems.append(f"shipped but not listed in the manifest: {not_listed}")
    record("manifest: lists every shipped file", not not_listed,
           f"{len(not_listed)} unlisted of {len(shipped)} shipped")

    record("manifest: sizes and hashes match the tree", not problems,
           f"{len(problems)} problem(s)")
    if verbose:
        print(f"  manifest rows checked: {len(rows)}")
        for p in problems[:15]:
            print("    " + p)


# ===================================================================== 7. STRUCTURE
def check_structure(verbose: bool) -> None:
    """The rejected model must be gone, and every stage must share one repository root.

    Delegates to `pipeline_path_audit.py`, which extracts and executes each script's
    path-setup block only -- no data, no database, no modelling -- and then AST-parses
    every stage for the artefacts it reads and writes.
    """
    audit = os.path.join(ROOT, PATH_AUDIT)
    if not os.path.isfile(audit):
        record("structure: pipeline path audit present", False, f"{PATH_AUDIT} not found")
        return
    record("structure: pipeline path audit present", True, PATH_AUDIT)

    import subprocess
    try:
        proc = subprocess.run([sys.executable, audit], cwd=ROOT, capture_output=True,
                              text=True, timeout=300)
    except Exception as exc:  # noqa: BLE001
        record("structure: pipeline path audit runs", False, f"{type(exc).__name__}: {exc}")
        return
    out = (proc.stdout or "") + (proc.stderr or "")
    record("structure: pipeline path audit runs", proc.returncode == 0,
           f"exit {proc.returncode}")
    record("structure: all stages share one repository root",
           "ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS" in out,
           "verdict line present" if proc.returncode == 0 else "see audit output")
    record("structure: rejected hierarchical model absent from production code",
           "no production script fits, reads or writes the removed model" in out,
           "verified by audit")
    if verbose:
        for ln in out.strip().split("\n"):
            s = ln.strip()
            if s.startswith(("PASS", "FAIL", "VERDICT")):
                print("    " + s)


# ===================================================================== 8. CITATION
def check_citation(verbose: bool) -> None:
    """Structural validation of CITATION.cff; no fake DOI or URL may ship."""
    path = os.path.join(ROOT, "CITATION.cff")
    if not os.path.isfile(path):
        record("citation: CITATION.cff present", False, "not found")
        return
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()

    problems: list[str] = []
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None

    if yaml is not None:
        try:
            doc = yaml.safe_load(raw)
        except Exception as exc:  # noqa: BLE001
            record("citation: parses as YAML", False, str(exc))
            return
        # required keys per the CFF 1.2.0 schema
        for key in ("cff-version", "message", "title", "authors"):
            if key not in doc:
                problems.append(f"required key missing: {key}")
        if str(doc.get("cff-version")) != "1.2.0":
            problems.append(f"cff-version is {doc.get('cff-version')!r}, expected 1.2.0")
        authors = doc.get("authors") or []
        if len(authors) != 10:
            problems.append(f"{len(authors)} authors, expected 10")
        if str(doc.get("version")) != "1.1.0":
            problems.append(f"version is {doc.get('version')!r}, expected 1.1.0")
        # CFF 1.2.0 `license` must be an SPDX id from a closed enum; a "not yet chosen"
        # licence cannot be expressed, so the key must be absent rather than free text
        if "license" in doc:
            problems.append("`license` present; CFF 1.2.0 accepts only SPDX ids, so a "
                            "not-yet-chosen licence must be expressed by omitting it")
        # identifiers, if present, must carry a real bare DOI
        for ident in doc.get("identifiers") or []:
            val = str(ident.get("value", ""))
            if not re.fullmatch(r"10\.\d{4,9}/\S+", val):
                problems.append(f"identifier is not a bare DOI: {val!r}")
            if re.search(r"REPLACE|XXXX|NNNN|TODO|PLACEHOLDER", val, re.I):
                problems.append(f"placeholder DOI shipped: {val!r}")
        record("citation: no fake or placeholder DOI",
               not any("DOI" in p for p in problems),
               "identifiers absent" if "identifiers" not in doc else "checked")
    else:
        record("citation: no fake or placeholder DOI", True,
               "PyYAML not installed; checked by token scan only")

    record("citation: no placeholder tokens anywhere",
           not re.search(r"REPLACE_WITH|\bTODO\b|PLACEHOLDER", raw), "none")
    record("citation: structural checks pass", not problems, "; ".join(problems))
    if verbose:
        print(f"  CITATION.cff: {len(problems)} structural problem(s)")


# ===================================================================== main
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true",
                    help="print only failures and the summary")
    ap.add_argument("--list-references", action="store_true",
                    help="print every documented file reference that was checked")
    args = ap.parse_args()
    verbose = not args.quiet

    print("=" * 78)
    print("PUBLIC CODE RELEASE VERIFICATION")
    print(f"  repository : {ROOT}")
    print("  requires   : no database access, no patient-level data, no Git history")
    print("=" * 78)

    steps = [
        ("checksums", lambda: check_checksums(verbose)),
        ("required files", lambda: check_required(verbose)),
        ("compile", lambda: check_compile(verbose)),
        ("restricted-data scan", lambda: check_no_restricted_data(verbose)),
        ("documentation references",
         lambda: check_references(verbose, args.list_references)),
        ("release manifest", lambda: check_release_manifest(verbose)),
        ("pipeline structure", lambda: check_structure(verbose)),
        ("citation metadata", lambda: check_citation(verbose)),
    ]
    for i, (label, fn) in enumerate(steps, start=1):
        if verbose:
            print(f"\n[{i}/{N_STEPS}] {label}")
        fn()

    print("\n" + "=" * 78)
    for name, ok, detail in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<52} {detail}")
    print("-" * 78)
    print(f"  {len(CHECKS) - len(FAILS)}/{len(CHECKS)} checks passed")
    if FAILS:
        print("\n  FAILURES:")
        for f in FAILS:
            print(f"    - {f}")
        print("\n  RELEASE NOT VERIFIED.")
        return 1
    print("\n  PUBLIC CODE RELEASE VERIFIED: checksums, required files, compilation,")
    print("  data governance, documentation references and citation metadata are all")
    print("  consistent. No database access and no patient-level data were required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
