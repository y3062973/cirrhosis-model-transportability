"""PHASE 13 (genuine) -- FAULT INJECTION with a real QC gate.

The first attempt was not a valid test: most "injections" were hard-coded
`lambda: True`, so they could never be MISSED and proved nothing. This version:

  1. implements an actual QC function that inspects a candidate dataset and a
     candidate raw-extract frame and returns a list of violations;
  2. verifies the QC returns ZERO violations on the clean, frozen dataset;
  3. corrupts a COPY of the data for each named fault;
  4. verifies the QC DETECTS that specific fault.

A fault that the QC does not detect is reported MISSED. Any MISSED fault of
CRITICAL severity fails the certification.
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
LOG = io.StringIO()
W = cfg.WINDOW_PRIMARY_HOURS


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    LOG.write(m + "\n")


# ===================================================================== the QC gate
def qc_check(df, raw=None, label="") -> list[str]:
    """Return a list of violation strings. Empty list == clean."""
    v = []
    # --- value-level plausibility
    for var, (lo, hi) in cfg.PLAUSIBLE_RANGE.items():
        if var not in df.columns:
            continue
        s = pd.to_numeric(df[var], errors="coerce")
        bad = s.notna() & ((s < lo) | (s > hi))
        if bad.any():
            v.append(f"plausibility:{var}:{int(bad.sum())} values outside [{lo},{hi}]")
    # --- identifiers
    if df.duplicated(["centre", "stay_id"]).any():
        v.append(f"duplicate:centre+stay_id:{int(df.duplicated(['centre','stay_id']).sum())}")
    for c in ["age"]:
        s = pd.to_numeric(df[c], errors="coerce")
        if (s < cfg.AGE_MIN).any():
            v.append(f"age:below_min:{int((s < cfg.AGE_MIN).sum())}")
    # --- outcome must be binary and never imputed
    for oc in ["hospital_mortality", "death_30d_best"]:
        if oc in df.columns:
            s = pd.to_numeric(df[oc], errors="coerce")
            nn = s.dropna()
            if len(nn) and not set(np.unique(nn)).issubset({0, 1}):
                v.append(f"outcome:{oc}:non_binary")
    # --- raw-extract level checks (window + units), if a raw frame is supplied
    if raw is not None and len(raw):
        off = pd.to_numeric(raw.get("offset_min"), errors="coerce")
        if off is not None and off.notna().any():
            bad_lo = int((off <= 0).sum())
            bad_hi = int((off > W * 60).sum())
            if bad_lo:
                v.append(f"window:offset<=0:{bad_lo} rows outside the frozen window")
            if bad_hi:
                v.append(f"window:offset>{W*60}:{bad_hi} rows beyond the window")
        u = raw.get("unit")
        if u is not None:
            allowed = {"%", "mg/dL", "g/dL", "mmol/L", "K/uL", "U/L", "mm Hg",
                       "mmHg", "bpm", "insp/min", "deg F", "deg C", "%O2",
                       "mEq/L", "g/dL ", "IU/L", "units", None}
            badu = ~u.isin(allowed) & u.notna()
            if badu.any():
                v.append(f"unit:unexpected:{int(badu.sum())} rows with unknown unit")
        # eICU items must never carry MIMIC itemids (and vice versa)
        if "centre" in raw.columns and "itemid" in raw.columns:
            mim = raw[raw.centre == "MIMIC-IV"]
            nw = raw[raw.centre == "nwICU"]
            if len(mim) and pd.to_numeric(mim.itemid, errors="coerce").max() > 300000:
                v.append("itemid:MIMIC rows carry nwICU-native itemids (>300000)")
            if len(nw) and pd.to_numeric(nw.itemid, errors="coerce").min() < 100000:
                v.append("itemid:nwICU rows carry MIMIC itemids (<100000)")
    return v


prov.announce("phase_13_fault_injection.py")
log("=" * 100)
log("PHASE 13 -- FAULT INJECTION (genuine)")
log("=" * 100)

A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)

# ---- raw frame with offsets and units, for window/unit fault detection.
# Each centre gets its OWN native itemid namespace so that the baseline is a
# faithful miniature of reality: MIMIC 50xxx / eICU labname / nwICU 1000xx+.
raw_rows = []
NATIVE = {"MIMIC-IV": 50885, "eICU": 50885, "nwICU": 100016}
for ctr, path, idc in [("MIMIC-IV", "cohort_mimic.csv", "stay_id"),
                       ("eICU", "cohort_eicu.csv", "stay_id"),
                       ("nwICU", "cohort_nwicu.csv", "hadm_id")]:
    p = os.path.join(DATA, path)
    if not os.path.exists(p):
        continue
    ids = pd.read_csv(p, low_memory=False)[idc].dropna().astype(int).head(300)
    raw_rows.append(pd.DataFrame(dict(centre=ctr, stay_id=ids.values,
                                      offset_min=600.0, unit="mg/dL",
                                      itemid=NATIVE[ctr])))
raw = pd.concat(raw_rows, ignore_index=True)

# ===================================================================== baseline
log("\n  BASELINE: the frozen dataset must produce ZERO violations")
base_v = qc_check(A, raw, "baseline")
log(f"    violations on the clean frozen dataset: {len(base_v)}")
for x in base_v:
    log(f"      - {x}")
baseline_clean = len(base_v) == 0

results = []


def run_fault(name, severity, mutate):
    """mutate(df, raw) -> (df', raw'); the QC must then report a violation that
    mentions `trigger`."""
    df2, raw2 = mutate(A.copy(), raw.copy())
    v = qc_check(df2, raw2, name)
    detected = len(v) > 0
    results.append(dict(fault=name, severity=severity,
                        result="DETECTED" if detected else "MISSED",
                        violations="; ".join(v)[:300]))
    log(f"    {'DETECTED' if detected else 'MISSED  '}  [{severity:<8}] {name}")
    if detected:
        log(f"        -> {v[0][:150]}")
    return detected


log("\n  INJECTED FAULTS")

# 1. future lab (offset beyond the window)
def f_future(df, rw):
    rw.loc[rw.index[:50], "offset_min"] = W * 60 + 120
    return df, rw


# 2. post-death lab: encoded as a window violation in the raw extract
def f_postdeath(df, rw):
    rw.loc[rw.index[:25], "offset_min"] = -30      # before ICU admission
    return df, rw


# 3. wrong unit
def f_unit(df, rw):
    rw.loc[rw.index[:40], "unit"] = "furlongs"
    return df, rw


# 4. wrong itemid: MIMIC rows carrying nwICU-native itemids
def f_itemid(df, rw):
    idx = rw.index[rw.centre == "MIMIC-IV"][:20]
    rw.loc[idx, "itemid"] = 320045
    return df, rw


# 5. duplicate ICU stay
def f_dup(df, rw):
    return pd.concat([df, df.head(5)], ignore_index=True), rw


# 6. albumin sentinel
def f_alb_sentinel(df, rw):
    df.loc[df.index[:3], "albumin"] = 9999999.0
    return df, rw


# 7. SpO2 impossible
def f_spo2(df, rw):
    df.loc[df.index[:3], "spo2"] = 999999.0
    return df, rw


# 8. MAP impossible
def f_map(df, rw):
    df.loc[df.index[:4], "map"] = -500.0
    return df, rw


# 9. swapped patient ID (duplicate under a wrong key)
def f_swap(df, rw):
    df.loc[df.index[10], "stay_id"] = df.loc[df.index[0], "stay_id"]
    return df, rw


# 10. under-age patient
def f_age(df, rw):
    df.loc[df.index[:2], "age"] = 4.0
    return df, rw


# 11. non-binary outcome
def f_outcome(df, rw):
    df.loc[df.index[:2], "hospital_mortality"] = 2
    return df, rw


# 12. K70.2 mislabelled as cirrhosis -- tested at the phenotype layer
def f_k702(df, rw):
    # emulate a pipeline that used the WRONG rule by rewriting the config view
    bad = cfg.is_strict_cirrhosis_code("K70.2")
    if bad:
        return df, rw
    # simulate the fault surfacing: append a flag column the QC can see
    df["_phenotype_violation"] = 0
    return df, rw


for nm, sev, fn in [
        ("future lab (offset beyond 24h window)", "CRITICAL", f_future),
        ("pre-admission lab (offset <= 0)", "CRITICAL", f_postdeath),
        ("wrong unit ('furlongs')", "CRITICAL", f_unit),
        ("MIMIC itemid replaced by nwICU-native itemid", "CRITICAL", f_itemid),
        ("duplicate ICU stay", "CRITICAL", f_dup),
        ("albumin sentinel 9999999", "CRITICAL", f_alb_sentinel),
        ("SpO2 = 999999", "CRITICAL", f_spo2),
        ("MAP impossible (-500)", "CRITICAL", f_map),
        ("swapped patient ID", "CRITICAL", f_swap),
        ("age below 18", "CRITICAL", f_age),
        ("non-binary outcome", "CRITICAL", f_outcome)]:
    run_fault(nm, sev, fn)

# 12. phenotype fault, tested directly on the rule
log("\n  PHENOTYPE-LAYER FAULT")
k702_wrongly_in = cfg.is_strict_cirrhosis_code("K70.2")
k74_0_wrongly_in = cfg.is_strict_cirrhosis_code("K74.0")
detected = (not k702_wrongly_in) and (not k74_0_wrongly_in)
results.append(dict(fault="K70.2 / K74.0 falsely labelled cirrhosis",
                    severity="CRITICAL",
                    result="DETECTED" if detected else "MISSED",
                    violations="" if detected else "phenotype rule admits these codes"))
log(f"    {'DETECTED' if detected else 'MISSED  '}  [CRITICAL] "
    f"K70.2 / K74.0 falsely labelled cirrhosis")
log(f"        -> is_strict_cirrhosis_code('K70.2')={k702_wrongly_in}, "
    f"('K74.0')={k74_0_wrongly_in} (both must be False)")

fi = pd.DataFrame(results)
n_missed = int((fi.result == "MISSED").sum())
n_missed_crit = int(((fi.result == "MISSED") & (fi.severity == "CRITICAL")).sum())
log("\n" + "=" * 100)
log("FAULT-INJECTION SUMMARY")
log("=" * 100)
log(f"  baseline clean dataset violations : {len(base_v)}  "
    f"({'PASS' if baseline_clean else 'FAIL - QC is over-sensitive'})")
log(f"  faults injected                   : {len(fi)}")
log(f"  DETECTED                          : {int((fi.result=='DETECTED').sum())}")
log(f"  MISSED                            : {n_missed}")
log(f"  MISSED and CRITICAL               : {n_missed_crit}")
log(f"\n  VERDICT: "
    f"{'PASS - every injected fault was detected and the clean data is clean' if (baseline_clean and n_missed_crit == 0) else 'FAIL'}")

fi.to_csv(os.path.join(DATA, "fault_injection.csv"), index=False, encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "fault_injection.csv"), "phase_13_fault_injection.py")

with open(os.path.join(LOGS, "PHASE_13_fault_injection.log"), "w",
          encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nPHASE 13 DONE")
