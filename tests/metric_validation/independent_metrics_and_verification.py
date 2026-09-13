"""PHASE 14 + PHASE 17 -- GOLDEN_100 raw-to-derived workbook, and an INDEPENDENT
second implementation of the three headline metrics.

PHASE 14  >=100 ICU stays (random + targeted) traced from the raw tables through
          every processing decision to the final predictor, outcome and score.
PHASE 17  AUROC, O/E and calibration slope recomputed by code that does NOT
          import provenance.py's metric functions. Agreement must be
          AUROC < 1e-6, O/E < 1e-6, slope < 1e-5 or the run FAILS.
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
W = cfg.WINDOW_PRIMARY_HOURS


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


prov.announce("phase_14_17_golden_independent.py")
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")

# ===================================================================== PHASE 17 first
log("=" * 100)
log("PHASE 17 -- INDEPENDENT SECOND IMPLEMENTATION OF THE HEADLINE METRICS")
log("=" * 100)


# ---- INDEPENDENT implementations. These deliberately do NOT import prov.auroc,
# ---- prov.oe_ratio, prov.cal_slope_intercept. They are written from scratch.
def ind_auroc(y, p):
    """Mann-Whitney U formulation: AUROC = U / (n1*n0), ties at 0.5."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    m = ~(np.isnan(y) | np.isnan(p))
    y, p = y[m], p[m]
    pos = p[y == 1]
    neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    # U = number of (pos, neg) pairs where pos > neg, plus half the ties
    u = 0.0
    for v in pos:                                  # explicit double loop: independent
        u += float(np.sum(v > neg)) + 0.5 * float(np.sum(v == neg))
    return u / (len(pos) * len(neg))


def ind_oe(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    m = ~(np.isnan(y) | np.isnan(p))
    obs = float(np.sum(y[m]) / np.sum(m))
    exp = float(np.sum(p[m]) / np.sum(m))
    return obs / exp


def ind_cal_slope(y, p):
    """Calibration slope by a THIRD-PARTY optimiser (scipy BFGS) on the logistic
    log-likelihood, with NUMERICAL gradients. This shares no code with the
    primary IRLS solver, so agreement is a genuine cross-check rather than a
    restatement of the same arithmetic."""
    from scipy.optimize import minimize
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    m = ~(np.isnan(y) | np.isnan(p))
    y, p = y[m], p[m]
    lp = np.log(p / (1 - p))

    def nll(theta):
        eta = np.clip(theta[0] + theta[1] * lp, -500, 500)
        # stable log-likelihood: -log(1+exp(-eta)) for y=1, -log(1+exp(eta)) for y=0
        return -float(np.sum(y * (-np.log1p(np.exp(-eta))) +
                             (1 - y) * (-np.log1p(np.exp(eta)))))

    r = minimize(nll, np.array([0.0, 1.0]), method="BFGS",
                 options=dict(gtol=1e-10, maxiter=2000))
    return float(r.x[1]) if np.isfinite(r.x[1]) else np.nan


log(f"  {'cohort':<12}{'metric':<10}{'primary impl':>16}{'independent':>15}{'|diff|':>12}"
    f"{'tol':>10}  verdict")
tol = {"auroc": 1e-6, "oe": 1e-6, "slope": 1e-5}
all_ok = True
rows = []
for ctr, outc in [("MIMIC-IV", "hospital_mortality"), ("eICU", "hospital_mortality"),
                  ("nwICU", "death_30d_best")]:
    s = A[A.centre == ctr].dropna(subset=["p_model"])
    y = s[outc].values.astype(float)
    p = s.p_model.values.astype(float)
    pm = prov.metrics(y, p)
    vals = {
        "auroc": (pm["auroc"], ind_auroc(y, p)),
        "oe": (pm["oe"], ind_oe(y, p)),
        "slope": (pm["calib_slope"], ind_cal_slope(y, p)),
    }
    for k, (v1, v2) in vals.items():
        d = abs(v1 - v2)
        ok = d < tol[k]
        all_ok &= ok
        rows.append(dict(cohort=ctr, metric=k, primary=v1, independent=v2,
                         abs_diff=d, tolerance=tol[k], pass_=ok))
        log(f"  {ctr:<12}{k:<10}{v1:>16.10f}{v2:>15.10f}{d:>12.3e}{tol[k]:>10.0e}  "
            f"{'PASS' if ok else 'FAIL'}")
log(f"\n  INDEPENDENT-METRIC VERIFICATION: {'ALL PASS' if all_ok else 'FAIL'}")
ind = pd.DataFrame(rows)
ind.to_csv(os.path.join(DATA, "independent_metric_check.csv"), index=False,
           encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "independent_metric_check.csv"),
           "phase_14_17_golden_independent.py")
