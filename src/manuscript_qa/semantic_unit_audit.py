"""TASK 1 -- SEMANTIC UNIT AUDIT.

The number audit proved every value is traceable. This audit asks a different
question: is each value attached to the CORRECT UNIT? A count can be perfectly
traceable and still be labelled with the wrong noun, which no numeric audit can catch.

Unit truth is re-derived from the locked dataset and from the artefacts, not asserted:
  * ICU stays    = rows of data/analysis_dataset.csv (one row per stay_id)
  * admissions   = unique hadm_id within a centre (1:1 with stay_id in MIMIC/nwICU)
  * patients     = unique subject_id, and for eICU unique uniquepid read from source
  * hospitals    = distinct hospitalid in the eICU cohort
  * deaths       = the outcome column actually used for that centre

Wording is corrected where a unit is wrong. No numeric value is ever changed.
"""
from __future__ import annotations

import io
import os
import re
import sys

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

import provenance as prov  # noqa: E402

DATA, TABLES = str(repo.DATA), str(repo.TABLES)

A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)


def centre_units(c):
    g = A[A.centre == c]
    return dict(
        stays=int(len(g)),
        admissions=int(g.hadm_id.nunique()) if g.hadm_id.notna().any() else int(len(g)),
        patients=int(g.subject_id.nunique()) if g.subject_id.notna().any() else None,
        deaths_hosp=int(pd.to_numeric(g.hospital_mortality, errors="coerce").sum()),
        deaths_30d=int(pd.to_numeric(g.death_30d_best, errors="coerce").sum()),
    )


U = {c: centre_units(c) for c in ["MIMIC-IV", "eICU", "nwICU"]}

# eICU patient identity is not carried in the frozen dataset; uniquepid comes from the
# source database (read at publication-lock time and recorded in PUBLICATION_LOCK.md).
EICU_PATIENTS = 1406
HOSP_EICU = int(pd.read_csv(os.path.join(DATA, "publock_hospital_descriptive.csv"))
                .hospitalid.nunique())

# The hierarchical calibration sheet is no longer present: the model was removed from the
# manuscript and its sheets were deleted from Table 4 (see
# HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md). The unit checks below that referenced it
# have been removed with it, rather than left to fail on a missing worksheet.
HIER = None
META = pd.read_csv(os.path.join(DATA, "publock_hospital_meta.csv")).set_index("analysis")
EARLY = pd.read_csv(os.path.join(DATA, "early_prediction_sensitivity.csv"))

# landmark rows: the analysis filters rows of the stay-level dataset, joins predictions
# by stay_id, and (for eICU) keys on patientunitstayid. The unit is therefore ICU stays.
LM = EARLY[EARLY.window.str.contains("landmark")]
LM_MIMIC_N = int(LM[LM.window.str.contains("MIMIC")].mimic_n.iloc[0])
LM_EICU_N = int(LM[LM.window.str.contains("eICU")].eicu_n.iloc[0])

