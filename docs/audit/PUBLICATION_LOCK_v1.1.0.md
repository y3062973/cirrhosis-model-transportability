# PUBLICATION LOCK -- PROJECT 1 -- v1.1.0

**Supersedes:** `PROJECT1_FINAL_MANUSCRIPT_v1.0.0` (preserved, unchanged, as superseded history)
**This release:** `PROJECT1_FINAL_MANUSCRIPT_v1.1.0`

> ## RELEASE STATUS: ANALYTICAL RELEASE LOCKED; ONE MANUSCRIPT WORDING ITEM OPEN
>
> This document was written when the removal was made. An independent re-check of the
> final manuscripts later found that the removal of the *shared-shift claim* was
> **intended but not fully applied to the text**: five sentences in
> `MANUSCRIPT_v3.2_EN.md` and `MANUSCRIPT_v3.2_CN.md` still assert, or presuppose, that
> the calibration shift was **uniform across hospitals** -- the claim whose only
> support was the removed model.
>
> The manuscripts are **not part of this code repository** and were not modified by
> this packaging pass. The offending sentences with their line numbers, why each
> offends, and minimal replacements are recorded in
> `docs/audit/AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`.
>
> No *number* from the removed model survives anywhere in either manuscript -- that
> part of the removal is complete and re-verified. What survives is the qualitative
> uniformity claim. The Discussion and Conclusions rows of the "What was removed"
> table below are therefore marked **OPEN**, and the verification row for superseded
> hierarchical values is qualified accordingly. Do not re-tag or publish v1.1.0 as
> final until the wording item is closed.

## Reason for the version bump

**Hierarchical calibration implementation correction.** The mixed-effects logistic
calibration model with a random intercept per hospital was **removed** from the
manuscript. An audit found that (a) the custom Laplace criterion omitted the
Gaussian prior normalisation `-(J/2) log(2 pi tau^2)`, a tau-dependent term, so the
variance component was not selected by the approximation it was reported as; and
(b) an independent, mature implementation (`lme4::glmer`, R 4.6.0, lme4 2.0.6)
disagreed materially about that variance component (approximately 0 versus 0.109)
while agreeing about the fixed effects. The decision rule applied is recorded in
`HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`; the mathematics is in
`HIERARCHICAL_LAPLACE_MATH_AUDIT.md`.

A version bump rather than a silent edit is required because an analytical
implementation changed after v1.0.0. v1.0.0 remains in the repository and in git as
the previous release; it has not been rewritten.

## Primary results -- UNCHANGED

Every value below is reproduced from the current artefacts and was present verbatim
in the v1.0.0 lock document:

| locked line from v1.0.0 | present in v1.0.0 | present now |
|---|---|---|
| `| eICU | 1,612 | 324 | 0.7918 | 0.1265 | 0.8582 | 1.0333 | -0.2175 |` | yes | checked below |
| `| MIMIC-IV | 4,237 | 857 | 0.7924 | 0.1272 | 1.0000 | 1.0000 | 0.0000 ` | yes | checked below |
| `| primary N>=20 | 18 | 0.7929 | 0.7456 to 0.8334 | 0.0000 | 0.0% | 8.9` | yes | checked below |
| `| dO/E model1 vs model0 | +0.14570 | +0.12438 to +0.16755 | **yes** |` | yes | checked below |
| `| FINAL_MODEL_V2 | 758 | 184 | 0.7858 | 0.7453 to 0.8265 | 0.8582 |` | yes | checked below |

### Cohorts

| cohort | ICU stays | deaths |
|---|---|---|
| MIMIC-IV | 4,237 | 857 (20.2) |
| eICU | 1,612 | 324 (20.1) |
| nwICU | 349 | 75 (21.5) |

### Primary external validation (eICU)

| metric | value |
|---|---|
| AUROC | 0.7918 |
| Brier score | 0.1265 |
| O/E ratio | 0.8582 |
| calibration slope | 1.0333 |
| calibration intercept | -0.2175 |
| AUPRC | 0.5529 |
| ICI | 0.0332 |
| Emax | 0.0788 |

