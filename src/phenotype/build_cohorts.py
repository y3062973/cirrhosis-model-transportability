"""PHASE 2 -- rebuild all three cohorts from the raw databases under the frozen
strict cirrhosis phenotype.

No previous cohort CSV or derived table is read. The only inputs are:
  * final_analysis_config.py   (the frozen phenotype and eligibility rules)
  * the four PostgreSQL databases, read-only

Outputs (all provenance-stamped):
  FINAL_REBUILD/data/cohort_mimic.csv
  FINAL_REBUILD/data/cohort_eicu.csv
  FINAL_REBUILD/data/cohort_nwicu.csv
  FINAL_REBUILD/data/cohort_flow.csv
  FINAL_REBUILD/tables/TableS8_cohort_composition.xlsx
  FINAL_REBUILD/data/cohort_old_vs_new.csv
"""
from __future__ import annotations

import db  # noqa: E402  shared environment-based connection helper
import io
import os
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
for d in (DATA, TABLES, LOGS):
    os.makedirs(d, exist_ok=True)
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


def sql_prefix_pred(col: str, prefixes: list[str]) -> str:
    """SQL predicate: normalised code starts with any prefix."""
    parts = [f"UPPER(REPLACE(BTRIM({col}),'.','')) LIKE '{p}%%'" for p in prefixes]
    return "(" + " OR ".join(parts) + ")"


prov.announce("phase_2_cohorts.py")
log(f"  phenotype: {len(cfg.STRICT_CIRRHOSIS_PREFIXES)} strict prefixes")
log(f"  excluded : {cfg.CIRRHOSIS_EXCLUDED_PREFIXES}")

flow = []
S = sql_prefix_pred("d.icd_code", cfg.STRICT_CIRRHOSIS_PREFIXES)
B = sql_prefix_pred("d.icd_code", cfg.BROAD_PREFIXES)

