"""PUBLICATION LOCK 搂3, 搂4, 搂5 -- optimism, repeated-patient sensitivity, and the
final cluster-aware external validation.

All three use the certified FINAL_MODEL_V2, the frozen config and the certified
dataset. Nothing about the phenotype, cohort eligibility, outcome, window,
predictors, aggregation, imputation, indicator set, model or score formulas is
modified. The model is refitted only where the brief explicitly requires it
(optimism, and the first-admission-per-patient sensitivity).

Outputs:
  tables/TableS7_optimism.xlsx
  data/publock_optimism.csv
  data/publock_repeated_patient.csv
  data/publock_external_ci.csv
"""
from __future__ import annotations

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
CONT = cfg.PRIMARY_CONTINUOUS
BIN = cfg.PRIMARY_BINARY
IND = cfg.MISSING_INDICATORS_PRIMARY


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


prov.announce("publock_03_04_05.py")
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")

dev = A[A.centre == "MIMIC-IV"].copy()
eic = A[A.centre == "eICU"].copy()
nw = A[A.centre == "nwICU"].copy()
med = dev[CONT].median(numeric_only=True)


def design(df, medians=med):
    """The frozen design matrix: config predictors + the config indicator set,
    median imputation from the DEVELOPMENT cohort."""
    x = df[CONT + BIN].astype(float).copy()
    for c in CONT:
        x[c] = x[c].fillna(float(medians[c]))
    for c in IND:
        x[f"miss_{c}"] = df[c].isna().astype(int)
    return x


NAMES = list(design(dev.head(3)).columns)


def fit(df, medians=med):
    X = design(df, medians)
    Xd = np.column_stack([np.ones(len(X)), X.values])
    b, conv, _ = prov.fit_logistic(Xd, df[OUT].values.astype(float))
    if not conv:
        raise SystemExit("STOP: unpenalized fit did not converge")
    return b


def predict(df, b, medians=med):
    X = design(df, medians).reindex(columns=NAMES, fill_value=0)
    return prov.expit(np.column_stack([np.ones(len(X)), X.values]) @ b)


def ici(p, y, bins=10):
    q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    if len(q) < 3:
        return np.nan
    idx = np.clip(np.digitize(p, q[1:-1]), 0, len(q) - 2)
    tot = 0.0
    for b in np.unique(idx):
        m = idx == b
        tot += m.sum() * abs(y[m].mean() - p[m].mean())
    return float(tot / len(p))


def emax(p, y, bins=10):
    q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    if len(q) < 3:
        return np.nan
    idx = np.clip(np.digitize(p, q[1:-1]), 0, len(q) - 2)
    worst = np.nan
    for b in np.unique(idx):
        m = idx == b
        d = abs(y[m].mean() - p[m].mean())
        worst = d if not np.isfinite(worst) else max(worst, d)
    return float(worst)


def auprc(y, p):
    """Area under the precision-recall curve (average precision), non-interpolated.

    Independent of the AUROC implementation: precision = TP/(TP+FP) is evaluated at
    every distinct threshold reached by sorting on p descending, then summed with the
    recall increment. Ties are handled by processing equal scores as one block.
    """
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    y, p = y[ok], p[ok]
    n_pos = float(y.sum())
    if n_pos == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    ys = y[order]
    ps = p[order]
    # block boundaries: all rows sharing an identical score form one threshold
    distinct = np.ones(len(ps), bool)
    distinct[1:] = ps[1:] != ps[:-1]
    last = np.flatnonzero(distinct)          # last index of each score block
    cum_tp = np.cumsum(ys)
    tp = cum_tp[last]                        # true positives at each threshold
    n_at = last + 1                          # predictions with score >= threshold
    fp = n_at - tp
    precision = np.divide(tp, tp + fp, out=np.ones_like(tp, float), where=(tp + fp) > 0)
    recall = tp / n_pos
    # average precision: sum over thresholds of precision * increase in recall
    d_recall = np.diff(np.concatenate([[0.0], recall]))
    return float(np.sum(precision * d_recall))


def full_metrics(y, p):
    m = prov.metrics(y, p)
    m["ici"] = ici(np.asarray(p, float), np.asarray(y, float))
    m["emax"] = emax(np.asarray(p, float), np.asarray(y, float))
    m["auprc"] = auprc(y, p)
    return m


OUT = "hospital_mortality"
b_full = fit(dev)
log(f"  development cohort: n={len(dev):,}  events={int(dev[OUT].sum()):,}  "
    f"patients={dev.subject_id.nunique():,}")
log(f"  refit reproduces the certified coefficients: "
    f"{np.allclose(b_full, pd.read_csv(os.path.join(DATA,'model_v2_coefficients.csv')).beta.values, atol=1e-8)}")

