"""MANUSCRIPT vs CLAIM LOCK -- automated compliance check.

MANUSCRIPT_CLAIMS.md is the highest claim authority. This script checks the drafted
manuscript against every DO NOT CLAIM entry and every required-terminology rule, so a
prohibited phrasing cannot reach submission unnoticed.

Run:  python manuscript_claim_compliance.py
"""
from __future__ import annotations

import io
import os
import re
import sys

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

MS_RAW = io.open(os.path.join(FR, "MANUSCRIPT_v3.2_EN.md"), encoding="utf-8").read()
CN_RAW = io.open(os.path.join(FR, "MANUSCRIPT_v3.2_CN.md"), encoding="utf-8").read()
CLAIMS = io.open(os.path.join(FR, "MANUSCRIPT_CLAIMS.md"), encoding="utf-8").read()


def flatten(t: str) -> str:
    """Normalise for pattern matching.

    Removes emphasis markers and collapses all whitespace to single spaces, so a
    required phrase is still found when the manuscript wraps it across lines or sets
    part of it in bold. Without this, a correct sentence reads as 'absent'.
    """
    t = t.replace("**", "").replace("*", "")
    t = re.sub(r"[`_]", "", t)
    return re.sub(r"\s+", " ", t)


MS = flatten(MS_RAW)
CN = flatten(CN_RAW)

OUT = io.StringIO()


def log(m=""):
    m = str(m).encode("ascii", "replace").decode("ascii")
    print(m)
    OUT.write(m + "\n")


violations, checks = [], []

# Negations that make a prohibited phrase acceptable: the manuscript is allowed to
# say it is NOT validated for early prediction; what is forbidden is claiming it is.
NEGATORS = ("not ", "no ", "never ", "cannot ", "cannot be ", "is not", "was not",
            "neither ", "nor ", "without ", "fails to ", "does not", "do not",
            "did not", "must not", "should not", "do not describe", "not described",
            "not claim", "we do not", "does not demonstrate", "did not demonstrate")


def negated(text: str, start: int, end: int, window: int = 90) -> bool:
    """Is the matched phrase negated, either just before or just after it?

    Both directions are needed. A sentence such as "we do not describe it as
    significantly better" places the negation *inside* the match when the pattern
    begins at an earlier word ("MELD ... and do not describe it as significantly
    better"), so a pre-match window alone would miss it.
    """
    before = text[max(0, start - window):start].lower()
    inside = text[start:end].lower()
    after = text[end:end + window].lower()
    return any(n in before or n in inside or n in after for n in NEGATORS)


def forbid(label: str, pattern: str, text: str = MS, where: str = "EN"):
    """A phrase that must NOT appear in a claiming voice."""
    real = []
    for m in re.finditer(pattern, text, re.I):
        if not negated(text, m.start(), m.end()):
            real.append(m.group(0))
    checks.append((label, not real, f"{len(real)} unnegated hit(s)"))
    if real:
        for h in sorted(set(real)):
            violations.append(f"{label}: {where} asserts '{h}'")


def require(label: str, pattern: str, text: str = MS, where: str = "EN"):
    """A phrase or value that MUST appear."""
    hit = re.search(pattern, text, re.I)
    checks.append((label, bool(hit), "present" if hit else "ABSENT"))
    if not hit:
        violations.append(f"{label}: {where} missing")


log("=" * 100)
log("MANUSCRIPT v1 vs MANUSCRIPT_CLAIMS.md COMPLIANCE CHECK")
log("=" * 100)

# ---------------------------------------------------------------- D1-D12
forbid("D1 severe/marked drift", r"severe\s+(?:calibration\s+)?drift|marked\s+miscalibration")
forbid("D2 percentage over-prediction", r"\d+\s*%\s*over[\s-]?predict|over[\s-]?predict\w*\s+by\s+\d+")
forbid("D2b '30%'", r"\b30\s?%")
forbid("D3 per-hospital slope 0.14", r"slope\w*[^.\n]{0,40}0\.14\b|0\.14\b[^.\n]{0,40}slope")
forbid("D4 restricted case mix attenuates slope",
       r"restricted case mix[^.\n]{0,60}attenuat|attenuat\w*[^.\n]{0,60}case mix")
forbid("D5 APACHE", r"APACHE")
forbid("D6 lab scores transport better",
       r"laborator\w+ scores? transport better|transport better than physio")
forbid("D7 significantly better than MELD",
       r"significant\w*\s+(?:better|outperform)\w*[^.\n]{0,60}MELD|"
       r"MELD[^.\n]{0,40}significant\w*\s+better")
forbid("D8 validated for 0-6 h prediction",
       r"validated for (?:early|very early|0-6)")
forbid("D9 single intercept sufficient everywhere",
       r"single (?:local )?intercept[^.\n]{0,40}(?:sufficien|guarantee|enough)")
forbid("D10 unqualified both transport",
       r"both calibration and discrimination transport\b")
forbid("D11 superseded tree cited", r"01_transportability")
forbid("D12 changed to improve results",
       r"changed[^.\n]{0,40}to improve (?:the )?results|tuned to improve")

