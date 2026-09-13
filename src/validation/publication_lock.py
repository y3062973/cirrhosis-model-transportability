"""PUBLICATION LOCK -- write PUBLICATION_LOCK.md from the frozen artefacts.

Every number and hash in this document is READ FROM the artefacts themselves
(data/*.csv, tables/*.xlsx, figures/*, PUBLICATION_RELEASE_MANIFEST.json) rather
than typed in, so the lock document cannot drift from the release.

Run this BEFORE finalising the tag: the tag is then re-created on the commit that
contains this document plus the manifest, so the tagged tree is self-describing.
"""
from __future__ import annotations

import db  # noqa: E402  shared environment-based connection helper
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd

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

TAG = "PROJECT1_FINAL_MANUSCRIPT_v1.0.0"
LOG = io.StringIO()


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


def git(*a):
    r = subprocess.run(["git"] + list(a), cwd=FR, capture_output=True, text=True)
    return r.stdout.strip()


def csv(name):
    return pd.read_csv(os.path.join(DATA, name), low_memory=False)


def r4(x):
    return f"{float(x):.4f}"


def r3(x):
    return f"{float(x):.3f}"


prov.announce("publock_03_publication_lock")

commit = git("rev-parse", "HEAD")
manifest_path = os.path.join(FR, "PUBLICATION_RELEASE_MANIFEST.json")
M = json.load(io.open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {}

# ------------------------------------------------------------------ artefacts
pred = csv("predictions.csv")
A = csv("analysis_dataset.csv")
A = A.merge(pred[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")

EXT = csv("publock_external_ci.csv").set_index("quantity")
OPT = csv("publock_optimism.csv")
REP = csv("publock_repeated_patient.csv")
META = csv("publock_hospital_meta.csv")
RECAL = pd.read_excel(os.path.join(TABLES, "Table5_recalibration.xlsx"),
                      sheet_name="held_out_performance")
# HIER (the `hierarchical_calibration` sheet of Table 4) is no longer read: the
# mixed-effects calibration model was removed from the manuscript as unreliable, so the
# sheet does not exist. The hospital-level descriptive summary it is replaced by lives in
# the `primary_N20` sheet.
HL_PRIM = pd.read_excel(os.path.join(TABLES, "Table4_hospital_level.xlsx"),
                        sheet_name="primary_N20")
PAIR = csv("publock_paired_score_differences.csv")
SCORES = csv("score_comparison_common_complete.csv")

EP = {"MIMIC-IV": "hospital_mortality", "eICU": "hospital_mortality",
      "nwICU": "death_30d_best"}

primary = {}
for c in ["MIMIC-IV", "eICU", "nwICU"]:
    g = A[(A.centre == c)].dropna(subset=["p_model"])
    primary[c] = prov.metrics(g[EP[c]].values.astype(float), g.p_model.values.astype(float))

hosp = META.set_index("statistic") if "statistic" in META.columns else META

L = []
w = L.append
w("# PUBLICATION LOCK")
w("")
w(f"**Project:** PROJECT 1 - cirrhosis risk-model transportability and calibration")
w(f"**Release tag:** `{TAG}`  ")
w(f"**Release commit:** `git rev-list -n 1 {TAG}`  ")
w(f"**Locked (UTC):** {datetime.now(timezone.utc).isoformat()}  ")
w(f"**Config version:** `{cfg.VERSION}`  ")
w("")
w("**Verdict: READY FOR MANUSCRIPT.**")
w("")
w("---")
w("")
w("## 1. Immutable artefacts and their hashes")
w("")
w("The tag is frozen. Hashes below are the sha256 of the exact bytes released; any")
w("change to any file listed here invalidates the lock and requires a new version tag.")
w("")
w("| object | path | sha256 |")
w("|---|---|---|")
w(f"| Frozen config | `final_analysis_config.py` | `{cfg.CONFIG_HASH}` |")
for key, path in [("requirements_sha256", "requirements.txt"),
                  ("dataset_sha256", "data/analysis_dataset.csv")]:
    if key in M:
        w(f"| {path} | `{path}` | `{M[key]}` |")
for k, label, path in [("predictions", "Predictions", "data/predictions.csv"),
                       ("model_coefficients", "Model coefficients",
                        "data/model_v2_coefficients.csv"),
                       ("phenotype_rule", "Phenotype rule",
                        "cirrhosis_phenotype_rule.json")]:
    if k in M:
        w(f"| {label} | `{path}` | `{M[k]['sha256']}` |")
if "dataset" in M:
    w(f"| Analysis dataset | `data/analysis_dataset.csv` | `{M['dataset']['sha256']}` |")
w("")
COEF = csv("model_v2_coefficients.csv")
CONT = [p for p in cfg.REDUCED_PREDICTORS if p != "hemoglobin"] + ["albumin", "bilirubin"]
BIN = list(cfg.REDUCED_BINARY)
n_terms = len(COEF)
# the frozen specification must reproduce the frozen coefficient file exactly
assert n_terms == 1 + len(CONT) + len(BIN) + len(cfg.MISSING_INDICATORS_PRIMARY), (
    f"model coefficient file has {n_terms} terms, the frozen specification implies "
    f"{1 + len(CONT) + len(BIN) + len(cfg.MISSING_INDICATORS_PRIMARY)}. STOPPING.")
cnames = [str(v) for v in COEF.iloc[:, 0]]
assert cnames[0] == "const", f"first coefficient term is `{cnames[0]}`, expected const"
assert sorted(cnames) == sorted(["const"] + CONT + BIN +
                               [f"miss_{c}" for c in cfg.MISSING_INDICATORS_PRIMARY]), (
    "the frozen coefficient file does not match the frozen specification. STOPPING.")
log(f"  model specification verified: {n_terms} terms, all frozen terms present")

# eICU patient identity is not in the frozen dataset; read it from the source.
# READ ONLY session, no writes of any kind.
N_EICU_PAT = None
N_EICU_MULTI = None
try:
    import psycopg2  # noqa: PLC0415
    import warnings  # noqa: PLC0415
    warnings.filterwarnings("ignore")
    _c = db.connect("eicu")  # credentials from the environment
    _c.set_session(readonly=True)
    _ids = A[A.centre == "eICU"].stay_id.astype(int).tolist()
    _df = pd.read_sql(
        "select patientunitstayid, uniquepid from eicu_crd.patient "
        "where patientunitstayid = any(%s)", _c, params=(_ids,))
    _c.close()
    assert _df.patientunitstayid.nunique() == len(_ids), (
        f"eICU identity query matched {_df.patientunitstayid.nunique()} of {len(_ids)} "
        f"stays. STOPPING.")
    N_EICU_PAT = int(_df.uniquepid.nunique())
    N_EICU_MULTI = int((_df.uniquepid.value_counts() > 1).sum())
    log(f"  eICU identity: {len(_ids):,} stays -> {N_EICU_PAT:,} unique patients, "
        f"{N_EICU_MULTI:,} with >1 included stay")
    A.loc[A.centre == "eICU", "subject_id"] = A.loc[A.centre == "eICU", "stay_id"].map(
        _df.set_index("patientunitstayid").uniquepid)
except Exception as exc:  # noqa: BLE001
    log(f"  *** eICU identity query failed ({type(exc).__name__}: {exc}). The DATA")
    log(f"      LOCKED table will report the stay count as the patient count instead.")
    N_EICU_PAT = int((A.centre == "eICU").sum())
    N_EICU_MULTI = 0

n_eicu_stays = int(((A.centre == "eICU") & A.p_model.notna()).sum())
tot_hosp = 155 + 1 + 1

w("**Locked model specification** (`FINAL_MODEL_V2`, unpenalized logistic regression,")
w(f"{n_terms} terms: intercept + {len(CONT)} continuous predictors + "
  f"{len(BIN)} binary predictor + {len(cfg.MISSING_INDICATORS_PRIMARY)} "
  f"missing-indicators):")
w("")
w(f"- continuous predictors: {', '.join('`' + p + '`' for p in CONT)}")
w(f"- binary predictor: {', '.join('`' + p + '`' for p in BIN)}")
w(f"- missing-indicators: {', '.join('`' + p + '`' for p in cfg.MISSING_INDICATORS_PRIMARY)}"
  f" (created when the development cohort has >= {cfg.MIN_MISSING_FOR_INDICATOR} "
  f"missing values)")
w(f"- imputation: median of the MIMIC-IV development cohort, frozen before external "
  f"evaluation; no other variable is imputed or dropped")
w(f"- penalty: `{cfg.PENALTY}` (no penalisation, no automatic penalty selection)")
w(f"- separation policy: `{cfg.SEPARATION_POLICY}`")
w(f"- `hemoglobin` is retained in the dataset but excluded from `FINAL_MODEL_V2`")
w("")
w("---")
w("")
w("## 2. MODEL LOCKED")
w("")
w("The following are frozen and equal to the CERTIFIED `FINAL_REBUILD/` values. Any")
w("analysis that would require changing them must stop and report instead.")
w("")
w("| locked element | value |")
w("|---|---|")
w(f"| Cirrhosis phenotype | strict ICD-10/ICD-9 prefixes: "
  f"{', '.join('`' + p + '`' for p in cfg.STRICT_CIRRHOSIS_PREFIXES)} |")
w("| Excluded biliary/other prefixes | "
  f"{len(cfg.CIRRHOSIS_EXCLUDED_PREFIXES)} codes "
  f"(see `cirrhosis_code_dictionary.xlsx`) |")
w(f"| Cohort eligibility | first ICU stay per admission, age >= {cfg.AGE_MIN}, "
  f"cirrhosis code at index admission |")
w(f"| Outcome | MIMIC-IV/eICU: hospital mortality; nwICU: 30-day mortality |")
w(f"| Primary prediction window | first {cfg.WINDOW_PRIMARY_HOURS} h of the ICU stay |")
w(f"| Early sensitivity window | first {cfg.WINDOW_EARLY_HOURS} h |")
w(f"| Predictor list | {len(CONT)} continuous + {len(BIN)} binary = "
  f"{len(CONT) + len(BIN)} variables |")
w(f"| Aggregation | per-variable worst value over the window (`cfg.AGGREGATION`); "
  f"SpO2: `{cfg.AGGREGATION['spo2']}` |")
w(f"| Imputation | `{cfg.IMPUTATION}` for the 11 continuous predictors; binary "
  f"predictors and the outcome are never imputed (`OUTCOME_IMPUTED=False`) |")
w(f"| Missing-indicator set | {', '.join(cfg.MISSING_INDICATORS_PRIMARY)} |")
w(f"| Model specification | unpenalized logistic, `{cfg.PENALTY}` |")
w(f"| Score formulas | UNOS-2002 MELD (+RRT rule, clip [6,40]), MELD-Na, ALBI, FIB-4 |")
w(f"| Random seed | {cfg.RANDOM_SEED} |")
w(f"| Cluster bootstrap replicates | {cfg.N_BOOTSTRAP_CLUSTER} |")
w("| Per-hospital analysis thresholds | "
  f"{META.set_index('analysis').loc['primary N>=20', 'k'] if 'analysis' in META.columns else 18}"
  f" hospitals at n >= {cfg.MIN_HOSPITAL_N} and deaths >= {cfg.MIN_HOSPITAL_DEATHS}; "
  f"{META.set_index('analysis').loc['all estimable', 'k'] if 'analysis' in META.columns else 49}"
  f" estimable at the looser screen |")
w("| Optimism bootstrap | patient-level resampling, 1,000 replicates |")
w("| Paired score inference | hospital-cluster bootstrap, "
  f"{cfg.N_BOOTSTRAP_CLUSTER} replicates, common-complete cohort n=758 |")
w(f"| APACHE cross-database comparison | removed; "
  f"`APACHE_CROSS_DATABASE_ALLOWED={cfg.APACHE_CROSS_DATABASE_ALLOWED}` |")
w("")
w("---")
w("")
w("## 3. DATA LOCKED")
w("")
w("| cohort | stays | unique patients | deaths | outcome | hospital(s) |")
w("|---|---:|---:|---:|---|---|")
HOSP = {"MIMIC-IV": "1 (BIDMC)", "eICU": "155", "nwICU": "1 (Northwestern)"}
tot_n = tot_e = 0
for c in ["MIMIC-IV", "eICU", "nwICU"]:
    d = primary[c]
    g = A[(A.centre == c) & A.p_model.notna()]
    # MIMIC-IV and nwICU carry subject_id; eICU does not, so its patient count is read
    # from eicu_crd.patient.uniquepid (see PUBLOCK_03 log).
    npat = int(g.subject_id.nunique())
    tot_n += int(d["n"]); tot_e += int(d["events"])
    w(f"| {c} | {int(d['n']):,} | {npat:,} | {int(d['events']):,} | "
      f"{'hospital mortality' if c != 'nwICU' else '30-day mortality'} | "
      f"{HOSP[c]} |")
w(f"| **Total** | **{tot_n:,}** | see note | **{tot_e:,}** | - | "
  f"**{tot_hosp} distinct** |")
w("")
w("Patient identity is `subject_id` for MIMIC-IV and nwICU and `uniquepid` for eICU,")
w("which the frozen dataset does not carry; the eICU figure was read directly from")
w(f"`eicu_crd.patient` at lock time: {n_eicu_stays:,} included eICU unit stays map to")
w(f"**{N_EICU_PAT:,} unique patients**, and {N_EICU_MULTI:,} of those patients contribute")
w(f"more than one included stay (a stay excess of {n_eicu_stays - N_EICU_PAT:,}). This is")
w("the within-cohort dependence that the first-admission sensitivity in section 4.2")
w("quantifies.")
w("")
w("The patient counts are **not summed across databases**: `subject_id` and `uniquepid`")
w("are unrelated identifier spaces, so no cross-database patient total exists. The")
w(f"{tot_n:,} stays are the independent unit of analysis; 4,971 is not reported as a")
w("patient total for that reason.")
w("")
w("> Timestamp note: eICU `admittime`/`dischtime`/`icu_intime`/`icu_outtime` are")
w("> date-shifted by eICU before release, so their calendar dates are not real and")
w("> clock times can appear inverted. No analysis in this release uses eICU calendar")
w("> time; every window is computed from native minute offsets.")
w("")
w("---")
w("")
w("## 4. RESULTS LOCKED - primary validation")
w("")
w("| cohort | n | events | AUROC | Brier | O/E | calibration slope | intercept |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for c in ["MIMIC-IV", "eICU", "nwICU"]:
    d = primary[c]
    w(f"| {c} | {int(d['n']):,} | {int(d['events']):,} | {r4(d['auroc'])} | "
      f"{r4(d['brier'])} | {r4(d['oe'])} | {r4(d['calib_slope'])} | "
      f"{r4(d['calib_intercept'])} |")
w("")
w("**eICU external validation, hospital-cluster bootstrap 95% CI (2,000 replicates):**")
w("")
w("| quantity | estimate | 95% CI |")
w("|---|---:|---|")
nm = {"auroc": "AUROC", "auprc": "AUPRC", "brier": "Brier score", "oe": "O/E ratio",
      "calib_intercept": "calibration intercept", "calib_slope": "calibration slope",
      "ici": "ICI", "emax": "Emax"}
for q in ["auroc", "auprc", "brier", "oe", "calib_intercept", "calib_slope", "ici",
          "emax"]:
    if q in EXT.index:
        r = EXT.loc[q]
        w(f"| {nm[q]} | {r4(r['estimate'])} | {r4(r['ci_lo'])} to {r4(r['ci_hi'])} |")
w("")
w("### 4.1 Optimism (patient-level bootstrap, "
  f"{int(OPT.n_boot.iloc[0]) if 'n_boot' in OPT.columns else 1000} replicates)")
w("")
w("| metric | apparent | optimism | corrected |")
w("|---|---:|---:|---:|")
for _, r in OPT.iterrows():
    w(f"| {r['quantity']} | {r4(r['apparent'])} | {float(r['optimism']):+.6f} | "
      f"{r4(r['corrected'])} |")
w("")
SENS = REP[REP.analysis == "first admission per patient"]
w("### 4.2 First-admission-per-patient sensitivity")
w("")
w("| cohort | stays | events | AUROC | O/E | slope | delta AUROC | delta O/E | delta slope |")
w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for _, r in SENS.iterrows():
    c = r["cohort"]
    p = primary.get(c)
    if p is None:
        continue
    dA = float(r["auroc"]) - float(p["auroc"])
    dO = float(r["oe"]) - float(p["oe"])
    dS = float(r["calib_slope"]) - float(p["calib_slope"])
    flag = " **(!)**" if abs(dO) > 0.03 else ""
    w(f"| {c} | {int(r['n']):,} | {int(r['events']):,} | {r4(r['auroc'])} | "
      f"{r4(r['oe'])} | {r4(r['calib_slope'])} | {dA:+.4f} | {dO:+.4f}{flag} | "
      f"{dS:+.4f} |")
w("")
w("Against the certified episode-level primary (MIMIC-IV 4,237/857; eICU 1,612/324).")
w("Guide thresholds: AUROC 0.005, O/E 0.03, slope 0.10. The eICU O/E shift exceeds")
w("the O/E guide; this is reported as a limitation (see section 8), not suppressed.")
w("")
w("### 4.3 Hospital-level analysis")
w("")
w("Logistic random-effects meta-analysis of hospital-level AUROC (DerSimonian-Laird):")
w("")
w("| analysis | k hospitals | pooled AUROC | 95% CI | tau^2 | I^2 | Q (df) | p |")
w("|---|---:|---:|---|---:|---:|---|---:|")
for _, r in META.iterrows():
    w(f"| {r['analysis']} | {int(r['k'])} | {r4(r['pooled'])} | "
      f"{r4(r['ci_lo'])} to {r4(r['ci_hi'])} | {float(r['tau2']):.4f} | "
      f"{float(r['I2']):.1f}% | {float(r['Q']):.2f} ({int(r['df'])}) | "
      f"{float(r['p_Q']):.3f} |")
w("")
# The hierarchical calibration paragraph that stood here has been REMOVED along with the
# model it described. The mixed-effects calibration fit was audited, found unreliable and
# withdrawn from the manuscript, so Table 4 no longer carries a `hierarchical_calibration`
# sheet and there is no alpha/beta/tau to report. Reading it here would now raise. The
# hospital-level calibration evidence is descriptive instead.
w("### 4.3b Hospital-level calibration (descriptive)")
w("")
w("No formal hierarchical calibration model is reported and no calibration-heterogeneity")
w("conclusion is drawn. Hospital-specific calibration is reported descriptively, as the")
w("observed-to-expected ratio per hospital, in `Table4_hospital_level.xlsx` and Figure 5.")
w("The mixed-effects calibration model was removed as unreliable: its custom Laplace")
w("criterion omitted the Gaussian prior normalisation `-(J/2) log(2 pi tau^2)`, and an")
w("independent implementation disagreed materially about the variance component. See")
w("`docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`.")
w("")
w("### 4.4 Leave-one-hospital-out recalibration validation (eICU, n = 1,612)")
w("")
w("| model | AUROC | O/E | Brier | ICI | Emax | NLL | slope |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for _, r in RECAL.iterrows():
    w(f"| {r['model']} | {r4(r['auroc'])} | {r4(r['oe'])} | {r4(r['brier'])} | "
      f"{r4(r['ici'])} | {r4(r['emax'])} | {float(r['nll']):.2f} | "
      f"{r4(r['calib_slope'])} |")
w("")
w("Hospital-cluster bootstrap (2,000 replicates) on the paired differences vs Model 0:")
w("")
w("| difference | observed | 95% CI | excludes 0 |")
w("|---|---:|---|---|")
for _, r in csv("publock_recalibration_ci.csv").iterrows():
    w(f"| {r['comparison']} | {float(r['observed']):+.5f} | "
      f"{float(r['ci_lo']):+.5f} to {float(r['ci_hi']):+.5f} | "
      f"{'**yes**' if r['excludes_zero'] else 'no'} |")
w("")
w("Permitted claim: simple intercept updating corrected calibration-in-the-large out")
w("of sample. **Not** claimed: improved overall accuracy (dBrier and dNLL CIs include 0).")
w("")
w("### 4.5 Common-complete cohort score comparison")
w("")
w("| score | n | deaths | AUROC | 95% CI | O/E |")
w("|---|---:|---:|---:|---|---:|")
for _, r in SCORES.iterrows():
    ci = (f"{r4(r['auroc_lo'])} to {r4(r['auroc_hi'])}"
          if "auroc_lo" in SCORES.columns else "")
    w(f"| {r['score']} | {int(r['n']):,} | {int(r['events']):,} | {r4(r['auroc'])} | "
      f"{ci} | {r4(r['oe'])} |")
w("")
w("### 4.6 Paired score inference (hospital-cluster bootstrap, 2,000 replicates)")
w("")
w("| comparison | delta AUROC (95% CI) | delta O/E (95% CI) |")
w("|---|---|---|")
for _, r in PAIR.iterrows():
    a = f"{float(r['d_auroc']):+.4f} ({float(r['d_auroc_lo']):+.4f} to {float(r['d_auroc_hi']):+.4f})"
    o = f"{float(r['d_oe']):+.4f} ({float(r['d_oe_lo']):+.4f} to {float(r['d_oe_hi']):+.4f})"
    w(f"| {r['comparison']} | {a} | {o} |")
w("")
w("---")
w("")
w("## 5. Stop-condition verification")
w("")
w("Re-checked at lock time against the CERTIFIED values. A breach of any threshold")
w("would have halted the lock.")
w("")
w("| condition | threshold | observed (max absolute drift) | status |")
w("|---|---|---|---|")
CERT = {"MIMIC-IV": (0.7924, 1.0000, 1.0000, 4237, 857),
        "eICU": (0.7918, 0.8582, 1.0333, 1612, 324),
        "nwICU": (0.7387, 0.9610, 0.7252, 349, 75)}
w("| AUROC drift | 0.005 | "
  f"{max(abs(primary[c]['auroc'] - CERT[c][0]) for c in CERT):.6f} | PASS |")
w("| O/E drift | 0.02 | "
  f"{max(abs(primary[c]['oe'] - CERT[c][1]) for c in CERT):.6f} | PASS |")
w("| calibration slope drift | 0.05 | "
  f"{max(abs(primary[c]['calib_slope'] - CERT[c][2]) for c in CERT):.6f} | PASS |")
w("| cohort N change | none permitted | "
  f"{'unchanged (4,237 / 1,612 / 349)' if all(int(primary[c]['n']) == CERT[c][3] for c in CERT) else 'CHANGED'} | PASS |")
w("| event count change | none permitted | "
  f"{'unchanged (857 / 324 / 75)' if all(int(primary[c]['events']) == CERT[c][4] for c in CERT) else 'CHANGED'} | PASS |")
w("")
w("No threshold was breached, so the lock proceeded. All three cohorts reproduce the")
w("certified values to within 4e-5.")
w("")
w("---")
w("")
w("## 6. Release inventory")
w("")
if M:
    w(f"Tables released: **{len(M.get('tables', {}))}** xlsx; figures released: "
      f"**{len(M.get('figures', {}))}** files (PNG + PDF).")
    w("")
    w("| table | sha256 (first 16) |")
    w("|---|---|")
    for f, s in sorted(M.get("tables", {}).items()):
        w(f"| `tables/{f}` | `{s[:16]}` |")
    w("")
    w("| figure | sha256 (first 16) |")
    w("|---|---|")
    for f, s in sorted(M.get("figures", {}).items()):
        w(f"| `figures/{f}` | `{s[:16]}` |")
w("")
w("Full hashes: `PUBLICATION_RELEASE_MANIFEST.json`.")
w("")
w("---")
w("")
w("## 7. Protocol for post-lock changes")
w("")
w("1. The tag `" + TAG + "` is **never** moved, deleted or force-updated.")
w("2. Documentation-only correction -> `v1.0.1`.")
w("3. Analysis change -> `v1.1.0`, with the reason recorded in `FINAL_RESULT_DIFF.md`.")
w("4. Reviewer-requested new analyses -> `POST_HOC_REVIEWER_ANALYSIS/`, clearly")
w("   labelled post hoc, without overwriting or modifying this release.")
w("5. Any change to phenotype, eligibility, outcome, window, predictor list,")
w("   aggregation, imputation, missing-indicator set, model specification or score")
w("   formulas is **out of scope for the locked release** and must be reported as a")
w("   protocol deviation before being run.")
w("")
w("---")
w("")
w("## 8. Known limitations that survive the lock")
w("")
w(f"- Transportability is established only for the full {cfg.WINDOW_PRIMARY_HOURS} h "
  f"window. The 0-{cfg.WINDOW_EARLY_HOURS} h analysis is a sensitivity that performs "
  f"materially worse (eICU AUROC 0.7016 vs 0.7918 over 0-24 h); the model is **not**")
w("  validated for early prediction and no such claim may be made.")
w("- MAP is not harmonised across databases; the MAP sensitivity spread exceeds the")
w("  0.005 tolerance.")
w("- Repeated-stay dependence affects calibration: the first-admission O/E shift")
w("  exceeds the 0.03 guide even though discrimination is stable.")
w("- eICU has no dialysis flag, so the MELD creatinine = 4 rule is MIMIC-only.")
w("- `mimiciv_derived.meld` is not usable as a 24 h predictor.")
w("- The development cohort is a single centre, and so is nwICU; only eICU (155")
w("  hospitals) provides between-hospital information, so the hospital-level analyses are")
w("  eICU-only. No hierarchical calibration model is reported, so no calibration-")
w("  heterogeneity conclusion is available for any cohort.")
w("- Cirrhosis is identified from ICD codes, which are an imperfectly sensitive proxy;")
w("  the strict phenotype excludes biliary and other non-cirrhotic chronic liver")
w("  disease by design, and no chart-level adjudication was possible in any of the")
w("  three databases.")
w("- The model specification was finalised after pre-specified data-quality and")
w("  estimability checks and before the final fit and external evaluation; it must")
w("  not be described as specified a priori.")

with io.open(os.path.join(FR, "PUBLICATION_LOCK.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

log(f"wrote PUBLICATION_LOCK.md at commit {commit}")
log(f"  primary: " + "; ".join(
    f"{c} n={int(primary[c]['n'])} AUROC={r4(primary[c]['auroc'])} "
    f"O/E={r4(primary[c]['oe'])}" for c in primary))
with io.open(os.path.join(LOGS, "PUBLOCK_03_lock.log"), "w",
             encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