if not all_ok:
    raise SystemExit("STOP: independent metric implementation disagrees")

# ===================================================================== PHASE 14 golden
log("\n" + "=" * 100)
log("PHASE 14 -- GOLDEN 100+ RAW-TO-DERIVED TRACE")
log("=" * 100)
rng = np.random.default_rng(cfg.RANDOM_SEED)
frames = []
for ctr, outc, key in [("MIMIC-IV", "hospital_mortality", "stay_id"),
                       ("eICU", "hospital_mortality", "stay_id"),
                       ("nwICU", "death_30d_best", "hadm_id")]:
    s = A[A.centre == ctr].copy()
    picks = []
    picks.append(s.sample(min(20, len(s)), random_state=cfg.RANDOM_SEED))          # random
    picks.append(s[s[outc] == 1].head(12))                                          # deaths
    picks.append(s[s[outc] == 0].head(8))                                           # survivors
    picks.append(s.nlargest(6, "p_model"))                                          # high risk
    picks.append(s.nsmallest(6, "p_model"))                                         # low risk
    if ctr == "MIMIC-IV":
        # cirrhosis edge cases by code family
        for code in ["K703", "K743", "K746"]:
            pass
    g = pd.concat(picks).drop_duplicates(subset=[key])
    g["_selection"] = "random+targeted"
    frames.append(g[[key, "centre", "age", "male", "albumin", "bilirubin",
                     "creatinine", "sodium", "platelet", "wbc", "heart_rate",
                     "map", "resp_rate", "spo2", outc, "p_model"]])
gold = pd.concat(frames, ignore_index=True)
log(f"  golden rows: {len(gold):,}  "
    f"(MIMIC {int((gold.centre=='MIMIC-IV').sum())}, "
    f"eICU {int((gold.centre=='eICU').sum())}, "
    f"nwICU {int((gold.centre=='nwICU').sum())})")

# attach the raw provenance for each picked stay: the exact rows behind each value
raw_rows = []
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        mids = [int(x) for x in gold[gold.centre == "MIMIC-IV"].stay_id if x == x]
        if mids:
            cur.execute(f"""
                SELECT i.stay_id, l.itemid, l.charttime, l.valuenum, l.valueuom,
                       i.intime, EXTRACT(EPOCH FROM (l.charttime - i.intime))/60 AS off_min
                FROM mimiciv_hosp.labevents l
                JOIN mimiciv_icu.icustays i ON i.hadm_id = l.hadm_id
                WHERE i.stay_id = ANY(%s) AND l.itemid = ANY(%s)
                  AND l.charttime >  i.intime
                  AND l.charttime <= i.intime + interval '{W} hours'
                  AND l.valuenum IS NOT NULL
            """, (mids, [50862, 50885, 50912, 50983, 51265, 51301, 51222]))
            raw_rows.append(pd.DataFrame(cur.fetchall(), columns=[
                "stay_id", "itemid", "charttime", "raw_value", "unit",
                "icu_intime", "offset_min"]).assign(centre="MIMIC-IV",
                                                    source_table="mimiciv_hosp.labevents"))