# ---------------------------------------------------------------- required wording
require("outcome stated as in-hospital mortality", r"in-hospital mortality")
require("outcome window explicit", r"first 24 hours?(?: after ICU admission)?")
require("O/E defined as observed/expected", r"observed[- ](?:to|/)[- ]expected|observed deaths divided by expected")
require("155 hospitals", r"\b155\b")
require("no detectable heterogeneity phrasing",
        r"no detectable between-hospital heterogeneity|absence of\s+\*{0,2}detectable")
require("intercept-only recalibration claim",
        r"intercept-only (?:recalibration|update)[^.\n]{0,80}calibration-in-the-large")
require("accuracy NOT demonstrated", r"(?:not|did not)[^.\n]{0,60}improve[^.\n]{0,30}(?:overall )?accuracy|without[^.\n]{0,40}improving overall")
require("numerically higher than MELD", r"numerically higher")
require("fourteen predictor terms -> twelve predictors wording",
        r"12 (?:clinical )?predictors?\b")
require("fifteen coefficients", r"15 coefficients")
require("repeated admissions wording",
        r"repeated admissions did not materially affect discrimination but did affect calibration-in-the-large")
require("a priori disclaimer", r"not claimed to have been fully|should not be described as fully")
# The ethics and code-availability content changed in v3.1: the authors supplied the
# ethics approval, so the old "VERIFY ETHICS STATEMENT" placeholder is correctly gone,
# and the code-availability placeholder was reworded. What must always hold is that the
# manuscript states the ethics determination, that the approval number is present, and
# that no informed-consent waiver is asserted without author confirmation.
require("ethics determination stated",
        r"Ethics Committee of Xingtai People's Hospital")
require("ethics approval number stated", r"2025\[327\]")
require("consent waiver not asserted without confirmation",
        r"AUTHOR TO CONFIRM WHETHER INFORMED CONSENT WAS WAIVED")
require("code availability policy flagged for the authors",
        r"CODE AVAILABILITY POLICY TO BE SELECTED BY THE AUTHORS")
require("funding stated", r"2020ZC376")
require("conflict of interest stated", r"declare no competing interests")
require("nwICU secondary/exploratory", r"secondary")

# ---------------------------------------------------------------- hospital count
# The prohibited claim is presenting 208 as the number of centres in THIS validation.
# Stating 208 as the eICU-CRD database total is correct and in fact required, because
# the point of the distinction is that only 155 of those hospitals contributed a cohort.
# The patterns therefore target 208 used as the study's own centre count: within a short
# span of words that make it this study's cohort rather than the source database.
forbid("208 not used as this study's centre count",
       r"208\s+(?:eICU\s+)?hospitals?[^.]{0,70}"
       r"(?:contribut|participat|external valid|validation cohort|in this study|our cohort)")
forbid("208 not used as this study's centre count (reversed word order)",
       r"(?:external valid|our cohort|contributing hospitals?)[^.]{0,70}"
       r"208\s+(?:eICU\s+)?hospitals?")
require("208 stated as the database total", r"208\s+hospitals")

# ---------------------------------------------------------------- CN mirror
forbid("CN: 24-hour mortality model", r"24\s*小时死亡率模型", CN, "CN")
forbid("CN: severe drift", r"严重校准漂移", CN, "CN")
forbid("CN: significantly better", r"显著优于", CN, "CN")
forbid("CN: three-centre study", r"三中心研究", CN, "CN")
forbid("CN: 208 used as this study's centre count",
       r"208 家医院[^。]{0,40}(?:贡献|参与|外部验证|本研究的队列)")
require("CN: 208 stated as the database total", r"208 家医院", CN, "CN")
forbid("CN: no heterogeneity at all", r"没有任何异质性", CN, "CN")
require("CN: in-hospital mortality", r"院内死亡", CN, "CN")
require("CN: 155 hospitals", r"155 家医院", CN, "CN")

log("")
for label, ok, detail in checks:
    log(f"  [{'PASS' if ok else 'FAIL'}] {label:<52} {detail}")
log("-" * 100)
n_ok = sum(1 for _, ok, _ in checks if ok)
log(f"  {n_ok}/{len(checks)} checks passed")

if violations:
    log("\n  VIOLATIONS:")
    for v in violations:
        log(f"    - {v}")
    verdict = "NOT READY - claim-lock violations must be fixed"
else:
    verdict = "READY - manuscript complies with the claim lock"

log("")
log(f"  VERDICT: {verdict}")

with io.open(os.path.join(FR, "MANUSCRIPT_CLAIM_COMPLIANCE.md"), "w",
             encoding="utf-8") as fh:
    fh.write("# MANUSCRIPT v1 - CLAIM-LOCK COMPLIANCE\n\n```\n" + OUT.getvalue() +
             "```\n")
prov.announce("manuscript_claim_compliance")
print(f"\nwrote MANUSCRIPT_CLAIM_COMPLIANCE.md")
if violations:
    raise SystemExit(1)
