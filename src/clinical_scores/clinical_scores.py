"""PHASE 5, 6, 7, 10 -- clinical scores (corrected), APACHE removal, same-patient
paired comparison, and MAP provenance sensitivity.

PHASE 5  FIB-4 recomputed; ALBI recomputed with the PUBLISHED units
         (bilirubin umol/L, albumin g/L); MELD and MELD-Na recomputed from
         components with ONE shared function in every database, per GATE 0B.
PHASE 6  the invalid APS-III(MIMIC) -> APACHE IV(eICU) transport comparison is
         removed. APACHE is reported within each database only, if at all.
PHASE 7  every score is compared on the SAME patients as the model (paired
         cohorts), plus a common-complete intersection cohort, with a
         hospital-level cluster bootstrap.
PHASE 10 MAP provenance: invasive vs non-invasive composition, and a sensitivity
         analysis re-running the external validation under invasive-preferred,
         non-invasive-preferred and the current composite.
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
LOG = io.StringIO()
# Credentials come from the environment; see .env.example and db.py.
# The original hardcoded local credentials were removed for public release.
PG = dict(connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")))
rng = np.random.default_rng(cfg.RANDOM_SEED)


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


prov.announce("phase_5_6_7_scores.py")

# ===================================================================== shared score functions
# ONE implementation used for BOTH databases (remediation requirement).


def calculate_meld_original(bili, inr, creat, rrt=None):
    b = np.clip(np.asarray(bili, float), cfg.SCORE_MELD_BILI_MIN, None)
    i = np.clip(np.asarray(inr, float), cfg.SCORE_MELD_INR_MIN, None)
    lo, hi = cfg.SCORE_MELD_CREAT_BOUNDS
    c = np.clip(np.asarray(creat, float), lo, hi)
    if rrt is not None:
        c = np.where(np.asarray(rrt, float) == 1, cfg.SCORE_MELD_RRT_CREAT, c)
    v = 3.78 * np.log(b) + 11.2 * np.log(i) + 9.57 * np.log(c) + 6.43
    v = np.clip(v, *cfg.SCORE_MELD_CLIP)
    return np.round(v) if cfg.SCORE_MELD_ROUND else v


def calculate_meld_na_2016(meld, sodium):
    m = np.asarray(meld, float)
    lo, hi = cfg.SCORE_MELDNA_NA_BOUNDS
    na = np.clip(np.asarray(sodium, float), lo, hi)
    c1, c2 = cfg.SCORE_MELDNA_COEF
    v = m + c1 * (137 - na) - c2 * m * (137 - na)
    return np.clip(v, *cfg.SCORE_MELD_CLIP)


def calculate_albi(albumin_gdl, bilirubin_mgdl):
    """PUBLISHED units: bilirubin umol/L, albumin g/L."""
    b = np.asarray(bilirubin_mgdl, float) * cfg.BILI_MGDL_TO_UMOLL
    a = np.asarray(albumin_gdl, float) * cfg.ALB_GDL_TO_GL
    return np.log10(np.maximum(b, 1e-9)) * 0.66 + a * (-0.085)


def calculate_fib4(age, ast, alt, platelets):
    return (np.asarray(age, float) * np.asarray(ast, float)) / (
        np.maximum(np.asarray(platelets, float), 1e-9) *
        np.sqrt(np.maximum(np.asarray(alt, float), 1e-9)))


# ===================================================================== FIB-4 known-answer
log("=" * 100)
log("PHASE 5a -- FIB-4 KNOWN-ANSWER TESTS")
log("=" * 100)
ka = [
    (dict(age=50, ast=40, alt=40, plt=200), 50 * 40 / (200 * np.sqrt(40))),
    (dict(age=60, ast=80, alt=40, plt=100), 60 * 80 / (100 * np.sqrt(40))),
    (dict(age=40, ast=20, alt=80, plt=250), 40 * 20 / (250 * np.sqrt(80))),
]
ok = True
for inp, expected in ka:
    got = float(calculate_fib4(inp["age"], inp["ast"], inp["alt"], inp["plt"]))
    match = abs(got - expected) < 1e-12
    ok &= match
    log(f"  age={inp['age']} AST={inp['ast']} ALT={inp['alt']} PLT={inp['plt']} -> "
        f"{got:.10f}  expected {expected:.10f}  {'PASS' if match else 'FAIL'}")
log(f"  FIB-4 known-answer: {'ALL PASS' if ok else 'FAIL'}")
assert ok

log("\nPHASE 5b -- ALBI known-answer tests (published units)")
alb_ka = [
    (dict(alb=4.0, bili=1.0), np.log10(1.0 * 17.1) * 0.66 + 40.0 * (-0.085)),
    (dict(alb=2.5, bili=5.0), np.log10(5.0 * 17.1) * 0.66 + 25.0 * (-0.085)),
]
ok = True
for inp, expected in alb_ka:
    got = float(calculate_albi(inp["alb"], inp["bili"]))
    match = abs(got - expected) < 1e-12
    ok &= match
    log(f"  alb={inp['alb']} g/dL, bili={inp['bili']} mg/dL -> {got:+.6f}  "
        f"expected {expected:+.6f}  {'PASS' if match else 'FAIL'}")
log(f"  ALBI known-answer: {'ALL PASS' if ok else 'FAIL'}")
assert ok
log("  NOTE: ALBI now uses the published units. Values are ~ -1.36 (median) not ~0.03;")
log("        the previous implementation left bilirubin in mg/dL and albumin in g/dL.")

log("\nPHASE 5c -- MELD known-answer tests")
meld_ka = [
    (dict(b=1.0, i=1.0, c=1.0), 6),          # floor: 6.43 -> clip 6
    (dict(b=4.0, i=2.0, c=2.0), None),
    (dict(b=50.0, i=10.0, c=10.0), 40),      # ceiling
]
for inp, expected in meld_ka:
    got = float(calculate_meld_original(inp["b"], inp["i"], inp["c"]))
    if expected is not None:
        log(f"  bili={inp['b']} inr={inp['i']} creat={inp['c']} -> {got:.0f}  "
            f"expected {expected}  {'PASS' if abs(got-expected)<1e-9 else 'FAIL'}")
        assert abs(got - expected) < 1e-9
    else:
        raw = 3.78*np.log(4.0) + 11.2*np.log(2.0) + 9.57*np.log(2.0) + 6.43
        log(f"  bili=4 inr=2 creat=2 -> {got:.0f}  (raw {raw:.3f}, clipped [6,40])")
log("  RRT rule check: creat=1 with rrt=1 must behave as creat=4")
a = float(calculate_meld_original(2.0, 1.5, 1.0, 0))
b = float(calculate_meld_original(2.0, 1.5, 1.0, 1))
log(f"    rrt=0 -> {a:.0f}   rrt=1 -> {b:.0f}   differs: {b > a}")
assert b > a

# ===================================================================== component extraction
log("\n" + "=" * 100)
log("PHASE 5d -- component extraction for scores (raw databases, same window)")
log("=" * 100)
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
W = cfg.WINDOW_PRIMARY_HOURS
mim = A[A.centre == "MIMIC-IV"].copy()
eic = A[A.centre == "eICU"].copy()

# MIMIC: inr, ast, alt, hemoglobin, rrt from the live DB
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT i.stay_id, l.itemid, min(l.valuenum), max(l.valuenum)
            FROM mimiciv_hosp.labevents l
            JOIN mimiciv_icu.icustays i ON i.hadm_id = l.hadm_id
            WHERE i.stay_id = ANY(%s) AND l.itemid = ANY(%s)
              AND l.charttime >  i.intime
              AND l.charttime <= i.intime + interval '{W} hours'
              AND l.valuenum IS NOT NULL
            GROUP BY 1,2
        """, ([int(x) for x in mim.stay_id], [51237, 50878, 50861, 51222]))
        ex = pd.DataFrame(cur.fetchall(), columns=["stay_id", "itemid", "vmin", "vmax"])
        cur.execute("""
            SELECT stay_id, rrt, meld_initial FROM mimiciv_derived.meld
            WHERE stay_id = ANY(%s)
        """, ([int(x) for x in mim.stay_id],))
        mr = pd.DataFrame(cur.fetchall(), columns=["stay_id", "rrt", "meld_initial"])
