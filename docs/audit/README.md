# Audit record

This directory holds the audit trail for the one analytical decision that changed
between release v1.0.0 and release v1.1.0: **the hierarchical mixed-effects calibration
analysis was removed from the manuscript as unreliable.**

It is here because a reader should be able to check that decision rather than take it on
trust. Nothing in this directory is a reported result.

## The decision in brief

A mixed-effects logistic calibration model with a random intercept per hospital had been
used to estimate a common calibration slope and a between-hospital variance component. It
was withdrawn:

1. its custom Laplace criterion **omitted the Gaussian prior normalisation**
   `-(J/2) log(2 pi tau^2)`, a term that is **not constant in tau** and diverges as tau
   approaches zero, so the variance component was not selected by the approximation it
   was reported as;
2. an **independent, mature implementation** (`lme4::glmer`, R 4.6.0, lme4 2.0.6)
   converged cleanly and disagreed materially about that variance component
   (`tau = 0.1088` against the custom fit's `1e-06`, with all 85 random intercepts
   exactly zero);
3. the fit was **singular**, with the variance component on the boundary of the
   parameter space.

The model was withdrawn rather than repaired further.

**No hierarchical numerical result is part of release v1.1.0.** The hospital-level
evidence is reported descriptively, as observed-to-expected ratios per hospital, and no
formal hierarchical calibration-heterogeneity conclusion is reported.

## What you may and may not conclude

| statement | status |
|---|---|
| "hospital-specific calibration estimates varied descriptively" | **supported** -- retained per-hospital descriptives |
| "all hospitals shared the same calibration shift" | **NOT claimed** -- its only support was the removed model |
| "significant calibration heterogeneity was proven" | **NOT claimed** -- not established by any retained analysis |

## Contents

| file | what it is | status |
|---|---|---|
| `HIERARCHICAL_LAPLACE_MATH_AUDIT.md` | the derivation, the four questions and the defect in the custom Laplace criterion | historical audit record; no number in it is a v1.1.0 result |
| `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` | the four-way comparison (original custom fit, repaired custom fit, `lme4::glmer`, complete-Laplace custom fit) and the decision rule that removed the model | **the decision document** |
| `HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` | the *first* defect: the optimiser returned the slope at its starting value after one iteration, and the multi-start repair | historical; superseded by the removal |
| `PUBLICATION_LOCK_v1.1.0.md` | release-level record: what changed, what did not, and what was removed | **one item is OPEN** -- see below |
| `LOCKED_RELEASE_CODE_VERIFICATION.md` | file-by-file comparison of the published code against the frozen analytical release | current |
| `CODE_INVENTORY.md` | mapping from each published file to its internal working-tree origin | current |
| `EXCLUDED_FILES_REVIEW.md` | what was withheld from the release and why | current |
| `AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` | **OPEN ACTION for the authors** | the manuscripts still contain wording whose only support was the removed model |

## The open item

`AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md` records five sentences in the final manuscripts
that still assert or presuppose the removed model's uniform-shift claim. The manuscripts
are **not part of this code repository** and were not modified here, so the code release
cannot fix this. The file gives the exact sentences, their line numbers, why each
offends, and minimal replacements.

No *number* from the removed model survives in either manuscript; that part of the
removal is complete and was re-verified. What survives is the qualitative claim.

## Reading order

For the removal decision: `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`, then
`HIERARCHICAL_LAPLACE_MATH_AUDIT.md`.

For what the code release actually contains: `LOCKED_RELEASE_CODE_VERIFICATION.md`.

For what still needs doing: `AUTHOR_ACTION_UNIFORM_SHIFT_WORDING.md`.

## Data safety

None of these documents contains patient-level or stay-level data, hospital identifiers,
credentials or absolute filesystem paths. They were checked before being included.
`HIERARCHICAL_LAPLACE_MATH_AUDIT.md`, `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` and
`HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` were written against the internal
working tree and name internal generator scripts that are **not shipped**; they cannot be
re-run from this repository alone, because they require the restricted analysis dataset
and the frozen predictions. Each says so in a header.

## Note on corrections made at v1.1.0 packaging

While preparing this release, three defects were found in the audit documents
themselves and were corrected **as documentation only -- no analysis was re-run and no
number was recomputed**:

- a row in `HIERARCHICAL_LAPLACE_MATH_AUDIT.md` labelled "code's `lap`" printed
  `3.205353`, which equals `log g(u*) + 0.25 log|H|` rather than the `0.5 log|H|` the
  code uses; the correct value is `592.983576`. The erroneous row is struck through and
  the correct one added beside it.
- the Findings table in the same document said the omitted normalisation "changes no
  reported value", contradicting section 2.4(b) of that document and the removal
  decision. The rows were restated to match 2.4(b).
- `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` was titled "THREE-WAY" while comparing
  four implementations; the title was corrected.

Each correction is marked in place with an audit note, so the original record and the
correction are both visible. Two further items are recorded rather than resolved, because
resolving them would require re-running the withdrawn analysis: implementation C's
bootstrap interval has a lower limit above its own point estimate, and the Laplace audit's
boundary sentence needed a scope qualifier so it is not misread as contradicting the
comparison document.