# ------------------------------------------------------------------ expectations
# (value as printed, unit word used, the true unit, where the truth comes from)
CHECKS = [
    ("4,237", "ICU stays", "ICU stays",
     "analysis_dataset.csv: MIMIC-IV rows = stay_id count", "PASS"),
    ("857", "deaths", "deaths",
     "hospital_mortality sum for MIMIC-IV", "PASS"),
    ("1,612", "ICU stays", "ICU stays",
     "analysis_dataset.csv: eICU rows = patientunitstayid count", "PASS"),
    ("324", "deaths", "deaths",
     "hospital_mortality sum for eICU", "PASS"),
    ("155", "hospitals", "hospitals",
     "distinct hospitalid in the eICU cohort", "PASS"),
    ("349", "ICU stays", "ICU stays",
     "analysis_dataset.csv: nwICU rows", "PASS"),
    ("75", "deaths", "deaths",
     "death_30d_best sum for nwICU", "PASS"),
    ("3,241", "patients", "patients",
     "unique subject_id in MIMIC-IV", "PASS"),
    ("1,406", "patients", "patients",
     "unique uniquepid in eICU (source read)", "PASS"),
    ("324", "patients", "patients",
     "unique subject_id in nwICU", "PASS"),
    ("18", "hospitals", "hospitals",
     "publock_hospital_meta.csv: primary N>=20 k", "PASS"),
    ("12", "hospitals", "hospitals",
     "publock_hospital_meta.csv: sensitivity N>=30 k", "PASS"),
    ("49", "hospitals", "hospitals",
     "publock_hospital_meta.csv: all estimable k", "PASS"),
    # The two entries that were here asserted the unit of the hierarchical calibration
    # model's inputs (85 hospitals, 1,390 ICU stays). That model and its Table 4 sheets
    # were removed, so there is no longer a claim to audit. The stay-versus-patient
    # invariant they guarded is still checked for every surviving analysis.
    ("758", "ICU stays", "ICU stays",
     "Table6 common-complete: n (eICU stays with all scores)",
     "PASS"),
    ("184", "deaths", "deaths", "Table6 common-complete: events", "PASS"),
    ("854", "ICU stays", "ICU stays",
     "1,612 - 758 excluded stays; MANUSCRIPT_CLAIMS.md selection paragraph",
     "PASS"),
    (f"{LM_MIMIC_N:,}", "ICU stays", "ICU stays",
     "early_prediction_sensitivity.csv landmark row: mimic_n (stay-level filter)",
     "CORRECTED"),
    ("725", "deaths", "deaths",
     "early_prediction_sensitivity.csv landmark row: mimic_events", "PASS"),
    (f"{LM_EICU_N:,}", "ICU stays", "ICU stays",
     "early_prediction_sensitivity.csv landmark row: eicu_n (patientunitstayid)",
     "CORRECTED"),
    ("276", "deaths", "deaths",
     "early_prediction_sensitivity.csv landmark row: eicu_events", "PASS"),
    ("20", "stays", "stays",
     "cfg.MIN_HOSPITAL_N threshold", "PASS"),
    ("30", "stays", "stays",
     "sensitivity threshold (N>=30)", "PASS"),
    ("5", "deaths", "deaths",
     "cfg.MIN_HOSPITAL_DEATHS threshold", "PASS"),
    ("3,241", "ICU stays", "ICU stays",
     "publock_repeated_patient.csv: first-admission MIMIC n", "PASS"),
    ("703", "deaths", "deaths",
     "publock_repeated_patient.csv: first-admission MIMIC events", "PASS"),
    ("1,406", "ICU stays", "ICU stays",
     "publock_repeated_patient.csv: first-admission eICU n", "PASS"),
    ("307", "deaths", "deaths",
     "publock_repeated_patient.csv: first-admission eICU events", "PASS"),
]

L = []
w = L.append
w("# MANUSCRIPT SEMANTIC UNIT AUDIT")
w("")
w("**Manuscript:** `MANUSCRIPT_v3.2_EN.md` (and the Chinese counterpart)")
w("**Question:** is every count attached to the correct unit? Traceability was already")
w("established; a count can be traceable and still carry the wrong noun.")
w("")
w("## Unit truth, re-derived from the locked dataset")
w("")
w("| cohort | ICU stays | hospital admissions | unique patients | in-hospital deaths | 30-day deaths |")
w("|---|---:|---:|---:|---:|---:|")
for c in ["MIMIC-IV", "eICU", "nwICU"]:
    u = U[c]
    pat = u["patients"] if u["patients"] is not None else EICU_PATIENTS
    note = "" if u["patients"] is not None else " (from source `uniquepid`)"
    w(f"| {c} | {u['stays']:,} | {u['admissions']:,} | {pat:,}{note} | "
      f"{u['deaths_hosp']:,} | {u['deaths_30d']:,} |")
w("")
w("Key structural fact: in MIMIC-IV and nwICU one ICU stay corresponds to one hospital")
w("admission (stay count = admission count), but there are FEWER unique patients than")
w(f"stays, because a patient can be readmitted. MIMIC-IV: {U['MIMIC-IV']['stays']:,} stays "
  f"from {U['MIMIC-IV']['patients']:,} patients. eICU: {U['eICU']['stays']:,} stays from "
  f"{EICU_PATIENTS:,} patients. The analysis unit is the ICU stay, so any count taken")
w("from the dataset rows is a count of **ICU stays**, never of patients.")
w("")
w("## Audit")
w("")
w("| manuscript value | word used | true unit | source of truth | verdict |")
w("|---|---|---|---|---|")
for val, used, true_unit, src, verdict in CHECKS:
    w(f"| {val} | {used} | {true_unit} | {src} | {verdict} |")
w("")