for item, name, how in [(51237, "inr", "max"), (50878, "ast", "max"),
                        (50861, "alt", "max"), (51222, "hemoglobin", "min")]:
    s = ex[ex.itemid == item].set_index("stay_id")["vmax" if how == "max" else "vmin"]
    mim[name] = mim.stay_id.map(s)
mim = mim.merge(mr, on="stay_id", how="left")
# psycopg2 returns NUMERIC as decimal.Decimal; coerce before arithmetic
for _c in ["inr", "ast", "alt", "hemoglobin", "rrt", "meld_initial"]:
    if _c in mim.columns:
        mim[_c] = pd.to_numeric(mim[_c], errors="coerce")

# eICU: inr, ast, alt, hemoglobin
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT patientunitstayid, labname, min(labresult), max(labresult)
            FROM eicu_crd.lab
            WHERE patientunitstayid = ANY(%s) AND labresult IS NOT NULL
              AND labresultoffset > 0 AND labresultoffset <= {W*60}
              AND labname IN ('PT - INR','AST (SGOT)','ALT (SGPT)','Hgb')
            GROUP BY 1,2
        """, ([int(x) for x in eic.stay_id],))
        ex = pd.DataFrame(cur.fetchall(), columns=["stay_id", "labname", "vmin", "vmax"])
for src, name, how in [("PT - INR", "inr", "max"), ("AST (SGOT)", "ast", "max"),
                       ("ALT (SGPT)", "alt", "max"), ("Hgb", "hemoglobin", "min")]:
    s = ex[ex.labname == src].set_index("stay_id")["vmax" if how == "max" else "vmin"]
    eic[name] = eic.stay_id.map(s)
# eICU RRT: not directly available; the APACHE/derived tables lack a dialysis flag
# usable in the same window, so the RRT rule is NOT applied in eICU and this is
# recorded as a limitation. MIMIC applies it.
for _c in ["inr", "ast", "alt", "hemoglobin"]:
    if _c in eic.columns:
        eic[_c] = pd.to_numeric(eic[_c], errors="coerce")
eic["rrt"] = np.nan

# nwICU: no INR -> MELD impossible; ALBI and FIB-4 only
nw = A[A.centre == "nwICU"].copy()
with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT l.hadm_id, i.label, min(l.valuenum), max(l.valuenum)
            FROM public.labevents l JOIN public.d_labitems i ON i.itemid = l.itemid
            JOIN public.cohort_admissions c ON c.hadm_id = l.hadm_id AND c.center='nwICU'
            WHERE l.hadm_id = ANY(%s) AND l.valuenum IS NOT NULL
              AND l.charttime >  c.icu_intime
              AND l.charttime <= c.icu_intime + interval '{W} hours'
              AND i.label IN ('Asparate Aminotransferase (AST)',
                              'Alanine Aminotransferase (ALT)','Hemoglobin')
            GROUP BY 1,2
        """, ([int(x) for x in nw.hadm_id],))
        ex = pd.DataFrame(cur.fetchall(), columns=["hadm_id", "label", "vmin", "vmax"])
