"""FINAL_REBUILD -- the ONE frozen analysis configuration.

Every downstream script must import this module and must NOT redefine any of these
objects locally. The module computes its own SHA256 and exposes it as
`CONFIG_HASH`; `provenance.py` stamps that hash into every output.

Status of the model specification (to be stated honestly in Methods and NOT
misrepresented as pre-specified before the analysis began):

    The model specification was finalised after prespecified data-quality and
    estimability checks, and before the final model was fitted and externally
    evaluated.

This is version FINAL_v1.0.0. Any change to the objects below must increment
VERSION and be recorded in CHANGELOG at the bottom; the hash changes with it, so a
stale run is detectable.
"""
from __future__ import annotations

import hashlib
import json
import os

VERSION = "FINAL_v1.0.0"
FROZEN_AT = "2026-09-14"

# ===================================================================== PATHOLOGY
# Strict cirrhosis phenotype. See CIRRHOSIS_PHENOTYPE.md for the adjudication.
# Codes are normalised before matching (strip, remove '.', upper) and matched by
# PREFIX so that K703 captures K7030 and K7031.
STRICT_CIRRHOSIS_PREFIXES = [
    "K703",   # alcoholic cirrhosis of liver (incl. K70.30, K70.31)
    "K717",   # toxic liver disease with fibrosis and cirrhosis of liver
    "K743",   # primary biliary cirrhosis
    "K744",   # secondary biliary cirrhosis
    "K745",   # biliary cirrhosis, unspecified
    "K746",   # other and unspecified cirrhosis of liver (incl. K74.60, K74.69)
    "5712",   # ICD-9 alcoholic cirrhosis of liver
    "5715",   # ICD-9 cirrhosis of liver without mention of alcohol
    "5716",   # ICD-9 biliary cirrhosis
]

# Explicitly NOT cirrhosis. Listed so the exclusion is auditable and so that
# tests can assert these do NOT enter the primary cohort.
CIRRHOSIS_EXCLUDED_PREFIXES = [
    "K700", "K701", "K702", "K704", "K709",            # alcohol-related, not cirrhosis
    "K740", "K741", "K742",                            # hepatic fibrosis / sclerosis
    "5710", "5711", "5713", "57140", "57142", "57149", "5718", "5719",
    "P7881",                                           # perinatal; excluded by age
]

# Broad advanced-liver-disease phenotype -- SENSITIVITY ANALYSIS ONLY.
BROAD_PREFIXES = STRICT_CIRRHOSIS_PREFIXES + [
    "K702", "K704", "K740", "K741", "K742",            # fibrosis / failure
    "K766", "I85", "R18", "K72",                       # portal HTN, varices, ascites, failure
    "4560", "4561", "4562",                            # ICD-9 oesophageal varices
]

# ===================================================================== ELIGIBILITY
AGE_MIN = 18
FIRST_ICU_STAY_ONLY = True          # primary specification
ICU_LOS_MAX_DAYS = 60               # plausibility filter
ICU_TO_ADMIT_MAX_HOURS = 24         # first ICU stay == ICU admission within 24h of hospital admit

# ===================================================================== TIME WINDOWS
WINDOW_PRIMARY_HOURS = 24           # predictors from (ICU intime, intime + 24h]
WINDOW_EARLY_HOURS = 6              # PHASE 9C early-prediction sensitivity
WINDOW_LANDMARK_HOURS = 24          # PHASE 9B landmark

# ===================================================================== OUTCOMES
OUTCOME_TRACK_A = "hospital_mortality"     # MIMIC + eICU
OUTCOME_TRACK_B = "death_30d_best"         # MIMIC + nwICU, from best available death date
OUTCOME_ALT_MIMIC = "death_by_discharge"   # sensitivity: dod <= dischtime

# ===================================================================== PREDICTORS
PRIMARY_CONTINUOUS = [
    "age", "albumin", "bilirubin", "creatinine", "sodium", "platelet",
    "wbc", "heart_rate", "map", "resp_rate", "spo2",
]
PRIMARY_BINARY = ["male"]

# Aggregation inside the window. Convention: "worst" value, defined per variable
# by clinical direction, applied IDENTICALLY in all three centres.
AGGREGATION = {
    "age": "first",
    "albumin": "min",
    "bilirubin": "max",
    "creatinine": "max",
    "sodium": "min",
    "platelet": "min",
    "wbc": "max",
    "heart_rate": "mean",
    "map": "mean",
    "resp_rate": "mean",
    "spo2": "mean",          # mean, not min -- see v1.0.1 rationale in the audit
}

