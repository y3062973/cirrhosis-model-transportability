"""GATE 0A -- build the authoritative cirrhosis code dictionary and phenotype.

Approach: derive the code set from the OFFICIAL ICD descriptors held in
mimiciv_hosp.d_icd_diagnoses (which covers both ICD-9 v9 and ICD-10 v10 with
their full titles), rather than from memory. Any code whose official title
contains "cirrhos" is a candidate; each candidate is then adjudicated on its
descriptor, with the reason recorded.

This immediately corrects the previous audit's proposed rule, which wrongly
included K70.2 (alcoholic fibrosis and sclerosis) and K70.4 (alcoholic hepatic
failure) and would have piled alcohol-related liver disease into a cirrhosis
cohort.

Outputs:
  FINAL_REBUILD/cirrhosis_code_dictionary.xlsx
  FINAL_REBUILD/PHASE_0A_phenotype.log
"""
from __future__ import annotations

import db  # noqa: E402  shared environment-based connection helper
import csv
import hashlib
import io
import os
import warnings

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
log("GATE 0A -- CIRRHOSIS PHENOTYPE: AUTHORITATIVE CODE ADJUDICATION")
log("=" * 100)

# ---------------------------------------------------------------- candidates from official titles
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT icd_version, icd_code, long_title
            FROM mimiciv_hosp.d_icd_diagnoses
            WHERE long_title ILIKE '%%cirrhos%%'
            ORDER BY icd_version, icd_code
        """)
        cand = pd.DataFrame(cur.fetchall(), columns=["version", "code", "title"])
log(f"\n  codes whose OFFICIAL title contains 'cirrhos': {len(cand)}")
for _, r in cand.iterrows():
    log(f"    v{r.version}  {r.code:<8} {r.title}")

# ---------------------------------------------------------------- adjudication
# Decision rule, applied to the descriptor text, recorded per code.
#   INCLUDE  : the descriptor states cirrhosis of the liver
#   EXCLUDE  : fibrosis / sclerosis / hepatic failure / hepatitis / fatty liver
#              without cirrhosis, or a perinatal code excluded by the age rule
P78 = {"P7881"}          # congenital cirrhosis -- perinatal; excluded by age >= 18


def adjudicate(version, code, title):
    t = title.lower()
    if code in P78:
        return False, ("perinatal code (P78.81 congenital cirrhosis); excluded by the "
                       "adult age criterion, not by the cirrhosis definition")
    if "cirrhos" in t:
        if "fibrosis and cirrhosis" in t or "cirrhosis of liver" in t:
            return True, "descriptor explicitly states cirrhosis of the liver"
        if "biliary cirrhosis" in t:
            return True, "descriptor explicitly states biliary cirrhosis"
        if t.strip() == "fibrosis and cirrhosis of liver":
            return True, "category header subsuming the cirrhosis subcodes"
        return True, "descriptor explicitly states cirrhosis"
    return False, "descriptor does not state cirrhosis"


cand["include_primary"] = [adjudicate(r.version, r.code, r.title)[0] for _, r in cand.iterrows()]
cand["reason"] = [adjudicate(r.version, r.code, r.title)[1] for _, r in cand.iterrows()]

# ---------------------------------------------------------------- explicit near-miss adjudications
# These do NOT contain 'cirrhos' in the title but are the exact candidates the
# previous audit wrongly included, plus their useful siblings. Recorded so the
# exclusion is documented rather than implicit.
NEAR_MISSES = [
    (10, "K702", "Alcoholic fibrosis and sclerosis of liver", False,
     "FIBROSIS/SCLEROSIS, not cirrhosis -- excluded from the primary phenotype"),
    (10, "K704", "Alcoholic hepatic failure", False,
     "HEPATIC FAILURE, not cirrhosis -- a patient with only K70.4 does not enter the "
     "primary cohort; if K70.3 is also coded the patient enters on K70.3"),
    (10, "K7040", "Alcoholic hepatic failure without coma", False, "hepatic failure, not cirrhosis"),
    (10, "K7041", "Alcoholic hepatic failure with coma", False, "hepatic failure, not cirrhosis"),
    (10, "K700", "Alcoholic fatty liver", False, "fatty liver, not cirrhosis"),
    (10, "K701", "Alcoholic hepatitis", False, "hepatitis, not cirrhosis"),
    (10, "K7010", "Alcoholic hepatitis without ascites", False, "hepatitis, not cirrhosis"),
    (10, "K7011", "Alcoholic hepatitis with ascites", False,
     "hepatitis with ascites is NOT cirrhosis; ascites alone does not define cirrhosis"),
    (10, "K709", "Alcoholic liver disease, unspecified", False, "unspecified, not cirrhosis"),
    (10, "K740", "Hepatic fibrosis", False, "fibrosis, not cirrhosis"),
    (10, "K7400", "Hepatic fibrosis, unspecified", False, "fibrosis, not cirrhosis"),
    (10, "K7401", "Hepatic fibrosis, early fibrosis", False, "fibrosis, not cirrhosis"),
    (10, "K7402", "Hepatic fibrosis, advanced fibrosis", False,
     "even ADVANCED fibrosis is not cirrhosis -- excluded"),
    (10, "K741", "Hepatic sclerosis", False, "sclerosis, not cirrhosis"),
    (10, "K742", "Hepatic fibrosis with hepatic sclerosis", False, "fibrosis/sclerosis, not cirrhosis"),
    (9, "5710", "Alcoholic fatty liver", False, "fatty liver, not cirrhosis"),
    (9, "5711", "Acute alcoholic hepatitis", False, "hepatitis, not cirrhosis"),
    (9, "5713", "Alcoholic liver damage, unspecified", False, "unspecified, not cirrhosis"),
    (9, "57140", "Chronic hepatitis, unspecified", False, "hepatitis, not cirrhosis"),
    (9, "57142", "Autoimmune hepatitis", False, "hepatitis, not cirrhosis"),
    (9, "57149", "Other chronic hepatitis", False, "hepatitis, not cirrhosis"),
    (9, "5718", "Other chronic nonalcoholic liver disease", False, "not cirrhosis"),
    (9, "5719", "Unspecified chronic liver disease without mention of alcohol", False,
     "unspecified chronic liver disease, not cirrhosis"),
]
nm = pd.DataFrame(NEAR_MISSES, columns=["version", "code", "title", "include_primary", "reason"])
cand = pd.concat([cand, nm], ignore_index=True).drop_duplicates(["version", "code"])

log("\n" + "=" * 100)
log("ADJUDICATED CODE SET")
log("=" * 100)
inc = cand[cand.include_primary]
exc = cand[~cand.include_primary]
log(f"\n  INCLUDE (primary strict cirrhosis): {len(inc)} codes")
for _, r in inc.sort_values(["version", "code"]).iterrows():
    log(f"    v{r.version}  {r.code:<8} {r.title}")
log(f"\n  EXCLUDE (near misses explicitly adjudicated): {len(exc)} codes")
for _, r in exc.sort_values(["version", "code"]).iterrows():
    log(f"    v{r.version}  {r.code:<8} {r.title:<52} {r.reason}")

# ---------------------------------------------------------------- frequencies per database
log("\n" + "=" * 100)
log("FREQUENCIES IN EACH DATABASE")
log("=" * 100)
inc_codes = set(inc.code.str.strip())
v9 = {c for v, c in zip(inc.version, inc.code) if v == 9}
v10 = {c for v, c in zip(inc.version, inc.code) if v == 10}
log(f"  include v9 : {sorted(v9)}")
log(f"  include v10: {sorted(v10)}")

# MIMIC: codes stored WITHOUT dots
with conn("mimiciv3") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT icd_version, icd_code, count(DISTINCT hadm_id) AS n_adm,
                   count(DISTINCT subject_id) AS n_pat
            FROM mimiciv_hosp.diagnoses_icd
            WHERE replace(icd_code,'.','') = ANY(%s)
            GROUP BY 1,2
        """, (sorted(inc_codes),))
        mim_freq = pd.DataFrame(cur.fetchall(), columns=["version", "code", "mimic_adm",
                                                         "mimic_pat"])
