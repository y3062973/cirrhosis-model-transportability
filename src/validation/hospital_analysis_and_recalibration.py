"""Hospital-level analysis and leave-one-hospital-out recalibration validation,
on FINAL_MODEL_V2 predictions only.

This script replaces `publock_06_07_hospital.py` from the internal working tree. It
contains ONLY the hospital-level analyses that are reported in the final manuscript:

  6A  descriptive per-hospital table (N>=20 & deaths>=5 primary; N>=30 sensitivity)
  6B  random-effects meta-analysis of per-hospital AUROC
  7   leave-one-hospital-out recalibration: Model 0 / 1 / 2 on pooled held-out
      predictions, with hospital-cluster bootstrap difference CIs.

Scope note -- what is deliberately NOT in this file
---------------------------------------------------
The internal working tree's version of this script carried a third section, 6C, a
custom hierarchical (mixed-effects) calibration fit with a random intercept per
hospital and a common slope. **That analysis was REMOVED from the manuscript as
unreliable** and is not part of release v1.1.0:

  * its custom Laplace criterion omitted the Gaussian prior normalisation
    `-(J/2) log(2 pi tau^2)`, which is not constant in tau;
  * an independent implementation (`lme4::glmer`) disagreed materially about the
    between-hospital variance component (tau = 0.109 against the custom fit's 1e-06);
  * the fit was withdrawn rather than repaired further.

No hierarchical calibration quantity is computed or written here, and no hierarchical
calibration sheet is written into Table 4. The hospital-level evidence is reported
descriptively instead, as observed-to-expected ratios per hospital. The historical
implementation is preserved for audit only, under `docs/archive/`, and must not be
run for inference. See `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`.

Consequently this file contains no mixed-effects fitting of any kind: the only
regressions are unpenalised logistic fits used for per-hospital calibration slopes
and for the recalibration updates.

Outputs
-------
  tables/Table4_hospital_level.xlsx     sheets: all_hospitals, primary_N20,
                                                sensitivity_N30, meta_analysis_AUROC
  tables/Table5_recalibration.xlsx      sheets: held_out_performance,
                                                bootstrap_differences
  data/publock_hospital_descriptive.csv
  data/publock_hospital_meta.csv
  data/publock_recalibration_ci.csv
  data/recalibration_cv_predictions.csv
  logs/PUBLOCK_06_07_hospital.log
"""
from __future__ import annotations

import io
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit

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
MIN_N, MIN_D = cfg.MIN_HOSPITAL_N, cfg.MIN_HOSPITAL_DEATHS
SCRIPT = "src/validation/hospital_analysis_and_recalibration.py"


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


def ici(p, y, bins=10):
    """Integrated Calibration Index: mean |observed - predicted| over deciles."""
    p = np.asarray(p, float); y = np.asarray(y, float)
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
    """Maximum absolute decile-level observed-minus-predicted difference."""
    p = np.asarray(p, float); y = np.asarray(y, float)
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


prov.announce(SCRIPT)
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")
e = A[(A.centre == "eICU")].dropna(subset=["hospitalid", "p_model"]).copy()
e["hospitalid"] = e.hospitalid.astype(int)
y = e[OUT].values.astype(float)
p = e.p_model.values.astype(float)
hid = e.hospitalid.values
log(f"  eICU: n={len(e):,}  events={int(y.sum()):,}  hospitals={e.hospitalid.nunique()}")

# ===================================================================== 6A descriptive
log("\n" + "=" * 100)
log("SECTION 6A -- PER-HOSPITAL DESCRIPTIVE ANALYSIS")
log("=" * 100)
rows = []
for h, g in e.groupby("hospitalid"):
    yy = g[OUT].values.astype(float)
    pp = g.p_model.values.astype(float)
    n1, n0 = int(yy.sum()), int((1 - yy).sum())
    auc = prov.auroc(yy, pp) if (n1 >= 2 and n0 >= 2) else np.nan
    sl = prov.cal_slope_intercept(yy, pp)[0] if (n1 >= 5 and n0 >= 5
                                                 and pp.std() > 0) else np.nan
    rows.append(dict(hospitalid=int(h), n=len(g), deaths=n1,
                     observed=float(yy.mean()), mean_predicted=float(pp.mean()),
                     oe=float(yy.mean() / pp.mean()) if pp.mean() > 0 else np.nan,
                     auroc=auc, calib_slope=sl,
                     teachingstatus=g.teachingstatus.iloc[0] if "teachingstatus" in g else None,
                     region=g.region.iloc[0] if "region" in g else None,
                     numbedscategory=g.numbedscategory.iloc[0] if "numbedscategory" in g else None))
