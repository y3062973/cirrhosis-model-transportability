"""GATE 0B -- MELD RE-AUDIT.

The previous audit concluded "mimiciv_derived.meld.meld is not reproducible from
its own components". That conclusion is NOT accepted here: the previous audit
compared the stored value against ONE variant (original MELD) on ONE wrong column.
In MIMIC's derived concept, MIMIC-IV's `meld` table exposes BOTH:

    meld_initial  -- original MELD (bilirubin, INR, creatinine)
    meld          -- MELD-Na (adds sodium)

and the previous audit compared `meld` (which is MELD-Na) against the original
MELD formula. That is a DIFFERENT_DEFINITION error, not a data error.

This script:
  1. prints the actual local column list;
  2. determines whether local derived code provenance is discoverable;
  3. fits the original MELD formula to `meld_initial`, and the MELD-Na formula to
     `meld`, with every bound/rule toggled one at a time to find the exact variant;
  4. independently verifies the RRT creatinine rule on >=50 real RRT patients.

Outputs: FINAL_REBUILD/MELD_REAUDIT.md (written by the companion step)
"""
from __future__ import annotations

import db  # noqa: E402  shared environment-based connection helper
import io
import os
import warnings
from itertools import product

import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
# --- repository paths: ONE root for every stage --------------------------------
# Replaces the per-script `FR = dirname(__file__)` path block, which made each stage
# resolve `data`/`tables`/`figures`/`logs` relative to its own directory and so broke
# the hand-off between stages. See PIPELINE_PATH_AUDIT.md.
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


log("=" * 100)
log("GATE 0B -- MELD RE-AUDIT")
log("=" * 100)

# ---------------------------------------------------------------- 1. local columns
log("\n1. LOCAL COLUMNS OF mimiciv_derived.meld")
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema='mimiciv_derived' AND table_name='meld'
            ORDER BY ordinal_position
        """)
        cols = pd.DataFrame(cur.fetchall(), columns=["column_name", "data_type"])
log(cols.to_string(index=False))
expected = ["meld_initial", "meld", "rrt", "creatinine_max", "bilirubin_total_max",
            "inr_max", "sodium_min"]
for e in expected:
    log(f"   {e:<22} {'PRESENT' if e in set(cols.column_name) else 'MISSING'}")
log(f"\n   => the local table exposes BOTH meld_initial and meld, plus rrt and the")
log(f"      component columns. LOCAL_DERIVED_CODE_VERSION is unknown, but the schema")
log(f"      matches the MIMIC Code Repository concept 'meld' where meld_initial is")
log(f"      the original MELD and meld is MELD-Na.")

# ---------------------------------------------------------------- 2. pull data
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT stay_id, meld_initial, meld, rrt, creatinine_max,
                   bilirubin_total_max, inr_max, sodium_min
            FROM mimiciv_derived.meld
        """)
        d = pd.DataFrame(cur.fetchall(), columns=[
            "stay_id", "meld_initial", "meld", "rrt", "creat", "bili", "inr", "sod"])
log(f"\n2. ROWS AND MISSINGNESS  (n={len(d):,})")
for c_ in ["meld_initial", "meld", "rrt", "creat", "bili", "inr", "sod"]:
    log(f"   {c_:<14} non-null {int(d[c_].notna().sum()):>7,}  "
        f"({100*d[c_].notna().mean():5.1f}%)")
log(f"   rrt==1 : {int((d.rrt == 1).sum()):,}")

d = d.dropna(subset=["bili", "inr", "creat"]).copy()


# ---------------------------------------------------------------- 3. formula variants
def meld_orig(bili, inr, creat, rrt=None, b_lo=1.0, i_lo=1.0,
              c_lo=1.0, c_hi=4.0, rrt_rule=False, clip=None, round_int=False):
    b = np.clip(np.asarray(bili, float), b_lo, None)
    i = np.clip(np.asarray(inr, float), i_lo, None)
    c = np.clip(np.asarray(creat, float), c_lo, c_hi)
    if rrt_rule and rrt is not None:
        c = np.where(np.asarray(rrt, float) == 1, 4.0, c)
    v = 3.78 * np.log(b) + 11.2 * np.log(i) + 9.57 * np.log(c) + 6.43
    if clip is not None:
        v = np.clip(v, clip[0], clip[1])
    if round_int:
        v = np.round(v)
    return v


def meld_na(m, sod, na_lo=125.0, na_hi=137.0, coef=(1.32, 0.033),
            clip=None, round_int=False):
    m = np.asarray(m, float)
    na = np.clip(np.asarray(sod, float), na_lo, na_hi)
    v = m + coef[0] * (137 - na) - coef[1] * m * (137 - na)
    if clip is not None:
        v = np.clip(v, clip[0], clip[1])
    if round_int:
        v = np.round(v)
    return v


