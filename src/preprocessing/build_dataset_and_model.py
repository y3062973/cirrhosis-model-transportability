"""PHASE 3-4 -- predictor extraction, QC, and FINAL_MODEL_V2.

Reads the frozen cohorts from PHASE 2 and extracts predictors from the raw
databases over the configured window, applies the configured aggregation and
plausibility rules, then fits the frozen model.

Guarantees enforced by assertions in this script:
  * the predictor list comes ONLY from final_analysis_config (no local redefinition)
  * no penalty is applied (cfg.PENALTY is None)
  * missing indicators are ONLY those in cfg.MISSING_INDICATORS_PRIMARY, and each
    must actually exist in the development cohort with >= MIN_MISSING_FOR_INDICATOR
    missing values, else the run FAILS
  * if the unpenalized fit does not converge, the run STOPS and reports; no penalty
    is added automatically

Outputs:
  FINAL_REBUILD/data/analysis_dataset.csv
  FINAL_REBUILD/data/qc_flags.csv
  FINAL_REBUILD/data/model_v2_coefficients.csv
  FINAL_REBUILD/data/predictions.csv
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
LOGS = str(repo.LOGS)
repo.ensure_writable_dirs()
LOG = io.StringIO()
# Credentials come from the environment; see .env.example and db.py.
# The original hardcoded local credentials were removed for public release.
PG = dict(connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")))
CONT = cfg.PRIMARY_CONTINUOUS            # imported, never redefined
BIN = cfg.PRIMARY_BINARY


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


prov.announce("phase_3_4_dataset_model.py")
log(f"  predictors imported from config: {CONT} + {BIN}")
log(f"  window PRIMARY = {cfg.WINDOW_PRIMARY_HOURS}h   EARLY = {cfg.WINDOW_EARLY_HOURS}h")
log(f"  penalty = {cfg.PENALTY}   separation policy = {cfg.SEPARATION_POLICY}")
log(f"  missing indicators (frozen) = {cfg.MISSING_INDICATORS_PRIMARY}")

assert cfg.PENALTY is None, "penalty must be None"
for c in cfg.MISSING_INDICATORS_PRIMARY:
    assert c in CONT, f"indicator variable {c} not in PRIMARY_CONTINUOUS"

W = cfg.WINDOW_PRIMARY_HOURS
qc_rows = []


def qc(centre, check, detail, value):
    qc_rows.append(dict(centre=centre, check=check, detail=detail, value=value))
    log(f"    QC {check:<38} {detail:<46} {value}")


# ===================================================================== MIMIC
log("\n" + "=" * 100)
log(f"MIMIC-IV predictor extraction (window: intime < t <= intime + {W}h)")
log("=" * 100)
co_m = pd.read_csv(os.path.join(DATA, "cohort_mimic.csv"), low_memory=False)
ids = [int(x) for x in co_m.stay_id]
log(f"  cohort stays: {len(ids):,}")

MIMIC_LAB_MIN = {50862: "albumin", 50983: "sodium", 51265: "platelet",
                 51222: "hemoglobin"}
MIMIC_LAB_MAX = {50885: "bilirubin", 50912: "creatinine", 51301: "wbc"}
MIMIC_VIT_MEAN = {220045: "heart_rate", 220181: "map", 220210: "resp_rate",
                  220277: "spo2"}
MIMIC_VIT_ALT = {220052: "map_art"}       # arterial MAP, used to test provenance

with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT i.stay_id, l.itemid, min(l.valuenum), max(l.valuenum),
                   min(l.charttime), max(l.charttime), count(*)
            FROM mimiciv_hosp.labevents l
            JOIN mimiciv_icu.icustays i ON i.hadm_id = l.hadm_id
            WHERE i.stay_id = ANY(%s) AND l.itemid = ANY(%s)
              AND l.charttime >  i.intime
              AND l.charttime <= i.intime + interval '{W} hours'
              AND l.valuenum IS NOT NULL
            GROUP BY 1,2
        """, (ids, list(MIMIC_LAB_MIN) + list(MIMIC_LAB_MAX)))
        mlab = pd.DataFrame(cur.fetchall(), columns=["stay_id", "itemid", "vmin", "vmax",
                                                     "tmin", "tmax", "n"])
        cur.execute(f"""
            SELECT ce.stay_id, ce.itemid, avg(ce.valuenum), count(*),
                   avg(ce.valuenum * ce.valuenum)
            FROM mimiciv_icu.chartevents ce
            JOIN mimiciv_icu.icustays i ON i.stay_id = ce.stay_id
            WHERE ce.stay_id = ANY(%s) AND ce.itemid = ANY(%s)
              AND ce.charttime >  i.intime
              AND ce.charttime <= i.intime + interval '{W} hours'
              AND ce.valuenum IS NOT NULL
            GROUP BY 1,2
        """, (ids, list(MIMIC_VIT_MEAN) + list(MIMIC_VIT_ALT)))
        mvit = pd.DataFrame(cur.fetchall(), columns=["stay_id", "itemid", "vavg", "n",
                                                     "v2"])
        # temperature units, verified per row (PHASE 11)
        cur.execute("""
            SELECT ce.itemid, ce.valueuom, count(*)
            FROM mimiciv_icu.chartevents ce
            WHERE ce.itemid IN (223761, 223762) AND ce.valuenum IS NOT NULL
            GROUP BY 1,2 ORDER BY 1,3 DESC
        """)
        tu = pd.DataFrame(cur.fetchall(), columns=["itemid", "valueuom", "n"])