# ===================================================================== 搂3 optimism
log("\n" + "=" * 100)
log("SECTION 3 -- BOOTSTRAP OPTIMISM CORRECTION (PATIENT-level resampling)")
log("=" * 100)
log("  Sampling unit: PATIENT. Each replicate resamples patients with replacement")
log("  and takes ALL their eligible admissions, so dependence between episodes of")
log("  the same patient is preserved rather than broken.")

pats = dev.subject_id.values
uniq_p = np.unique(pats)
by_pat = {p_: np.where(pats == p_)[0] for p_ in uniq_p}
log(f"  distinct patients in development cohort: {len(uniq_p):,}")
log(f"  patients contributing >1 eligible admission: "
    f"{int(sum(1 for v in by_pat.values() if len(v) > 1)):,}")

N_BOOT = int(os.environ.get("PUBLOCK_OPTIMISM_BOOT", "1000"))
rng = np.random.default_rng(cfg.RANDOM_SEED)
app_auc = prov.auroc(dev[OUT].values.astype(float), dev.p_model.values)
app_brier = prov.brier(dev[OUT].values.astype(float), dev.p_model.values)
app_slope = prov.cal_slope_intercept(dev[OUT].values.astype(float),
                                     dev.p_model.values)[0]
log(f"\n  apparent (certified) performance:")
log(f"    AUROC {app_auc:.6f}   Brier {app_brier:.6f}   calibration slope {app_slope:.6f}")

opt_auc, opt_brier, opt_slope = [], [], []
y_dev = dev[OUT].values.astype(float)
for i in range(N_BOOT):
    sel = rng.choice(uniq_p, size=len(uniq_p), replace=True)
    idx = np.concatenate([by_pat[p_] for p_ in sel])
    db_ = dev.iloc[idx]
    if db_[OUT].nunique() < 2:
        continue
    try:
        b_b = fit(db_)
    except SystemExit:
        continue
    # apparent in the bootstrap sample
    p_b = predict(db_, b_b)
    y_b = db_[OUT].values.astype(float)
    # tested on the ORIGINAL development dataset
    p_o = predict(dev, b_b)
    opt_auc.append(prov.auroc(y_b, p_b) - prov.auroc(y_dev, p_o))
    opt_brier.append(prov.brier(y_b, p_b) - prov.brier(y_dev, p_o))
    opt_slope.append(float(np.polyfit(np.log(np.clip(p_b, 1e-9, 1 - 1e-9) /
                                                 (1 - np.clip(p_b, 1e-9, 1 - 1e-9))),
                                      y_b, 1)[0])
                     - float(np.polyfit(np.log(np.clip(p_o, 1e-9, 1 - 1e-9) /
                                                 (1 - np.clip(p_o, 1e-9, 1 - 1e-9))),
                                        y_dev, 1)[0]))
    if (i + 1) % 250 == 0:
        log(f"    ... {i+1}/{N_BOOT} replicates")

opt_auc = np.array(opt_auc)
opt_brier = np.array(opt_brier)
opt_slope = np.array(opt_slope)
log(f"\n  usable replicates: {len(opt_auc)}/{N_BOOT}")
log(f"  mean optimism AUROC   : {opt_auc.mean():+.6f}  "
    f"(95% range {np.percentile(opt_auc,2.5):+.6f} to {np.percentile(opt_auc,97.5):+.6f})")
log(f"  mean optimism Brier   : {opt_brier.mean():+.6f}")
log(f"  mean optimism slope   : {opt_slope.mean():+.6f}")

opt = pd.DataFrame([
    dict(quantity="AUROC", apparent=app_auc, optimism=float(opt_auc.mean()),
         corrected=float(app_auc - opt_auc.mean()),
         opt_lo=float(np.percentile(opt_auc, 2.5)),
         opt_hi=float(np.percentile(opt_auc, 97.5)), n_boot=len(opt_auc)),
    dict(quantity="Brier", apparent=app_brier, optimism=float(opt_brier.mean()),
         corrected=float(app_brier + opt_brier.mean()),
         opt_lo=float(np.percentile(opt_brier, 2.5)),
         opt_hi=float(np.percentile(opt_brier, 97.5)), n_boot=len(opt_brier)),
    dict(quantity="calibration slope", apparent=app_slope,
         optimism=float(opt_slope.mean()), corrected=float(app_slope - opt_slope.mean()),
         opt_lo=float(np.percentile(opt_slope, 2.5)),
         opt_hi=float(np.percentile(opt_slope, 97.5)), n_boot=len(opt_slope)),
])
log("\n" + opt.to_string(index=False))
opt.to_csv(os.path.join(DATA, "publock_optimism.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_optimism.csv"), "publock_03_04_05.py")
# Published as Table_Final_Optimism.xlsx (the filename fixed by the publication-lock
# specification) and repeated as sheet S7 of Supplementary_Tables_S1_S7.xlsx so the
# supplementary series is self-contained. Both are written from this one frame.
with pd.ExcelWriter(os.path.join(TABLES, "Table_Final_Optimism.xlsx"),
                    engine="openpyxl") as xl:
    opt.to_excel(xl, sheet_name="optimism", index=False)
