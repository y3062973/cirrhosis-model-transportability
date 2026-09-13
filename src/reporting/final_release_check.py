"""FINAL RELEASE CHECK -- independent verification of the published claims.

Recomputes every headline number from the frozen artefacts and asserts it matches
what the release documents state. Also re-checks the tag, the checksums, the
known-answer suite and the fault-injection suite. Non-zero exit on any failure.

This is deliberately a separate implementation path from the scripts that produced
the numbers: it reads the released tables/documents and compares, rather than
re-deriving from the same code.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

import numpy as np
import pandas as pd

import repo  # noqa: E402
repo.add_src_to_path()

# --- repository paths: ONE root for every stage --------------------------------
# `FR` is the REPOSITORY ROOT, not this file's directory. It replaces the per-script
# `FR = dirname(__file__)` block, which made each stage resolve `data` and `outputs`
# relative to its own folder, so no stage could read what the previous stage wrote.
# See PIPELINE_PATH_AUDIT.md.
FR = str(repo.REPO_ROOT)
SRC_DIR = str(repo.SRC_DIR)          # reserved for the import shim only
DATA = str(repo.DATA)
TABLES = str(repo.TABLES)
FIGS = str(repo.FIGURES)
LOGS = str(repo.LOGS)
repo.ensure_writable_dirs()

import provenance as prov  # noqa: E402

DATA, TABLES, LOGS = str(repo.DATA), str(repo.TABLES), str(repo.LOGS)
FIGS = str(repo.FIGURES)
repo.ensure_writable_dirs()
TAG = "PROJECT1_FINAL_MANUSCRIPT_v1.0.0"
fails, checks = [], []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    if not ok:
        fails.append(f"{name}: {detail}")


def git(*a):
    r = subprocess.run(["git"] + list(a), cwd=FR, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------- 1. tag state
# The analytical release v1.0.0 is FROZEN. Later phases (manuscript drafting) commit
# documentation on top of it, so HEAD is allowed to advance past the tag. What must
# hold is that the tag has not moved and is still an ancestor of HEAD; the artefact
# checksums below are what prove the analysis itself is unchanged.
rc, head, _ = git("rev-parse", "HEAD")
rc_t, tag_sha, _ = git("rev-list", "-n", "1", TAG)
check("tag exists", rc_t == 0, TAG)
rc, dirty, _ = git("status", "--porcelain")
check("working tree clean", dirty == "", f"{len(dirty.splitlines())} entries")
rc, tagtype, _ = git("cat-file", "-t", TAG)
check("tag is annotated", tagtype == "tag", tagtype)
rc_anc = subprocess.run(["git", "merge-base", "--is-ancestor", tag_sha, head],
                        cwd=FR, capture_output=True).returncode
check("tag is an ancestor of HEAD", rc_anc == 0,
      f"tag {tag_sha[:12]} head {head[:12]}"
      + (" (identical)" if tag_sha == head else " (HEAD advanced past the release)"))
# the release commit recorded in the manifest must still resolve to the same tree
MAN0 = json.load(io.open(os.path.join(FR, "PUBLICATION_RELEASE_MANIFEST.json"),
                         encoding="utf-8"))
check("release tag name in manifest", MAN0["release"] == TAG, MAN0["release"])

# ---------------------------------------------------------------- 2. artefacts
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")
check("dataset rows == 6198", len(A) == 6198, str(len(A)))
check("predictions present for all stays", A.p_model.notna().all(),
      f"{int(A.p_model.isna().sum())} missing")

EP = {"MIMIC-IV": "hospital_mortality", "eICU": "hospital_mortality",
      "nwICU": "death_30d_best"}
EXPECT = {  # exactly as stated in PUBLICATION_LOCK.md / FINAL_PUBLICATION_REPORT.md
    "MIMIC-IV": dict(n=4237, events=857, auroc=0.7924, brier=0.1272, oe=1.0000,
                     slope=1.0000),
    "eICU": dict(n=1612, events=324, auroc=0.7918, brier=0.1265, oe=0.8582,
                 slope=1.0333),
    "nwICU": dict(n=349, events=75, auroc=0.7387, brier=0.1484, oe=0.9610,
                  slope=0.7252),
}
for c, e in EXPECT.items():
    g = A[A.centre == c].dropna(subset=["p_model"])
    m = prov.metrics(g[EP[c]].values.astype(float), g.p_model.values.astype(float))
    for k in ["n", "events"]:
        check(f"{c} {k}", int(m[k]) == e[k], f"{int(m[k])} vs {e[k]}")
    for k, key, tol in [("auroc", "auroc", 5e-5), ("brier", "brier", 5e-5),
                        ("oe", "oe", 5e-5), ("calib_slope", "slope", 5e-5)]:
        got = float(m[k])
        check(f"{c} {key}", abs(got - e[key]) < tol, f"{got:.6f} vs {e[key]}")

# ---------------------------------------------------------------- 3. manifest
M = json.load(io.open(os.path.join(FR, "PUBLICATION_RELEASE_MANIFEST.json"),
                      encoding="utf-8"))
check("manifest release name", M["release"] == TAG, M["release"])
check("manifest config hash == live config hash",
      M["config_sha256"] == __import__("final_analysis_config").CONFIG_HASH)
check("manifest dataset hash matches file",
      M["dataset"]["sha256"] == prov.sha256_file(
          os.path.join(DATA, "analysis_dataset.csv")))
check("manifest model hash matches file",
      M["model_coefficients"]["sha256"] == prov.sha256_file(
          os.path.join(DATA, "model_v2_coefficients.csv")))
for c, e in EXPECT.items():
    lr = M["locked_primary_results"][c]
    check(f"manifest locked {c} AUROC", abs(lr["auroc"] - e["auroc"]) < 5e-5,
          f"{lr['auroc']} vs {e['auroc']}")

# ---------------------------------------------------------------- 4. checksums
ck = os.path.join(FR, "PUBLICATION_ARTIFACT_CHECKSUMS.txt")
ok = bad = miss = 0
for line in io.open(ck, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line or line.startswith("#") or "  " not in line:
        continue
    d, rel = line.split("  ", 1)
    p = os.path.join(FR, rel.replace("/", os.sep))
    if not os.path.exists(p):
        miss += 1
    elif prov.sha256_file(p) == d:
        ok += 1
    else:
        bad += 1
check("checksums all match", bad == 0 and miss == 0,
      f"ok={ok} bad={bad} missing={miss}")
check("checksum count matches manifest",
      ok == M.get("artifact_checksums", {}).get("n_entries", ok),
      f"{ok} vs {M.get('artifact_checksums', {}).get('n_entries')}")

# ---------------------------------------------------------------- 5. suites
k = pd.read_csv(os.path.join(DATA, "known_answer_tests.csv"))
npass = int((k.result == "PASS").sum())
check("known-answer 50/50", npass == 50 and len(k) == 50, f"{npass}/{len(k)}")

fi = pd.read_csv(os.path.join(DATA, "fault_injection.csv"))
dcol = [c for c in fi.columns if "detect" in c.lower() or "result" in c.lower()]
ndet = int(fi[dcol[0]].astype(str).str.contains("DETECT", case=False).sum()) \
    if dcol else -1
check("fault injection all detected", ndet == len(fi), f"{ndet}/{len(fi)}")

# ---------------------------------------------------------------- 6. documents
lock = io.open(os.path.join(FR, "PUBLICATION_LOCK.md"), encoding="utf-8").read()
rep = io.open(os.path.join(FR, "FINAL_PUBLICATION_REPORT.md"), encoding="utf-8").read()
claims = io.open(os.path.join(FR, "MANUSCRIPT_CLAIMS.md"), encoding="utf-8").read()
check("lock states MODEL LOCKED", "MODEL LOCKED" in lock)
check("lock states DATA LOCKED", "DATA LOCKED" in lock)
check("lock states RESULTS LOCKED", "RESULTS LOCKED" in lock)
check("report verdict READY FOR MANUSCRIPT", "READY FOR MANUSCRIPT" in rep)
check("no stale '208 hospitals' claim", "208 hospital" not in lock
      and "208 hospital" not in rep and "208 eICU" not in claims)
check("no stale '14-term' claim",
      not re.search(r"14[- ]term", lock + rep + claims))
check("no stale '48/48' known-answer claim",
      "48/48" not in lock + rep + claims)
check("checksum count stated in report",
      str(M.get("artifact_checksums", {}).get("n_entries")) in rep,
      f"report must quote {M.get('artifact_checksums', {}).get('n_entries')}")
for forbidden in ["significantly outperform", "severe calibration drift",
                  "30% over-prediction"]:
    hit = forbidden.lower() in claims.lower()
    # these may appear only inside the DO NOT CLAIM table
    if hit:
        idx = claims.lower().find(forbidden.lower())
        in_dnc = idx > claims.find("## DO NOT CLAIM")
        check(f"'{forbidden}' only in DO NOT CLAIM", in_dnc,
              "found outside the prohibition table")

# ---------------------------------------------------------------- 7. stop conditions
CERT = {c: (e["auroc"], e["oe"], e["slope"], e["n"], e["events"])
        for c, e in EXPECT.items()}
maxd = {k: 0.0 for k in ["auroc", "oe", "slope"]}
for c in EXPECT:
    g = A[A.centre == c].dropna(subset=["p_model"])
    m = prov.metrics(g[EP[c]].values.astype(float), g.p_model.values.astype(float))
    maxd["auroc"] = max(maxd["auroc"], abs(float(m["auroc"]) - CERT[c][0]))
    maxd["oe"] = max(maxd["oe"], abs(float(m["oe"]) - CERT[c][1]))
    maxd["slope"] = max(maxd["slope"], abs(float(m["calib_slope"]) - CERT[c][2]))
check("stop: AUROC drift <= 0.005", maxd["auroc"] <= 0.005, f"{maxd['auroc']:.6f}")
check("stop: O/E drift <= 0.02", maxd["oe"] <= 0.02, f"{maxd['oe']:.6f}")
check("stop: slope drift <= 0.05", maxd["slope"] <= 0.05, f"{maxd['slope']:.6f}")

# ---------------------------------------------------------------- 8. objective deliverables
EXT = pd.read_csv(os.path.join(DATA, "publock_external_ci.csv")).set_index("quantity")
need8 = ["auroc", "auprc", "brier", "oe", "calib_intercept", "calib_slope", "ici", "emax"]
check("external CI has all 8 required quantities",
      all(q in EXT.index for q in need8),
      f"missing {[q for q in need8 if q not in EXT.index]}")
check("external bootstrap >= 2000 replicates",
      int(EXT.n_boot.min()) >= 2000, str(int(EXT.n_boot.min())))

opt = pd.read_excel(os.path.join(TABLES, "Table_Final_Optimism.xlsx"))
check("Table_Final_Optimism present with 3 quantities",
      set(opt.quantity) == {"AUROC", "Brier", "calibration slope"},
      str(list(opt.quantity)))
check("optimism bootstrap >= 1000 replicates",
      int(opt.n_boot.min()) >= 1000, str(int(opt.n_boot.min())))

for f in ["Table1_baseline", "Table2_model_coefficients", "Table3_primary_validation",
          "Table4_hospital_level", "Table5_recalibration", "Table6_score_comparison"]:
    check(f"{f} exists", os.path.exists(os.path.join(TABLES, f + ".xlsx")))
check("Supplementary S1-S7 workbook exists",
      os.path.exists(os.path.join(TABLES, "Supplementary_Tables_S1_S7.xlsx")))
for i in range(1, 8):
    p = [f for f in os.listdir(FIGS) if f.startswith(f"Figure{i}_") and f.endswith(".png")]
    check(f"Figure {i} exists", len(p) == 1, str(p))
check("supplementary figures S1-S4 exist",
      all(any(f.startswith(f"FigureS{i}_") and f.endswith(".png")
              for f in os.listdir(FIGS)) for i in range(1, 5)))

# The removed hierarchical calibration model must NOT reappear. In release v1.0.0 this
# section REQUIRED a `hierarchical_calibration` sheet carrying alpha/beta/tau, and a
# `random_intercepts` sheet. The model was audited, found unreliable and REMOVED from the
# manuscript, so those checks are inverted: the sheets must now be ABSENT. If either ever
# comes back, this gate fails and the release must not be tagged. See
# docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md.
_t4_sheets = set(pd.ExcelFile(
    os.path.join(TABLES, "Table4_hospital_level.xlsx")).sheet_names)
check("hierarchical calibration sheet removed from Table 4",
      "hierarchical_calibration" not in _t4_sheets, str(sorted(_t4_sheets)))
check("random-intercept sheet removed from Table 4",
      "random_intercepts" not in _t4_sheets, str(sorted(_t4_sheets)))
check("retained Table 4 sheets present",
      {"all_hospitals", "primary_N20", "sensitivity_N30", "meta_analysis_AUROC"}
      <= _t4_sheets, str(sorted(_t4_sheets)))

# NOTE ON SCOPE. This script is an INTERNAL release-audit gate, not a reproduction step.
# It reads restricted artefacts (data/analysis_dataset.csv, data/predictions.csv), an
# internal checksum file and a historical Git tag, so it cannot run against a clean clone
# of the public code release. That is by design and is stated in README.md and in
# docs/audit/LOCKED_RELEASE_CODE_VERIFICATION.md. The public-safe alternative, which needs
# no database and no patient-level data, is `verify_public_release.py` at the
# repository root.

# provenance on every released artefact
missing_prov = []
for grp, ext in [("data", ".csv"), ("tables", ".xlsx")]:
    for f in os.listdir(os.path.join(FR, grp)):
        if f.endswith(ext) and not os.path.exists(
                os.path.join(FR, grp, f + ".meta.json")):
            missing_prov.append(f"{grp}/{f}")
for f in os.listdir(FIGS):
    if f.endswith((".png", ".pdf")) and not os.path.exists(
            os.path.join(FIGS, f + ".meta.json")):
        missing_prov.append(f"figures/{f}")
check("provenance stamp on every released artefact", not missing_prov,
      f"missing: {missing_prov}")

# ---------------------------------------------------------------- report
print("=" * 96)
print("FINAL RELEASE CHECK")
print("=" * 96)
for name, ok, detail in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<46} {detail}")
print("-" * 96)
print(f"  {len(checks) - len(fails)}/{len(checks)} checks passed")
if fails:
    print("\n  FAILURES:")
    for f in fails:
        print(f"    - {f}")
    raise SystemExit(1)
print("\n  RELEASE VERIFIED: tag, artefacts, manifest, checksums, suites and")
print("  documents are mutually consistent.")