log(f"  labevent aggregates: {len(mlab):,}   chartevent aggregates: {len(mvit):,}")
log("\n  MIMIC temperature itemid/valueuom cross-tab (PHASE 11):")
log(tu.to_string(index=False))
qc("MIMIC-IV", "temperature unit", "rows with unexpected valueuom",
   int(tu[~tu.valueuom.isin(["deg F", "deg C", "掳F", "掳C"])].n.sum()))

mm = co_m[["stay_id", "hadm_id", "subject_id", "centre", "age", "male",
           "hospital_mortality", "death_30d_best", "death_by_discharge",
           "admittime", "dischtime", "deathtime", "dod", "icu_intime",
           "icu_outtime"]].copy()
mm["hospitalid"] = pd.NA          # MIMIC-IV is a single centre; no hospital column
for item, name in MIMIC_LAB_MIN.items():
    mm[name] = mm.stay_id.map(mlab[mlab.itemid == item].set_index("stay_id").vmin)
for item, name in MIMIC_LAB_MAX.items():
    mm[name] = mm.stay_id.map(mlab[mlab.itemid == item].set_index("stay_id").vmax)
for item, name in MIMIC_VIT_MEAN.items():
    mm[name] = mm.stay_id.map(mvit[mvit.itemid == item].set_index("stay_id").vavg)
mm["map_arterial"] = mm.stay_id.map(
    mvit[mvit.itemid == 220052].set_index("stay_id").vavg)
mm["centre"] = "MIMIC-IV"

# ===================================================================== eICU
log("\n" + "=" * 100)
log(f"eICU predictor extraction (window: 0 < offset <= {W*60} min)")
log("=" * 100)
co_e = pd.read_csv(os.path.join(DATA, "cohort_eicu.csv"), low_memory=False)
ids_e = [int(x) for x in co_e.stay_id]
EICU_LAB_MIN = {"albumin": "albumin", "sodium": "sodium", "platelets x 1000": "platelet",
                "Hgb": "hemoglobin"}