prov.stamp(os.path.join(TABLES, "Table_Final_Optimism.xlsx"), "publock_03_04_05.py")

# ===================================================================== 搂4 repeated patients
log("\n" + "=" * 100)
log("SECTION 4 -- REPEATED-PATIENT SENSITIVITY (first eligible admission per patient)")
log("=" * 100)
log("  Primary analysis unit is the first ICU stay per hospital admission, so a")
log("  patient may contribute several admissions. This sensitivity keeps only each")
log("  patient's FIRST eligible admission.")

dev_f = (dev.sort_values(["subject_id", "admittime"])
            .groupby("subject_id", as_index=False).first())
# the analysis dataset carries no eICU patient identifier, so pull the patient key
# from the frozen cohort file (read-only, no change to any definition)
_co = pd.read_csv(os.path.join(DATA, "cohort_eicu.csv"), low_memory=False)
uid_map = _co.set_index("stay_id")["patient_uid"]
eic["patient_uid"] = eic.stay_id.map(uid_map)
eic_f = (eic.sort_values(["patient_uid", "stay_id"])
            .groupby("patient_uid", as_index=False).first())
log(f"  MIMIC : {len(dev):,} -> {len(dev_f):,} admissions "
    f"({dev_f.subject_id.nunique():,} patients)")
log(f"  eICU  : {len(eic):,} -> {len(eic_f):,} admissions "
    f"({eic_f.patient_uid.nunique():,} patients)")

med_f = dev_f[CONT].median(numeric_only=True)
b_f = fit(dev_f, med_f)
rows = []
m_prim_dev = full_metrics(y_dev, dev.p_model.values)
rows.append(dict(analysis="primary (episode-level, certified)", cohort="MIMIC-IV",
                 n=len(dev), events=int(dev[OUT].sum()), auroc=round(m_prim_dev["auroc"], 4),
                 brier=round(m_prim_dev["brier"], 4), oe=round(m_prim_dev["oe"], 3),
                 calib_slope=round(m_prim_dev["calib_slope"], 4)))
p_f_dev = predict(dev_f, b_f, med_f)
m_f = full_metrics(dev_f[OUT].values.astype(float), p_f_dev)
rows.append(dict(analysis="first admission per patient", cohort="MIMIC-IV",
                 n=len(dev_f), events=int(dev_f[OUT].sum()), auroc=round(m_f["auroc"], 4),
                 brier=round(m_f["brier"], 4), oe=round(m_f["oe"], 3),
                 calib_slope=round(m_f["calib_slope"], 4)))
m_prim_e = full_metrics(eic[OUT].values.astype(float), eic.p_model.values)
rows.append(dict(analysis="primary (episode-level, certified)", cohort="eICU",
                 n=len(eic), events=int(eic[OUT].sum()), auroc=round(m_prim_e["auroc"], 4),
                 brier=round(m_prim_e["brier"], 4), oe=round(m_prim_e["oe"], 3),
                 calib_slope=round(m_prim_e["calib_slope"], 4)))
# eICU validated with the MIMIC first-admission model
p_f_e = predict(eic_f, b_f, med_f)
m_fe = full_metrics(eic_f[OUT].values.astype(float), p_f_e)
rows.append(dict(analysis="first admission per patient", cohort="eICU",
                 n=len(eic_f), events=int(eic_f[OUT].sum()), auroc=round(m_fe["auroc"], 4),
                 brier=round(m_fe["brier"], 4), oe=round(m_fe["oe"], 3),
                 calib_slope=round(m_fe["calib_slope"], 4)))
rp = pd.DataFrame(rows)
log("\n" + rp.to_string(index=False))

d_auc = abs(m_fe["auroc"] - m_prim_e["auroc"])
d_oe = abs(m_fe["oe"] - m_prim_e["oe"])
d_slope = abs(m_fe["calib_slope"] - m_prim_e["calib_slope"])
GUIDE = dict(auroc=0.01, oe=0.03, slope=0.10)
log(f"\n  change in the eICU external result (primary vs first-admission):")
log(f"    dAUROC = {d_auc:.4f}   (guide < {GUIDE['auroc']})  "
    f"{'within' if d_auc < GUIDE['auroc'] else 'EXCEEDS'}")
log(f"    dO/E   = {d_oe:.4f}   (guide < {GUIDE['oe']})  "
    f"{'within' if d_oe < GUIDE['oe'] else 'EXCEEDS'}")