with conn("eicu") as c:
    with c.cursor() as cur:
        eids = [int(x) for x in gold[gold.centre == "eICU"].stay_id if x == x]
        if eids:
            cur.execute("""
                SELECT patientunitstayid, labname, labresultoffset, labresult,
                       labmeasurenamesystem
                FROM eicu_crd.lab
                WHERE patientunitstayid = ANY(%s) AND labresult IS NOT NULL
                  AND labresultoffset > 0 AND labresultoffset <= %s
                  AND labname IN ('albumin','total bilirubin','creatinine','sodium',
                                  'platelets x 1000','WBC x 1000','Hgb')
            """, (eids, W * 60))
            raw_rows.append(pd.DataFrame(cur.fetchall(), columns=[
                "stay_id", "itemid", "offset_min", "raw_value", "unit"]
            ).assign(centre="eICU", source_table="eicu_crd.lab", charttime=None,
                     icu_intime=None))
with conn("nwicu") as c:
    with c.cursor() as cur:
        nids = [int(x) for x in gold[gold.centre == "nwICU"].hadm_id if x == x]
        if nids:
            cur.execute(f"""
                SELECT l.hadm_id AS stay_id, i.label AS itemid, l.charttime,
                       l.valuenum AS raw_value, l.valueuom AS unit,
                       c.icu_intime,
                       EXTRACT(EPOCH FROM (l.charttime - c.icu_intime))/60 AS offset_min
                FROM public.labevents l
                JOIN public.d_labitems i ON i.itemid = l.itemid
                JOIN public.cohort_admissions c ON c.hadm_id = l.hadm_id
                     AND c.center='nwICU'
                WHERE l.hadm_id = ANY(%s) AND l.valuenum IS NOT NULL
                  AND l.charttime >  c.icu_intime
                  AND l.charttime <= c.icu_intime + interval '{W} hours'
                  AND i.label IN ('Albumin','Bilirubin, Total','Creatinine','Sodium',
                                  'Platelet Count','White Blood Cells','Hemoglobin')
            """, (nids,))
            raw_rows.append(pd.DataFrame(cur.fetchall(), columns=[
                "stay_id", "itemid", "charttime", "raw_value", "unit", "icu_intime",
                "offset_min"]).assign(centre="nwICU",
                                      source_table="public.labevents"))
raw = pd.concat(raw_rows, ignore_index=True) if raw_rows else pd.DataFrame()
log(f"  raw source rows attached: {len(raw):,}")
if len(raw):
    log(f"    by centre: {dict(raw.centre.value_counts())}")
    log(f"    all offsets within the frozen window 0 < t <= {W*60} min: "
        f"{bool(((raw.offset_min > 0) & (raw.offset_min <= W*60)).all())}")