hl = pd.DataFrame(rows)
hl["estimable_auroc"] = hl.auroc.notna()
hl = hl.sort_values("n", ascending=False).reset_index(drop=True)
hl.to_csv(os.path.join(DATA, "publock_hospital_descriptive.csv"), index=False,
          encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_hospital_descriptive.csv"), SCRIPT)
log(f"  hospitals total                     : {len(hl)}")
log(f"  with an estimable AUROC             : {int(hl.estimable_auroc.sum())}")
for tag, sub in [("N>=20 & deaths>=5 (PRIMARY)", hl[(hl.n >= MIN_N) & (hl.deaths >= MIN_D)]),
                 ("N>=30 sensitivity", hl[(hl.n >= 30) & (hl.deaths >= MIN_D)])]:
    log(f"  {tag:<32} k={len(sub):>3}  stays={int(sub.n.sum()):>6,}  "
        f"deaths={int(sub.deaths.sum()):>5,}  "
        f"median AUROC={sub.auroc.median():.3f}  median O/E={sub.oe.median():.3f}")
prim = hl[(hl.n >= MIN_N) & (hl.deaths >= MIN_D) & hl.auroc.notna()].copy()
log(f"\n  primary per-hospital summary (k={len(prim)}):")
log(f"    AUROC  median {prim.auroc.median():.3f}  "
    f"IQR {prim.auroc.quantile(.25):.3f}-{prim.auroc.quantile(.75):.3f}  "
    f"range {prim.auroc.min():.3f}-{prim.auroc.max():.3f}")
log(f"    O/E    median {prim.oe.median():.3f}  "
    f"IQR {prim.oe.quantile(.25):.3f}-{prim.oe.quantile(.75):.3f}")
log(f"    slope  median {prim.calib_slope.median():.3f}")
# The retained hospital-level calibration evidence is DESCRIPTIVE. The spread of the
# per-hospital O/E ratios is reported as observed; NO formal conclusion about
# calibration heterogeneity across hospitals is drawn, and the manuscript must not
# state either that the shift was uniform or that heterogeneity was established.
log(f"    O/E    range {prim.oe.min():.3f}-{prim.oe.max():.3f}  "
    f"{100 * (prim.oe < 1).mean():.1f}% of hospitals below 1")
log("  NOTE: hospital-specific calibration estimates are reported descriptively.")
log("        No formal hierarchical calibration-heterogeneity test is reported:")
log("        the mixed-effects calibration model was removed as unreliable.")

# ===================================================================== 6B meta-analysis
log("\n" + "=" * 100)
log("SECTION 6B -- RANDOM-EFFECTS META-ANALYSIS OF PER-HOSPITAL AUROC")
log("=" * 100)


def hanley_se(auc, n1, n0):
    auc = min(max(auc, 1e-6), 1 - 1e-6)
    q1 = auc / (2 - auc)
    q2 = 2 * auc ** 2 / (1 + auc)
    se = np.sqrt((auc * (1 - auc) + (n1 - 1) * (q1 - auc ** 2) +
                  (n0 - 1) * (q2 - auc ** 2)) / (n1 * n0))
    return se / (auc * (1 - auc))       # logit scale


def dl_meta(yi, sei):
    yi, sei = np.asarray(yi, float), np.asarray(sei, float)
    wi = 1 / sei ** 2
    fe = float(np.sum(wi * yi) / np.sum(wi))
    Q = float(np.sum(wi * (yi - fe) ** 2))
    k = len(yi)
    dfree = k - 1
    C = float(np.sum(wi) - np.sum(wi ** 2) / np.sum(wi))
    tau2 = max(0.0, (Q - dfree) / C) if C > 0 else 0.0
    wr = 1 / (sei ** 2 + tau2)
    re = float(np.sum(wr * yi) / np.sum(wr))
    se_re = float(np.sqrt(1 / np.sum(wr)))
    I2 = max(0.0, (Q - dfree) / Q) * 100 if Q > 0 else 0.0
    pQ = float(1 - stats.chi2.cdf(Q, dfree)) if dfree > 0 else np.nan
    return dict(k=k, pooled_logit=re, se=se_re, tau2=float(tau2), tau=float(np.sqrt(tau2)),
                Q=Q, df=dfree, p_Q=pQ, I2=I2,
                pooled=float(expit(re)),
                ci_lo=float(expit(re - 1.96 * se_re)),
                ci_hi=float(expit(re + 1.96 * se_re)))


meta_rows = []
for tag, sub in [("primary N>=20", prim),
                 ("sensitivity N>=30", hl[(hl.n >= 30) & (hl.deaths >= MIN_D) & hl.auroc.notna()]),
                 ("all estimable", hl[hl.auroc.notna()])]:
    sei = np.array([hanley_se(a, int(d), int(n - d))
                    for a, n, d in zip(sub.auroc, sub.n, sub.deaths)])
    yi = np.log(np.clip(sub.auroc, 1e-6, 1 - 1e-6) /
                (1 - np.clip(sub.auroc, 1e-6, 1 - 1e-6)))
    m = dl_meta(yi, sei)
    m["analysis"] = tag
    meta_rows.append(m)
    log(f"\n  {tag}")
    log(f"    k={m['k']}  pooled AUROC = {m['pooled']:.4f} "
        f"({m['ci_lo']:.4f}, {m['ci_hi']:.4f})")
    log(f"    tau^2 = {m['tau2']:.5f}  tau = {m['tau']:.4f}")
    log(f"    Q = {m['Q']:.2f} (df {m['df']}, p = {m['p_Q']:.4g})   I^2 = {m['I2']:.1f}%")
meta = pd.DataFrame(meta_rows)[["analysis", "k", "pooled", "ci_lo", "ci_hi",
                                "tau2", "tau", "Q", "df", "p_Q", "I2"]]
meta.to_csv(os.path.join(DATA, "publock_hospital_meta.csv"), index=False,
            encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_hospital_meta.csv"), SCRIPT)

# ===================================================================== 7 recalibration
log("\n" + "=" * 100)
log("SECTION 7 -- RECALIBRATION VALIDATION (leave-one-hospital-out)")
log("=" * 100)
loho = {k: np.full(len(e), np.nan) for k in ["m0", "m1", "m2"]}
uniq_h = np.unique(hid)
for h in uniq_h:
    te = hid == h
    tr = ~te
    if te.sum() == 0 or tr.sum() == 0 or len(np.unique(y[tr])) < 2:
        continue
    ltr, lte = prov.logit(p[tr]), prov.logit(p[te])
    ytr = y[tr]
    # Model 1: intercept-only
    a = 0.0
    for _ in range(200):
        mu = expit(ltr + a)
        wsum = float(np.sum(mu * (1 - mu)))
        if wsum < 1e-12:
            break
        step = float(np.sum(ytr - mu)) / wsum
        a += np.clip(step, -1, 1)
        if abs(step) < 1e-12:
            break
    loho["m1"][te] = expit(lte + a)
    # Model 2: intercept + slope
    X = np.column_stack([np.ones(len(ltr)), ltr])
    b2, conv, _ = prov.fit_logistic(X, ytr)
    loho["m2"][te] = expit(b2[0] + b2[1] * lte)
    loho["m0"][te] = p[te]
ok = ~np.isnan(loho["m0"])
log(f"  held-out predictions available for {int(ok.sum()):,} of {len(e):,} patients "
    f"across {len(uniq_h)} hospitals")


def nll(yv, pv):
    pv = np.clip(pv, 1e-12, 1 - 1e-12)
    return float(-np.sum(yv * np.log(pv) + (1 - yv) * np.log(1 - pv)))


rows7 = []
for k, lbl in [("m0", "Model 0 original"), ("m1", "Model 1 intercept-only"),
               ("m2", "Model 2 intercept+slope")]:
    mm = prov.metrics(y[ok], loho[k][ok])
    mm["ici"] = ici(loho[k][ok], y[ok])
    mm["emax"] = emax(loho[k][ok], y[ok])
    mm["nll"] = nll(y[ok], loho[k][ok])
    rows7.append(dict(model=lbl, n=mm["n"], events=mm["events"],
                      auroc=round(mm["auroc"], 4), brier=round(mm["brier"], 4),
                      oe=round(mm["oe"], 4), calib_intercept=round(mm["calib_intercept"], 4),
                      calib_slope=round(mm["calib_slope"], 4),
                      ici=round(mm["ici"], 4), emax=round(mm["emax"], 4),
                      nll=round(mm["nll"], 2)))
rec = pd.DataFrame(rows7)
log("\n  POOLED HELD-OUT PERFORMANCE")
log(rec.to_string(index=False))
log("\n  changes vs Model 0:")
for i in (1, 2):
    log(f"    {rec.model[i]:<26} dBrier {rec.brier[i]-rec.brier[0]:+.5f}   "
        f"dO/E {rec.oe[i]-rec.oe[0]:+.4f}   dNLL {rec.nll[i]-rec.nll[0]:+.2f}")

# cluster bootstrap on the differences
NB7 = cfg.N_BOOTSTRAP_CLUSTER
rng3 = np.random.default_rng(cfg.RANDOM_SEED + 3)
ok_idx = np.where(ok)[0]
by_h3 = {h: ok_idx[hid[ok_idx] == h] for h in np.unique(hid[ok_idx])}
d_oe1, d_oe2, d_b1, d_b2, d_ll1, d_ll2 = [], [], [], [], [], []
for _ in range(NB7):
    sel = rng3.choice(list(by_h3), size=len(by_h3), replace=True)
    idx = np.concatenate([by_h3[h] for h in sel])
    yb = y[idx]
    if len(np.unique(yb)) < 2:
        continue
    o0 = yb.mean() / loho["m0"][idx].mean()
    o1 = yb.mean() / loho["m1"][idx].mean()
    o2 = yb.mean() / loho["m2"][idx].mean()
    d_oe1.append(o1 - o0); d_oe2.append(o2 - o0)
    b0 = prov.brier(yb, loho["m0"][idx])
    d_b1.append(prov.brier(yb, loho["m1"][idx]) - b0)
    d_b2.append(prov.brier(yb, loho["m2"][idx]) - b0)
    l0 = nll(yb, loho["m0"][idx])
    d_ll1.append(nll(yb, loho["m1"][idx]) - l0)
    d_ll2.append(nll(yb, loho["m2"][idx]) - l0)
cis = []
for nm, arr, obs in [("dO/E model1 vs model0", d_oe1, rec.oe[1] - rec.oe[0]),
                     ("dO/E model2 vs model0", d_oe2, rec.oe[2] - rec.oe[0]),
                     ("dBrier model1 vs model0", d_b1, rec.brier[1] - rec.brier[0]),
                     ("dBrier model2 vs model0", d_b2, rec.brier[2] - rec.brier[0]),
                     ("dNLL model1 vs model0", d_ll1, rec.nll[1] - rec.nll[0]),
                     ("dNLL model2 vs model0", d_ll2, rec.nll[2] - rec.nll[0])]:
    arr = np.array(arr, float)
    lo, hi = np.percentile(arr, [2.5, 97.5])
    exc = bool(lo > 0 or hi < 0)
    cis.append(dict(comparison=nm, observed=float(obs), ci_lo=float(lo), ci_hi=float(hi),
                    excludes_zero=exc, n_boot=len(arr)))
    log(f"    {nm:<26} {obs:+.5f}  95% CI ({lo:+.5f}, {hi:+.5f})  "
        f"{'EXCLUDES 0' if exc else 'includes 0'}")
ci7 = pd.DataFrame(cis)
ci7.to_csv(os.path.join(DATA, "publock_recalibration_ci.csv"), index=False,
           encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "publock_recalibration_ci.csv"), SCRIPT)

# export the held-out predictions so the figure script can plot the three curves
pd.DataFrame(dict(centre="eICU", stay_id=e.stay_id.values, hospitalid=hid,
                  outcome=y, p_m0=loho["m0"], p_m1=loho["m1"], p_m2=loho["m2"])
             ).to_csv(os.path.join(DATA, "recalibration_cv_predictions.csv"), index=False,
                      encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "recalibration_cv_predictions.csv"), SCRIPT)
