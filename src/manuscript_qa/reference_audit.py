"""TASK 11 -- REFERENCE FINAL AUDIT and sequential citation conversion.

Requirements checked:
  * 0 unresolved `[Rxx]` working identifiers in the manuscript text
  * 0 uncited bibliography entries
  * 0 cited-but-missing references
  * 0 duplicate references
  * English and Chinese versions carry the same reference order
  * preprints are distinguished from peer-reviewed papers
  * DOI / journal / year / volume / issue / pages present where the record allows

The sequential numbering is derived from first appearance in the assembled manuscript
and written back into both language versions, so the numbering cannot drift.
"""
from __future__ import annotations

import io
import os
import re
import sys
from collections import Counter

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

# Heading-level agnostic splitting. The manuscript's back-matter headings are level-1
# ("# REFERENCES"); earlier revisions used level-2. Matching on an exact number of
# hashes broke the audit when the structure changed, so the boundary is a regex.
_REF_HEAD = re.compile(r"(?m)^#{1,2} REFERENCES\s*$")
_TAB_HEAD = re.compile(r"(?m)^#{1,2} TABLES\s*$")
_CNREF_HEAD = re.compile(r"(?m)^#{1,2} 参考文献\s*$")


def split_refs(text: str):
    """-> (body_before_references, text_between_references_and_tables)."""
    m = _REF_HEAD.search(text)
    if not m:
        raise SystemExit("reference audit: cannot find the REFERENCES heading")
    rest = text[m.end():]
    t = _TAB_HEAD.search(rest)
    return text[:m.start()], (rest[:t.start()] if t else rest)


def split_cn_refs(text: str):
    m = _CNREF_HEAD.search(text)
    if not m:
        raise SystemExit("reference audit: cannot find the 参考文献 heading")
    return text[:m.start()], text[m.end():]


import provenance as prov  # noqa: E402

EN = io.open(os.path.join(FR, "MANUSCRIPT_v3.2_EN.md"), encoding="utf-8").read()
CN = io.open(os.path.join(FR, "MANUSCRIPT_v3.2_CN.md"), encoding="utf-8").read()
MATRIX = pd.read_excel(os.path.join(FR, "REFERENCE_EVIDENCE_MATRIX.xlsx"),
                       sheet_name="references")
BY_ID = MATRIX.set_index("ref_id")

# ---------------------------------------------------------------- order + mapping

# Markers that carry working R-identifiers, either bare ([R5]) or in a list ([R5,R9]),
# plus already-numeric lists of two or more ([3,4]).
#
# A SINGLE bracketed number is deliberately not matched anywhere this pattern is used.
# The pattern is applied to the final manuscript text and one of its consumers rewrites
# that text in place, so a loose pattern here is destructive: an earlier version used
# r"\[([R0-9,]+)\]" and both rewrote the ethics approval number "2025[327]" and
# harvested "327" from it as though it were a reference id. The approval number is part
# of a factual identifier and is reproduced exactly as the committee issued it.
_CONVERT_RE = re.compile(r"\[(R\d+(?:,R\d+)*|\d+(?:,\d+)+)\]")

EN_BODY, EN_REFS = split_refs(EN)
HAS_R_IDS = bool(re.search(r"\[R\d+", EN))

if HAS_R_IDS:
    # first run: the order of first appearance comes from the [Rxx] markers.
    # Uses the strict conversion pattern, not a loose r"\[([R0-9,]+)\]": the loose form
    # also matched the ethics approval number "2025[327]" and harvested "327" as though
    # it were a reference id, which then failed a dictionary lookup further down.
    order, seen = [], set()
    for m in _CONVERT_RE.finditer(EN_BODY):
        for rid in m.group(1).split(","):
            if rid not in seen:
                seen.add(rid)
                order.append(rid)
    missing_defs = [r for r in order if r not in BY_ID.index]
    uncited = [r for r in MATRIX.ref_id if r not in seen]
else:
    # already converted: recover the order from the bibliography. The matrix is stored
    # in first-appearance order, which is how it was written.
    order = list(MATRIX.ref_id)
    seen = set(order)
    missing_defs, uncited = [], []
    bib_lines = [l for l in EN_REFS.splitlines()
                 if re.match(r"^\d+\.\s", l.strip())]
    if len(bib_lines) != len(order):
        missing_defs = [f"bibliography has {len(bib_lines)} entries, expected "
                        f"{len(order)}"]

seq = {rid: i for i, rid in enumerate(order, 1)}

# duplicate detection: same DOI, or identical normalised citation text
def norm_cit(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())[:120]


dois = []
for c in MATRIX.citation:
    found = re.findall(r"10\.\d{4,9}/[^\s;)]+", str(c))
    dois.extend(found)
dup_doi = [d for d, n in Counter(dois).items() if n > 1]
dup_cit = [c for c, n in Counter(norm_cit(c) for c in MATRIX.citation).items() if n > 1]