# Physiological / analytical plausibility bounds. Values outside are set to
# missing AND counted; they are never winsorised or silently dropped.
PLAUSIBLE_RANGE = {
    "age": (18.0, 120.0),
    "albumin": (0.5, 7.0),
    "bilirubin": (0.05, 80.0),
    "creatinine": (0.1, 30.0),
    "sodium": (90.0, 190.0),
    "platelet": (2.0, 2000.0),
    "wbc": (0.1, 200.0),
    "hemoglobin": (2.0, 25.0),
    "inr": (0.5, 20.0),
    "lactate": (0.1, 40.0),
    "ast": (1.0, 20000.0),
    "alt": (1.0, 20000.0),
    "heart_rate": (10.0, 300.0),
    "map": (10.0, 200.0),
    "sbp": (20.0, 300.0),
    "dbp": (5.0, 200.0),
    "resp_rate": (2.0, 80.0),
    "spo2": (50.0, 100.0),
    "temperature": (25.0, 45.0),
}

# ===================================================================== MISSING DATA
# Primary: median imputation from the DEVELOPMENT cohort (MIMIC) only, applied
# unchanged to validation centres, plus a FIXED set of missing indicators.
#
# Rationale (frozen after the estimability audit): indicators for variables with
# only ~10-18 missing development patients are quasi-completely separated and make
# the fit penalty-dependent. Only albumin and bilirubin have enough missing
# development patients to identify an indicator without a penalty.
MISSING_INDICATORS_PRIMARY = ["albumin", "bilirubin"]
IMPUTATION = "development-cohort median"
OUTCOME_IMPUTED = False

# Strategy C (reduced complete-variable specification) -- frozen HERE, not chosen
# by the script. Exactly these predictors, all with adequate coverage in all three
# centres, no indicators, no imputation needed for the great majority.
REDUCED_PREDICTORS = [
    "age", "creatinine", "sodium", "platelet", "wbc",
    "hemoglobin", "heart_rate", "map", "resp_rate", "spo2",
]
REDUCED_BINARY = ["male"]

# ===================================================================== MODEL
MODEL_TYPE = "logistic"
PENALTY = None                       # UNPENALIZED. No ridge, no lasso.
SEPARATION_POLICY = ("stop-and-report")   # never auto-add a penalty
MIN_MISSING_FOR_INDICATOR = 50       # enforced by an assertion in the builder

# ===================================================================== SCORES
SCORE_MELD_ROUND = True
SCORE_MELD_CLIP = (6, 40)
SCORE_MELD_CREAT_BOUNDS = (1.0, 4.0)
SCORE_MELD_BILI_MIN = 1.0
SCORE_MELD_INR_MIN = 1.0
SCORE_MELD_RRT_CREAT = 4.0
SCORE_MELDNA_NA_BOUNDS = (125.0, 137.0)
SCORE_MELDNA_COEF = (1.32, 0.033)
BILI_MGDL_TO_UMOLL = 17.1            # for ALBI
ALB_GDL_TO_GL = 10.0                 # for ALBI
# APACHE: MIMIC exposes APS-III (mimiciv_derived.apsiii); eICU exposes APACHE IV
# (apachepatientresult.apachescore). These are DIFFERENT instruments. Cross-database
# transportability of "APACHE" is FORBIDDEN; each may be described within its own
# database only.
APACHE_CROSS_DATABASE_ALLOWED = False

# ===================================================================== UNCERTAINTY
# Bootstrap resampling unit. eICU-CRD contains 208 hospitals in total, but only 155
# contribute at least one stay to the frozen cirrhosis cohort (49 have enough events
# to estimate an AUROC); the clustering unit is the hospitalid column as loaded, so
# the count is whatever the cohort contains, never the database total.
CLUSTER_UNIT = "hospitalid"
N_BOOTSTRAP_CLUSTER = 2000
N_BOOTSTRAP_OPTIMISM = 300
N_SIM_NULL_SLOPE = 5000              # calibration-slope null guard
MIN_HOSPITAL_N = 20                  # per-hospital analysis threshold
MIN_HOSPITAL_DEATHS = 5
RANDOM_SEED = 20260914

# ===================================================================== DERIVED CODE PROVENANCE
LOCAL_DERIVED_CODE_VERSION = "UNKNOWN"   # could not be established from the local install
DERIVED_VERIFICATION = {
    "meld_initial": "verified 100.00% exact vs UNOS-2002 with RRT rule, clip[6,40], integer round",
    "meld": "NOT VERIFIED (max 84.87%) -- DO NOT USE; recompute MELD-Na from components",
    "first_day_lab": "verified 100.00% exact vs analysis dataset",
    "first_day_vitalsign": "verified 100.00% exact vs analysis dataset",
    "apsiii": "APS-III, not APACHE IV",
}


# ===================================================================== helpers
def normalise_code(code: str) -> str:
    """Strip whitespace, remove '.', uppercase. Applied before prefix matching."""
    return str(code).strip().replace(".", "").upper()


def is_strict_cirrhosis_code(code: str) -> bool:
    c = normalise_code(code)
    return any(c.startswith(p) for p in STRICT_CIRRHOSIS_PREFIXES)


def is_excluded_cirrhosis_code(code: str) -> bool:
    c = normalise_code(code)
    return any(c.startswith(p) for p in CIRRHOSIS_EXCLUDED_PREFIXES)


def is_broad_code(code: str) -> bool:
    c = normalise_code(code)
    return any(c.startswith(p) for p in BROAD_PREFIXES)


