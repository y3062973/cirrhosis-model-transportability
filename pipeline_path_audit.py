"""PIPELINE PATH AUDIT (dry run). NO DATABASE ACCESS. NO ANALYSIS. NO DATA NEEDED.

Verifies the property that was broken in the v1.1.0 release candidate: every script in the
pipeline must resolve `data/`, `outputs/tables`, `outputs/figures` and `outputs/logs` to
the SAME repository-root locations. In the broken design each script computed

    FR = os.path.dirname(os.path.abspath(__file__))
    DATA = os.path.join(FR, "data")

so a script in `src/validation/` read `src/validation/data/` while a script in
`tests/metric_validation/` read `tests/metric_validation/data/`, and no stage could read
what the previous stage wrote. All scripts now resolve those four paths through
`src/repo.py`.

For every production and verification module this audit extracts that module's path-setup
block, executes ONLY those lines, and reads the resulting DATA / TABLES / FIGS / LOGS / FR
values. The statistical body of each script is never run, so no data is read and no model
is fitted. It then:

  1. asserts every stage resolves the four locations to the same repository-root paths;
  2. asserts no stage points inside src/ or tests/;
  3. AST-parses each stage for the generated artefacts it reads and writes, and checks the
     hand-off order: every artefact a stage reads must be produced by that stage or an
     earlier one;
  4. asserts no production script fits, reads or writes the rejected hierarchical
     model's quantities, and that `final_release_check.py` actively forbids its sheets.

Usage
-----
    python pipeline_path_audit.py

Exit code is 0 only if every check passes.

Verdict printed on success:
    ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = HERE
SRC = os.path.join(RELEASE, "src")
sys.path.insert(0, SRC)

import repo  # noqa: E402  the shared helper under test

# (relative path, stage number or None)
MODULES = [
    ("src/phenotype/build_cohorts.py", 1),
    ("src/phenotype/phenotype_audit.py", 2),
    ("src/phenotype/cohort_composition.py", 3),
    ("src/preprocessing/build_dataset_and_model.py", 4),
    ("src/clinical_scores/clinical_scores.py", 5),
    ("src/clinical_scores/meld_component_audit.py", None),
    ("src/validation/validation_and_sensitivity.py", 6),
    ("tests/fault_injection/fault_injection_suite.py", 7),
    ("tests/metric_validation/independent_metrics_and_verification.py", 8),
    ("src/validation/primary_validation.py", 9),
    ("src/validation/hospital_analysis_and_recalibration.py", 10),
    ("src/clinical_scores/paired_score_comparison.py", 11),
    ("src/reporting/tables_and_figures.py", 12),
    ("src/validation/publication_lock.py", None),
    ("src/reporting/final_release_check.py", None),
    ("src/reporting/release_verification.py", None),
    ("src/manuscript_qa/semantic_unit_audit.py", None),
    ("src/manuscript_qa/number_audit.py", None),
    ("src/manuscript_qa/claim_compliance.py", None),
    ("src/manuscript_qa/language_pass.py", None),
    ("src/manuscript_qa/reference_audit.py", None),
]

PATHSET_RE = re.compile(
    r"^(?:import repo\b.*|repo\.add_src_to_path\(\).*|FR = .*|SRC_DIR = .*|DATA = .*|"
    r"TABLES = .*|FIGS = .*|LOGS = .*|ROOT = .*|repo\.ensure_writable_dirs\(\).*|"
    r"for d in \(DATA, TABLES, LOGS\):|    os\.makedirs\(d, exist_ok=True\))\s*$")

FAILS: list[str] = []
print("=" * 100)
print("DRY-RUN PATH TEST -- no database access, no analysis, no data required")
print("=" * 100)
print(f"  release root : {RELEASE}")
print(f"  helper root  : {repo.REPO_ROOT}")
print()

print("[1] extracted path block per module (body NOT executed)")
print(f"  {'module':<52} {'DATA':<10} {'TABLES':<12} {'FIGS':<12} {'LOGS':<10}")
observed: dict[str, tuple] = {}
for relpath, stage in MODULES:
    full = os.path.join(RELEASE, relpath.replace("/", os.sep))
    with io.open(full, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    block = [ln for ln in lines if PATHSET_RE.match(ln)]
    ns = {"os": os, "sys": sys, "repo": repo, "__name__": "dryrun"}
    try:
        exec(compile("\n".join(block), relpath, "exec"), ns)   # noqa: S102
    except Exception as exc:  # noqa: BLE001
        FAILS.append(f"{relpath}: path block failed: {type(exc).__name__}: {exc}")
        print(f"  {relpath:<52} PATH BLOCK FAILED ({type(exc).__name__})")
        continue

    def leaf(p):
        if p is None:
            return "-"
        return os.path.join(os.path.basename(os.path.dirname(str(p))),
                            os.path.basename(str(p)))

    d, t = ns.get("DATA"), ns.get("TABLES")
    f, l = ns.get("FIGS"), ns.get("LOGS")
    observed[relpath] = tuple(str(x) if x is not None else "None" for x in (d, t, f, l))
    tag = f"stage {stage}" if stage else "      "
    print(f"  {relpath:<52} {leaf(d):<10} {leaf(t):<12} {leaf(f):<12} {leaf(l):<10} {tag}")

print()
print("[2] do all stages agree on the same four locations?")
expected = (str(repo.DATA), str(repo.TABLES), str(repo.FIGURES), str(repo.LOGS))
mismatch = {r: v for r, v in observed.items()
            if v != expected and v != ("None", "None", "None", "None")}
if mismatch:
    for r, v in mismatch.items():
        FAILS.append(f"{r}: resolves elsewhere: {v}")
    print(f"  FAIL: {len(mismatch)} module(s) resolve elsewhere")
    for r, v in sorted(mismatch.items()):
        print(f"        {r}: {v}")
else:
    print(f"  PASS: all {len(observed)} modules that define paths agree exactly")
    print(f"        DATA    = {expected[0]}")
    print(f"        TABLES  = {expected[1]}")
    print(f"        FIGURES = {expected[2]}")
    print(f"        LOGS    = {expected[3]}")
    noval = [r for r, v in observed.items() if v == ("None", "None", "None", "None")]
    if noval:
        print(f"  NOTE: {len(noval)} script(s) define no data/output paths at all "
              f"(they audit the manuscript or the release only):")
        for r in noval:
            print(f"        {r}")

print()
print("[3] no module points inside src/ or tests/")
bad = [r for r, v in observed.items()
       if any(str(p).startswith((SRC, os.path.join(RELEASE, "tests")))
              for p in v if p != "None")]
if bad:
    for r in bad:
        FAILS.append(f"{r}: a path constant points inside src/ or tests/")
    print(f"  FAIL: {bad}")
else:
    print("  PASS: every path constant points at <repo>/data or <repo>/outputs/*")

print()
print("[4] stage hand-off: artefacts written vs artefacts read (AST-parsed)")
import ast  # noqa: E402

READ_FUNCS = {"read_csv", "read_excel", "read_json", "read_parquet", "load"}
WRITE_FUNCS = {"to_csv", "to_excel", "to_json", "to_parquet", "savefig", "dump"}


def docstring_spans(tree) -> list[tuple[int, int]]:
    """Line spans of every statement-level docstring in the tree."""
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                spans.append((body[0].lineno, body[0].end_lineno or body[0].lineno))
    return spans


def outline(node) -> str:
    """Best-effort single-line source for an AST node, with continuations collapsed."""
    try:
        return " ".join(ast.unparse(node).split())
    except Exception:  # noqa: BLE001
        return ""


def artefacts(full: str) -> tuple[set[str], set[str]]:
    """(files_read, files_written) named by string literals in the script."""
    with io.open(full, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    reads, writes = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        bucket = (reads if name in READ_FUNCS
                  else writes if name in WRITE_FUNCS
                  else None)
        if name == "open" and node.args:
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            bucket = writes if any(c in mode for c in "wax") else reads
        if bucket is None:
            continue
        src = outline(node)
        for m in re.finditer(r'"([^"]+\.(?:csv|xlsx|json|png|pdf))"', src):
            bucket.add(m.group(1))
    return reads, writes


PRODUCES = {
    1: ["cohort_mimic.csv", "cohort_eicu.csv", "cohort_nwicu.csv", "cohort_flow.csv",
        "cohort_old_vs_new.csv", "cohort_newonly_review_sample.csv"],
    2: ["cirrhosis_code_dictionary.xlsx", "cirrhosis_phenotype_rule.json"],
    3: ["cohort_code_composition.csv", "TableS8_cohort_composition.xlsx"],
    4: ["analysis_dataset.csv", "predictions.csv", "model_v2_coefficients.csv",
        "qc_flags.csv"],
    5: ["score_comparison_common_complete.csv", "score_comparison_paired.csv",
        "map_sensitivity.csv", "TableS9_score_detail.xlsx"],
    6: ["early_prediction_sensitivity.csv", "missingness_sensitivity.csv",
        "publock_repeated_patient.csv", "known_answer_tests.csv"],
    7: ["fault_injection.csv"],
    8: ["independent_metric_check.csv", "GOLDEN_100_RAW_TO_DERIVED.xlsx"],
    9: ["publock_external_ci.csv", "publock_optimism.csv", "Table_Final_Optimism.xlsx"],
    10: ["publock_hospital_descriptive.csv", "publock_hospital_meta.csv",
         "publock_recalibration_ci.csv", "recalibration_cv_predictions.csv",
         "Table4_hospital_level.xlsx", "Table5_recalibration.xlsx"],
    11: ["publock_paired_score_differences.csv", "publock_score_mappings.csv",
         "Table6_score_comparison.xlsx"],
    12: ["Table1_baseline.xlsx", "Table2_model_coefficients.xlsx",
         "Table3_primary_validation.xlsx", "Supplementary_Tables_S1_S7.xlsx"],
}
written: dict[str, int] = {}
for stage, names in PRODUCES.items():
    for n in names:
        written[n] = stage

# inputs the user supplies or that are written by the same stage
EXEMPT = {"analysis_dataset.csv", "predictions.csv", "model_v2_coefficients.csv"}
problems = []
for relpath, stage in MODULES:
    full = os.path.join(RELEASE, relpath.replace("/", os.sep))
    reads, writes = artefacts(full)
    for name in sorted(reads - writes - EXEMPT):
        producer = written.get(name)
        if producer is None:
            problems.append(f"stage {stage or '-'} ({os.path.basename(relpath)}) reads "
                            f"{name}, not listed as any stage's output")
        elif stage is not None and producer > stage:
            problems.append(f"stage {stage} ({os.path.basename(relpath)}) reads {name} "
                            f"produced by LATER stage {producer}")

if problems:
    for p in problems:
        FAILS.append("stage hand-off: " + p)
    print(f"  FAIL: {len(problems)} ordering problem(s)")
    for p in sorted(set(problems)):
        print("        " + p)
else:
    print("  PASS: every artefact a stage reads is produced by that stage or an earlier one")

print()
print("[5] rejected hierarchical model must be absent from production code")
# Precise rules. Asserting that the removed sheets are ABSENT is required and correct; it
# is only a violation to READ, WRITE or FIT the removed quantities.
RULES = [
    (re.compile(r"\bfit_hier\s*\("), "calls the removed mixed-effects fit"),
    (re.compile(r"sheet_name\s*=\s*[\"']hierarchical_calibration[\"']"),
     "reads/writes the removed `hierarchical_calibration` sheet"),
    (re.compile(r"sheet_name\s*=\s*[\"']random_intercepts[\"']"),
     "reads/writes the removed `random_intercepts` sheet"),
    (re.compile(r"\brandom_intercepts\.csv\b"), "reads the removed random-intercept file"),
    (re.compile(r"\bHIER\["), "indexes the removed hierarchical result frame"),
    (re.compile(r"\btau_hat\b"), "uses the removed variance-component estimate"),
    (re.compile(r"hierarchical_calibration\.py"), "invokes the deleted pipeline script"),
    (re.compile(r"\bpublock_hospital_random_intercepts\b"),
     "writes the removed random-intercept file"),
]

prod_hits = []
for relpath, _s in MODULES:
    full = os.path.join(RELEASE, relpath.replace("/", os.sep))
    with io.open(full, encoding="utf-8") as fh:
        text = fh.read()
    tree = ast.parse(text)
    spans = docstring_spans(tree)
    lines = text.split("\n")
    for pat, label in RULES:
        for m in re.finditer(pat, text):
            line_no = text[:m.start()].count("\n") + 1
            line = lines[line_no - 1].strip()
            if line.startswith("#"):
                continue                                   # an explanatory comment
            if any(a <= line_no <= b for a, b in spans):
                continue                                   # a docstring
            prod_hits.append(f"{relpath}:{line_no}: {label}")

if prod_hits:
    for h in prod_hits:
        FAILS.append("production code references the removed model: " + h)
    print(f"  FAIL: {len(prod_hits)} executable reference(s)")
    for h in prod_hits:
        print("        " + h)
else:
    print("  PASS: no production script fits, reads or writes the removed model's quantities")

# and positively require that the release check FORBIDS the removed sheets
frc = os.path.join(RELEASE, "src", "reporting", "final_release_check.py")
with io.open(frc, encoding="utf-8") as fh:
    frc_text = fh.read()
if ("hierarchical calibration sheet removed from Table 4" in frc_text
        and "random-intercept sheet removed from Table 4" in frc_text):
    print("  PASS: final_release_check.py actively asserts the removed sheets are absent")
else:
    FAILS.append("final_release_check.py no longer asserts the removed sheets are absent")
    print("  FAIL: final_release_check.py does not assert the removed sheets are absent")

print()
print("=" * 100)
if FAILS:
    print(f"VERDICT: FAILED ({len(FAILS)} problem(s))")
    for f in FAILS:
        print("  - " + f)
    raise SystemExit(1)
print("VERDICT: ALL PRODUCTION STAGES SHARE THE SAME REPOSITORY-ROOT DATA/OUTPUT PATHS")
print("=" * 100)