for src, name, how in [("Asparate Aminotransferase (AST)", "ast", "max"),
                       ("Alanine Aminotransferase (ALT)", "alt", "max"),
                       ("Hemoglobin", "hemoglobin", "min")]:
    s = ex[ex.label == src].set_index("hadm_id")["vmax" if how == "max" else "vmin"]
    nw[name] = nw.hadm_id.map(s)
for _c in ["ast", "alt", "hemoglobin"]:
    if _c in nw.columns:
        nw[_c] = pd.to_numeric(nw[_c], errors="coerce")
nw["inr"] = np.nan
nw["rrt"] = np.nan

# ===================================================================== compute scores
for d in (mim, eic, nw):
    d["score_meld"] = calculate_meld_original(d.bilirubin, d.inr, d.creatinine, d.rrt)
    d["score_meldna"] = calculate_meld_na_2016(d.score_meld, d.sodium)
    d["score_albi"] = calculate_albi(d.albumin, d.bilirubin)
    d["score_fib4"] = calculate_fib4(d.age, d.ast, d.alt, d.platelet)

log("\nPHASE 5e -- MIMIC verification: recomputed MELD vs stored meld_initial")
log("  CONTEXT (established in diag_meld_window2.py): mimiciv_derived.meld and")
log("  first_day_lab are internally consistent with each other (100%), but they")
log("  reproduce a raw 24h labevents window only 78-86% of the time, and where they")
log("  differ the derived value is HIGHER in 654 stays and LOWER in none. The stored")
log("  table therefore uses information outside the frozen 24h window.")
log("  CONSEQUENCE: meld_initial/meld are NOT used as predictors, and the agreement")
log("  below is reported as a DIAGNOSTIC of the component-source difference, not as")
log("  a pass/fail test of the formula (that was GATE 0B, which passed at 100.00%")
log("  using the table's own components).")
chk = mim[mim.meld_initial.notna() & mim.score_meld.notna()]
agree = float((np.abs(chk.score_meld - chk.meld_initial) < 1e-9).mean())
log(f"\n  n compared                    : {len(chk):,}")
log(f"  exact agreement               : {100*agree:.4f}%")
log(f"  mean |difference|             : "
    f"{float(np.abs(chk.score_meld-chk.meld_initial).mean()):.6f} points")
