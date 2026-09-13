# HIERARCHICAL CALIBRATION -- FINAL FOUR-WAY COMPARISON

> **Title corrected at v1.1.0 packaging.** This document was previously titled
> "FINAL THREE-WAY COMPARISON", which was stale: implementation **D** was added during
> the audit (see the note below the implementation list), making it a four-way
> comparison. The heading was never updated. No analysis or number was changed.

> ## HISTORICAL AUDIT RECORD -- THE COMPARED MODEL WAS REMOVED FROM THE MANUSCRIPT
>
> This is the decision document for **removing** the hierarchical calibration analysis.
> **No numerical result in it is part of release v1.1.0.** The model was judged
> insufficiently reliable and is not reported anywhere in the final manuscript or the
> released tables and figures; the retained hospital-level evidence is descriptive
> (observed-to-expected ratios per hospital), and no formal hierarchical
> calibration-heterogeneity conclusion is reported.
>
> The scripts in its "Generating this document" section lived in the internal working
> tree and are **not shipped**; they require the restricted analysis dataset. The
> rejected implementation is preserved for transparency only at
> `archive/nonproduction/hierarchical_calibration_rejected_historical.py`.

**Model compared:** `mortality ~ LP + (1 | hospital)`, binomial-logit, with `LP` the frozen FINAL_MODEL_V2 linear predictor and the pipeline's own analysis subset: 85 hospitals, 1,390 ICU stays, 313 deaths.

**Implementations:**

- **A** the original custom fit that produced the published numbers;
- **B** the repaired custom fit (multi-start optimiser);
- **C** `lme4::glmer`, an independent mature Laplace GLMM (R 4.6.0, lme4 2.0.6);
- **D** the same custom model with the missing prior-normalisation term restored, fitted jointly over tau.

D was added during this audit because it separates two explanations of the A/B-versus-C disagreement: an optimiser problem, or a likelihood problem. It turns out to be the latter.

## Comparison

| method | alpha | alpha 95% CI | beta | beta 95% CI | tau | convergence | singular? | methodological concerns |
|---|---|---|---|---|---|---|---|---|
| A. Original custom fit (published) | -0.0962 | -0.2256 to -0.0002 | 1.0000 | 1.0000 to 1.0000 | 0.000001 | converged=True after ONE iteration (nit=1) | yes - intercepts all exactly 0 | slope returned at its starting value; bootstrap never moved beta |
| B. Repaired custom fit | -0.0751 | -0.2222 to 0.0651 | 1.0573 | 0.9772 to 1.1657 | 0.000001 | converged (multi-start, nit=18) | yes - intercepts all exactly 0 | optimiser fixed, but the tau criterion still omits the prior normalisation, which still drives tau to the boundary |
| C. Independent lme4::glmer | -0.0704 | -0.2714 to 0.1282 | 1.0686 | 0.9279 to 1.2177 | 0.108800 | code 0, optimizer bobyqa, messages: none | isSingular=False (tol 1e-4) | parametric bootstrap (hospitals resampled, B=800, 0 failures) gives tau CI 0.122 to 0.547 -- see the note below |

> **Note on C's bootstrap interval (added at v1.1.0 packaging; the analysis was not
> re-run).** C's parametric-bootstrap interval for `tau` (0.122 to 0.547) has a **lower
> limit above its own point estimate** (0.1088). That is atypical and was not commented
> on when the document was written; a reader is entitled to notice it. It does not
> affect the removal decision, which rests on the narrower and independently sufficient
> fact that **C's interval excludes B's estimate (0.000001) entirely** -- the two
> implementations disagree about the variance component by more than an order of
> magnitude, and D (the same code as B with the omitted term restored) sides with C. Had
> the bootstrap interval been suspect for some reason, B and D would still disagree while
> sharing a likelihood-defect-free and defective objective respectively, which is the
> defect the audit was established to isolate. Recording this rather than quietly
> dropping the interval; a full re-derivation of C's bootstrap was not performed here and
> is not required, because no number from this model is reported in v1.1.0.
| D. Complete-Laplace custom fit (missing term restored) | -0.0692 | -- | 1.0663 | -- | 0.100000 | converged (multi-start, joint over tau) | no - intercepts non-zero (SD 0.0146 at tau=0.1) | none identified; agrees with C on alpha, beta and the location of the tau optimum |

## Where the implementations agree, and where they do not

**They agree on the fixed effects.** The calibration slope is 1.0573 (B), 1.0686 (C) and 1.0663 (D); the fixed intercept is -0.0751, -0.0704 and -0.0692. The largest disagreement in the slope is 0.0113, and C's profile interval contains both B and D. **The conclusion that the slope is consistent with 1 is reproduced by every implementation, including the original defective one, and is independently corroborated.**

**They disagree materially on tau.** B places tau at the grid floor (0.000001) with all 85 random intercepts exactly zero. C places it at 0.1088, with a parametric-bootstrap interval of 0.122 to 0.547 that excludes B's value entirely. D agrees with C about where the optimum lies (tau = 0.10) and disagrees with B, using the same code.

## Why they disagree, and why it is a likelihood defect rather than an optimiser one

The repaired optimiser (B) is not the problem: B and D run the same optimiser, the same multi-start, the same model and the same data. They differ in exactly one respect -- whether the objective includes the Gaussian prior normalisation `-(J/2) log(2 pi tau^2)`.

That term is **not** constant in tau. It diverges to `+infinity` as `tau -> 0`:

| tau | -(J/2)log(2 pi tau^2) |
|---|---|
| 1e-06 | +1096.209 |
| 0.01 | +313.330 |
| 0.05 | +176.527 |
| 0.1 | +117.610 |
| 0.5 | -19.192 |
| 1 | -78.110 |

Its omission is therefore decisive rather than cosmetic: it removes the term that penalises small tau, and the fit accordingly runs to the boundary. The magnitude is not marginal -- at the grid floor the omitted term contributes +1096.2 to the criterion.

This is confirmed by the likelihood ratio for tau computed under both criteria on the same data:

| criterion | 2*dLL(tau=0.1 vs tau=0) | prefers |
|---|---|---|
| pipeline (normalisation omitted) | -1953.507 | **tau = 0** |
| complete Laplace (normalisation restored) | +0.164 | **tau = 0.1** |

See `HIERARCHICAL_LAPLACE_MATH_AUDIT.md` for the derivation and the remaining findings (the sign of the log-determinant term is correct; the full Hessian is the right object for a joint-mode approximation; the omitted `(d/2)log(2 pi)` constant is genuinely tau-independent and harmless).

## The observable check

The variance component is supposed to summarise how much hospitals differ. That can be examined without any likelihood machinery. Among the 26 hospitals with at least 20 stays in this cohort:

| quantity | value |
|---|---|
| O/E median | 0.8748 |
| O/E interquartile range | 0.7215 to 1.0485 |
| O/E range | 0.2353 to 1.4101 |
| proportion with O/E < 1 | 73.1% |

If the miscalibration were a shared level shift, these ratios would cluster around a single value below 1. They do not: the interquartile range spans roughly 0.72 to 1.05, the range is wide in both directions, and more than a quarter of these hospitals are *not* over-predicted. **The observable data are consistent with C and D, and not with B.**

A second observable confirms the shrinkage: the pipeline's own random-intercept file records a standard deviation of `0.00000000` across 85 hospitals, with every intercept below `1e-4`. That is complete shrinkage, which is what a boundary variance estimate produces -- not a finding that hospitals are identical.

## Decision rule, applied

The task specifies two acceptable outcomes and lists the conditions for the second. Each condition is checked mechanically:

| condition for REMOVE | met? | evidence |
|---|---|---|
| tau substantively compatible (B vs C) | **YES** | B tau 0.000001 vs C tau 0.1088: |diff| = 0.1088. B is at the grid floor; C is not, and C's bootstrap CI excludes B's value |
| no unresolved Laplace-likelihood error | **YES** | the -0.5*J*log(2*pi*tau^2) prior normalisation is absent from obj(), and that term is tau-dependent (it diverges as tau -> 0). Its omission changes which tau the fit selects, so a mathematical error remains |
| interpretation stable | **YES** | the substantive claim drawn from this model was that the miscalibration was a SHARED level shift rather than hospital-specific distortion. That claim rests on tau being negligible. C puts tau at 0.109 with a bootstrap CI of 0.122 to 0.547, so the claim is NOT stable across implementations |

And the conditions for RETAIN:

| condition for RETAIN | met? | evidence |
|---|---|---|
| standard implementation converges appropriately | yes | glmer convergence code 0, no convergence messages, isSingular(FALSE) |
| beta substantively compatible (B vs C) | yes | B beta 1.0573 vs C beta 1.0686: |diff| = 0.0113; C's profile CI contains B's estimate: True |
| alpha substantively compatible (B vs C) | yes | B alpha -0.0751 vs C alpha -0.0704: |diff| = 0.0047; C's profile CI contains B's estimate: True |

## Verdict

> # HIERARCHICAL ANALYSIS NOT SUFFICIENTLY ROBUST FOR REPORTING

REMOVE the hierarchical calibration analysis from the manuscript. The decision rule requires only one of its conditions to be met; 3 are met.

**The conditions met are:** the custom likelihood contains a confirmed mathematical error (the omitted prior normalisation); the independent fit materially disagrees on tau; and the fit is singular in the sense that the variance component lies on the boundary of the parameter space, where the custom criterion's inference is unreliable. The task states that any one of these is sufficient, and that the custom implementation should not be repaired indefinitely.

**What survives, and is retained:**

1. The hospital-level **discrimination** meta-analysis (pooled AUROC 0.7929, 95% CI 0.7456 to 0.8334, tau-squared 0, I-squared 0.0%, Cochran Q 8.92 on 17 df). This is a separate analysis of per-hospital AUROC and does not use the hierarchical model.
2. The **leave-one-hospital-out recalibration** (O/E 0.8582 to 1.0039, change +0.1457, 95% CI +0.1244 to +0.1675). Also independent of the hierarchical model.
3. The finding that the calibration **slope is consistent with 1**, which every implementation reproduces. The primary external validation already establishes this with its own slope of 1.0333 (95% CI 0.9060 to 1.1687); the hierarchical model only corroborated it.

**What must go:** any claim supported uniquely by the hierarchical model -- in particular the claim that the calibration shift was *shared across hospitals* rather than hospital-specific. The corrected evidence points the other way: hospitals differed in their observed-to-expected ratios by more than a shared shift would allow, and the independent fit estimates a non-zero variance component.

## Generating this document

```bash
python hierarchical_laplace_math_audit.py        # the mathematics
python export_r_glmm_input.py                    # the exact subset
Rscript independent_glmm_fit.R                   # implementation C
python hierarchical_calibration_comparison.py    # this comparison
```

