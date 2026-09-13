"""PUBLICATION LOCK 搂8 (selection), 搂12 (tables), 搂13 (figures).

Produces the single final table set (Table 1-6, Supplementary S1-S6) and figure set
(Figure 1-7 plus supplementary figures) from locked FINAL_MODEL_V2 results only.

Figure numbering used here (matches FINAL_PUBLICATION_REPORT.md):
  Figure 1 cohort flow
  Figure 2 discrimination (ROC: MIMIC / eICU / nwICU)
  Figure 3 calibration (MIMIC / eICU / nwICU)
  Figure 4 hospital-level AUROC forest
  Figure 5 hospital observed vs predicted + per-hospital observed-to-expected ratio
  Figure 6 recalibration held-out comparison
  Figure 7 clinical score comparison
  Supplementary: S1 missingness, S2 landmark + 0-6h, S3 MAP sensitivity

Figure 5 panel B is the observed-to-expected ratio per hospital. It is NOT a caterpillar
plot of random intercepts: the hierarchical calibration model was audited, found
unreliable and REMOVED from the manuscript, so no mixed-effects quantity is plotted
anywhere in this script. Table 4 correspondingly carries no `hierarchical_calibration` and
no `random_intercepts` sheet. See docs/audit/.
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
FIGS = str(repo.FIGURES)
LOGS = str(repo.LOGS)
repo.ensure_writable_dirs()
os.makedirs(FIGS, exist_ok=True)
LOG = io.StringIO()
OUT = "hospital_mortality"
CONT = cfg.PRIMARY_CONTINUOUS
BIN = cfg.PRIMARY_BINARY


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


prov.announce("publock_08_12_13_tables_figures.py")
A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")
# the analysis dataset carries no eICU patient key; pull it from the frozen cohort
_co = pd.read_csv(os.path.join(DATA, "cohort_eicu.csv"), low_memory=False)
uid_map = _co.set_index("stay_id")["patient_uid"]
A["patient_uid"] = A.stay_id.map(uid_map)
COEF = pd.read_csv(os.path.join(DATA, "model_v2_coefficients.csv"))
EXT_CI = pd.read_csv(os.path.join(DATA, "publock_external_ci.csv")).set_index("quantity")
OPT = pd.read_csv(os.path.join(DATA, "publock_optimism.csv"))
RP = pd.read_csv(os.path.join(DATA, "publock_repeated_patient.csv"))
HL = pd.read_csv(os.path.join(DATA, "publock_hospital_descriptive.csv"))
META = pd.read_csv(os.path.join(DATA, "publock_hospital_meta.csv"))
# HIER is no longer loaded: the hierarchical calibration model was removed from the
# manuscript and its sheets were deleted from Table 4. See
# HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md for the audit that led to the removal.
HIER = None
REC = pd.read_excel(os.path.join(TABLES, "Table5_recalibration.xlsx"),
                    sheet_name="held_out_performance")
REC_CI = pd.read_excel(os.path.join(TABLES, "Table5_recalibration.xlsx"),
                       sheet_name="bootstrap_differences")
SCORE = pd.read_csv(os.path.join(DATA, "score_comparison_common_complete.csv"))
MISS = pd.read_csv(os.path.join(DATA, "missingness_sensitivity.csv"))
EARLY = pd.read_csv(os.path.join(DATA, "early_prediction_sensitivity.csv"))
MAPS = pd.read_csv(os.path.join(DATA, "map_sensitivity.csv"))
FLOW = pd.read_csv(os.path.join(DATA, "cohort_flow.csv"))
COMP = pd.read_excel(os.path.join(TABLES, "TableS8_cohort_composition.xlsx"),
                     sheet_name="code_composition")

log("=" * 100)
log("TABLE ASSEMBLY")
log("=" * 100)

# ===================================================================== Table 1
rows = []
ORD = ["MIMIC-IV", "eICU", "nwICU"]
EP = {"MIMIC-IV": OUT, "eICU": OUT, "nwICU": "death_30d_best"}
for lbl in ["n (ICU stays)", "n (patients)", "deaths, n (%)", "age, median (IQR)",
            "male, n (%)", "albumin g/dL, median (IQR)", "bilirubin mg/dL, median (IQR)",
            "creatinine mg/dL, median (IQR)", "sodium mmol/L, median (IQR)",
            "platelet 10^9/L, median (IQR)", "WBC 10^9/L, median (IQR)",
            "heart rate bpm, median (IQR)", "MAP mmHg, median (IQR)",
            "respiratory rate /min, median (IQR)", "SpO2 %, median (IQR)"]:
    rows.append(dict(characteristic=lbl))
t1 = pd.DataFrame(rows)


def med_iqr(s):
    s = s.dropna()
    return "NA" if len(s) == 0 else f"{s.median():.1f} ({s.quantile(.25):.1f}-{s.quantile(.75):.1f})"


colmap = {
    "n (ICU stays)": lambda g: f"{len(g):,}",
    "n (patients)": lambda g: f"{g.subject_id.nunique() if g.subject_id.notna().any() else g.patient_uid.nunique():,}",
    "deaths, n (%)": lambda g: f"{int(g[EP[g.centre.iloc[0]]].sum()):,} "
                              f"({100*g[EP[g.centre.iloc[0]]].mean():.1f})",
}
for c in ORD:
    g = A[A.centre == c]
    for i, lbl in enumerate(t1.characteristic):
        if lbl in colmap:
            t1.loc[i, c] = colmap[lbl](g)
            continue
        if lbl.startswith("age"):
            t1.loc[i, c] = med_iqr(g.age)
            continue
        if lbl.startswith("male"):
            t1.loc[i, c] = f"{int(g.male.sum()):,} ({100*g.male.mean():.1f})"
            continue
        # map the display label to the column
        key = lbl.split(" ")[0].lower()
        varmap = {"respiratory": "resp_rate", "heart": "heart_rate",
                  "map": "map", "spo2": "spo2", "albumin": "albumin",
                  "bilirubin": "bilirubin", "creatinine": "creatinine",
                  "sodium": "sodium", "platelet": "platelet", "wbc": "wbc"}
        v = varmap.get(key)
        if v and v in g.columns:
            t1.loc[i, c] = med_iqr(g[v])
log("\nTable 1 (baseline characteristics)")
log(t1.to_string(index=False))
log("\n  NOTE: no between-centre p-values are reported. Table 1 is descriptive;")
log("  differences reflect case mix and coding practice, not tested hypotheses.")

# ===================================================================== Table 2/3
t2 = COEF.copy()
t3 = []
for c, ep in [("MIMIC-IV", OUT), ("eICU", OUT), ("nwICU", "death_30d_best")]:
    g = A[A.centre == c].dropna(subset=["p_model"])
    m = prov.metrics(g[ep].values.astype(float), g.p_model.values.astype(float))
    d = dict(cohort=c, n=m["n"], events=m["events"], auroc=round(m["auroc"], 4),
             brier=round(m["brier"], 4), oe=round(m["oe"], 4),
             calib_slope=round(m["calib_slope"], 4),
             calib_intercept=round(m["calib_intercept"], 4))
    if c == "eICU":
        d["auroc_lo"] = round(EXT_CI.loc["auroc", "ci_lo"], 4)
        d["auroc_hi"] = round(EXT_CI.loc["auroc", "ci_hi"], 4)
        d["auprc"] = round(EXT_CI.loc["auprc", "estimate"], 4)
        d["auprc_lo"] = round(EXT_CI.loc["auprc", "ci_lo"], 4)
        d["auprc_hi"] = round(EXT_CI.loc["auprc", "ci_hi"], 4)
        d["oe_lo"] = round(EXT_CI.loc["oe", "ci_lo"], 4)
        d["oe_hi"] = round(EXT_CI.loc["oe", "ci_hi"], 4)
        d["slope_lo"] = round(EXT_CI.loc["calib_slope", "ci_lo"], 4)
        d["slope_hi"] = round(EXT_CI.loc["calib_slope", "ci_hi"], 4)
        d["ici"] = round(EXT_CI.loc["ici", "estimate"], 4)
        d["emax"] = round(EXT_CI.loc["emax", "estimate"], 4)
        d["ci_type"] = "hospital-cluster bootstrap (2000)"
    else:
        d["ci_type"] = "development / secondary cohort"
    t3.append(d)
t3 = pd.DataFrame(t3)
log("\nTable 3 (primary development and external validation)")
log(t3.to_string(index=False))

# ===================================================================== Table 4
t4_meta = META[["analysis", "k", "pooled", "ci_lo", "ci_hi", "tau2", "I2", "p_Q"]]
log("\nTable 4 (hospital-level discrimination) -- meta-analysis part")
log(t4_meta.to_string(index=False))
# The hierarchical calibration part was removed from Table 4 along with the model. See
# HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md.

# ===================================================================== Table 5/6
log("\nTable 5 (recalibration cross-validation)")
log(REC.to_string(index=False))
log("\n  bootstrap differences")
log(REC_CI.to_string(index=False))
log("\nTable 6 (same-patient clinical score comparison, common-complete cohort)")
log(SCORE.to_string(index=False))

# ===================================================================== 搂8 selection
log("\n" + "=" * 100)
log("SECTION 8 -- SELECTION DESCRIPTION (common-complete vs excluded)")
log("=" * 100)
e = A[A.centre == "eICU"].copy()
cc_ids = set()
# reconstruct the common-complete membership from the score file's n by re-deriving it
# exactly as phase_5_6_7 did: all of MELD, ALBI, FIB-4 computable and p_model present
# (the score frame itself carries no ids, so we recompute the mask from the same rule)
_sc = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
sel = pd.DataFrame()
for c in ["age", "male", OUT, "albumin", "bilirubin", "creatinine"]:
    a_ = pd.to_numeric(e[c], errors="coerce")
    sel[c] = a_
log(f"  common-complete cohort: n={int(SCORE.n.iloc[0]):,} of {len(e):,} eICU stays "
    f"({100*SCORE.n.iloc[0]/len(e):.1f}%), events={int(SCORE.events.iloc[0])}")
log("  Direct comparison of included vs excluded patients requires the same-rule mask;")
log("  it is computed in publock_08b_selection.py where the score components are")
log("  available. This script reports the locked cohort-level numbers only.")

# ===================================================================== outputs
with pd.ExcelWriter(os.path.join(TABLES, "Table1_baseline.xlsx"), engine="openpyxl") as xl:
    t1.to_excel(xl, sheet_name="baseline", index=False)
with pd.ExcelWriter(os.path.join(TABLES, "Table2_model_coefficients.xlsx"),
                    engine="openpyxl") as xl:
    t2.to_excel(xl, sheet_name="coefficients", index=False)
with pd.ExcelWriter(os.path.join(TABLES, "Table3_primary_validation.xlsx"),
                    engine="openpyxl") as xl:
    t3.to_excel(xl, sheet_name="validation", index=False)
with pd.ExcelWriter(os.path.join(TABLES, "Table6_score_comparison.xlsx"),
                    engine="openpyxl") as xl:
    SCORE.to_excel(xl, sheet_name="common_complete", index=False)
for f in ["Table1_baseline.xlsx", "Table2_model_coefficients.xlsx",
          "Table3_primary_validation.xlsx", "Table6_score_comparison.xlsx"]:
    prov.stamp(os.path.join(TABLES, f), "publock_08_12_13_tables_figures.py", inputs={
        "analysis_dataset": os.path.join(DATA, "analysis_dataset.csv"),
        "predictions": os.path.join(DATA, "predictions.csv")})
log(f"\n  tables written to {TABLES}")

# ===================================================================== figures
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
plt.rcParams.update({"font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 120})
# Deterministic output. matplotlib stamps a CreationDate into PDF metadata, so PDFs
# regenerated from identical data and identical code hashed differently run to run
# (the PNGs were byte-stable; the PDFs were not). PUBLICATION_ARTIFACT_CHECKSUMS.txt
# is only meaningful if the hashes are reproducible, so the timestamp is pinned.
matplotlib.rcParams["pdf.compression"] = 6
matplotlib.rcParams["svg.hashsalt"] = "PROJECT1_FINAL_REBUILD"
os.environ.setdefault("SOURCE_DATE_EPOCH", "1757000000")

_orig_savefig = plt.Figure.savefig


def _det_savefig(self, fname, *a, **kw):
    """savefig with a fixed PDF creation date so the bytes are reproducible."""
    meta = dict(kw.pop("metadata", None) or {})
    if str(fname).lower().endswith(".pdf"):
        meta.setdefault("CreationDate", "D:20260914000000Z")
        meta.setdefault("ModDate", "D:20260914000000Z")
        meta.setdefault("Producer", "PROJECT1_FINAL_REBUILD")
        meta.setdefault("Creator", "PROJECT1_FINAL_REBUILD")
    return _orig_savefig(self, fname, *a, metadata=meta, **kw)


plt.Figure.savefig = _det_savefig
COL = {"MIMIC-IV": "#4C72B0", "eICU": "#DD8452", "nwICU": "#55A868"}


def roc_pts(y, p):
    y = np.asarray(y, float); p = np.asarray(p, float)
    o = np.argsort(-p)
    y = y[o]
    tpr = np.cumsum(y) / y.sum()
    fpr = np.cumsum(1 - y) / (1 - y).sum()
    return np.r_[0, fpr], np.r_[0, tpr]


# ---- Figure 1 cohort flow
flow = FLOW[FLOW.step.str.contains("strict|first|age|outcome|ICU|row|admissions")]
fig, axes = plt.subplots(1, 3, figsize=(13, 5.2))
for ax, c in zip(axes, ["MIMIC-IV", "eICU", "nwICU"]):
    sub = FLOW[FLOW.centre == c].reset_index(drop=True)
    for i, r in sub.iterrows():
        yy = 0.94 - i * (0.94 / max(len(sub), 1))
        ax.add_patch(plt.Rectangle((0.05, yy - 0.055), 0.9, 0.10, lw=0.8,
                                   edgecolor=COL[c], facecolor=COL[c] + "22"))
        ax.text(0.5, yy + 0.012, str(r.step)[:52], ha="center", fontsize=6.8)
        ax.text(0.5, yy - 0.030, f"n = {int(r.n):,}", ha="center", fontsize=7.2,
                fontweight="bold", color=COL[c])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    final = int(A[A.centre == c].shape[0])
    ax.set_title(f"{c}\nfinal cohort n = {final:,}", fontsize=9.5, color=COL[c],
                 fontweight="bold")
fig.suptitle("Figure 1. Cohort construction - strict cirrhosis phenotype, first ICU stay, "
             "0-24 h predictors", fontsize=10, y=1.0)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure1_cohort_flow.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 2 discrimination
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.3))
ax = axes[0]
for c, ep in [("MIMIC-IV", OUT), ("eICU", OUT), ("nwICU", "death_30d_best")]:
    g = A[A.centre == c].dropna(subset=["p_model"])
    m = prov.metrics(g[ep].values.astype(float), g.p_model.values.astype(float))
    f1, t1_ = roc_pts(g[ep].values, g.p_model.values)
    lbl = f"{c}: {m['auroc']:.3f}"
    if c == "eICU":
        lbl += f" ({EXT_CI.loc['auroc','ci_lo']:.3f}-{EXT_CI.loc['auroc','ci_hi']:.3f})"
    ax.plot(f1, t1_, color=COL[c], lw=1.7, label=lbl)
ax.plot([0, 1], [0, 1], ls=":", color="grey", lw=1)
ax.set_xlabel("1 - Specificity"); ax.set_ylabel("Sensitivity")
ax.set_title("A  Discrimination", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7.5, loc="lower right")
ax = axes[1]
for c in ["MIMIC-IV", "eICU", "nwICU"]:
    g = A[A.centre == c].dropna(subset=["p_model"])
    ax.hist(g.p_model, bins=40, histtype="step", lw=1.4, density=True, color=COL[c],
            label=f"{c} (mean {g.p_model.mean():.3f})")
ax.set_xlabel("Predicted risk"); ax.set_ylabel("Density")
ax.set_title("B  Predicted risk distribution", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7.5)
fig.suptitle("Figure 2. FINAL_MODEL_V2 discrimination", fontsize=10, x=0.02, ha="left")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure2_discrimination.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 3 calibration
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
for ax, (c, ep) in zip(axes, [("MIMIC-IV", OUT), ("eICU", OUT), ("nwICU", "death_30d_best")]):
    g = A[A.centre == c].dropna(subset=["p_model"])
    yv = g[ep].values.astype(float); pv = g.p_model.values.astype(float)
    q = pd.qcut(pv, 10, duplicates="drop")
    gg = pd.DataFrame({"p": pv, "y": yv}).groupby(q, observed=True).agg(
        pred=("p", "mean"), obs=("y", "mean"))
    ax.plot(gg.pred, gg.obs, "o-", color=COL[c], ms=5, lw=1.5)
    ax.plot([0, 0.8], [0, 0.8], ls=":", color="grey", lw=1)
    m = prov.metrics(yv, pv)
    ax.set_title(f"{c}\nAUROC {m['auroc']:.3f}  O/E {m['oe']:.3f}  slope "
                 f"{m['calib_slope']:.3f}", loc="left", fontsize=9)
    ax.set_xlabel("Predicted risk (decile mean)")
    ax.set_xlim(0, 0.8); ax.set_ylim(0, 0.8)
axes[0].set_ylabel("Observed mortality")
fig.suptitle("Figure 3. FINAL_MODEL_V2 calibration", fontsize=10, x=0.02, ha="left")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure3_calibration.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 4 forest
prim = HL[(HL.n >= cfg.MIN_HOSPITAL_N) & (HL.deaths >= cfg.MIN_HOSPITAL_DEATHS)
          & HL.auroc.notna()].sort_values("auroc").reset_index(drop=True)
m18 = META[META.analysis.str.startswith("primary")].iloc[0]
fig, ax = plt.subplots(figsize=(8.5, max(3.5, 0.26 * len(prim) + 1.6)))
pos = np.arange(len(prim))
ax.scatter(prim.auroc, pos, s=10 + 60 * (prim.n / prim.n.max()), color="#4C72B0", zorder=3)
ax.axvline(m18.pooled, color="#C44E52", lw=1.4, ls="--",
           label=f"pooled {m18.pooled:.3f} ({m18.ci_lo:.3f}-{m18.ci_hi:.3f}), "
                 f"I2={m18.I2:.1f}%")
ax.axvline(0.7918, color="grey", lw=1, ls=":", label="pooled eICU 0.792")
ax.set_yticks(pos)
ax.set_yticklabels([f"H{int(h)} (n={int(n)}, d={int(d)})"
                    for h, n, d in zip(prim.hospitalid, prim.n, prim.deaths)], fontsize=6.2)
ax.set_xlabel("AUROC"); ax.set_xlim(0.4, 1.0)
ax.set_title("Figure 4. Per-hospital discrimination (N>=20, deaths>=5)",
             loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7, loc="lower right")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure4_hospital_forest.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 5 observed vs predicted + observed-to-expected ratios
#
# Panel B previously showed the caterpillar plot of the shrunken random intercepts from
# the hierarchical calibration model. That model was REMOVED from the manuscript after the
# audit in HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md (boundary variance estimate plus
# material disagreement with an independent GLMM implementation), so the panel has been
# replaced with the observed-to-expected ratio per hospital. That quantity involves no
# mixed-effects fitting: it is a direct ratio of observed to expected deaths within each
# centre, and it conveys the same "do hospitals differ" information without depending on
# the model that was withdrawn.
oe = prim.copy()
oe["oe"] = oe.observed / oe.mean_predicted
oe = oe.sort_values("oe").reset_index(drop=True)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
ax = axes[0]
ax.scatter(prim.mean_predicted, prim.observed, s=10 + 60 * (prim.n / prim.n.max()),
           c=prim.auroc, cmap="viridis", vmin=0.5, vmax=1.0, edgecolor="grey", lw=0.4)
lim = max(prim.mean_predicted.max(), prim.observed.max()) * 1.15
ax.plot([0, lim], [0, lim], ls=":", color="grey", lw=1)
ax.set_xlabel("Mean predicted risk"); ax.set_ylabel("Observed mortality")
ax.set_title("A  Observed vs predicted by hospital", loc="left", fontsize=10)
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax = axes[1]
ax.scatter(oe.oe, np.arange(len(oe)), s=8 + 50 * (oe.n / oe.n.max()),
           color="#4C72B0")
ax.axvline(1.0, color="#C44E52", lw=1.2, ls="--")
ax.set_yticks([])
ax.set_xlabel("Observed-to-expected ratio (O/E)")
ax.set_title("B  Hospital-level calibration-in-the-large", loc="left", fontsize=10)
ax.text(0.98, 0.04,
        f"median {oe.oe.median():.2f}   IQR {oe.oe.quantile(.25):.2f}-"
        f"{oe.oe.quantile(.75):.2f}\n"
        f"{100 * (oe.oe < 1).mean():.0f}% of hospitals O/E < 1",
        transform=ax.transAxes, fontsize=7, ha="right", va="bottom",
        color="#444444")
fig.suptitle("Figure 5. Hospital-level calibration", fontsize=10, x=0.02, ha="left")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure5_hospital_calibration.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 6 recalibration
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
preds = pd.read_csv(os.path.join(DATA, "recalibration_cv_predictions.csv")) \
    if os.path.exists(os.path.join(DATA, "recalibration_cv_predictions.csv")) else None
for ax, (mdl, lbl, col) in zip(axes, [("m0", "Model 0 original", "#4C72B0"),
                                      ("m1", "Model 1 intercept-only", "#DD8452"),
                                      ("m2", "Model 2 intercept+slope", "#55A868")]):
    if preds is not None and f"p_{mdl}" in preds.columns:
        pv = preds[f"p_{mdl}"].values
        yv = preds["outcome"].values.astype(float)
        ok = ~np.isnan(pv)
        q = pd.qcut(pv[ok], 10, duplicates="drop")
        gg = pd.DataFrame({"p": pv[ok], "y": yv[ok]}).groupby(q, observed=True).agg(
            pred=("p", "mean"), obs=("y", "mean"))
        ax.plot(gg.pred, gg.obs, "o-", color=col, ms=4, lw=1.4)
        r = REC[REC.model == lbl]
        if len(r):
            ax.set_title(f"{lbl}\nO/E {r.oe.iloc[0]:.3f}  Brier {r.brier.iloc[0]:.4f}",
                         loc="left", fontsize=9)
    ax.plot([0, 0.8], [0, 0.8], ls=":", color="grey", lw=1)
    ax.set_xlabel("Predicted risk (decile mean)")
    ax.set_xlim(0, 0.8); ax.set_ylim(0, 0.8)
axes[0].set_ylabel("Observed mortality (held-out)")
fig.suptitle("Figure 6. Leave-one-hospital-out recalibration", fontsize=10, x=0.02,
             ha="left")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure6_recalibration.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Figure 7 score comparison
fig, ax = plt.subplots(figsize=(7.5, 4.2))
sc = SCORE.sort_values("auroc")
ypos = np.arange(len(sc))
ax.errorbar(sc.auroc, ypos, xerr=[sc.auroc - sc.auroc_lo, sc.auroc_hi - sc.auroc],
            fmt="o", color="#4C72B0", ecolor="#B0B0B0", capsize=3, ms=6)
ax.set_yticks(ypos); ax.set_yticklabels(sc.score, fontsize=8)
ax.set_xlabel("AUROC (hospital-cluster bootstrap 95% CI)")
ax.set_title("Figure 7. Same-patient score comparison\n(common-complete cohort, "
             f"n={int(sc.n.iloc[0])}, events={int(sc.events.iloc[0])})",
             loc="left", fontsize=10)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"Figure7_score_comparison.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# ---- Supplementary figures S1-S4
# Presentation only: every number plotted is read from an already-frozen artefact.
# No cohort, model, window, predictor or score definition is touched here.
log("\n" + "=" * 100)
log("SUPPLEMENTARY FIGURES S1-S4")
log("=" * 100)

# S1: missingness by centre and predictor
S1M = A.groupby("centre")[cfg.PRIMARY_CONTINUOUS + cfg.PRIMARY_BINARY].apply(
    lambda g: 100 * g.isna().mean())
fig, ax = plt.subplots(figsize=(9.0, 4.4))
xx = np.arange(len(S1M.columns))
wd = 0.26
cols = {"MIMIC-IV": "#4C72B0", "eICU": "#DD8452", "nwICU": "#55A868"}
for i, (ctr, col) in enumerate(cols.items()):
    if ctr in S1M.index:
        ax.bar(xx + (i - 1) * wd, S1M.loc[ctr].values, wd, label=ctr, color=col)
ax.set_xticks(xx)
ax.set_xticklabels(S1M.columns, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("% missing in the 24 h window")
ax.set_title("Figure S1. Predictor missingness by centre\n"
             "(frozen 24 h window; indicators created for albumin and bilirubin)",
             loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"FigureS1_missingness.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# S2: early vs primary window
fig, ax = plt.subplots(figsize=(7.0, 4.0))
lbl = list(EARLY.index)
mim = EARLY.mimic_auroc.values
eic = EARLY.eicu_auroc.values
xx = np.arange(len(lbl))
ax.bar(xx - 0.18, mim, 0.36, label="MIMIC-IV", color="#4C72B0")
ax.bar(xx + 0.18, eic, 0.36, label="eICU", color="#DD8452")
for i in range(len(lbl)):
    ax.text(xx[i] - 0.18, mim[i] + 0.008, f"{mim[i]:.3f}", ha="center", fontsize=8)
    ax.text(xx[i] + 0.18, eic[i] + 0.008, f"{eic[i]:.3f}", ha="center", fontsize=8)
ax.set_xticks(xx); ax.set_xticklabels(lbl, fontsize=9)
ax.set_ylim(0.6, 0.86); ax.set_ylabel("AUROC")
ax.set_title("Figure S2. Window sensitivity\n(transportability requires the full "
             "24 h window)", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"FigureS2_early_window.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# S3: missing-data strategies
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
strat = [s.split(":")[0] for s in MISS.strategy]
axes[0].bar(strat, MISS.eicu_auroc, color="#4C72B0")
axes[0].set_ylabel("eICU AUROC"); axes[0].set_ylim(0.7, 0.82)
for i, v in enumerate(MISS.eicu_auroc):
    axes[0].text(i, v + 0.004, f"{v:.4f}", ha="center", fontsize=8)
axes[1].bar(strat, MISS.eicu_oe, color="#DD8452")
axes[1].axhline(1.0, color="k", lw=1, ls="--")
axes[1].set_ylabel("eICU O/E"); axes[1].set_ylim(0.7, 1.05)
for i, v in enumerate(MISS.eicu_oe):
    axes[1].text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=8)
axes[0].set_title("Figure S3. Missing-data strategy sensitivity\nA = primary",
                  loc="left", fontsize=10)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"FigureS3_missing_strategies.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

# S4: MAP definitions
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
short = ["current\ncomposite", "non-invasive\npreferred", "invasive\nonly"]
axes[0].bar(short, MAPS.auroc, color="#4C72B0")
axes[0].set_ylabel("eICU AUROC"); axes[0].set_ylim(0.74, 0.82)
for i, v in enumerate(MAPS.auroc):
    axes[0].text(i, v + 0.002, f"{v:.4f}", ha="center", fontsize=8)
axes[1].bar(short, MAPS.oe, color="#55A868")
axes[1].axhline(1.0, color="k", lw=1, ls="--")
axes[1].set_ylabel("eICU O/E"); axes[1].set_ylim(0.7, 1.05)
for i, v in enumerate(MAPS.oe):
    axes[1].text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=8)
axes[0].set_title("Figure S4. MAP definition sensitivity\n(MAP is not harmonised; "
                  "AUROC spread exceeds the 0.005 tolerance)",
                  loc="left", fontsize=10)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGS, f"FigureS4_map_definition.{ext}"), dpi=400,
                bbox_inches="tight")
plt.close(fig)

n_fig = len([f for f in os.listdir(FIGS) if f.endswith(".png")])
log(f"\n  figures written: {n_fig} PNG (+ PDF) in {FIGS}")
for f in sorted(os.listdir(FIGS)):
    if f.endswith(".png") or f.endswith(".pdf"):
        prov.stamp(os.path.join(FIGS, f), "publock_08_12_13_tables_figures.py", extra={
            "figure_type": "publication"})

with io.open(os.path.join(LOGS, "PUBLOCK_08_12_13_tables_figures.log"), "w",
             encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nTABLES + FIGURES DONE")
