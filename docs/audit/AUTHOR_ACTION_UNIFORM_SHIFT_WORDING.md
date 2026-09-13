# AUTHOR ACTION REQUIRED -- surviving "uniform shift" wording in the manuscript

**Status: OPEN. Not resolved by code release v1.1.0.**

**Scope: the manuscripts are NOT part of this code repository and were NOT modified by
this packaging pass.** This file exists because the code release must not assert
something about the manuscript that is not true. It records a discrepancy that the
authors need to close.

---

## 1. The problem in one paragraph

Publication/release v1.1.0 removed the hierarchical mixed-effects calibration model
because it was unreliable (`docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`).
Once that model is gone, **no retained analysis establishes that the calibration shift
was uniform across hospitals**, so the manuscript must not say that it was. Five
sentences in the final manuscript pair still say exactly that, or presuppose it. They
also contradict other sentences in the *same* documents, so the manuscript currently
argues both ways.

The required framing, which the repository uses throughout, is:

> Hospital-specific calibration estimates varied descriptively, but no formal
> hierarchical calibration-heterogeneity conclusion is reported.

Neither of these may be claimed:

- **NOT** "all hospitals shared the same calibration shift" -- not established by any
  retained analysis; its only support was the removed model.
- **NOT** "significant calibration heterogeneity was proven" -- also not established.
  The retained per-hospital O/E ratios are descriptive.

## 2. What is already correct

No numeric result from the removed model survives anywhere in either manuscript. Both
v3.2 files were checked for every value of the withdrawn fit (alpha, beta, tau, the
Laplace criteria, the bootstrap tau interval, the random-intercept SD) and for the
phrases "random intercept", "variance component", "laplace", "loglik", "随机截距": **zero
hits**. Every tau-squared / I-squared figure in the manuscripts belongs to the
**retained** DerSimonian-Laird meta-analysis of per-hospital *discrimination*, which is
a separate analysis and does not use the removed model.

Several sentences already state the correct position, for example:

- `MANUSCRIPT_v3.2_EN.md:357-358` -- "we report the hospital-level evidence
  descriptively, and it does not support treating the shift as uniform across centres."
- `MANUSCRIPT_v3.2_EN.md:532` -- "the shift was **not** uniform"
- `MANUSCRIPT_v3.2_EN.md:661-663` -- the conclusion states the hospital-level evidence
  "did not support treating that shift as uniform"
- `MANUSCRIPT_v3.2_CN.md:137` -- "并不支持将该偏移视为各医院一致"
- `MANUSCRIPT_v3.2_CN.md:189` -- "该偏移并**非**各医院一致"

So the correction below makes the manuscript consistent with itself, not merely with
the repository.

## 3. Sentences requiring correction

Line numbers refer to the final v3.2 files as shipped at release v1.1.0.

### 3.1 `MANUSCRIPT_v3.2_EN.md` lines 500-503 -- Discussion, principal finding

Current (verbatim):

> The O/E ratio of 0.8582
> showed that the model systematically over-predicted the absolute risk of death,
> and this shift was common across hospitals rather than concentrated in particular
> centres.

Why: a flat assertion that the shift was common across hospitals. Its only support was
the removed model. It contradicts `:532` and `:661-663` in the same file.

Suggested replacement (drops the overclaim, keeps the finding):

> The O/E ratio of 0.8582
> showed that the model systematically over-predicted the absolute risk of death;
> the hospital-level observed-to-expected ratios varied descriptively rather than
> concentrating on a single shared value.

### 3.2 `MANUSCRIPT_v3.2_EN.md` lines 546-549 -- between-hospital variation

Current (verbatim):

> The practical implication is that a single local correction of
> the baseline is a reasonable starting point, because it removed the shared level
> error when the intercept was re-estimated WITHOUT the held-out hospital, but the [13,33]
> between-hospital spread means it should not be assumed sufficient everywhere.

Why: "the shared level error" presupposes the uniformity the removed model claimed.

Suggested replacement:

> The practical implication is that a single local correction of
> the baseline is a reasonable starting point, because it corrected the cohort-level
> calibration-in-the-large error when the intercept was re-estimated WITHOUT the
> held-out hospital, but the [13,33] between-hospital spread means it should not be
> assumed sufficient everywhere.

### 3.3 `MANUSCRIPT_v3.2_EN.md` line 567 -- recalibration

Current (verbatim, excerpt):