EICU_LAB_MAX = {"total bilirubin": "bilirubin", "creatinine": "creatinine",
                "WBC x 1000": "wbc"}
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT patientunitstayid, labname, min(labresult), max(labresult), count(*)
            FROM eicu_crd.lab
            WHERE patientunitstayid = ANY(%s) AND labresult IS NOT NULL
              AND labresultoffset > 0 AND labresultoffset <= {W*60}
              AND labname = ANY(%s)
            GROUP BY 1,2
        """, (ids_e, list(EICU_LAB_MIN) + list(EICU_LAB_MAX)))
        elab = pd.DataFrame(cur.fetchall(), columns=["stay_id", "labname", "vmin",
                                                     "vmax", "n"])
        cur.execute(f"""
            SELECT patientunitstayid, avg(heartrate), avg(systemicmean),
                   avg(respiration), avg(sao2), count(*)
            FROM eicu_crd.vitalperiodic
            WHERE patientunitstayid = ANY(%s)
              AND observationoffset > 0 AND observationoffset <= {W*60}
            GROUP BY 1
        """, (ids_e,))
        evp = pd.DataFrame(cur.fetchall(), columns=["stay_id", "hr_vp", "map_vp",
                                                    "rr_vp", "spo2_vp", "n_vp"])
        cur.execute(f"""
            SELECT patientunitstayid, avg(noninvasivemean),
                   avg(noninvasivesystolic), avg(noninvasivediastolic),
                   avg(noninv_dummy) FROM (
              SELECT patientunitstayid, noninvasivemean, noninvasivesystolic,
                     noninvasivediastolic, 0 AS noninv_dummy
              FROM eicu_crd.vitalaperiodic
              WHERE patientunitstayid = ANY(%s)
                AND observationoffset > 0 AND observationoffset <= {W*60}
            ) t GROUP BY 1
        """, (ids_e,)) if False else None
        cur.execute(f"""
            SELECT patientunitstayid, avg(noninvasivemean), avg(noninvasivesystolic),
                   avg(noninvasivediastolic), count(*)
            FROM eicu_crd.vitalaperiodic
            WHERE patientunitstayid = ANY(%s)
              AND observationoffset > 0 AND observationoffset <= {W*60}
            GROUP BY 1
        """, (ids_e,))
        eva = pd.DataFrame(cur.fetchall(), columns=["stay_id", "map_ni", "sbp_ni",
                                                    "dbp_ni", "n_ni"])
log(f"  lab aggregates: {len(elab):,}   vitalperiodic: {len(evp):,}   "
    f"vitalaperiodic: {len(eva):,}")

ee = co_e.copy()
# hospital-level timestamps for eICU, required by the landmark analysis.
# eICU stores offsets (minutes) plus a shifted clock time; the death time is
# reconstructed as hospital discharge time for Expired patients, and the ICU
# admission time from unitadmittime24.
for _c in ["adm24", "disch24", "unitadm24", "unitdisch24"]:
    ee[_c] = pd.to_datetime(ee[_c], errors="coerce")
ee["admittime"] = ee["adm24"]
ee["dischtime"] = ee["disch24"]
ee["deathtime"] = ee["disch24"].where(ee.hosp_status == "Expired")
ee["icu_intime"] = ee["unitadm24"]
ee["icu_outtime"] = ee["unitdisch24"]
# NOTE: eICU's *24 clock columns are date-shifted and NOT reliable for durations
# (taken literally they imply all 1,612 patients left ICU within 24h). The
# landmark analysis therefore uses the minute OFFSET columns (unit/hospital
# discharge offset), fetched directly in PHASE 9B.
for src, name in EICU_LAB_MIN.items():
    ee[name] = ee.stay_id.map(elab[elab.labname == src].set_index("stay_id").vmin)
for src, name in EICU_LAB_MAX.items():
    ee[name] = ee.stay_id.map(elab[elab.labname == src].set_index("stay_id").vmax)
vp = evp.set_index("stay_id")
va = eva.set_index("stay_id")
ee["heart_rate"] = ee.stay_id.map(vp.hr_vp)
ee["resp_rate"] = ee.stay_id.map(vp.rr_vp)
ee["spo2"] = ee.stay_id.map(vp.spo2_vp)
# MAP provenance: record the source so PHASE 10 can audit it
ee["map_invasive"] = ee.stay_id.map(vp.map_vp)
ee["map_noninv"] = ee.stay_id.map(va.map_ni)
ee["map_pref_invasive"] = ee.map_invasive.fillna(ee.map_noninv)
ee["map_pref_noninv"] = ee.map_noninv.fillna(ee.map_invasive)
ee["map"] = ee.map_pref_invasive           # current composite
ee["map_arterial"] = ee.map_invasive
ee["sbp"] = ee.stay_id.map(va.sbp_ni)
ee["dbp"] = ee.stay_id.map(va.dbp_ni)
ee["hospitalid"] = ee.hospitalid

# ===================================================================== nwICU
log("\n" + "=" * 100)
log(f"nwICU predictor extraction (window: icu_intime < t <= icu_intime + {W}h)")
log("=" * 100)
co_n = pd.read_csv(os.path.join(DATA, "cohort_nwicu.csv"), low_memory=False)
ids_n = [int(x) for x in co_n.hadm_id]
NW_LAB_MIN = {"Albumin": "albumin", "Sodium": "sodium", "Platelet Count": "platelet",
              "Hemoglobin": "hemoglobin"}
NW_LAB_MAX = {"Bilirubin, Total": "bilirubin", "Creatinine": "creatinine",
              "White Blood Cells": "wbc"}
with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT l.hadm_id, i.label, min(l.valuenum), max(l.valuenum), count(*)
            FROM public.labevents l
            JOIN public.d_labitems i ON i.itemid = l.itemid
            JOIN public.cohort_admissions c ON c.hadm_id = l.hadm_id AND c.center='nwICU'
            WHERE l.hadm_id = ANY(%s) AND l.valuenum IS NOT NULL
              AND l.charttime >  c.icu_intime
              AND l.charttime <= c.icu_intime + interval '{W} hours'
              AND i.label = ANY(%s)
            GROUP BY 1,2
        """, (ids_n, list(NW_LAB_MIN) + list(NW_LAB_MAX)))
        nlab = pd.DataFrame(cur.fetchall(), columns=["hadm_id", "label", "vmin",
                                                     "vmax", "n"])
        cur.execute(f"""
            SELECT m.hadm_id, m.itemid, avg(m.valuenum), avg(m.valuenum*m.valuenum),
                   count(*)
            FROM public.chartevents m
            JOIN public.cohort_admissions c ON c.hadm_id = m.hadm_id AND c.center='nwICU'
            WHERE m.hadm_id = ANY(%s) AND m.valuenum IS NOT NULL
              AND m.charttime >  c.icu_intime
              AND m.charttime <= c.icu_intime + interval '{W} hours'
              AND m.itemid IN (320045, 320179, 320180, 320210, 320277)
            GROUP BY 1,2
        """, (ids_n,))
        nvit = pd.DataFrame(cur.fetchall(), columns=["hadm_id", "itemid", "vavg",
                                                     "v2", "n"])
        cur.execute("""
            SELECT i.itemid, i.unitname, count(*)
            FROM public.chartevents m JOIN public.d_items i ON i.itemid = m.itemid
            WHERE m.itemid IN (320045,320179,320180,320210,320277)
            GROUP BY 1,2 ORDER BY 1
        """)
        nu = pd.DataFrame(cur.fetchall(), columns=["itemid", "unitname", "n"])