# nwICU: ICD-10 without dots
with conn("nwicu") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT icd_code, count(DISTINCT hadm_id) AS n_adm, count(DISTINCT subject_id) AS n_pat
            FROM public.diagnoses_icd
            WHERE replace(icd_code,'.','') = ANY(%s)
            GROUP BY 1
        """, (sorted(inc_codes),))
        nw_freq = pd.DataFrame(cur.fetchall(), columns=["code_nw", "nwicu_adm", "nwicu_pat"])
# eICU: ICD-9 with dots and ICD-10 with dots, comma/semicolon separated
with conn("eicu") as c:
    with c.cursor() as cur:
        cur.execute("""
            SELECT icd9code, count(DISTINCT patientunitstayid) AS n
            FROM eicu_crd.diagnosis WHERE icd9code <> '' GROUP BY 1
        """)
        rows = cur.fetchall()
eicu_count = {}
import re as _re
for code_string, n in rows:
    for tok in _re.split(r"[,\s;]+", code_string):
        k = tok.strip().replace(".", "").upper()
        if k:
            eicu_count[k] = eicu_count.get(k, 0) + n

mim_freq["key"] = mim_freq.code.str.replace(".", "", regex=False).str.upper()
mim_freq["nwicu_adm"] = mim_freq.key.map(nw_freq.set_index("code_nw").nwicu_adm)
mim_freq["nwicu_pat"] = mim_freq.key.map(nw_freq.set_index("code_nw").nwicu_pat)
mim_freq["eicu_stays"] = mim_freq.key.map(eicu_count)

dic = cand.merge(
    mim_freq[["version", "key", "mimic_adm", "mimic_pat", "nwicu_adm", "nwicu_pat", "eicu_stays"]],
    left_on=["version", cand.code.str.replace(".", "", regex=False).str.upper()],
    right_on=["version", "key"], how="left").drop(columns=["key"], errors="ignore")
dic = dic.rename(columns={"version": "icd_version", "code": "code",
                          "title": "official_description"})
dic = dic[["code", "icd_version", "official_description", "include_primary", "reason",
           "mimic_adm", "mimic_pat", "eicu_stays", "nwicu_adm", "nwicu_pat"]]
dic = dic.sort_values(["include_primary", "icd_version", "code"], ascending=[False, True, True])

log("\n  per-code frequency table (admissions / stays):")
log(f"  {'code':<8}{'v':>3}{'include':>9}{'MIMIC adm':>11}{'eICU stays':>12}{'nwICU adm':>11}")
for _, r in dic.iterrows():
    log(f"  {r.code:<8}{int(r.icd_version):>3}{str(bool(r.include_primary)):>9}"
        f"{('' if pd.isna(r.mimic_adm) else int(r.mimic_adm)):>11}"
        f"{('' if pd.isna(r.eicu_stays) else int(r.eicu_stays)):>12}"
        f"{('' if pd.isna(r.nwicu_adm) else int(r.nwicu_adm)):>11}")

with pd.ExcelWriter(os.path.join(TABLES, "cirrhosis_code_dictionary.xlsx"), engine="openpyxl") as xl:
    dic.to_excel(xl, sheet_name="code_dictionary", index=False)
    inc[["version", "code", "title", "reason"]].to_excel(xl, sheet_name="included", index=False)
    exc[["version", "code", "title", "reason"]].to_excel(xl, sheet_name="excluded_near_miss",
                                                         index=False)
log(f"\n  wrote FINAL_REBUILD/cirrhosis_code_dictionary.xlsx ({len(dic)} rows)")

# ---------------------------------------------------------------- the phenotype rule, machine-readable
RULE = {
    "icd10_include": sorted({c for v, c in zip(inc.version, inc.code) if v == 10}),
    "icd9_include": sorted({c for v, c in zip(inc.version, inc.code) if v == 9}),
    "explicitly_excluded": sorted({c for v, c in zip(nm.version, nm.code)}),
    "age_min": 18,
}
with open(os.path.join(DATA, "cirrhosis_phenotype_rule.json"), "w", encoding="utf-8") as fh:
    import json
    json.dump(RULE, fh, indent=2)
log("\n  machine-readable rule written to cirrhosis_phenotype_rule.json")
log(f"    ICD-10 include : {RULE['icd10_include']}")
log(f"    ICD-9  include : {RULE['icd9_include']}")

with open(os.path.join(LOGS, "PHASE_0A_phenotype.log"), "w", encoding="utf-8") as fh:
    fh.write(LOG.getvalue())
log("\nGATE 0A code adjudication DONE")
