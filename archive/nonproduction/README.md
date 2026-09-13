# Archive -- non-production code

> # HISTORICAL IMPLEMENTATION.
> # NOT USED IN THE FINAL MANUSCRIPT.
> # DO NOT USE FOR INFERENCE.

**Nothing in this directory is part of the production pipeline. It is not executed by any
step of the documented run sequence, it is not imported by any shipped script, and no
number it produces may be used for any purpose.**

## Contents

| file | what it is |
|---|---|
| `hierarchical_calibration_rejected_historical.py` | the complete internal implementation of the custom hierarchical (mixed-effects) logistic calibration model that was audited and **REMOVED** from the manuscript as unreliable |

## Why a rejected implementation is shipped at all

Transparency. A reader is entitled to see exactly what was fitted, what went wrong, and how
the decision to remove it was reached, rather than being told only the conclusion.
Preserving the rejected code in an unambiguous archive is the honest option; deleting it
would leave the audit record unverifiable.

The file carries a long header stating what it is, why it is here, what was wrong with it,
and what it must not be used for. It is **disabled**: all of its executable code sits inside
a function that is never called, and running the file directly prints a refusal and exits
non-zero. `python -m compileall` still parses it, so a syntax error could not hide here.

## What was wrong with it

1. Its custom Laplace criterion omitted the Gaussian prior normalisation
   `-(J/2) log(2 pi tau^2)`. That term is **not constant in tau** -- it diverges as tau
   approaches zero -- so the variance component was not selected by the approximation it was
   reported as.
2. An independent, mature implementation (`lme4::glmer`, R 4.6.0, lme4 2.0.6) converged
   cleanly and estimated `tau = 0.1088`, against this fit's `1e-06` with all 85 random
   intercepts exactly zero.
3. An earlier run of the same code returned the common calibration slope at the optimiser's
   **starting value of 1.0** after a single iteration, with a degenerate confidence interval
   at (1, 1). It was repaired to a multi-start optimisation -- the repair is visible in the
   archived code -- and then withdrawn entirely when the independent fit disagreed.

The audit is in `docs/audit/`: the mathematics in
`docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md`, the comparison and the decision rule in
`docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`.

## Verification that the removal is real

`verify_public_release.py` and `pipeline_path_audit.py` both check that no production
script fits, reads or writes any quantity from this model, and
`src/reporting/final_release_check.py` actively **fails** if the removed
`hierarchical_calibration` or `random_intercepts` sheets ever reappear in Table 4.

## Where to look instead

The **retained** hospital-level analyses -- per-hospital descriptive performance, the
random-effects AUROC meta-analysis, descriptive hospital-level observed-to-expected ratios,
and the leave-one-hospital-out recalibration -- are in
`src/validation/hospital_analysis_and_recalibration.py`. That script performs no
mixed-effects fitting of any kind.

## Note

This file was produced by re-indenting the published
`src/validation/hierarchical_calibration.py` (v1.0.0/v1.1.0) into a disabled function and
prepending the header. The code is otherwise verbatim, including the original comments that
document the starting-value hazard and the authorised multi-start repair. No line of the
analysis was rewritten to look better in hindsight.