# ===================================================================== MIMIC
log("\n" + "=" * 100)
log("MIMIC-IV")
log("=" * 100)
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT d.hadm_id FROM mimiciv_hosp.diagnoses_icd d WHERE {S}
        """)
        strict_h = {r[0] for r in cur.fetchall()}
        cur.execute(f"""
            SELECT DISTINCT d.hadm_id FROM mimiciv_hosp.diagnoses_icd d WHERE {B}
        """)
        broad_h = {r[0] for r in cur.fetchall()}
        log(f"  admissions, strict cirrhosis : {len(strict_h):,}")
        log(f"  admissions, broad phenotype  : {len(broad_h):,}  (+{len(broad_h-strict_h):,})")
        flow.append(dict(centre="MIMIC-IV", step="admissions with strict cirrhosis codes",
                         n=len(strict_h)))

        hl = ",".join(str(int(x)) for x in strict_h)
        cur.execute(f"""
            WITH st AS (
              SELECT i.subject_id, i.hadm_id, i.stay_id, i.intime, i.outtime, i.los,
                     ROW_NUMBER() OVER (PARTITION BY i.hadm_id ORDER BY i.intime) AS rn
              FROM mimiciv_icu.icustays i WHERE i.hadm_id IN ({hl})
            )
            SELECT s.subject_id, s.hadm_id, s.stay_id, s.rn, s.intime, s.outtime, s.los,
                   a.admittime, a.dischtime, a.deathtime, a.hospital_expire_flag,
                   a.race, a.admission_type, p.gender, p.anchor_age, p.dod
            FROM st s
            JOIN mimiciv_hosp.admissions a ON a.hadm_id = s.hadm_id
            JOIN mimiciv_hosp.patients  p ON p.subject_id = s.subject_id
        """)
        m = pd.DataFrame(cur.fetchall(), columns=[
            "subject_id", "hadm_id", "stay_id", "rn", "icu_intime", "icu_outtime",
            "icu_los", "admittime", "dischtime", "deathtime", "hospital_expire_flag",
            "race", "admission_type", "gender", "anchor_age", "dod"])
log(f"  ICU stays in those admissions : {len(m):,}")
flow.append(dict(centre="MIMIC-IV", step="+ ICU stays", n=len(m)))

m = m[m.rn == 1] if cfg.FIRST_ICU_STAY_ONLY else m
flow.append(dict(centre="MIMIC-IV", step="+ first ICU stay per admission", n=len(m)))
m["age"] = pd.to_numeric(m.anchor_age, errors="coerce")
m = m[m.age >= cfg.AGE_MIN]
flow.append(dict(centre="MIMIC-IV", step=f"+ age >= {cfg.AGE_MIN}", n=len(m)))
m = m[(pd.to_numeric(m.icu_los, errors="coerce") > 0) &
      (pd.to_numeric(m.icu_los, errors="coerce") <= cfg.ICU_LOS_MAX_DAYS)]
flow.append(dict(centre="MIMIC-IV", step="+ plausible ICU LOS", n=len(m)))
for c_ in ["admittime", "dischtime", "deathtime", "dod", "icu_intime", "icu_outtime"]:
    m[c_] = pd.to_datetime(m[c_], errors="coerce")
off = (m.icu_intime - m.admittime).dt.total_seconds() / 3600
m = m[off <= cfg.ICU_TO_ADMIT_MAX_HOURS]
flow.append(dict(centre="MIMIC-IV", step="+ ICU within 24h of hospital admission", n=len(m)))
m = m[m.hospital_expire_flag.notna()]
flow.append(dict(centre="MIMIC-IV", step="+ hospital outcome recorded", n=len(m)))
m["male"] = (m.gender.astype(str).str.upper().str[0] == "M").astype(int)
m["hospital_mortality"] = pd.to_numeric(m.hospital_expire_flag, errors="coerce").astype(int)
m["death_by_discharge"] = ((m.dod.notna()) & (m.dod <= m.dischtime)).astype(int)
m["death_30d_best"] = ((m.dod.notna()) &
                       (m.dod <= m.admittime + pd.Timedelta(days=30))).astype(int)
m["centre"] = "MIMIC-IV"
m["phenotype"] = "strict"
log(f"  FINAL MIMIC cohort: {len(m):,} stays, {m.subject_id.nunique():,} patients, "
    f"{int(m.hospital_mortality.sum()):,} deaths ({100*m.hospital_mortality.mean():.1f}%)")

# ===================================================================== eICU
log("\n" + "=" * 100)
log("eICU-CRD v2")
log("=" * 100)
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute("SELECT patientunitstayid, icd9code FROM eicu_crd.diagnosis "
                    "WHERE icd9code <> ''")
        dx = cur.fetchall()
strict_stay, broad_stay, contrib = set(), set(), {}
for sid, s in dx:
    for tok in str(s).replace(";", ",").split(","):
        t = tok.strip()
        if not t:
            continue
        n = cfg.normalise_code(t)
        if cfg.is_strict_cirrhosis_code(n):
            strict_stay.add(sid)
            contrib[n] = contrib.get(n, 0) + 1
        if cfg.is_broad_code(n):
            broad_stay.add(sid)
log(f"  stays, strict cirrhosis : {len(strict_stay):,}")
log(f"  stays, broad phenotype  : {len(broad_stay):,}  (+{len(broad_stay-strict_stay):,})")
log(f"  code contributions (strict): "
    f"{dict(sorted(contrib.items(), key=lambda kv: -kv[1]))}")
flow.append(dict(centre="eICU", step="stays with strict cirrhosis codes", n=len(strict_stay)))

sl = ",".join(str(int(x)) for x in strict_stay)
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT p.patientunitstayid, p.uniquepid, p.hospitalid, p.gender, p.age,
                   p.ethnicity, p.unitvisitnumber, p.hospitaldischargestatus,
                   p.unitdischargestatus, p.hospitaladmittime24, p.hospitaldischargetime24,
                   p.unitadmittime24, p.unitdischargetime24,
                   h.teachingstatus, h.region, h.numbedscategory
            FROM eicu_crd.patient p LEFT JOIN eicu_crd.hospital h USING (hospitalid)
            WHERE p.patientunitstayid IN ({sl})
        """)
        e = pd.DataFrame(cur.fetchall(), columns=[
            "stay_id", "patient_uid", "hospitalid", "gender", "age", "ethnicity",
            "unitvisitnumber", "hosp_status", "unit_status", "adm24", "disch24",
            "unitadm24", "unitdisch24", "teachingstatus", "region", "numbedscategory"])
