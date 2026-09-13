"""PUBLICATION LOCK 搂8 (paired score inference + selection) and 搂12 supplementary
tables S1-S6, plus the age fix for Table 1.

搂8  paired bootstrap differences on the UNCHANGED common-complete cohort
    (n=758, 184 deaths): FINAL_MODEL_V2 vs MELD / MELD-Na / ALBI / FIB-4.
    Selection description: included vs excluded patients.
S1  missingness by centre
S2  missing-data strategies (A/B/C)
S3  24h landmark + 0-6h early prediction
S4  MAP definition sensitivity
S5  first-admission-per-patient sensitivity
S6  cirrhosis ICD phenotype composition
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
OUT = "hospital_mortality"


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


prov.announce("publock_08b_selection_paired.py")
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")

# ===================================================================== rebuild score components
# exactly as phase_5_6_7_scores.py did, so the common-complete mask is identical
e = A[A.centre == "eICU"].copy()
W = cfg.WINDOW_PRIMARY_HOURS
import psycopg2  # noqa: E402
# Credentials come from the environment; see .env.example and db.py.
# The original hardcoded local credentials were removed for public release.
PG = dict(connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")))


def conn(dbname):
    c = db.connect(dbname)  # credentials from the environment
    c.set_session(readonly=True, autocommit=True)
    return c


with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute(f"""
            SELECT patientunitstayid, labname, min(labresult), max(labresult)
            FROM eicu_crd.lab
            WHERE patientunitstayid = ANY(%s) AND labresult IS NOT NULL
              AND labresultoffset > 0 AND labresultoffset <= {W*60}
              AND labname IN ('PT - INR','AST (SGOT)','ALT (SGPT)','Hgb')
            GROUP BY 1,2
        """, ([int(x) for x in e.stay_id],))
        ex = pd.DataFrame(cur.fetchall(), columns=["stay_id", "labname", "vmin", "vmax"])
for src, name, how in [("PT - INR", "inr", "max"), ("AST (SGOT)", "ast", "max"),
                       ("ALT (SGPT)", "alt", "max"), ("Hgb", "hemoglobin", "min")]:
    s = ex[ex.labname == src].set_index("stay_id")["vmax" if how == "max" else "vmin"]
    e[name] = pd.to_numeric(e.stay_id.map(s), errors="coerce")
e["rrt"] = np.nan


def calc_meld(b, i, cr, rrt=None):
    b = np.clip(np.asarray(b, float), 1.0, None)
    i = np.clip(np.asarray(i, float), 1.0, None)
    cr = np.clip(np.asarray(cr, float), 1.0, 4.0)
    if rrt is not None:
        cr = np.where(np.asarray(rrt, float) == 1, 4.0, cr)
    return np.round(np.clip(3.78*np.log(b) + 11.2*np.log(i) + 9.57*np.log(cr) + 6.43, 6, 40))


def calc_meldna(m, na):
    m = np.asarray(m, float)
    na = np.clip(np.asarray(na, float), *cfg.SCORE_MELDNA_NA_BOUNDS)
    c1, c2 = cfg.SCORE_MELDNA_COEF
    return np.clip(m + c1*(137-na) - c2*m*(137-na), *cfg.SCORE_MELD_CLIP)


def calc_albi(alb, bili):
    return (np.log10(np.maximum(np.asarray(bili, float) *
                                cfg.BILI_MGDL_TO_UMOLL, 1e-9)) * 0.66 +
            np.asarray(alb, float) * cfg.ALB_GDL_TO_GL * (-0.085))


def calc_fib4(age, ast, alt, plt_):
    return (np.asarray(age, float) * np.asarray(ast, float)) / (
        np.maximum(np.asarray(plt_, float), 1e-9) * np.sqrt(np.maximum(np.asarray(alt, float), 1e-9)))


e["score_meld"] = calc_meld(e.bilirubin, e.inr, e.creatinine)
e["score_meldna"] = calc_meldna(e.score_meld, e.sodium)
e["score_albi"] = calc_albi(e.albumin, e.bilirubin)
e["score_fib4"] = calc_fib4(e.age, e.ast, e.alt, e.platelet)

mask_cc = e[["score_meld", "score_albi", "score_fib4"]].notna().all(axis=1) & e.p_model.notna()
cc = e[mask_cc].copy()
log("=" * 100)
log("SECTION 8 -- COMMON-COMPLETE COHORT")
log("=" * 100)
log(f"  reconstructed common-complete cohort: n={len(cc):,}  events={int(cc[OUT].sum()):,}")
log(f"  (matches the locked value of 758 / 184: "
    f"{len(cc) == 758 and int(cc[OUT].sum()) == 184})")

# ===================================================================== selection description
log("\n" + "=" * 100)
log("SELECTION DESCRIPTION -- included vs excluded patients")
log("=" * 100)
inc = e[mask_cc]
exc = e[~mask_cc]
rows = []
for lbl, col in [("n", None), ("age, median (IQR)", "age"), ("male %", "male"),
                 ("in-hospital mortality %", OUT), ("albumin g/dL", "albumin"),
                 ("bilirubin mg/dL", "bilirubin"), ("creatinine mg/dL", "creatinine"),
                 ("predicted risk (model)", "p_model")]:
    r = dict(characteristic=lbl)
    for nm, g in [("included (n=%d)" % len(inc), inc), ("excluded (n=%d)" % len(exc), exc)]:
        if col is None:
            r[nm] = f"{len(g):,}"
        elif col == "male":
            r[nm] = f"{100*g.male.mean():.1f}"
        elif col == OUT:
            r[nm] = f"{100*g[OUT].mean():.1f}"
        else:
            s = pd.to_numeric(g[col], errors="coerce").dropna()
            r[nm] = "NA" if len(s) == 0 else f"{s.median():.1f} ({s.quantile(.25):.1f}-{s.quantile(.75):.1f})"
    rows.append(r)
sel = pd.DataFrame(rows)
log(sel.to_string(index=False))
log("\n  reading: the common-complete subset is defined by score availability, so any")
log("  difference reflects which patients have the required laboratory components")
log("  (notably INR) rather than a modelling choice. This is reported as a")
log("  description of selection, not corrected for.")

# ===================================================================== paired bootstrap
log("\n" + "=" * 100)
log("PAIRED INFERENCE -- FINAL_MODEL_V2 vs each score (same patients)")
log("=" * 100)
hid = cc.hospitalid.values
uniq_h = np.unique(hid)
by_h = {h: np.where(hid == h)[0] for h in uniq_h}
y = cc[OUT].values.astype(float)


def score_risk(col, dev_col=None):
    """fit the score->risk mapping in MIMIC only, apply to eICU."""
    mim = A[A.centre == "MIMIC-IV"].copy()
    # MIMIC side components are already in the analysis dataset except INR/AST/ALT
    # -> refit is done in publock_03 for the model; here reuse the locked AUROC/OE
    #    by mapping the eICU score through a logistic fitted on eICU-independent
    #    MIMIC values carried in score_comparison_common_complete.csv inputs.
    raise NotImplementedError


# The score -> risk mapping is refitted HERE from the frozen MIMIC data, because the
# historical score_mappings.csv belongs to the superseded tree and must not be read.
# Method is unchanged: fit logit(mortality) = a + b*score in MIMIC only, apply the
# coefficients unchanged to eICU.
log("\n  refitting score -> risk mappings in MIMIC only (never in eICU)")
mim = A[A.centre == "MIMIC-IV"].copy()
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
        """, ([int(x) for x in mim.stay_id], [51237, 50878, 50861]))
        mx = pd.DataFrame(cur.fetchall(), columns=["stay_id", "itemid", "vmin", "vmax"])
