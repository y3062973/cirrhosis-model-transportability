"""PHASE 2b + PHASE 1b -- cohort code composition, old-vs-new comparison,
dependency lockfile, and git commit.
"""
from __future__ import annotations

import db  # noqa: E402  shared environment-based connection helper
import io
import os
import subprocess
import sys
import warnings

import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
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

import final_analysis_config as cfg  # noqa: E402
import provenance as prov  # noqa: E402

DATA = str(repo.DATA)
TABLES = str(repo.TABLES)
LOGS = str(repo.LOGS)
repo.ensure_writable_dirs()
LOG = io.StringIO()
# Credentials come from the environment; see .env.example and db.py.
# The original hardcoded local credentials were removed for public release.
PG = dict(connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")))


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


def conn(dbname):
    c = db.connect(dbname)  # credentials from the environment
    c.set_session(readonly=True, autocommit=True)
    with c.cursor() as cur:
        cur.execute("SET max_parallel_workers_per_gather = 0")
    return c


prov.announce("phase_2b_composition.py")

# ===================================================================== code composition
log("\n" + "=" * 100)
log("CODE COMPOSITION BY COHORT")
log("=" * 100)
rows = []
# The database-name loop variable is `dbname`, NOT `db`: naming it `db` rebinds the
# module-level `db` import to a string at module scope, so the `conn()` helper below
# would call `.connect` on that string and fail with AttributeError.
for centre, dbname, tbl, col, key in [
        ("MIMIC-IV", "mimiciv3", "mimiciv_hosp.diagnoses_icd", "icd_code", "hadm_id"),
        ("nwICU", "nwicu", "public.diagnoses_icd", "icd_code", "hadm_id")]:
    with conn(dbname) as c:
        with c.cursor() as cur:
            cur.execute(f"SELECT DISTINCT {key}, {col} FROM {tbl}")
            data = cur.fetchall()
    per_code = {}
    hadm_sets = {}
    for h, code in data:
        n = cfg.normalise_code(code)
        if cfg.is_strict_cirrhosis_code(n):
            root = next(p for p in cfg.STRICT_CIRRHOSIS_PREFIXES if n.startswith(p))
            per_code.setdefault(root, set()).add(h)
            hadm_sets.setdefault(h, set()).add(root)
    for root, hs in sorted(per_code.items()):
        rows.append(dict(centre=centre, code_root=root, n_admissions=len(hs),
                         pct_of_strict_cohort=round(
                             100 * len(hs) / max(len(hadm_sets), 1), 1)))
    log(f"  {centre}: {len(hadm_sets):,} strict admissions, "
        f"{len(per_code)} distinct qualifying code roots")

# eICU: split the multi-code strings
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute("SELECT patientunitstayid, icd9code FROM eicu_crd.diagnosis "
                    "WHERE icd9code <> ''")
        data = cur.fetchall()
per_code, stay_sets = {}, {}
for sid, s in data:
    for tok in str(s).replace(";", ",").split(","):
        n = cfg.normalise_code(tok)
        if not n:
            continue
        if cfg.is_strict_cirrhosis_code(n):
            root = next(p for p in cfg.STRICT_CIRRHOSIS_PREFIXES if n.startswith(p))
            per_code.setdefault(root, set()).add(sid)
            stay_sets.setdefault(sid, set()).add(root)
for root, ss in sorted(per_code.items()):
    rows.append(dict(centre="eICU", code_root=root, n_admissions=len(ss),
                     pct_of_strict_cohort=round(100 * len(ss) / max(len(stay_sets), 1), 1)))
log(f"  eICU: {len(stay_sets):,} strict stays, {len(per_code)} distinct qualifying code roots")

comp = pd.DataFrame(rows)
log("\n" + comp.to_string(index=False))

# multi-code overlap: how many patients carry >1 qualifying root
log("\n  patients/admissions with more than one qualifying code root:")
for centre, sets in [("MIMIC-IV", None), ("eICU", stay_sets), ("nwICU", None)]:
    if sets is None:
        continue
    n_multi = sum(1 for v in sets.values() if len(v) > 1)
    log(f"    {centre:<10} {n_multi:,} of {len(sets):,} "
        f"({100*n_multi/len(sets):.1f}%)")

# ===================================================================== old vs new cohort
log("\n" + "=" * 100)
log("OLD vs NEW COHORT (old = superseded K74*|5715*|5712* / K74*-only rules)")
log("=" * 100)
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE icd_code LIKE 'K74%' OR icd_code LIKE '5715%'
                          OR icd_code LIKE '5712%'""")
        old_m = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE UPPER(REPLACE(BTRIM(icd_code),'.','')) LIKE ANY(%s)""",
                    (["K703%", "K717%", "K743%", "K744%", "K745%", "K746%",
                      "5712%", "5715%", "5716%"],))
        new_m = {r[0] for r in cur.fetchall()}