log(f"  rows retrieved: {len(e):,}")
flow.append(dict(centre="eICU", step="+ patient rows", n=len(e)))

e["age_num"] = pd.to_numeric(e.age.where(e.age.astype(str).str.fullmatch(r"\s*\d+\s*",
                                                                        na=False)),
                             errors="coerce")
e.loc[e.age.astype(str).str.strip() == "> 89", "age_num"] = 90.0
e = e[e.age_num.notna() & (e.age_num >= cfg.AGE_MIN)]
flow.append(dict(centre="eICU", step=f"+ age >= {cfg.AGE_MIN}", n=len(e)))
e = e[e.hosp_status.isin(["Alive", "Expired"])]
flow.append(dict(centre="eICU", step="+ hospital outcome recorded", n=len(e)))
e = e[e.unitvisitnumber == 1] if cfg.FIRST_ICU_STAY_ONLY else e
flow.append(dict(centre="eICU", step="+ first ICU stay (unitvisitnumber=1)", n=len(e)))
e["age"] = e.age_num
e["male"] = (e.gender.astype(str).str.lower() == "male").astype(int)
e["hospital_mortality"] = (e.hosp_status == "Expired").astype(int)
e["death_30d_best"] = np.nan
e["centre"] = "eICU"
e["phenotype"] = "strict"
log(f"  FINAL eICU cohort: {len(e):,} stays, {e.patient_uid.nunique():,} patients, "
    f"{int(e.hospital_mortality.sum()):,} deaths ({100*e.hospital_mortality.mean():.1f}%)")

# ===================================================================== nwICU
log("\n" + "=" * 100)
log("nwICU v0.1")
log("=" * 100)
with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT d.subject_id, d.hadm_id, d.icd_code
            FROM public.diagnoses_icd d WHERE {S}
        """)
        nw_strict = cur.fetchall()
        cur.execute(f"""
            SELECT DISTINCT d.hadm_id FROM public.diagnoses_icd d WHERE {B}
        """)
        nw_broad = {r[0] for r in cur.fetchall()}
nw_h = sorted({r[1] for r in nw_strict})
log(f"  admissions, strict cirrhosis : {len(nw_h):,}")
log(f"  admissions, broad phenotype  : {len(nw_broad):,}  (+{len(nw_broad-set(nw_h)):,})")
flow.append(dict(centre="nwICU", step="admissions with strict cirrhosis codes", n=len(nw_h)))

hl = ",".join(str(int(x)) for x in nw_h)
with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT a.subject_id, a.hadm_id, a.admittime, a.dischtime, a.deathtime,
                   a.hospital_expire_flag, a.race, a.admission_type,
                   p.gender, p.anchor_age, p.dod,
                   i.stay_id, i.intime, i.outtime, i.los
            FROM public.admissions a
            JOIN public.patients p ON p.subject_id = a.subject_id
            LEFT JOIN (SELECT hadm_id, min(stay_id) AS stay_id, min(intime) AS intime,
                              max(outtime) AS outtime, max(los) AS los
                       FROM public.icustays GROUP BY hadm_id) i ON i.hadm_id = a.hadm_id
            WHERE a.hadm_id IN ({hl})
        """)
        n = pd.DataFrame(cur.fetchall(), columns=[
            "subject_id", "hadm_id", "admittime", "dischtime", "deathtime",
            "hospital_expire_flag", "race", "admission_type", "gender", "anchor_age",
            "dod", "stay_id", "icu_intime", "icu_outtime", "icu_los"])