### Hospital-level discrimination meta-analysis (retained)

| quantity | value |
|---|---|
| pooled AUROC | 0.7929 |
| 95% CI | 0.7456 to 0.8334 |
| hospitals (k) | 18 |
| tau-squared | 0.0000 |
| I-squared | 0.0% |
| Cochran Q | 8.9156 |

This analysis is **retained**. It is a separate per-hospital AUROC meta-analysis
and does not use the removed model.

### Leave-one-hospital-out recalibration (retained)

| model | O/E | Brier | calibration slope |
|---|---|---|---|
| Model 0 original | 0.8582 | 0.1265 | 1.0333 |
| Model 1 intercept-only | 1.0039 | 0.1254 | 1.0254 |
| Model 2 intercept+slope | 1.0037 | 0.1255 | 0.9883 |

Also retained and unchanged.

### Clinical score comparison (retained)

| score | n | AUROC | O/E |
|---|---|---|---|
| FINAL_MODEL_V2 | 758 | 0.7858 | 0.8582 |
| MELD | 758 | 0.7718 | 1.0289 |
| MELD-Na | 758 | 0.7714 | 1.0343 |
| ALBI | 758 | 0.6145 | 0.8014 |
| FIB-4 | 758 | 0.6316 | 1.1380 |

## Model coefficients -- UNCHANGED

FINAL_MODEL_V2 has not been refitted. All 15 coefficients are identical
to v1.0.0 (coefficient-set digest `c9e60e189e56307e`).

## What was removed

| artefact | change |
|---|---|
| Table 4 sheets | removed `hierarchical_calibration`, `random_intercepts`; remaining sheets: all_hospitals, primary_N20, sensitivity_N30, meta_analysis_AUROC |
| Figure 5 panel B | the caterpillar plot of shrunken random intercepts was
  replaced with the observed-to-expected ratio per hospital, which requires no
  mixed-effects fitting |
| Methods | the paragraph describing the hierarchical calibration model was
  replaced with a statement that the model is not reported, and why |
| Results | the hierarchical-model paragraph was replaced with hospital-level
  observed-to-expected descriptives |
| Discussion | **OPEN -- not fully applied.** The 'shared level shift rather than hospital-specific distortion' claim was intended to be removed, and the hospital-level spread is now reported descriptively and explicitly not treated as uniform (`MANUSCRIPT_v3.2_EN.md:357-358`, `:532`). **But the uniformity assertion survives at `MANUSCRIPT_v3.2_EN.md:500-503`**, contradicted by the same file. See `AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`. |
| Conclusions | **OPEN -- not applied to the Chinese file.** The English conclusions are correct (`MANUSCRIPT_v3.2_EN.md:660-663`: the hospital-level evidence "did not support treating that shift as uniform"). **The Chinese conclusions still assert uniformity at `MANUSCRIPT_v3.2_CN.md:279`**, which the Chinese file's own precedence rule makes an outright contradiction. See `AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`. |

## Manuscript version

The manuscript moves to **v3.2** (`MANUSCRIPT_v3.2_EN.md`, `MANUSCRIPT_v3.2_CN.md`)
because the change affects reported content. The title and abstract are unchanged:
neither contained a hierarchical-model claim.

## Verification performed on this release

| check | result |
|---|---|
| primary results versus v1.0.0's own lock | all reproduce |
| numeric-token audit | 480 values, 0 untraceable |
| semantic-unit audit | 27 checks, 0 fail |
| claim-lock compliance | pass |
| reference audit | 33 references, 0 unresolved / uncited / missing / duplicate |
| superseded hierarchical values in the manuscript | none present |

## Superseded release

`PROJECT1_FINAL_MANUSCRIPT_v1.0.0` is preserved unchanged and still points at its original commit. It is
not deleted, not rewritten, and not reused: a reader who needs the previous
analysis can still obtain it exactly as published.