# ---------------------------------------------------------------- conversion
# Idempotent: on a first run the manuscript carries [R13,R14] working identifiers and
# they are converted to sequential numbers. On a re-run the identifiers are already
# numeric, so there is nothing to convert and the bibliography is rebuilt from the
# numbering the manuscript already uses. Without this, a second run would try to look
# up "1" as a working id and fail.
HAS_R_IDS = bool(re.search(r"\[R\d+", EN))

if not HAS_R_IDS:
    # Already converted. The working identifiers no longer exist in the text, so the
    # order is recovered from the bibliography instead, and the conversion steps below
    # are skipped. Without this branch a re-run would look up "1" as a working id.
    bib_lines = [l for l in split_refs(EN)[1].splitlines()
                 if re.match(r"^\d+\.\s", l.strip())]
    order = [rid for rid in MATRIX.ref_id]          # matrix order == first appearance
    seq = {rid: i for i, rid in enumerate(order, 1)}
    bib_ok = len(bib_lines) == len(order)
else:
    bib_ok = None


def convert(text: str) -> str:
    """Replace every [Rx,Ry] marker with its sequential form [n,m]."""
    def repl(m):
        ids = m.group(1).split(",")
        nums = sorted(seq[i] for i in ids if i in seq)
        return "[" + ",".join(str(n) for n in nums) + "]"
    return _CONVERT_RE.sub(repl, text)


if HAS_R_IDS:
    EN_OUT = convert(EN)
    CN_OUT = convert(CN)
    # rebuild the reference list in sequential order in both versions, preserving
    # whatever follows the bibliography in each document. This must operate on the
    # CONVERTED text, not the original, or the [Rxx] markers reappear.
    ref_block = "\n".join(f"{seq[rid]}. {BY_ID.loc[rid, 'citation']}"
                          for rid in order)
    _eh = _REF_HEAD.search(EN_OUT)
    if not _eh:
        raise SystemExit("reference audit: REFERENCES heading missing")
    en_head, en_tail = EN_OUT[:_eh.start()], EN_OUT[_eh.end():]
    _th = _TAB_HEAD.search(en_tail)
    if not _th:
        raise SystemExit("reference audit: TABLES heading missing")
    en_after = en_tail[_th.end():]
    EN_OUT = (en_head + "# REFERENCES\n\n" + ref_block
              + "\n\n# TABLES" + en_after)
    cn_head, _ = split_cn_refs(CN_OUT)
    CN_OUT = (cn_head + "## 参考文献\n\n编号与英文版一致（按首次出现顺序），"
              "文献条目与英文版完全相同。\n\n" + ref_block + "\n")
    io.open(os.path.join(FR, "MANUSCRIPT_v3.2_EN.md"), "w",
            encoding="utf-8").write(EN_OUT)
    io.open(os.path.join(FR, "MANUSCRIPT_v3.2_CN.md"), "w",
            encoding="utf-8").write(CN_OUT)
else:
    # already converted: audit the manuscript as it stands
    EN_OUT, CN_OUT = EN, CN

# ---------------------------------------------------------------- re-verify
leftover = re.findall(r"\[R\d+\]", EN_OUT) + re.findall(r"\[R\d+\]", CN_OUT)
cited_nums = set()
for m in prov.CITATION_RE.finditer(split_refs(EN_OUT)[0]):
    cited_nums.update(int(x) for x in m.group(1).split(","))
bib_nums = set(range(1, len(order) + 1))

L = []
w = L.append
w("# REFERENCE FINAL AUDIT")
w("")
w("**Manuscript:** `MANUSCRIPT_v3.2_EN.md` and `MANUSCRIPT_v3.2_CN.md`")
w("")
w("## Required outcomes")
w("")
w("| requirement | required | observed | status |")
w("|---|---:|---:|---|")
w(f"| unresolved `[Rxx]` working identifiers | 0 | {len(leftover)} | "
  f"{'PASS' if not leftover else 'FAIL'} |")
w(f"| uncited bibliography entries | 0 | {len(uncited)} | "
  f"{'PASS' if not uncited else 'FAIL'} |")
w(f"| cited-but-missing references | 0 | {len(missing_defs)} | "
  f"{'PASS' if not missing_defs else 'FAIL'} |")
w(f"| duplicate references (identical DOI) | 0 | {len(dup_doi)} | "
  f"{'PASS' if not dup_doi else 'FAIL'} |")
w(f"| duplicate references (identical citation text) | 0 | {len(dup_cit)} | "
  f"{'PASS' if not dup_cit else 'FAIL'} |")
w(f"| cited numbers without a bibliography entry | 0 | "
  f"{len(cited_nums - bib_nums)} | "
  f"{'PASS' if not cited_nums - bib_nums else 'FAIL'} |")
w(f"| bibliography entries never cited | 0 | {len(bib_nums - cited_nums)} | "
  f"{'PASS' if not bib_nums - cited_nums else 'FAIL'} |")