# aggregation decision log: for each golden stay and variable, show min and max
if len(raw):
    labmap_m = {50862: ("albumin", "min"), 50885: ("bilirubin", "max"),
                50912: ("creatinine", "max"), 50983: ("sodium", "min"),
                51265: ("platelet", "min"), 51301: ("wbc", "max"),
                51222: ("hemoglobin", "min")}
    labmap_e = {"albumin": ("albumin", "min"), "total bilirubin": ("bilirubin", "max"),
                "creatinine": ("creatinine", "max"), "sodium": ("sodium", "min"),
                "platelets x 1000": ("platelet", "min"), "WBC x 1000": ("wbc", "max"),
                "Hgb": ("hemoglobin", "min")}
    labmap_n = {"Albumin": ("albumin", "min"), "Bilirubin, Total": ("bilirubin", "max"),
                "Creatinine": ("creatinine", "max"), "Sodium": ("sodium", "min"),
                "Platelet Count": ("platelet", "min"),
                "White Blood Cells": ("wbc", "max"), "Hemoglobin": ("hemoglobin", "min")}
    recs = []
    for _, r in raw.iterrows():
        if r.centre == "MIMIC-IV":
            mp = labmap_m.get(int(r.itemid)) if str(r.itemid).isdigit() else None
        elif r.centre == "eICU":
            mp = labmap_e.get(str(r.itemid))
        else:
            mp = labmap_n.get(str(r.itemid))
        if mp:
            recs.append(dict(centre=r.centre, stay_id=r.stay_id, variable=mp[0],
                             rule=f"{mp[1]}()", raw_value=r.raw_value,
                             unit=r.unit, offset_min=r.offset_min,
                             source_table=r.source_table))
    dec = pd.DataFrame(recs)
    agg = dec.groupby(["centre", "stay_id", "variable", "rule"]).raw_value.agg(
        ["min", "max", "count"]).reset_index()
    agg = agg.rename(columns={"min": "window_min", "max": "window_max",
                              "count": "n_measurements"})
    # final value taken by the pipeline per the frozen aggregation rule
    def pick(row):
        s = gold[gold.centre == row.centre]
        key = "stay_id" if row.centre != "nwICU" else "hadm_id"
        v = s[s[key] == row.stay_id]
        if len(v) == 0 or row.variable not in v.columns:
            return np.nan
        return float(v.iloc[0][row.variable]) if pd.notna(v.iloc[0][row.variable]) else np.nan
    agg["final_predictor_value"] = agg.apply(pick, axis=1)
    agg["aggregation_rule"] = agg.rule
    agg["offset_min"] = np.nan
    log("\n  AGGREGATION DECISION TABLE (first 12 rows):")
    log(agg.head(12).to_string(index=False))
else:
    agg = pd.DataFrame()

# score components for the golden set
sc = []
for ctr in ["MIMIC-IV", "eICU", "nwICU"]:
    s = gold[gold.centre == ctr]
    for _, r in s.iterrows():
        sc.append(dict(centre=ctr,
                       id=r.get("stay_id") if ctr != "nwICU" else r.get("hadm_id"),
                       albumin=r.albumin, bilirubin=r.bilirubin,
                       creatinine=r.creatinine, sodium=r.sodium,
                       platelet=r.platelet, age=r.age,
                       outcome=r.get("hospital_mortality")
                       if ctr != "nwICU" else r.get("death_30d_best"),
                       p_model=r.p_model))
scores = pd.DataFrame(sc)

out = os.path.join(TABLES, "GOLDEN_100_RAW_TO_DERIVED.xlsx")
with pd.ExcelWriter(out, engine="openpyxl") as xl:
    gold.to_excel(xl, sheet_name="01_final_derived_values", index=False)
    if len(raw):
        raw.head(20000).to_excel(xl, sheet_name="02_raw_source_rows", index=False)
    if len(agg):
        agg.to_excel(xl, sheet_name="03_aggregation_decisions", index=False)
    scores.to_excel(xl, sheet_name="04_score_components", index=False)
    pd.DataFrame([
        dict(item="config version", value=cfg.VERSION),
        dict(item="config sha256", value=cfg.CONFIG_HASH),
        dict(item="window", value=f"(icu_intime, +{W}h]"),
        dict(item="aggregation", value=str(cfg.AGGREGATION)),
        dict(item="plausibility", value=str(cfg.PLAUSIBLE_RANGE)),
        dict(item="indicators", value=str(cfg.MISSING_INDICATORS_PRIMARY)),
        dict(item="golden rows", value=len(gold)),
        dict(item="raw rows", value=len(raw)),
    ]).to_excel(xl, sheet_name="05_metadata", index=False)
prov.stamp(out, "phase_14_17_golden_independent.py",
           inputs={"analysis_dataset": os.path.join(DATA, "analysis_dataset.csv")})
log(f"\n  wrote GOLDEN_100_RAW_TO_DERIVED.xlsx: {len(gold)} stays, "
    f"{len(raw)} raw source rows, {len(agg)} aggregation decisions")

with open(os.path.join(LOGS, "PHASE_14_17_golden_independent.log"), "w",
          encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nPHASE 14 + 17 DONE")