> ... what is supported is that an intercept re-estimated WITHOUT the held-out hospital removed the shared level error in that hospital.

Why: same presupposition, and "in that hospital" over-localises an error the
leave-one-hospital-out design cannot localise.

Suggested replacement:

> ... what is supported is that an intercept re-estimated WITHOUT the held-out hospital corrected calibration-in-the-large for the held-out hospitals.

### 3.4 `MANUSCRIPT_v3.2_CN.md` line 181 -- section 4.1

Current (verbatim, excerpt):

> O/E 为 0.8582 表明模型系统性地高估了绝对死亡风险，且这一偏移在各医院之间是共同的，而非集中于个别中心。

Suggested replacement:

> O/E 为 0.8582 表明模型系统性地高估了绝对死亡风险；各医院观察值与预期值之比呈描述性差异，而非集中于同一数值。

### 3.5 `MANUSCRIPT_v3.2_CN.md` line 279 -- section 7, conclusions (**highest priority**)

Current (verbatim, excerpt):

> ... 而校准水平发生偏移，且该偏移在各医院之间是共同的，而非特定于个别中心。

Why: this is the worst of the five. The uniformity claim sits in the **Conclusions**,
and the English conclusions say the opposite. The Chinese file's own rule is that the
English version governs where they conflict, so this is an outright internal
contradiction, not a translation nuance.

Suggested replacement:

> ... 而校准水平发生偏移；各医院校准估计存在描述性差异，本文不报告正式的层次化校准异质性结论。

### 3.6 `MANUSCRIPT_v3.2_CN.md` lines 189 and 195 -- "共同的水平误差"

Line 189 contains "重新估计截距可消除共同的水平误差" and line 195 "消除了该医院的共同水平误差".
These are the Chinese counterparts of 3.2 and 3.3 and should be changed in the same way
(drop "共同的水平误差"; state that calibration-in-the-large was corrected).

## 4. Origin of the wording, so it is not reintroduced

The "shared level error" phrasing at EN 546-549 and EN 567 was **recommended** by
`RECALIBRATION_WORDING_AUDIT.md` (see its line 42) as the fix for an earlier, worse
formulation. That audit predates the removal of the hierarchical model. The phrase was
correct when a shared shift was still an established result; it is not correct now.
`docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` already lists "the claim that
the calibration shift was *shared across hospitals* rather than hospital-specific" as
one of the statements that "must go".

## 5. The audit gap that let this through

`MANUSCRIPT_CLAIM_COMPLIANCE.md` reports 44/44 pass and "READY", but it is scoped to
`MANUSCRIPT_v1` and it contains **no check for the uniform / shared-shift phrasing**.
Its heterogeneity checks cover the discrimination meta-analysis only. That is why
offenders 3.1, 3.4 and 3.5 survived a passing compliance run.

Before the manuscript is re-tagged, add an explicit prohibition check for at least:

```text
common across hospitals
shared level shift
shared level error
uniform across
共同的
各医院一致
```

and require each hit to be inside a negation ("not uniform", "并**非**各医院一致") rather
than an assertion.

## 6. What the authors must do

1. Apply the corrections in section 3 to `MANUSCRIPT_v3.2_EN.md` and
   `MANUSCRIPT_v3.2_CN.md`.
2. Add the prohibition check in section 5 to the claim-compliance pass.
3. Rebuild the `.docx` submission files from the corrected sources.
4. Re-run `MANUSCRIPT_CLAIM_COMPLIANCE.md`, `MANUSCRIPT_NUMBER_AUDIT.md` and
   `MANUSCRIPT_SEMANTIC_UNIT_AUDIT.md`, and confirm the 480 traced numeric tokens and
   the 27 unit checks are unchanged (no number should move: these are wording edits
   only).
5. Update `PUBLICATION_LOCK_v1.1.0.md` and this file to record the corrections as
   applied, with line references.

**Do not re-tag or publish release v1.1.0 as final until step 1 is done.** A reader who
checks the code against the manuscript will otherwise find the manuscript asserting a
result whose supporting model the code release has withdrawn.

## 7. Note on `MANUSCRIPT_NUMBER_AUDIT.md`

Its header reads "Release: `PROJECT1_FINAL_MANUSCRIPT_v1.0.0`", which is now the
superseded analytical release. The header should be updated to
`PROJECT1_FINAL_MANUSCRIPT_v1.1.0`. This is cosmetic -- no traced number changes -- but
it is the kind of stale string that makes a reader doubt the rest of the document.