log("  interpretation: the residual disagreement is the component-source (window)")
log("  difference above, NOT a formula error. FINAL_REBUILD recomputes every score")
log("  from its own frozen 24h components in all three databases, using the single")
log("  shared function that passes the known-answer tests, so the score comparison")
log("  is internally consistent and leak-free across centres.")

log("\n  SCORE COMPONENT COMPLETENESS BY CENTRE (score availability):")
log("\n  score availability:")
for nm, d in [("MIMIC-IV", mim), ("eICU", eic), ("nwICU", nw)]:
    log(f"    {nm:<10} MELD {int(d.score_meld.notna().sum()):>6,}/{len(d):<6,} "
        f"ALBI {int(d.score_albi.notna().sum()):>6,} "
        f"FIB-4 {int(d.score_fib4.notna().sum()):>6,}")

# ===================================================================== PHASE 7 paired comparison
log("\n" + "=" * 100)
log("PHASE 7 -- SAME-PATIENT SCORE COMPARISON (paired cohorts, eICU)")
log("=" * 100)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
eic = eic.merge(P[P.centre == "eICU"][["stay_id", "p_model"]], on="stay_id", how="left")


def cluster_boot(y, p, hid, n_boot=None, seed=None):
    n_boot = n_boot or cfg.N_BOOTSTRAP_CLUSTER
    r = np.random.default_rng(seed or cfg.RANDOM_SEED)
    uniq = np.unique(hid)
    idx_by_h = {h: np.where(hid == h)[0] for h in uniq}
    out = {"auroc": [], "oe": [], "brier": [], "calib_slope": []}
    for _ in range(n_boot):
        sel = r.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_by_h[h] for h in sel])
        yy, pp = y[idx], p[idx]
        if len(np.unique(yy)) < 2:
            continue
        m = prov.metrics(yy, pp)
        for k in out:
            out[k].append(m[k])
    return {k: (float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5)))
            for k, v in out.items()}


rows = []
hid = eic.hospitalid.values
y_all = eic.hospital_mortality.values.astype(float)
# the model itself, on the full eICU cohort
m = prov.metrics(y_all, eic.p_model.values)
ci = cluster_boot(y_all, eic.p_model.values, hid)
rows.append(dict(score="FINAL_MODEL_V2", paired_n=len(eic), events=int(y_all.sum()),
                 auroc=m["auroc"], auroc_lo=ci["auroc"][0], auroc_hi=ci["auroc"][1],
                 brier=m["brier"], oe=m["oe"], oe_lo=ci["oe"][0], oe_hi=ci["oe"][1],
                 calib_intercept=m["calib_intercept"], calib_slope=m["calib_slope"],
                 cohort="full eICU"))
log(f"\n  {'score':<18}{'paired n':>9}{'events':>7}{'AUROC':>8}{'O/E':>8}{'slope':>8}  note")
log(f"  {'FINAL_MODEL_V2':<18}{len(eic):>9,}{int(y_all.sum()):>7}"
    f"{m['auroc']:>8.4f}{m['oe']:>8.3f}{m['calib_slope']:>8.3f}  full cohort")