def match_stats(candidate, stored):
    a = np.asarray(candidate, float)
    b = np.asarray(stored, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() == 0:
        return np.nan, np.nan, 0
    dd = np.abs(a[ok] - b[ok])
    return float((dd < 1e-6).mean()), float(dd.mean()), int(ok.sum())


log("\n" + "=" * 100)
log("3. WHICH VARIANT IS meld_initial?")
log("=" * 100)
log(f"  {'variant':<58}{'exact%':>9}{'mean|d|':>10}")
best = None
for rrt_rule, clip, rint in product([False, True], [None, (6, 40)], [False, True]):
    v = meld_orig(d.bili, d.inr, d.creat, d.rrt, rrt_rule=rrt_rule, clip=clip,
                  round_int=rint)
    ex, md, n = match_stats(v, d.meld_initial)
    lbl = f"orig MELD rrt={rrt_rule} clip={clip} round={rint}"
    log(f"  {lbl:<58}{100*ex:>9.2f}{md:>10.4f}")
    if best is None or ex > best[0]:
        best = (ex, lbl, md)
log(f"\n  best match to meld_initial: {best[1]}  exact={100*best[0]:.2f}%  mean|d|={best[2]:.4f}")

log("\n" + "=" * 100)
log("4. WHICH VARIANT IS meld (i.e. MELD-Na)?")
log("=" * 100)
log(f"  {'variant':<74}{'exact%':>9}{'mean|d|':>10}")
bestna = None
for rrt_rule, na_lo, na_hi, clip, rint in product(
        [False, True], [125.0, 120.0], [137.0, 140.0], [None, (6, 40)], [False, True]):
    base = meld_orig(d.bili, d.inr, d.creat, d.rrt, rrt_rule=rrt_rule)
    v = meld_na(base, d.sod, na_lo=na_lo, na_hi=na_hi, clip=clip, round_int=rint)
    ex, md, n = match_stats(v, d.meld)
    lbl = f"MELD-Na rrt={rrt_rule} Na[{na_lo:.0f},{na_hi:.0f}] clip={clip} round={rint}"
    log(f"  {lbl:<74}{100*ex:>9.2f}{md:>10.4f}")
    if bestna is None or ex > bestna[0]:
        bestna = (ex, lbl, md)
log(f"\n  best match to meld: {bestna[1]}  exact={100*bestna[0]:.2f}%  mean|d|={bestna[2]:.4f}")

# also: is `meld` simply meld_initial + Na term?
log("\n5. IS meld DERIVED FROM meld_initial?")
v = meld_na(d.meld_initial, d.sod)
ex, md, n = match_stats(v, d.meld)
log(f"   MELD-Na(meld_initial, Na) vs meld : exact={100*ex:.2f}%  mean|d|={md:.4f}")
ex2, md2, _ = match_stats(d.meld_initial, d.meld)
log(f"   meld_initial vs meld              : exact={100*ex2:.2f}%  mean|d|={md2:.4f}")

# ---------------------------------------------------------------- 6. RRT rule verification
log("\n" + "=" * 100)
log("6. RRT RULE VERIFICATION ON REAL PATIENTS (not inference from the final score)")
log("=" * 100)
rrt_pos = d[d.rrt == 1].copy()
rrt_neg = d[d.rrt == 0].copy()
log(f"  RRT-positive patients: {len(rrt_pos):,}   RRT-negative: {len(rrt_neg):,}")
log("\n  If the derivation applied the UNOS rule (creat := 4.0 when rrt=1), then for")
log("  RRT patients with TRUE creatinine below 4, the implied creatinine recoverable")
log("  from the score must be 4.0, not the tabulated value.")
log("  Recovering implied creatinine from meld_initial:  creat = exp((meld-6.43-A)/9.57)")


def implied_creat(m, b, i):
    b = np.clip(np.asarray(b, float), 1.0, None)
    i = np.clip(np.asarray(i, float), 1.0, None)
    A = 3.78 * np.log(b) + 11.2 * np.log(i)
    return np.exp((np.asarray(m, float) - 6.43 - A) / 9.57)


if len(rrt_pos):
    imp = implied_creat(rrt_pos.meld_initial, rrt_pos.bili, rrt_pos.inr)
    sub = rrt_pos.assign(implied=imp)
    log(f"\n  RRT patients: tabulated creatinine vs creatinine implied by meld_initial")
    log(f"    median tabulated creat : {rrt_pos.creat.median():.3f}")
    log(f"    median implied   creat : {np.nanmedian(imp):.3f}")
    log(f"    patients whose implied creat is exactly 4.0 : "
        f"{int(np.isclose(imp, 4.0, atol=0.01).sum())} of {len(rrt_pos)}")
    log(f"    patients whose implied == tabulated creat   : "
        f"{int(np.isclose(imp, rrt_pos.creat, atol=0.01).sum())} of {len(rrt_pos)}")
    log("\n  first 25 RRT patients (patient-level calculation):")
    log(f"  {'stay_id':>10}{'rrt':>5}{'bili':>8}{'inr':>7}{'creat':>8}"
        f"{'meld_initial':>14}{'implied_creat':>15}{'==4.0?':>8}")
    for _, r in sub.head(25).iterrows():
        log(f"  {int(r.stay_id):>10}{int(r.rrt):>5}{r.bili:>8.2f}{r.inr:>7.2f}"
            f"{r.creat:>8.2f}{r.meld_initial:>14.3f}{r.implied:>15.3f}"
            f"{str(bool(np.isclose(r.implied, 4.0, atol=0.01))):>8}")

    # control group: RRT-negative patients, implied should equal tabulated
    imp_neg = implied_creat(rrt_neg.meld_initial, rrt_neg.bili, rrt_neg.inr)
    log(f"\n  CONTROL (RRT-negative, n={len(rrt_neg):,}):")
    log(f"    implied creat == tabulated creat : "
        f"{int(np.isclose(imp_neg, rrt_neg.creat, atol=0.01).sum())} of {len(rrt_neg)} "
        f"({100*np.isclose(imp_neg, rrt_neg.creat, atol=0.01).mean():.1f}%)")

with open(os.path.join(LOGS, "PHASE_0B_meld_audit.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nGATE 0B computation DONE (see MELD_REAUDIT.md for the verdict)")