log(f"  lab aggregates: {len(nlab):,}   chartevent aggregates: {len(nvit):,}")
log("\n  nwICU vital unitnames (unit verification):")
log(nu.to_string(index=False))

nn = co_n.copy()
nn["hospitalid"] = pd.NA          # nwICU is a single centre
# psycopg2 returns NUMERIC columns as decimal.Decimal; coerce numerics to float
# before any arithmetic (Decimal does not interoperate with float).
for _c in ["age", "sbp", "dbp"]:
    if _c in nn.columns:
        nn[_c] = pd.to_numeric(nn[_c], errors="coerce").astype(float)
for src, name in NW_LAB_MIN.items():
    nn[name] = nn.hadm_id.map(nlab[nlab.label == src].set_index("hadm_id").vmin)
for src, name in NW_LAB_MAX.items():
    nn[name] = nn.hadm_id.map(nlab[nlab.label == src].set_index("hadm_id").vmax)
nv = nvit.set_index("hadm_id")
for item, name in [(320045, "heart_rate"), (320210, "resp_rate"), (320277, "spo2")]:
    nn[name] = nn.hadm_id.map(nv[nv.itemid == item].set_index("hadm_id").vavg) \
        if False else nn.hadm_id.map(nvit[nvit.itemid == item].set_index("hadm_id").vavg)