def as_dict() -> dict:
    """All frozen objects, for hashing and for provenance stamping."""
    return {
        "VERSION": VERSION, "FROZEN_AT": FROZEN_AT,
        "STRICT_CIRRHOSIS_PREFIXES": STRICT_CIRRHOSIS_PREFIXES,
        "CIRRHOSIS_EXCLUDED_PREFIXES": CIRRHOSIS_EXCLUDED_PREFIXES,
        "BROAD_PREFIXES": BROAD_PREFIXES,
        "AGE_MIN": AGE_MIN, "FIRST_ICU_STAY_ONLY": FIRST_ICU_STAY_ONLY,
        "ICU_LOS_MAX_DAYS": ICU_LOS_MAX_DAYS,
        "ICU_TO_ADMIT_MAX_HOURS": ICU_TO_ADMIT_MAX_HOURS,
        "WINDOW_PRIMARY_HOURS": WINDOW_PRIMARY_HOURS,
        "WINDOW_EARLY_HOURS": WINDOW_EARLY_HOURS,
        "WINDOW_LANDMARK_HOURS": WINDOW_LANDMARK_HOURS,
        "OUTCOME_TRACK_A": OUTCOME_TRACK_A, "OUTCOME_TRACK_B": OUTCOME_TRACK_B,
        "OUTCOME_ALT_MIMIC": OUTCOME_ALT_MIMIC,
        "PRIMARY_CONTINUOUS": PRIMARY_CONTINUOUS, "PRIMARY_BINARY": PRIMARY_BINARY,
        "AGGREGATION": AGGREGATION, "PLAUSIBLE_RANGE": PLAUSIBLE_RANGE,
        "MISSING_INDICATORS_PRIMARY": MISSING_INDICATORS_PRIMARY,
        "IMPUTATION": IMPUTATION, "OUTCOME_IMPUTED": OUTCOME_IMPUTED,
        "REDUCED_PREDICTORS": REDUCED_PREDICTORS, "REDUCED_BINARY": REDUCED_BINARY,
        "MODEL_TYPE": MODEL_TYPE, "PENALTY": PENALTY,
        "SEPARATION_POLICY": SEPARATION_POLICY,
        "MIN_MISSING_FOR_INDICATOR": MIN_MISSING_FOR_INDICATOR,
        "SCORE_MELD_ROUND": SCORE_MELD_ROUND, "SCORE_MELD_CLIP": SCORE_MELD_CLIP,
        "SCORE_MELD_CREAT_BOUNDS": SCORE_MELD_CREAT_BOUNDS,
        "SCORE_MELD_BILI_MIN": SCORE_MELD_BILI_MIN,
        "SCORE_MELD_INR_MIN": SCORE_MELD_INR_MIN,
        "SCORE_MELD_RRT_CREAT": SCORE_MELD_RRT_CREAT,
        "SCORE_MELDNA_NA_BOUNDS": SCORE_MELDNA_NA_BOUNDS,
        "SCORE_MELDNA_COEF": SCORE_MELDNA_COEF,
        "BILI_MGDL_TO_UMOLL": BILI_MGDL_TO_UMOLL, "ALB_GDL_TO_GL": ALB_GDL_TO_GL,
        "APACHE_CROSS_DATABASE_ALLOWED": APACHE_CROSS_DATABASE_ALLOWED,
        "CLUSTER_UNIT": CLUSTER_UNIT, "N_BOOTSTRAP_CLUSTER": N_BOOTSTRAP_CLUSTER,
        "N_BOOTSTRAP_OPTIMISM": N_BOOTSTRAP_OPTIMISM,
        "N_SIM_NULL_SLOPE": N_SIM_NULL_SLOPE,
        "MIN_HOSPITAL_N": MIN_HOSPITAL_N, "MIN_HOSPITAL_DEATHS": MIN_HOSPITAL_DEATHS,
        "RANDOM_SEED": RANDOM_SEED,
        "LOCAL_DERIVED_CODE_VERSION": LOCAL_DERIVED_CODE_VERSION,
        "DERIVED_VERIFICATION": DERIVED_VERIFICATION,
    }


CANONICAL_JSON = json.dumps(as_dict(), sort_keys=True, indent=2)
CONFIG_HASH = hashlib.sha256(CANONICAL_JSON.encode()).hexdigest()
CONFIG_HASH_SHORT = CONFIG_HASH[:16]

if __name__ == "__main__":
    print(f"FINAL_REBUILD config {VERSION}  frozen {FROZEN_AT}")
    print(f"SHA256 = {CONFIG_HASH}")
    print(json.dumps(as_dict(), indent=2)[:2000])


CHANGELOG = [
    "FINAL_v1.0.0  2026-09-14  initial frozen configuration after GATE 0A "
    "(cirrhosis phenotype adjudicated from official ICD descriptors, K70.2/K70.4/"
    "K74.0-2 excluded) and GATE 0B (local MELD verified: meld_initial reproduces "
    "UNOS-2002 with RRT rule at 100.00%; meld is unverified and barred).",
]