log(f"  rows retrieved: {len(n):,}")
flow.append(dict(centre="nwICU", step="+ admissions with patient row", n=len(n)))
n = n[n.icu_intime.notna()]
flow.append(dict(centre="nwICU", step="+ has an ICU stay", n=len(n)))
for c_ in ["admittime", "dischtime", "deathtime", "dod", "icu_intime", "icu_outtime"]:
    n[c_] = pd.to_datetime(n[c_], errors="coerce")
n["age"] = pd.to_numeric(n.anchor_age, errors="coerce")
n = n[n.age >= cfg.AGE_MIN]
flow.append(dict(centre="nwICU", step=f"+ age >= {cfg.AGE_MIN}", n=len(n)))
n = n[(pd.to_numeric(n.icu_los, errors="coerce") > 0) &
      (pd.to_numeric(n.icu_los, errors="coerce") <= cfg.ICU_LOS_MAX_DAYS)]
off = (n.icu_intime - n.admittime).dt.total_seconds() / 3600
n = n[off <= cfg.ICU_TO_ADMIT_MAX_HOURS]
flow.append(dict(centre="nwICU", step="+ first ICU stay within 24h of admission", n=len(n)))
n["male"] = (n.gender.astype(str).str.upper().str[0] == "M").astype(int)
n["hospital_mortality"] = ((n.deathtime.notna()) &
                           (n.deathtime <= n.dischtime + pd.Timedelta(days=1))).astype(int)
# PHASE 3: best available death time
n["death_time_best"] = n.deathtime.combine_first(n.dod)
n["death_30d_best"] = ((n.death_time_best.notna()) &
                       (n.death_time_best <= n.admittime + pd.Timedelta(days=30))).astype(int)
n["centre"] = "nwICU"
n["phenotype"] = "strict"
log(f"  FINAL nwICU cohort: {len(n):,} stays, {n.subject_id.nunique():,} patients, "
    f"30-day deaths {int(n.death_30d_best.sum()):,} ({100*n.death_30d_best.mean():.1f}%)")

# ===================================================================== persist
for name, df in [("cohort_mimic.csv", m), ("cohort_eicu.csv", e), ("cohort_nwicu.csv", n)]:
    p = os.path.join(DATA, name)
    df.to_csv(p, index=False, encoding="utf-8-sig")
    prov.stamp(p, "phase_2_cohorts.py")
    log(f"  wrote {name} ({len(df):,} rows)")

fl = pd.DataFrame(flow)
fl.to_csv(os.path.join(DATA, "cohort_flow.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "cohort_flow.csv"), "phase_2_cohorts.py")
log("\n" + "=" * 100)
log("COHORT FLOW")
log("=" * 100)
log(fl.to_string(index=False))

log("\n" + "=" * 100)
log("CROSS-CENTRE CONSISTENCY CHECK")
log("=" * 100)
log(f"  {'centre':<10}{'stays':>9}{'patients':>10}{'deaths':>8}{'mortality%':>12}{'median age':>12}")
for nm, df, idc, outc in [("MIMIC-IV", m, "subject_id", "hospital_mortality"),
                          ("eICU", e, "patient_uid", "hospital_mortality"),
                          ("nwICU", n, "subject_id", "death_30d_best")]:
    med = df.age.median()
    log(f"  {nm:<10}{len(df):>9,}{df[idc].nunique():>10,}"
        f"{int(df[outc].sum()):>8,}{100*df[outc].mean():>12.1f}{med:>12.1f}")

with open(os.path.join(LOGS, "PHASE_2_cohorts.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nPHASE 2 DONE")
