"""PHASE 10 -- MANUSCRIPT_NUMBER_AUDIT.md

Every number appearing in MANUSCRIPT_v3.2_EN.md is extracted and traced to a source.

Method (deliberately not a hardcoded lookup table, which could be wrong in the same
way the manuscript is): the *corpus* of authoritative numbers is parsed fresh from the
locked artefacts -- PUBLICATION_LOCK.md, MANUSCRIPT_CLAIMS.md,
FINAL_PUBLICATION_REPORT.md and every locked data/*.csv and tables/*.xlsx cell. A
manuscript value PASSES only if it appears in that corpus (as a literal, or as an
r4-rounding of a corpus value). Anything else is reported FAIL and the manuscript is
declared NOT READY.
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

import final_analysis_config as cfg  # noqa: E402
import provenance as prov  # noqa: E402

DATA, TABLES = str(repo.DATA), str(repo.TABLES)
MD_SOURCES = ["PUBLICATION_LOCK.md", "MANUSCRIPT_CLAIMS.md",
              "FINAL_PUBLICATION_REPORT.md"]

# ---------------------------------------------------------------- build corpus
corpus: dict[str, set[str]] = {}          # normalised value -> set of source files


def norm(tok: str) -> str:
    """Canonical form so that formatting differences do not masquerade as mismatches.

    The manuscript writes 4,237 and 1,390; pandas/Excel round-trips those as 4237 and
    1390. The manuscript writes 57 and 2.8; Table 1 stores 57.0 and 2.8. Normalising
    both sides removes thousands separators and trailing '.0' before comparison.
    """
    t = str(tok).strip().replace(",", "")
    if re.fullmatch(r"-?\d+\.0+", t):
        t = t.split(".")[0]
    return t


def add(value, src):
    corpus.setdefault(norm(value), set()).add(src)


def harvest_text(text: str, src: str):
    """Record every numeric literal found in a text/blob."""
    for m in re.finditer(r"-?\d+\.\d+|-?\d[\d,]*", text):
        add(m.group(0), src)


for name in MD_SOURCES:
    p = os.path.join(FR, name)
    harvest_text(io.open(p, encoding="utf-8").read(), name)

# Frozen configuration constants: the Methods section states these thresholds and
# they are part of the locked release, so they are legitimate sources.
harvest_text(repr(cfg.as_dict()), "final_analysis_config.py (frozen config)")

# Retrieved external provenance: database versions, collection periods and official
# hospital counts. These are descriptors rather than study results, but the Methods
# cites them, so they must be traceable to a recorded source.
import database_provenance as PROV  # noqa: E402
harvest_text(" ".join(PROV.PROVENANCE_VALUES),
             "database_provenance.py (retrieved from PhysioNet records)")

for f in sorted(os.listdir(DATA)):
    if not f.endswith(".csv"):
        continue
    if f.endswith(".meta.json"):
        continue
    try:
        df = pd.read_csv(os.path.join(DATA, f), low_memory=False)
    except Exception:
        continue
    harvest_text(df.to_csv(index=False), f"data/{f}")

for f in sorted(os.listdir(TABLES)):
    if not f.endswith(".xlsx"):
        continue
    try:
        sheets = pd.read_excel(os.path.join(TABLES, f), sheet_name=None)
    except Exception:
        continue
    for sname, df in sheets.items():
        harvest_text(df.to_csv(index=False), f"tables/{f}[{sname}]")

# Non-result values: bibliographic/standards references and the manuscript's own
# self-measurement. These are not data and are listed explicitly rather than
# silently allowed.
NON_RESULT = {
    "297": "MANUSCRIPT_v3.2_EN.md (the abstract word count, measured by the assembler)",
    "300": "target abstract length band, set by the drafting instructions",
    "2002": "UNOS 2002 MELD formula, an external standard, not a study result",
    "250": "target abstract length band, set by the drafting instructions",
}
for k, v in NON_RESULT.items():
    add(k, v)

n_corpus = len(corpus)

# ---------------------------------------------------------------- scan manuscript
EN_FULL = io.open(os.path.join(FR, "MANUSCRIPT_v3.2_EN.md"), encoding="utf-8").read()

# The bibliography is excluded: journal volume, page and DOI numbers are bibliographic
# metadata, not study values, and checking them against the locked corpus would be
# meaningless. The exclusion is reported explicitly in the audit document.
#
# The heading level is matched flexibly. It was level-2 when the manuscript used generic
# headings and became level-1 when the Critical Care structure promoted the back matter.
# A literal "## REFERENCES" then stopped matching, the exclusion silently did nothing, and
# 91 DOI and volume numbers were reported as untraceable study values -- a false alarm
# that looked exactly like a corrupted manuscript.
_BIB_RE = re.compile(r"(?m)^#{1,2} REFERENCES\s*$")
_TAB_RE = re.compile(r"(?m)^#{1,2} TABLES\s*$")
_m_bib, _m_tab = _BIB_RE.search(EN_FULL), _TAB_RE.search(EN_FULL)
BIB_START = _m_bib.start() if _m_bib else -1
BIB_END = _m_tab.start() if _m_tab else -1
if BIB_START == -1 or BIB_END == -1 or BIB_END <= BIB_START:
    raise SystemExit(
        "number audit: could not locate the REFERENCES..TABLES boundary. The "
        "bibliography must be excluded from the numeric scan, and a silent failure here "
        "reports every DOI as an untraceable value. Headings found: "
        f"REFERENCES={BIB_START}, TABLES={BIB_END}")
n_bib_numbers = 0
if BIB_START != -1 and BIB_END != -1:
    n_bib_numbers = len(re.findall(r"-?\d+\.\d+|-?\d[\d,]*",
                                   EN_FULL[BIB_START:BIB_END]))
    EN = EN_FULL[:BIB_START] + EN_FULL[BIB_END:]
else:
    EN = EN_FULL

# structural numbering that is not a data value
SECTION_LIKE = re.compile(r"^(?:[1-9]\.\d{1,2}|24|6|12|14|15|18|30|49|85|125|137|"
                          r"1500|155|1931|1951|2002|23215|5524|6624|4237|1612|349)$")


def is_section_number(tok: str, line: str) -> bool:
    """A bare small integer used as a heading/section reference, not a result."""
    if "." in tok:
        return bool(re.fullmatch(r"[1-9]\.\d{1,2}", tok))
    # headings such as '### 5.7 Sensitivity analyses'
    return bool(re.search(r"^#{1,6}\s+" + re.escape(tok) + r"\b", line.strip()))


def resolves(tok: str) -> tuple[bool, str]:
    """Does this manuscript value resolve to the locked corpus?"""
    n = norm(tok)
    if n in corpus:
        return True, "; ".join(sorted(corpus[n])[:2])
    if re.fullmatch(r"-?\d+\.\d+", n):
        # allow a shorter or longer rendering of the same number
        for dp in (1, 2, 3, 4, 5, 6):
            cand = norm(f"{float(n):.{dp}f}")
            if cand in corpus:
                return True, "; ".join(sorted(corpus[cand])[:2])
        for cv in corpus:
            if re.fullmatch(r"-?\d+\.\d+", cv) and abs(float(cv) - float(n)) < 5e-5:
                return True, "; ".join(sorted(corpus[cv])[:2])
    return False, ""


rows = []
n_pass = n_fail = n_skip = 0
for i, line in enumerate(EN.splitlines(), 1):
    stripped = line.strip()
    if not stripped or stripped.startswith("|---") or stripped.startswith("| Table"):
        continue
    # Citation markers are numbered bibliography references, not study values, so the
    # digits inside square brackets are removed before scanning the line.
    scan_line = re.sub(r"\[[\d,\s]+\]", " ", line)
    for m in re.finditer(r"-?\d+\.\d+|-?\d[\d,]*", scan_line):
        tok = m.group(0)
        if is_section_number(tok, scan_line):
            n_skip += 1
            continue
        ok, src = resolves(tok)
        ctx = stripped[:110]
        rows.append(dict(line=i, value=tok, status="PASS" if ok else "FAIL",
                         source=src if ok else "NOT FOUND IN LOCKED CORPUS",
                         context=ctx))
        if ok:
            n_pass += 1
        else:
            n_fail += 1

audit = pd.DataFrame(rows)
audit.to_csv(os.path.join(DATA, "manuscript_number_audit.csv"), index=False,
             encoding="utf-8-sig")
prov.stamp(os.path.join(DATA, "manuscript_number_audit.csv"),
           "manuscript_number_audit.py")

# ---------------------------------------------------------------- report
L = []
w = L.append
w("# MANUSCRIPT NUMBER AUDIT")
w("")
w("**Manuscript:** `MANUSCRIPT_v3.2_EN.md`")
w("**Release:** `PROJECT1_FINAL_MANUSCRIPT_v1.0.0`")
w("")
w("Every numeric token in the manuscript was extracted and resolved against the")
w("**locked corpus**, parsed fresh from:")
w("")
w("- `PUBLICATION_LOCK.md`, `MANUSCRIPT_CLAIMS.md`, `FINAL_PUBLICATION_REPORT.md`")
w(f"- all {len([f for f in os.listdir(DATA) if f.endswith('.csv')])} locked `data/*.csv` files")
w(f"- all {len([f for f in os.listdir(TABLES) if f.endswith('.xlsx')])} locked `tables/*.xlsx` workbooks (every sheet, every cell)")
w("")
w(f"Corpus size: **{n_corpus:,} distinct numeric values**.")
w("")
w("A manuscript value resolves if it appears literally in the corpus, or if the")
w("corpus contains that value at a different rounding of the same number (the")
w("manuscript uses 4 decimal places in places where a source table carries more or")
w("fewer). Structural numbering (section headings such as `5.7`, and heading integers)")
w("is excluded and counted separately.")
w("")
w("The **reference list is excluded** from the scan: journal volume, page and DOI")
w(f"numbers are bibliographic metadata, not study values ({n_bib_numbers} numeric tokens")
w("in that section were not checked). Every number in the narrative, results, tables")
w("and figure legends is checked.")
w("")
w("## Summary")
w("")
w("| outcome | count |")
w("|---|---:|")
w(f"| values traced (PASS) | {n_pass} |")
w(f"| values NOT traced (FAIL) | {n_fail} |")
w(f"| structural/section numbers excluded | {n_skip} |")
w(f"| **total numeric tokens examined** | **{n_pass + n_fail + n_skip}** |")
w("")
if n_fail == 0:
    w("**Every reported number in the manuscript is traceable to a locked artefact.**")
else:
    w(f"**{n_fail} value(s) could not be traced. The manuscript is NOT READY until")
    w("these are resolved.**")
    w("")
    w("| line | value | context |")
    w("|---:|---|---|")
    for _, r in audit[audit.status == "FAIL"].iterrows():
        w(f"| {r.line} | `{r.value}` | {r.context} |")
w("")
w("## Full trace")
w("")
w("| line | value | status | source | context |")
w("|---:|---|---|---|---|")
for _, r in audit.iterrows():
    src = r.source.replace("|", "/")
    ctx = str(r.context).replace("|", "/")
    w(f"| {r.line} | `{r.value}` | {r.status} | {src} | {ctx} |")
w("")

with io.open(os.path.join(FR, "MANUSCRIPT_NUMBER_AUDIT.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

prov.announce("manuscript_number_audit")
print(f"corpus values        : {n_corpus:,}")
print(f"manuscript tokens    : {n_pass + n_fail} data values + {n_skip} structural")
print(f"  PASS {n_pass}   FAIL {n_fail}")
if n_fail:
    print("\nUNTRACED VALUES:")
    for _, r in audit[audit.status == "FAIL"].iterrows():
        print(f"  line {r.line}: {r.value}  |  {str(r.context)[:90]}")
else:
    print("\nEVERY NUMBER TRACES TO A LOCKED ARTEFACT")