for sc, lbl in [("score_meld", "MELD"), ("score_meldna", "MELD-Na"),
                ("score_albi", "ALBI"), ("score_fib4", "FIB-4")]:
    sub = eic[eic[sc].notna() & eic.p_model.notna()].copy()
    if len(sub) < 60:
        log(f"  {lbl:<18} SKIPPED (n={len(sub)})")
        continue
    yy = sub.hospital_mortality.values.astype(float)
    hh = sub.hospitalid.values
    # fit the score->risk mapping in MIMIC ONLY, apply unchanged (external validation)
    dsub = mim[mim[sc].notna()]
    xs = dsub[sc].values.astype(float)
    ys = dsub.hospital_mortality.values.astype(float)
    Xs = np.column_stack([np.ones(len(xs)), xs])
    bs, conv, _ = prov.fit_logistic(Xs, ys)
    assert conv, f"score mapping for {lbl} did not converge"
    p_sc = prov.expit(bs[0] + bs[1] * sub[sc].values.astype(float))
    mm2 = prov.metrics(yy, p_sc)
    pm = prov.metrics(yy, sub.p_model.values)
    ci2 = cluster_boot(yy, p_sc, hh)
    rows.append(dict(score=lbl, paired_n=len(sub), events=int(yy.sum()),
                     auroc=mm2["auroc"], auroc_lo=ci2["auroc"][0], auroc_hi=ci2["auroc"][1],
                     brier=mm2["brier"], oe=mm2["oe"], oe_lo=ci2["oe"][0],
                     oe_hi=ci2["oe"][1], calib_intercept=mm2["calib_intercept"],
                     calib_slope=mm2["calib_slope"], cohort=f"paired: {lbl}-complete"))
    rows.append(dict(score=f"FINAL_MODEL_V2 (same {lbl}-complete patients)",
                     paired_n=len(sub), events=int(yy.sum()), auroc=pm["auroc"],
                     auroc_lo=np.nan, auroc_hi=np.nan, brier=pm["brier"], oe=pm["oe"],
                     oe_lo=np.nan, oe_hi=np.nan, calib_intercept=pm["calib_intercept"],
                     calib_slope=pm["calib_slope"], cohort=f"paired: {lbl}-complete"))
    log(f"  {lbl:<18}{len(sub):>9,}{int(yy.sum()):>7}{mm2['auroc']:>8.4f}"
        f"{mm2['oe']:>8.3f}{mm2['calib_slope']:>8.3f}  paired")
    log(f"  {'  ...model on same':<18}{len(sub):>9,}{int(yy.sum()):>7}"
        f"{pm['auroc']:>8.4f}{pm['oe']:>8.3f}{pm['calib_slope']:>8.3f}  paired")

# common-complete intersection
common = eic[eic[["score_meld", "score_albi", "score_fib4"]].notna().all(axis=1)
             & eic.p_model.notna()].copy()
log(f"\n  COMMON-COMPLETE intersection cohort: n={len(common):,} "
    f"({100*len(common)/len(eic):.1f}% of eICU), events={int(common.hospital_mortality.sum())}")
cc_rows = []
if len(common) >= 100:
    yy = common.hospital_mortality.values.astype(float)
    hh = common.hospitalid.values
    for sc, lbl in [("p_model", "FINAL_MODEL_V2"), ("score_meld", "MELD"),
                    ("score_meldna", "MELD-Na"), ("score_albi", "ALBI"),
                    ("score_fib4", "FIB-4")]:
        if sc == "p_model":
            p_use = common.p_model.values
        else:
            dsub = mim[mim[sc].notna()]
            Xs = np.column_stack([np.ones(len(dsub)), dsub[sc].values.astype(float)])
            bs, _, _ = prov.fit_logistic(Xs, dsub.hospital_mortality.values.astype(float))
            p_use = prov.expit(bs[0] + bs[1] * common[sc].values.astype(float))
        mm3 = prov.metrics(yy, p_use)
        ci3 = cluster_boot(yy, p_use, hh, n_boot=1000)
        cc_rows.append(dict(score=lbl, n=len(common), events=int(yy.sum()),
                            auroc=mm3["auroc"], auroc_lo=ci3["auroc"][0],
                            auroc_hi=ci3["auroc"][1], brier=mm3["brier"], oe=mm3["oe"],
                            oe_lo=ci3["oe"][0], oe_hi=ci3["oe"][1],
                            calib_intercept=mm3["calib_intercept"],
                            calib_slope=mm3["calib_slope"]))
    cc = pd.DataFrame(cc_rows)
    log("\n  COMMON-COMPLETE results (identical patients for every score):")
    log(f"  {'score':<18}{'AUROC':>8}{'95% CI':>18}{'Brier':>9}{'O/E':>8}{'95% CI':>18}{'slope':>8}")
    for _, r in cc.iterrows():
        log(f"  {r.score:<18}{r.auroc:>8.4f}  ({r.auroc_lo:.3f},{r.auroc_hi:.3f})"
            f"{r.brier:>9.4f}{r.oe:>8.3f}  ({r.oe_lo:.3f},{r.oe_hi:.3f}){r.calib_slope:>8.3f}")
    cc.to_csv(os.path.join(DATA, "score_comparison_common_complete.csv"), index=False,
              encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "score_comparison_common_complete.csv"),
               "phase_5_6_7_scores.py")