log(f"\n  wrote held-out predictions for {int(ok.sum()):,} patients "
    f"(recalibration_cv_predictions.csv)")

claim_ok = bool((ci7.set_index("comparison").loc["dO/E model1 vs model0", "excludes_zero"])
                and rec.oe[1] > rec.oe[0])
log(f"\n  intercept-only update improves held-out O/E with a CI excluding 0: {claim_ok}")
log(f"  -> the manuscript MAY state that simple intercept updating corrected")
log(f"     calibration-in-the-large out of sample: {claim_ok}")
if not claim_ok:
    log("  -> the claim is NOT supported by this run and must be deleted.")

# ===================================================================== outputs
with pd.ExcelWriter(os.path.join(TABLES, "Table4_hospital_level.xlsx"),
                    engine="openpyxl") as xl:
    hl.to_excel(xl, sheet_name="all_hospitals", index=False)
    prim.to_excel(xl, sheet_name="primary_N20", index=False)
    hl[(hl.n >= 30) & (hl.deaths >= MIN_D)].to_excel(xl, sheet_name="sensitivity_N30",
                                                     index=False)
    meta.to_excel(xl, sheet_name="meta_analysis_AUROC", index=False)
    # No "hierarchical_calibration" and no "random_intercepts" sheet: the mixed-effects
    # calibration model was removed from the manuscript as unreliable. Its absence here
    # is deliberate and is asserted by src/reporting/final_release_check.py.
prov.stamp(os.path.join(TABLES, "Table4_hospital_level.xlsx"), SCRIPT)

with pd.ExcelWriter(os.path.join(TABLES, "Table5_recalibration.xlsx"),
                    engine="openpyxl") as xl:
    rec.to_excel(xl, sheet_name="held_out_performance", index=False)
    ci7.to_excel(xl, sheet_name="bootstrap_differences", index=False)
prov.stamp(os.path.join(TABLES, "Table5_recalibration.xlsx"), SCRIPT)

with io.open(os.path.join(LOGS, "PUBLOCK_06_07_hospital.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nSECTION 6A/6B/7 DONE")