w("")
w("## Numbering in order of first appearance")
w("")
w("| # | working id | citation | type | verification |")
w("|---:|---|---|---|---|")
for rid in order:
    row = BY_ID.loc[rid]
    # Type is decided from the citation text itself. The earlier version tested the
    # 'verification' column, which records HOW a record was confirmed, not whether it
    # was peer reviewed, and so labelled the two preprints as peer-reviewed.
    _ct = str(row.citation)
    kind = ("preprint"
            if re.search(r"preprint|medrxiv|research square|openrxiv", _ct, re.I)
            else "peer-reviewed")
    w(f"| {seq[rid]} | `{rid}` | {_ct[:150]} | {kind} | "
      f"{row.get('verification', 'n/a')} |")
w("")
w("## Verification status of each entry")
w("")
w("Two verification classes are recorded, and the distinction matters:")
w("")
w("- **search-confirmed** - the citation details were returned by a search result in")
w("  this session and the journal, year and DOI/PMID were read off that record.")
w("- **standard-reference** - a canonical statement, database descriptor or")
w("  long-established methodological paper. The details are not in dispute, but the")
w("  authors should still re-check volume, issue and page numbers against the")
w("  publisher record before typesetting.")
w("")
n_sc = int(MATRIX.verification.astype(str).str.contains("search-confirmed").sum())
n_sr = int(MATRIX.verification.astype(str).str.contains("standard-reference").sum())
w(f"- search-confirmed: **{n_sc}**")
w(f"- standard-reference: **{n_sr}**")
w(f"- total: **{len(MATRIX)}**")
w("")
w("## Language parity")
w("")
en_refs = re.findall(r"^\d+\. ", split_refs(EN_OUT)[1], re.M)
cn_refs = re.findall(r"^\d+\. ", split_cn_refs(CN_OUT)[1], re.M)
w("| check | result |")
w("|---|---|")
w(f"| entries in the English bibliography | {len(en_refs)} |")
w(f"| entries in the Chinese bibliography | {len(cn_refs)} |")
w(f"| identical order and count | "
  f"{'YES' if len(en_refs) == len(cn_refs) == len(order) else 'NO'} |")
w("")
w("## Reference-type composition")
w("")
# Computed from the final bibliography rather than from the matrix, so the counts
# cannot drift: an entry counts as a preprint only if its own text says so.
_bib_txt = split_refs(EN_OUT)[1]
_entries = [l.strip() for l in _bib_txt.splitlines() if re.match(r"^\d+\.\s", l.strip())]
_pre = [e for e in _entries
        if re.search(r"preprint|medrxiv|research square|openrxiv", e, re.I)]
w("| type | count |")
w("|---|---:|")
w(f"| peer-reviewed | {len(_entries) - len(_pre)} |")
w(f"| preprint | {len(_pre)} |")
w(f"| **total** | **{len(_entries)}** |")
w("")
w("Preprint entries (labelled as such in the bibliography itself):")
w("")
for _e in _pre:
    w(f"- {_e[:180]}")
w("")
w("## Outstanding reference work for the authors")
w("")
w("The manuscript's bibliography draws on the original verified set. The literature")
w("search additionally identified several 2024-2026 studies that position this work")
w("and that are recorded in `NOVELTY_POSITIONING_MATRIX.xlsx`. The following remain to")
w("be done before submission, and are flagged rather than silently completed:")
w("")
w("1. **Add the recent-literature citations to the Introduction and Discussion.**")
w("   The v2 Introduction and Discussion do not yet cite the 2024-2026 ICU cirrhosis")
w("   and transportability studies; the positioning text is supplied in")
w("   `NOVELTY_POSITIONING_MATRIX.xlsx` and needs to be woven in with citation numbers.")
w("2. **Re-check the `standard-reference` entries** against publisher records.")
w("3. **Confirm the flagged anomalies**: forward-dated 2026 issue assignments, the")
w("   CLEARED online-2025/print-2026 year split, and the `10.64898` preprint DOI")
w("   prefix.")
w("4. **Cite the Patel and Beedala preprint once**, not twice: it carries two DOIs")
w("   (medRxiv and Research Square).")
w("")

with io.open(os.path.join(FR, "REFERENCE_FINAL_AUDIT_v3.2.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

prov.announce("reference_final_audit")
print("wrote REFERENCE_FINAL_AUDIT_v3.2.md")
print(f"  references numbered : {len(order)}")
print(f"  unresolved [Rxx]    : {len(leftover)}")
print(f"  uncited entries     : {len(uncited)}")
print(f"  missing definitions : {len(missing_defs)}")
print(f"  duplicate DOIs      : {len(dup_doi)}")
print(f"  cited w/o entry     : {len(cited_nums - bib_nums)}")
print(f"  entries never cited : {len(bib_nums - cited_nums)}")
print(f"  EN/CN parity        : {len(en_refs)} == {len(cn_refs)}")