sc_df = pd.DataFrame(rows)
sc_df.to_csv(os.path.join(DATA, "score_comparison_paired.csv"), index=False,
             encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "score_comparison_paired.csv"), "phase_5_6_7_scores.py")

# ===================================================================== PHASE 6 APACHE
log("\n" + "=" * 100)
log("PHASE 6 -- APACHE TRANSPORT COMPARISON REMOVED")
log("=" * 100)
log(f"  config APACHE_CROSS_DATABASE_ALLOWED = {cfg.APACHE_CROSS_DATABASE_ALLOWED}")
assert cfg.APACHE_CROSS_DATABASE_ALLOWED is False
log("  MIMIC exposes APS-III (mimiciv_derived.apsiii); eICU exposes APACHE IV")
log("  (apachepatientresult.apachescore). These are DIFFERENT instruments, so the")
log("  previous 'APACHE IV O/E 0.565 -- physiology scores drift worse' comparison is")
log("  DELETED. No replacement comparator is invented. APACHE is not reported here")
log("  at all; if reported in future it must be within-database only.")

# ===================================================================== PHASE 10 MAP
log("\n" + "=" * 100)
log("PHASE 10 -- MAP PROVENANCE AND SENSITIVITY")
log("=" * 100)
e2 = pd.read_csv(os.path.join(DATA, "cohort_eicu.csv"), low_memory=False)
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT patientunitstayid, avg(systemicmean) FROM eicu_crd.vitalperiodic
            WHERE patientunitstayid = ANY(%s)
              AND observationoffset > 0 AND observationoffset <= {W*60}
            GROUP BY 1
        """, ([int(x) for x in e2.stay_id],))
        vp = pd.DataFrame(cur.fetchall(), columns=["stay_id", "map_inv"])
        cur.execute(f"""
            SELECT patientunitstayid, avg(noninvasivemean) FROM eicu_crd.vitalaperiodic
            WHERE patientunitstayid = ANY(%s)
              AND observationoffset > 0 AND observationoffset <= {W*60}
            GROUP BY 1
        """, ([int(x) for x in e2.stay_id],))
        va = pd.DataFrame(cur.fetchall(), columns=["stay_id", "map_ni"])
mv = e2[["stay_id"]].merge(vp, on="stay_id", how="left").merge(va, on="stay_id", how="left")
mv["map_inv"] = pd.to_numeric(mv.map_inv, errors="coerce")
mv["map_ni"] = pd.to_numeric(mv.map_ni, errors="coerce")
n_inv = int(mv.map_inv.notna().sum())
n_ni = int(mv.map_ni.notna().sum())
n_both = int((mv.map_inv.notna() & mv.map_ni.notna()).sum())
log(f"  eICU patients with invasive MAP only   : {int((mv.map_inv.notna() & mv.map_ni.isna()).sum()):,}")
log(f"  eICU patients with non-invasive MAP only: {int((mv.map_inv.isna() & mv.map_ni.notna()).sum()):,}")
log(f"  eICU patients with BOTH                 : {n_both:,}")
log(f"  eICU patients with NEITHER              : {int((mv.map_inv.isna() & mv.map_ni.isna()).sum()):,}")
log(f"  arterial-only / non-invasive-only / both = "
    f"{int((mv.map_inv.notna() & mv.map_ni.isna()).sum())} / "
    f"{int((mv.map_inv.isna() & mv.map_ni.notna()).sum())} / {n_both}")
if n_both:
    dfboth = mv[mv.map_inv.notna() & mv.map_ni.notna()]
    d = (dfboth.map_inv - dfboth.map_ni)
    log(f"  paired difference (invasive - non-invasive), same patient:")
    log(f"    mean {d.mean():+.3f} mmHg   median {d.median():+.3f}   "
        f"IQR {d.quantile(.25):+.2f} to {d.quantile(.75):+.2f}")
log("\n  MIMIC MAP sources: mbp_mean (itemid 220181, non-invasive cuff) and")
log("  map_arterial (220052). MIMIC mbp_mean does NOT prioritise invasive.")
log("  => the two centres do NOT define MAP identically. This is a REAL limitation.")

# sensitivity: rebuild eICU MAP three ways and re-validate
log("\n  SENSITIVITY -- external validation under three MAP definitions:")
sens = []
for lbl, col_inv, col_ni in [("current composite (invasive preferred)", "map_inv", "map_ni"),
                             ("non-invasive preferred", "map_ni", "map_inv"),
                             ("invasive ONLY (drop if absent)", "map_inv", None)]:
    e3 = A[A.centre == "eICU"].merge(mv, on="stay_id", how="left")
    if col_ni is None:
        e3["map"] = e3[col_inv]
    else:
        e3["map"] = e3[col_inv].fillna(e3[col_ni])
    # re-apply the frozen model with the modified MAP only
    coef = pd.read_csv(os.path.join(DATA, "model_v2_coefficients.csv"))
    dev = A[A.centre == "MIMIC-IV"]
    med = dev[cfg.PRIMARY_CONTINUOUS].median(numeric_only=True)
    X = e3[cfg.PRIMARY_CONTINUOUS + cfg.PRIMARY_BINARY].astype(float).copy()
    for c_ in cfg.PRIMARY_CONTINUOUS:
        X[c_] = X[c_].fillna(float(med[c_]))
    for c_ in cfg.MISSING_INDICATORS_PRIMARY:
        X[f"miss_{c_}"] = e3[c_].isna().astype(int)
    X = X[list(coef.term[1:])]
    p = prov.expit(np.column_stack([np.ones(len(X)), X.values]) @ coef.beta.values)
    mt = prov.metrics(e3.hospital_mortality.values.astype(float), p)
    sens.append(dict(map_definition=lbl, n=mt["n"], events=mt["events"],
                     auroc=round(mt["auroc"], 4), brier=round(mt["brier"], 4),
                     oe=round(mt["oe"], 3), calib_slope=round(mt["calib_slope"], 4)))
    log(f"    {lbl:<38} n={mt['n']:>5,}  AUROC={mt['auroc']:.4f}  "
        f"O/E={mt['oe']:.3f}  slope={mt['calib_slope']:.3f}")
sensdf = pd.DataFrame(sens)
spread_auc = sensdf.auroc.max() - sensdf.auroc.min()
spread_oe = sensdf.oe.max() - sensdf.oe.min()
log(f"\n  spread across MAP definitions: AUROC {spread_auc:.4f}   O/E {spread_oe:.4f}")
log(f"  -> {'ROBUST to the MAP definition' if spread_auc < 0.005 and spread_oe < 0.02 else 'SENSITIVE to the MAP definition -- must be reported as a limitation'}")
sensdf.to_csv(os.path.join(DATA, "map_sensitivity.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "map_sensitivity.csv"), "phase_5_6_7_scores.py")

with pd.ExcelWriter(os.path.join(TABLES, "TableS9_score_detail.xlsx"),
                    engine="openpyxl") as xl:
    sc_df.to_excel(xl, sheet_name="paired_comparisons", index=False)
    if len(common) >= 100:
        cc.to_excel(xl, sheet_name="common_complete", index=False)
    sensdf.to_excel(xl, sheet_name="map_sensitivity", index=False)
prov.stamp(os.path.join(TABLES, "TableS9_score_detail.xlsx"), "phase_5_6_7_scores.py")

with open(os.path.join(LOGS, "PHASE_5_6_7_scores.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nPHASE 5-7 + 10 DONE")