for item, name in [(51237, "inr"), (50878, "ast"), (50861, "alt")]:
    s = mx[mx.itemid == item].set_index("stay_id")["vmax"]
    mim[name] = pd.to_numeric(mim.stay_id.map(s), errors="coerce")
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT stay_id, rrt, meld_initial FROM mimiciv_derived.meld
            WHERE stay_id = ANY(%s)
        """, ([int(x) for x in mim.stay_id],))
        mr = pd.DataFrame(cur.fetchall(), columns=["stay_id", "rrt", "meld_initial"])
mim = mim.merge(mr, on="stay_id", how="left")
mim["rrt"] = pd.to_numeric(mim.rrt, errors="coerce")
mim["score_meld"] = calc_meld(mim.bilirubin, mim.inr, mim.creatinine, mim.rrt)
mim["score_meldna"] = calc_meldna(mim.score_meld, mim.sodium)
mim["score_albi"] = calc_albi(mim.albumin, mim.bilirubin)
mim["score_fib4"] = calc_fib4(mim.age, mim.ast, mim.alt, mim.platelet)

MAP_ROWS = []
for col, lbl in [("score_meld", "MELD"), ("score_meldna", "MELD-Na"),
                 ("score_albi", "ALBI"), ("score_fib4", "FIB-4")]:
    d_ = mim[mim[col].notna() & mim[OUT].notna()]
    X = np.column_stack([np.ones(len(d_)), d_[col].values.astype(float)])
    b_, conv, _ = prov.fit_logistic(X, d_[OUT].values.astype(float))
    assert conv, f"score mapping for {lbl} did not converge"
    MAP_ROWS.append(dict(score=lbl, alpha=float(b_[0]), beta=float(b_[1]),
                         n_used=len(d_)))
MAP = pd.DataFrame(MAP_ROWS)
log(MAP.to_string(index=False))
MAP.to_csv(os.path.join(DATA, "publock_score_mappings.csv"), index=False,
           encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_score_mappings.csv"),
           "publock_08b_selection_paired.py")


def risk_from_score(name, x):
    r = MAP[MAP.score == name]
    a, b = float(r.alpha.iloc[0]), float(r.beta.iloc[0])
    return prov.expit(a + b*np.asarray(x, float))


cc = cc.assign(
    p_MELD=risk_from_score("MELD", cc.score_meld),
    p_MELD_Na=risk_from_score("MELD-Na", cc.score_meldna),
    p_ALBI=risk_from_score("ALBI", cc.score_albi),
    p_FIB_4=risk_from_score("FIB-4", cc.score_fib4))
log("\n  risk columns built for: FINAL_MODEL_V2, MELD, MELD-Na, ALBI, FIB-4")

PAIRS = [("FINAL_MODEL_V2", "p_model", "MELD", "p_MELD"),
         ("FINAL_MODEL_V2", "p_model", "MELD-Na", "p_MELD_Na"),
         ("FINAL_MODEL_V2", "p_model", "ALBI", "p_ALBI"),
         ("FINAL_MODEL_V2", "p_model", "FIB-4", "p_FIB_4")]
NB = 2000
rng = np.random.default_rng(cfg.RANDOM_SEED + 11)
rows = []
for a_lbl, a_col, b_lbl, b_col in PAIRS:
    pa, pb = cc[a_col].values.astype(float), cc[b_col].values.astype(float)
    obs = dict(
        d_auroc=prov.auroc(y, pa) - prov.auroc(y, pb),
        d_brier=prov.brier(y, pa) - prov.brier(y, pb),
        d_oe=prov.oe_ratio(y, pa) - prov.oe_ratio(y, pb),
        d_slope=prov.cal_slope_intercept(y, pa)[0] - prov.cal_slope_intercept(y, pb)[0])
    bs = {k: [] for k in obs}
    for _ in range(NB):
        sel_h = rng.choice(uniq_h, size=len(uniq_h), replace=True)
        idx = np.concatenate([by_h[h] for h in sel_h])
        yb = y[idx]
        if len(np.unique(yb)) < 2:
            continue
        a_, b_ = pa[idx], pb[idx]
        bs["d_auroc"].append(prov.auroc(yb, a_) - prov.auroc(yb, b_))
        bs["d_brier"].append(prov.brier(yb, a_) - prov.brier(yb, b_))
        bs["d_oe"].append(prov.oe_ratio(yb, a_) - prov.oe_ratio(yb, b_))
        sa, sb_ = prov.cal_slope_intercept(yb, a_)[0], prov.cal_slope_intercept(yb, b_)[0]
        bs["d_slope"].append(sa - sb_)
    rec = dict(comparison=f"{a_lbl} vs {b_lbl}", n=len(cc), events=int(y.sum()))
    for k, v in obs.items():
        arr = np.array(bs[k], float)
        arr = arr[np.isfinite(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5])
        rec[f"{k}"] = round(float(v), 4)
        rec[f"{k}_lo"] = round(float(lo), 4)
        rec[f"{k}_hi"] = round(float(hi), 4)
        rec[f"{k}_excl0"] = bool(lo > 0 or hi < 0)
    rows.append(rec)
    log(f"\n  {rec['comparison']}")
    log(f"    dAUROC {rec['d_auroc']:+.4f}  95% CI ({rec['d_auroc_lo']:+.4f}, "
        f"{rec['d_auroc_hi']:+.4f})  {'EXCLUDES 0' if rec['d_auroc_excl0'] else 'includes 0'}")
    log(f"    dBrier {rec['d_brier']:+.4f}  95% CI ({rec['d_brier_lo']:+.4f}, "
        f"{rec['d_brier_hi']:+.4f})  {'EXCLUDES 0' if rec['d_brier_excl0'] else 'includes 0'}")
    log(f"    dO/E   {rec['d_oe']:+.4f}  95% CI ({rec['d_oe_lo']:+.4f}, "
        f"{rec['d_oe_hi']:+.4f})  {'EXCLUDES 0' if rec['d_oe_excl0'] else 'includes 0'}")
    log(f"    dslope {rec['d_slope']:+.4f}  95% CI ({rec['d_slope_lo']:+.4f}, "
        f"{rec['d_slope_hi']:+.4f})  {'EXCLUDES 0' if rec['d_slope_excl0'] else 'includes 0'}")
paired = pd.DataFrame(rows)
paired.to_csv(os.path.join(DATA, "publock_paired_score_differences.csv"), index=False,
              encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_paired_score_differences.csv"),
           "publock_08b_selection_paired.py")

sig = paired[paired.comparison.str.contains("MELD")].d_auroc_excl0.all()
log(f"\n  'significantly better discrimination than MELD/MELD-Na': {sig}")
log("  -> manuscript wording: " +
    ("'significantly better' is permitted for MELD comparisons"
     if sig else "'numerically higher' only; the paired CI includes 0"))

with pd.ExcelWriter(os.path.join(TABLES, "Table6_score_comparison.xlsx"),
                    engine="openpyxl") as xl:
    pd.read_csv(os.path.join(DATA, "score_comparison_common_complete.csv")).to_excel(
        xl, sheet_name="common_complete", index=False)
    paired.to_excel(xl, sheet_name="paired_differences", index=False)
    sel.to_excel(xl, sheet_name="selection", index=False)
prov.stamp(os.path.join(TABLES, "Table6_score_comparison.xlsx"),
           "publock_08b_selection_paired.py")

# ===================================================================== supplementary tables
log("\n" + "=" * 100)
log("SUPPLEMENTARY TABLES S1-S6")
log("=" * 100)
S1 = A.groupby("centre")[cfg.PRIMARY_CONTINUOUS + cfg.PRIMARY_BINARY + ["hemoglobin"]].apply(
    lambda g: (100*g.notna().mean()).round(1)).T
S2 = pd.read_csv(os.path.join(DATA, "missingness_sensitivity.csv"))
S3 = pd.read_csv(os.path.join(DATA, "early_prediction_sensitivity.csv"))
S4 = pd.read_csv(os.path.join(DATA, "map_sensitivity.csv"))
S5 = pd.read_csv(os.path.join(DATA, "publock_repeated_patient.csv"))
S6 = pd.read_excel(os.path.join(TABLES, "TableS8_cohort_composition.xlsx"),
                   sheet_name="code_composition")
S7 = pd.read_csv(os.path.join(DATA, "publock_optimism.csv"))   # optimism correction
for nm, t in [("S1 missingness", S1), ("S2 missing-data strategies", S2),
              ("S3 landmark + early", S3), ("S4 MAP sensitivity", S4),
              ("S5 first-admission sensitivity", S5), ("S6 phenotype composition", S6),
              ("S7 optimism", S7)]:
    log(f"\n  {nm}")
    log(t.to_string() if len(t) < 20 else t.head(20).to_string())

with pd.ExcelWriter(os.path.join(TABLES, "Supplementary_Tables_S1_S7.xlsx"),
                    engine="openpyxl") as xl:
    S1.to_excel(xl, sheet_name="S1_missingness")
    S2.to_excel(xl, sheet_name="S2_missing_strategies", index=False)
    S3.to_excel(xl, sheet_name="S3_landmark_early", index=False)
    S4.to_excel(xl, sheet_name="S4_MAP_sensitivity", index=False)
    S5.to_excel(xl, sheet_name="S5_first_admission", index=False)
    S6.to_excel(xl, sheet_name="S6_phenotype_composition", index=False)
    S7.to_excel(xl, sheet_name="S7_optimism", index=False)
prov.stamp(os.path.join(TABLES, "Supplementary_Tables_S1_S7.xlsx"),
           "publock_08b_selection_paired.py")
log(f"\n  wrote Supplementary_Tables_S1_S7.xlsx")

with io.open(os.path.join(LOGS, "PUBLOCK_08b_selection_paired.log"), "w",
             encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nSECTION 8 + SUPPLEMENTARY DONE")