new_cohort = set(pd.read_csv(os.path.join(DATA, "cohort_mimic.csv")).hadm_id)
both = len(old_m & new_m)
log(f"  MIMIC (admission level, phenotype only, before ICU filters)")
log(f"    old rule only : {len(old_m - new_m):,}")
log(f"    new rule only : {len(new_m - old_m):,}")
log(f"    both          : {both:,}")

# why did admissions leave?  fibrosis-only, i.e. K74.0-2 with no cirrhosis code
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE icd_code LIKE 'K74%'""")
        k74 = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE UPPER(REPLACE(BTRIM(icd_code),'.','')) LIKE ANY(%s)""",
                    (["K743%", "K744%", "K745%", "K746%"],))
        k74cirr = {r[0] for r in cur.fetchall()}
fib_only = k74 - k74cirr
log(f"    admissions left out because they carry ONLY fibrosis codes (K74.0-2): "
    f"{len(fib_only):,}")
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE UPPER(REPLACE(BTRIM(icd_code),'.','')) LIKE 'K703%'""")
        k703 = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT hadm_id FROM mimiciv_hosp.diagnoses_icd
                       WHERE icd_code LIKE '5712%'""")
        v5712 = {r[0] for r in cur.fetchall()}
log(f"    admissions ADDED by including K70.3 (alcoholic cirrhosis): "
    f"{len(k703 - old_m):,}")
log(f"    of which also have 571.2 : {len(k703 & v5712):,}")
log(f"    of which K70.3 only      : {len(k703 - v5712):,}")

# sample the new-only admissions for human review
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        newonly = sorted(new_m - old_m)[:400]
        if newonly:
            hl = ",".join(str(int(x)) for x in newonly)
            cur.execute(f"""
                SELECT d.hadm_id, d.icd_code, dd.long_title
                FROM mimiciv_hosp.diagnoses_icd d
                LEFT JOIN mimiciv_hosp.d_icd_diagnoses dd
                       ON dd.icd_code = d.icd_code AND dd.icd_version = d.icd_version
                WHERE d.hadm_id IN ({hl})
                  AND UPPER(REPLACE(BTRIM(d.icd_code),'.','')) LIKE ANY(%s)
            """, (["K703%", "K717%", "K743%", "K744%", "K745%", "K746%"],))
            rev = pd.DataFrame(cur.fetchall(), columns=["hadm_id", "icd_code", "title"])
rev_path = os.path.join(DATA, "cohort_newonly_review_sample.csv")
rev.to_csv(rev_path, index=False, encoding="utf-8-sig")
prov.stamp(rev_path, "phase_2b_composition.py")
log(f"\n    wrote {len(rev)} new-only qualifying code rows for human review "
    f"(cohort_newonly_review_sample.csv)")
log("    distinct descriptors driving the ADDITIONS:")
if len(rev):
    log(rev.groupby(["icd_code", "title"]).size().sort_values(ascending=False)
        .head(12).to_string())

# eICU and nwICU old vs new
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute("SELECT patientunitstayid, icd9code FROM eicu_crd.diagnosis "
                    "WHERE icd9code <> ''")
        d = cur.fetchall()
old_rule = r"(^|[,\s])(571\.?[256]|K70\.?[234]|K74\.?[3456])([,\s]|$)"
import re as _re
old_e = {s for s, t in d if _re.search(old_rule, str(t))}
new_e = stay_sets.keys()
log(f"\n  eICU (stay level)")
log(f"    old rule only : {len(old_e - new_e):,}")
log(f"    new rule only : {len(new_e - old_e):,}")
log(f"    both          : {len(old_e & new_e):,}")
log(f"    -> the old eICU rule also admitted K70.2 and K70.4; those {len(old_e - new_e)}")
log(f"       stays are now correctly EXCLUDED (fibrosis / hepatic failure, not cirrhosis)")