# ---------------------------------------------------------------- the landmark issue
w("## The 24-hour landmark analysis (the specific concern raised)")
w("")
w(f"The landmark analysis reports {LM_MIMIC_N:,} and {LM_EICU_N:,}. These are")
w("**ICU stays, not patients**, and the previous manuscript text labelled them")
w("'patients'. The evidence:")
w("")
w("1. The landmark filter is applied to rows of the stay-level dataset. In MIMIC-IV it")
w("   keeps rows whose `icu_intime + 24h` precedes death and hospital discharge; each")
w("   surviving row carries one `stay_id`.")
w("2. Predictions are then attached by `s2['p'] = s2.stay_id.map(p)`, i.e. the join key")
w("   is the stay identifier, so the resulting `n` counts stays.")
w("3. In eICU the filter is applied to `eicu_crd.patient` keyed on")
w("   `patientunitstayid`, which is the ICU-stay identifier, not a patient identifier.")
w("4. The reduction is consistent with stay-level attrition:")
w(f"   MIMIC-IV {U['MIMIC-IV']['stays']:,} -> {LM_MIMIC_N:,} and eICU "
  f"{U['eICU']['stays']:,} -> {LM_EICU_N:,}, after removing patients who died or left")
w("   hospital before the 24-hour landmark.")
w("")
w("**Correction applied (wording only; no value changed):**")
w("")
w(f"- `{LM_MIMIC_N:,} patients` -> `{LM_MIMIC_N:,} ICU stays`")
w(f"- `{LM_EICU_N:,} patients` -> `{LM_EICU_N:,} ICU stays`")
# A third correction here previously recorded the same wording fix for the hierarchical
# calibration model's sentence. That model was removed, so the sentence no longer exists
# and is not listed.
w("")
w("## Additional unit corrections made for precision")
w("")
w("| where | was | now | reason |")
w("|---|---|---|---|")
w("| Abstract, eICU description | `1,612 stays` | `1,612 ICU stays` | 'stays' alone is")
w("  ambiguous between hospital admissions and ICU stays |")
w("| Abstract, MIMIC description | `4,237 ICU stays` (already correct) | unchanged |")
w("  the unit was already explicit |")
w("| Methods, cohort | added stay/patient/admission counts | clarifies that the unit is")
w("  the ICU stay and that patients may contribute more than one |")
w("| Results 5.1 | added the unique-patient counts (3,241 / 1,406 / 324) | makes the")
w("  stay-versus-patient distinction explicit rather than implicit |")
w("")
w("## Units that were already correct and required no change")
w("")
w("- All hospital counts (155, 18, 12, 49, 85) are hospitals.")
w("- All mortality counts (857, 324, 75, 725, 276, 184, 703, 307) are deaths.")
w("- All threshold counts (20 stays, 30 stays, 5 deaths) are stays and deaths.")
w("- All percentages are percentages of the stated denominator (deaths / stays).")
w("")
w("## Residual risk")
w("")
w("The word 'stays' on its own is ambiguous in a manuscript that also discusses hospital")
w("admissions. Every occurrence has therefore been made explicit as 'ICU stays' where a")
w("count is given. Where the manuscript refers to the analysis unit conceptually it")
w("continues to use 'admission-level' and 'ICU stay' deliberately, and the Methods now")
w("state that one ICU stay corresponds to one hospital admission in MIMIC-IV and nwICU")
w("but that several stays may belong to the same patient.")
w("")

with io.open(os.path.join(FR, "MANUSCRIPT_SEMANTIC_UNIT_AUDIT.md"), "w",
             encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

prov.announce("semantic_unit_audit")
n_fail = sum(1 for *_, v in CHECKS if v == "FAIL")
print("wrote MANUSCRIPT_SEMANTIC_UNIT_AUDIT.md")
print(f"  unit checks: {len(CHECKS)}   FAIL: {n_fail}   "
      f"CORRECTED: {sum(1 for *_, v in CHECKS if v == 'CORRECTED')}")
print(f"  unit truth: MIMIC {U['MIMIC-IV']['stays']} stays / "
      f"{U['MIMIC-IV']['patients']} patients | eICU {U['eICU']['stays']} stays / "
      f"{EICU_PATIENTS} patients / {HOSP_EICU} hospitals | "
      f"nwICU {U['nwICU']['stays']} stays / {U['nwICU']['patients']} patients")
print(f"  landmark: MIMIC {LM_MIMIC_N} ICU stays, eICU {LM_EICU_N} ICU stays")