nn["sbp"] = pd.to_numeric(nn.hadm_id.map(
    nvit[nvit.itemid == 320179].set_index("hadm_id").vavg), errors="coerce").astype(float)
nn["dbp"] = pd.to_numeric(nn.hadm_id.map(
    nvit[nvit.itemid == 320180].set_index("hadm_id").vavg), errors="coerce").astype(float)
nn["map"] = (nn.sbp + 2 * nn.dbp) / 3.0
nn["map_arterial"] = nn["map"]
nn["centre"] = "nwICU"

# ===================================================================== combine + QC
log("\n" + "=" * 100)
log("VALUE QC -- plausibility ranges applied, never winsorised")
log("=" * 100)
KEEP = ["centre", "subject_id", "hadm_id", "stay_id", "hospitalid", "age", "male",
        "hospital_mortality", "death_30d_best", "death_by_discharge",
        "admittime", "dischtime", "deathtime", "dod", "icu_intime", "icu_outtime",
        "map_arterial"] + [c for c in CONT if c != "age"] + BIN
# hemoglobin is not a primary predictor but IS required by the reduced
# sensitivity specification (cfg.REDUCED_PREDICTORS), so it must be carried.
KEEP = list(dict.fromkeys(KEEP + ["hemoglobin"]))


def align(df):
    for k in KEEP:
        if k not in df.columns:
            df[k] = np.nan
    return df[KEEP]


for _c in CONT + BIN + ["hospital_mortality", "death_30d_best", "death_by_discharge"]:
    for _df in (mm, ee, nn):
        if _c in _df.columns:
            _df[_c] = pd.to_numeric(_df[_c], errors="coerce")
A = pd.concat([align(mm), align(ee), align(nn)], ignore_index=True)
for c_ in ["admittime", "dischtime", "deathtime", "dod", "icu_intime", "icu_outtime"]:
    A[c_] = pd.to_datetime(A[c_], errors="coerce")

for var, (lo, hi) in cfg.PLAUSIBLE_RANGE.items():
    if var not in A.columns:
        continue
    v = pd.to_numeric(A[var], errors="coerce")
    bad = v.notna() & ((v < lo) | (v > hi))
    if bad.any():
        for ctr in A.loc[bad, "centre"].unique():
            qc(ctr, f"plausibility {var}", f"set to missing (<{lo} or >{hi})",
               int((bad & (A.centre == ctr)).sum()))
        A.loc[bad, var] = np.nan