with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute("SELECT DISTINCT hadm_id FROM public.diagnoses_icd "
                    "WHERE icd_code LIKE 'K74%'")
        old_n = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT hadm_id FROM public.diagnoses_icd
                       WHERE UPPER(REPLACE(BTRIM(icd_code),'.','')) LIKE ANY(%s)""",
                    (["K703%", "K717%", "K743%", "K744%", "K745%", "K746%"],))
        new_n = {r[0] for r in cur.fetchall()}
log(f"\n  nwICU (admission level)")
log(f"    old rule only : {len(old_n - new_n):,}")
log(f"    new rule only : {len(new_n - old_n):,}")
log(f"    both          : {len(old_n & new_n):,}")

ov = pd.DataFrame([
    dict(centre="MIMIC-IV", old_rule="K74*|5715*|5712*",
         new_rule="K703,K717,K743-K746,5712,5715,5716",
         old_n=len(old_m), new_n=len(new_m), old_only=len(old_m - new_m),
         new_only=len(new_m - old_m), both=both),
    dict(centre="eICU", old_rule="571.2/5/6|K70.2-4|K74.3-6",
         new_rule="571.2/5/6|K703,K717,K743-K746",
         old_n=len(old_e), new_n=len(new_e), old_only=len(old_e - new_e),
         new_only=len(new_e - old_e), both=len(old_e & new_e)),
    dict(centre="nwICU", old_rule="K74*", new_rule="K703,K717,K743-K746",
         old_n=len(old_n), new_n=len(new_n), old_only=len(old_n - new_n),
         new_only=len(new_n - old_n), both=len(old_n & new_n)),
])
ov.to_csv(os.path.join(DATA, "cohort_old_vs_new.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "cohort_old_vs_new.csv"), "phase_2b_composition.py")
log("\n" + ov.to_string(index=False))

with pd.ExcelWriter(os.path.join(TABLES, "TableS8_cohort_composition.xlsx"),
                    engine="openpyxl") as xl:
    comp.to_excel(xl, sheet_name="code_composition", index=False)
    ov.to_excel(xl, sheet_name="old_vs_new", index=False)
    if len(rev):
        rev.to_excel(xl, sheet_name="new_only_review_sample", index=False)
prov.stamp(os.path.join(TABLES, "TableS8_cohort_composition.xlsx"),
           "phase_2b_composition.py")

# ===================================================================== dependency lock
log("\n" + "=" * 100)
log("DEPENDENCY LOCKFILE")
log("=" * 100)
pk = prov.package_versions()
lines = ["# FINAL_REBUILD dependency lock -- generated from the live environment",
         f"# python {pk['python']}", f"# platform {pk['platform']}", ""]
for k, v in pk.items():
    if k in ("python", "platform"):
        continue
    lines.append(f"{k}=={v}" if v not in ("NOT_INSTALLED", "unknown") else f"# {k} {v}")
req = os.path.join(FR, "requirements.txt")
with open(req, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
prov.stamp(req, "phase_2b_composition.py")
log(f"  wrote requirements.txt  ({len(lines)} lines)  sha256={prov.sha256_file(req)[:32]}")
for ln in lines[:12]:
    log(f"    {ln}")

with open(os.path.join(LOGS, "PHASE_2b_composition.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())

# ===================================================================== git commit
log("\n" + "=" * 100)
log("GIT COMMIT")
log("=" * 100)
for cmd in (["git", "add", "-A"],
            ["git", "commit", "-q", "-m",
             "FINAL_REBUILD: frozen config, cirrhosis phenotype, cohorts, dependency lock"]):
    r = subprocess.run(cmd, cwd=FR, capture_output=True, text=True)
    log(f"  {' '.join(cmd[:3])} -> rc={r.returncode} {r.stdout.strip()[:120]}"
        f"{r.stderr.strip()[:200]}")
r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=FR, capture_output=True, text=True)
log(f"  HEAD = {r.stdout.strip()}")
r = subprocess.run(["git", "log", "--oneline"], cwd=FR, capture_output=True, text=True)
log("  log:")
for ln in r.stdout.strip().splitlines():
    log(f"    {ln}")

log("\nPHASE 2b DONE")
