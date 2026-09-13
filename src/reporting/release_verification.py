"""Verify a release against PUBLICATION_ARTIFACT_CHECKSUMS.txt.

Re-hashes every released data / table / figure file and reports any mismatch. Exit
code is non-zero if anything differs, so the check can gate a submission.

Usage:  python verify_release.py
"""
from __future__ import annotations

import io
import os
import sys

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

CK = os.path.join(FR, "PUBLICATION_ARTIFACT_CHECKSUMS.txt")
if not os.path.exists(CK):
    raise SystemExit(f"missing {CK}; run publock_02_release.py first")

ok = bad = missing = 0
problems = []
with io.open(CK, encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line or line.startswith("#") or line.startswith("##"):
            continue
        if "  " not in line:
            continue
        digest, rel = line.split("  ", 1)
        path = os.path.join(FR, rel.replace("/", os.sep))
        if not os.path.exists(path):
            missing += 1
            problems.append(f"MISSING  {rel}")
            continue
        actual = prov.sha256_file(path)
        if actual == digest:
            ok += 1
        else:
            bad += 1
            problems.append(f"MISMATCH {rel}\n    expected {digest}\n    actual   {actual}")

print(f"verified : {ok}")
print(f"mismatch : {bad}")
print(f"missing  : {missing}")
if problems:
    print("\nproblems:")
    for p in problems:
        print("  " + p)
    raise SystemExit(1)
print("\nALL RELEASED ARTEFACTS MATCH THE FROZEN CHECKSUMS")