A.to_csv(os.path.join(DATA, "analysis_dataset.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "analysis_dataset.csv"), "phase_3_4_dataset_model.py",
           inputs={"cohort_mimic": os.path.join(DATA, "cohort_mimic.csv"),
                   "cohort_eicu": os.path.join(DATA, "cohort_eicu.csv"),
                   "cohort_nwicu": os.path.join(DATA, "cohort_nwicu.csv")})
log(f"\n  analysis dataset: {len(A):,} rows -> data/analysis_dataset.csv")
for ctr, g in A.groupby("centre"):
    log(f"    {ctr:<10} n={len(g):>6,}  deaths={int(g.hospital_mortality.sum()):>5,}  "
        f"SpO2 median={g.spo2.median():.1f}  albumin median={g.albumin.median():.2f}")

log("\n  coverage (%) of the frozen predictors:")
cov = A.groupby("centre")[CONT + BIN].apply(lambda g: (100 * g.notna().mean()).round(1))
log(cov.T.to_string())

qcdf = pd.DataFrame(qc_rows)
qcdf.to_csv(os.path.join(DATA, "qc_flags.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "qc_flags.csv"), "phase_3_4_dataset_model.py")
log(f"\n  QC flags recorded: {len(qcdf)}")

# ===================================================================== FINAL_MODEL_V2
log("\n" + "=" * 100)
log("FINAL_MODEL_V2 -- unpenalized logistic regression")
log("=" * 100)
dev = A[A.centre == "MIMIC-IV"].copy()
med = dev[CONT].median(numeric_only=True)
ind = list(cfg.MISSING_INDICATORS_PRIMARY)
for c in ind:
    n_miss = int(dev[c].isna().sum())
    log(f"  indicator {c}: {n_miss:,} missing in development "
        f"({100*n_miss/len(dev):.1f}%)  required >= {cfg.MIN_MISSING_FOR_INDICATOR}")
    assert n_miss >= cfg.MIN_MISSING_FOR_INDICATOR, (
        f"indicator {c} has only {n_miss} missing development values; the frozen "
        f"specification requires >= {cfg.MIN_MISSING_FOR_INDICATOR}. STOPPING.")


def design(df):
    x = df[CONT + BIN].astype(float).copy()
    for c in CONT:
        x[c] = x[c].fillna(float(med[c]))
    for c in ind:
        x[f"miss_{c}"] = df[c].isna().astype(int)
    return x


Xtr = design(dev)
names = list(Xtr.columns)
Xd = np.column_stack([np.ones(len(Xtr)), Xtr.values])
ytr = dev.hospital_mortality.values.astype(float)
beta, conv, se = prov.fit_logistic(Xd, ytr)
log(f"  convergence: {conv}    terms: {len(names)+1}")
if not conv:
    log("  *** SEPARATION / NON-CONVERGENCE. Per cfg.SEPARATION_POLICY the run STOPS")
    log("      here. No penalty is added automatically.")
    raise SystemExit("STOP: unpenalized model did not converge")

log(f"\n  {'term':<18}{'beta':>12}{'SE':>10}{'OR':>10}")
for nm, b, s in zip(["const"] + names, beta, se):
    log(f"  {nm:<18}{b:>12.5f}{s:>10.5f}{np.exp(np.clip(b,-50,50)):>10.4f}")

# apply to all three centres with the SAME coefficients
preds = []
for ctr in ["MIMIC-IV", "eICU", "nwICU"]:
    sub = A[A.centre == ctr].copy()
    Xs = design(sub).reindex(columns=names, fill_value=0)
    sub["p_model"] = prov.expit(np.column_stack([np.ones(len(Xs)), Xs.values]) @ beta)
    preds.append(sub[["centre", "subject_id", "hadm_id", "stay_id", "hospitalid",
                      "hospital_mortality", "death_30d_best", "death_by_discharge",
                      "p_model"]])
P = pd.concat(preds, ignore_index=True)
P.to_csv(os.path.join(DATA, "predictions.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "predictions.csv"), "phase_3_4_dataset_model.py",
           inputs={"analysis_dataset": os.path.join(DATA, "analysis_dataset.csv")})

coef = pd.DataFrame(dict(term=["const"] + names, beta=beta, se=se))
coef.to_csv(os.path.join(DATA, "model_v2_coefficients.csv"), index=False,
            encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "model_v2_coefficients.csv"),
           "phase_3_4_dataset_model.py")

log("\n" + "=" * 100)
log("FINAL_MODEL_V2 PERFORMANCE")
log("=" * 100)
for ctr, outc in [("MIMIC-IV", "hospital_mortality"), ("eICU", "hospital_mortality"),
                  ("nwICU", "death_30d_best")]:
    s = P[P.centre == ctr]
    mt = prov.metrics(s[outc].values, s.p_model.values)
    log(f"  {ctr:<10} n={mt['n']:>6,} ev={mt['events']:>5,}  AUROC={mt['auroc']:.4f}  "
        f"Brier={mt['brier']:.4f}  O/E={mt['oe']:.3f}  "
        f"slope={mt['calib_slope']:.4f}  intercept={mt['calib_intercept']:+.4f}")

with open(os.path.join(LOGS, "PHASE_3_4_dataset_model.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nPHASE 3-4 DONE")