log(f"    dslope = {d_slope:.4f}   (guide < {GUIDE['slope']})  "
    f"{'within' if d_slope < GUIDE['slope'] else 'EXCEEDS'}")
robust = d_auc < GUIDE["auroc"] and d_oe < GUIDE["oe"] and d_slope < GUIDE["slope"]
log(f"\n  VERDICT: repeated episodes do {'NOT ' if robust else ''}materially change the")
log(f"  conclusion (predefined robustness guide, not a significance test).")
rp.to_csv(os.path.join(DATA, "publock_repeated_patient.csv"), index=False,
          encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_repeated_patient.csv"), "publock_03_04_05.py")

# ===================================================================== 搂5 cluster CI
log("\n" + "=" * 100)
log("SECTION 5 -- FINAL CLUSTER-AWARE EXTERNAL VALIDATION (hospital bootstrap)")
log("=" * 100)
e = eic.dropna(subset=["hospitalid"]).copy()
e["hospitalid"] = e.hospitalid.astype(int)
y_e = e[OUT].values.astype(float)
p_e = e.p_model.values.astype(float)
hosp = e.hospitalid.values
uniq_h = np.unique(hosp)
by_h = {h: np.where(hosp == h)[0] for h in uniq_h}
log(f"  eICU cohort: n={len(e):,}  events={int(y_e.sum()):,}  hospitals={len(uniq_h)}")

est = full_metrics(y_e, p_e)
log(f"\n  point estimates:")
for k in ["auroc", "auprc", "brier", "oe", "calib_intercept", "calib_slope", "ici",
          "emax", "n", "events"]:
    log(f"    {k:<18} {est[k]}")

NB = max(2000, cfg.N_BOOTSTRAP_CLUSTER)
rng2 = np.random.default_rng(cfg.RANDOM_SEED + 1)
boot = {k: [] for k in ["auroc", "auprc", "brier", "oe", "calib_intercept",
                        "calib_slope", "ici", "emax"]}
for _ in range(NB):
    sel = rng2.choice(uniq_h, size=len(uniq_h), replace=True)
    idx = np.concatenate([by_h[h] for h in sel])
    if len(np.unique(y_e[idx])) < 2:
        continue
    m = full_metrics(y_e[idx], p_e[idx])
    for k in boot:
        boot[k].append(m[k])
log(f"\n  CLUSTER-AWARE 95% CIs ({len(boot['auroc'])} / {NB} usable replicates):")
ci_rows = []
for k in ["auroc", "auprc", "brier", "oe", "calib_intercept", "calib_slope", "ici",
          "emax"]:
    arr = np.array(boot[k], float)
    lo, hi = np.percentile(arr, [2.5, 97.5])
    ci_rows.append(dict(quantity=k, estimate=est[k], ci_lo=float(lo), ci_hi=float(hi),
                        n_boot=len(arr)))
    log(f"    {k:<18} {est[k]:>10.5f}   95% CI ({lo:.5f}, {hi:.5f})")
ci = pd.DataFrame(ci_rows)
ci.to_csv(os.path.join(DATA, "publock_external_ci.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_external_ci.csv"), "publock_03_04_05.py")

log("\n  NOTE: eICU calibration quantities in the manuscript must use these")
log("  cluster-aware intervals. A naive individual-level CI is not permitted.")

# stop-condition check against the certified numbers
log("\n" + "=" * 100)
log("STOP-CONDITION CHECK vs the certified result")
log("=" * 100)
CERT = dict(auroc=0.7918, oe=0.858, slope=1.0333, n=1612, events=324)
checks = [("AUROC", abs(est["auroc"] - CERT["auroc"]), 0.005),
          ("O/E", abs(est["oe"] - CERT["oe"]), 0.02),
          ("calibration slope", abs(est["calib_slope"] - CERT["slope"]), 0.05)]
viol = []
for nm, d, tol in checks:
    ok = d <= tol
    log(f"  {nm:<18} |change| = {d:.6f}  tolerance {tol}  {'OK' if ok else 'VIOLATED'}")
    if not ok:
        viol.append(nm)
if est["n"] != CERT["n"] or est["events"] != CERT["events"]:
    viol.append("cohort N/events")
log(f"  cohort N/events    {est['n']}/{est['events']} vs certified "
    f"{CERT['n']}/{CERT['events']}  "
    f"{'OK' if (est['n']==CERT['n'] and est['events']==CERT['events']) else 'CHANGED'}")
log(f"\n  STOP CONDITIONS: {'all clear' if not viol else 'VIOLATED -> ' + ', '.join(viol)}")

with io.open(os.path.join(LOGS, "PUBLOCK_03_04_05.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nSECTION 3-5 DONE")
