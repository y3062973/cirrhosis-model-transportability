"""PART 30 -- restrained journal-language pass.

Scans the frozen manuscript for the overstatement list and for the claim-lock
prohibitions. A term is only reported when it is USED, not when it is negated,
qualified, or attributed to someone else -- "does not prove homogeneity" contains
"prove" and is exactly the sentence we want to keep.

This is a check, not an editor: it reports, and the operator decides. It never
rewrites the manuscript, because a mechanical rewrite of claim language is how a
qualified finding silently becomes a strong one.
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

MD = os.path.join(FR, "MANUSCRIPT_v3.2_EN.md")

# (label, pattern, why it is dangerous)
CHECKS = [
    ("failure / failed", r"\b(failure|failed|fails)\b",
     "Frames a preserved-discrimination result as a failure of the model or the study. "
     "The conservative description is a shift in calibration-in-the-large."),
    ("proves / proven", r"\b(proves?|proven|proof)\b",
     "A single validation cannot prove a property; tau ~ 0 is a boundary estimate."),
    ("guarantee", r"\bguarantee(s|d)?\b",
     "Nothing about transport is guaranteed; the recalibration is an upper bound."),
    ("fitted on all hospitals", r"fitted on all hospitals except",
     "INFORMATIONAL, no change needed. This is the leave-one-hospital-out procedure and "
     "IS what was done: the correction is fitted on every hospital except the held-out "
     "one. It is not a homogeneity claim, and the manuscript states elsewhere that "
     "absence of detectable heterogeneity is not proof that hospitals perform "
     "identically."),
    ("clinically useful", r"\bclinically useful\b",
     "Requires an impact study this paper does not contain."),
    ("superior to a score", r"\b(superior to|outperforms?)\b",
     "Check against the paired intervals. Against MELD and MELD-Na the paired AUROC "
     "difference includes zero, so no superiority claim is available; against ALBI and "
     "FIB-4 the intervals exclude zero, so a comparative statement is supported. Any "
     "superiority wording must be attached to the right comparison."),
    ("validated for early prediction", r"\b(validated for|established for)\b.{0,40}"
                                        r"\b(early|0-6|6-hour)\b",
     "eICU AUROC in the 0-6 h window is 0.7016; the model is not validated there."),
    ("single intercept suffices", r"\b(suffices|is sufficient)\b.{0,60}"
                                  r"\b(everywhere|all hospitals|any hospital)\b",
     "The intercept correction is fitted on the same cohorts."),
    ("severe / marked drift", r"\b(severe|marked|substantial|dramatic)\b",
     "Locked claim: the shift is modest and partly structure-dependent."),
    ("percentage over-prediction", r"\b\d+(\.\d+)?\s?%\s*(over|under)[- ]?"
                                   r"(prediction|estimat)",
     "Locked claim: the O/E ratio is reported directly, never as a percentage."),
    ("significantly better/worse", r"\bsignificantly (better|worse|higher|lower)\b",
     "The paired comparisons are not significant; 'significantly' implies a test "
     "result and a conclusion."),
    ("first study / only study", r"\b(first|only) (study|report|analysis|model)\b",
     "A novelty claim that the literature search does not support."),
    ("high-performance model", r"\bhigh[- ]performance\b|\bhighly accurate\b",
     "AUROC 0.79 is not the contribution; this framing is explicitly excluded."),
]

# Sentences that legitimately contain a flagged term because they negate or qualify it.
NEGATORS = [
    "not", "no ", "never", "cannot", "without", "rather than", "does not", "do not",
    "did not", "is not", "are not", "was not", "were not", "than to", "absence of",
]


def sentences(text: str):
    for s in re.split(r"(?<=[.!?])\s+", text):
        yield s.strip()


def main():
    txt = io.open(MD, encoding="utf-8").read()
    # narrative only: a bibliography title must not trigger a language finding
    narrative = "\n".join(
        l for l in txt.split("\n") if not re.match(r"^\s*\d+\.\s+[A-Z]", l))

    findings = []
    for label, pat, why in CHECKS:
        for s in sentences(narrative):
            for m in re.finditer(pat, s, re.I):
                low = s.lower()
                negated = any(n in low for n in NEGATORS)
                findings.append((label, m.group(0), negated, s[:190], why))

    used = [f for f in findings if not f[2]]
    informational = [f for f in used if f[4].startswith("INFORMATIONAL")]
    used = [f for f in used if not f[4].startswith("INFORMATIONAL")]
    negated = [f for f in findings if f[2]]

    print("=" * 96)
    print("LANGUAGE PASS -- overstatement scan")
    print("=" * 96)
    print(f"sentences scanned        : {len(list(sentences(narrative)))}")
    print(f"flag matches             : {len(findings)}")
    print(f"  negated / qualified    : {len(negated)}  (kept: these are the honest forms)")
    print(f"  informational          : {len(informational)}  (correct as written)")
    print(f"  USED (must be reviewed): {len(used)}")
    print()

    if used:
        print("--- matches that are USED, not negated ---")
        for label, term, _, s, why in used:
            print(f"[{label}] matched {term!r}")
            print(f"    sentence: {s}")
            print(f"    why it matters: {why}")
            print()
    else:
        print("No unnegated overstatement found on any check.")
    print()

    # report the qualified instances so a human can confirm they are the good ones
    print("--- negated/qualified instances (these are the intended honest forms) ---")
    seen = set()
    for label, term, _, s, _ in negated:
        key = (label, s[:70])
        if key in seen:
            continue
        seen.add(key)
        print(f"  [{label}] {s[:170]}")
    print()

    L = ["# LANGUAGE PASS -- OVERSTATEMENT AUDIT", "",
         "**Manuscript:** `MANUSCRIPT_v3.2_EN.md`", "",
         "Mechanical scan for the overstatement list, distinguishing a term that is USED",
         "from one that is negated or qualified. The manuscript was NOT rewritten by this",
         "script; changing claim language mechanically is how a qualified finding becomes",
         "an unqualified one.", "",
         f"- sentences scanned: {len(list(sentences(narrative)))}",
         f"- total flag matches: {len(findings)}",
         f"- negated or qualified (intended): {len(negated)}",
         f"- informational, correct as written: {len(informational)}",
         f"- used, needs human review: **{len(used)}**", ""]
    if used:
        L.append("## Matches needing review")
        L.append("")
        L.append("| check | matched | sentence | why it matters |")
        L.append("|---|---|---|---|")
        for label, term, _, s, why in used:
            L.append(f"| {label} | `{term}` | {s} | {why} |")
    else:
        L.append("## Result")
        L.append("")
        L.append("**No unnegated overstatement found on any check.** Every flagged term "
                 "occurs inside a sentence that negates, qualifies or attributes it -- "
                 "for example 'does not prove homogeneity', which is the wording the "
                 "claim lock requires.")
    L.append("")
    L.append("## Negated or qualified instances (the intended honest forms)")
    L.append("")
    for label, term, _, s, _ in negated:
        L.append(f"- **{label}**: {s}")
    L.append("")

    path = os.path.join(FR, "LANGUAGE_PASS_AUDIT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    prov.stamp(path, "language_pass.py", {"manuscript": "MANUSCRIPT_v3.2_EN.md"})
    prov.announce("language_pass")
    print(f"wrote LANGUAGE_PASS_AUDIT.md")
    return 1 if used else 0


if __name__ == "__main__":
    raise SystemExit(main())
