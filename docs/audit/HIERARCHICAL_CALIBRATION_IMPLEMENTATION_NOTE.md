# HIERARCHICAL CALIBRATION -- IMPLEMENTATION NOTE

> ## HISTORICAL NOTE -- THE MODEL IT DESCRIBES WAS REMOVED FROM THE MANUSCRIPT
>
> **Read the status below before the rest of this note. The note was written while the
> repair was still believed to be the final state. It is not.**
>
> | stage | outcome |
> |---|---|
> | original implementation | slope returned at its starting value after one iteration; defect identified |
> | repair (multi-start) | slope located; this note describes that state |
> | independent verification | `lme4::glmer` disagreed materially about the variance component |
> | **final decision** | **the model was judged insufficiently reliable and REMOVED from the manuscript** |
>
> **No hierarchical numerical result is part of release v1.1.0.** In particular, the
> sentence below stating that "the manuscript's hierarchical numbers have been
> regenerated to match" describes the repaired-but-still-retained state, which
> **superseded** the state this note documents. The manuscript reports **no**
> hierarchical calibration numbers at all: the hospital-level evidence is reported
> descriptively, as observed-to-expected ratios per hospital, and no formal hierarchical
> calibration-heterogeneity conclusion is reported.
>
> The file this note names (`publock_06_07_hospital.py` / the v1.0.0 release's
> `src/validation/hierarchical_calibration.py`) **no longer exists in the pipeline**. The
> rejected implementation is preserved, non-executable and clearly marked, at
> `archive/nonproduction/hierarchical_calibration_rejected_historical.py`. The retained hospital
> analyses live in `src/validation/hospital_analysis_and_recalibration.py`.
>
> This note is retained because it is the clearest account of the *first* defect -- the
> optimiser returning its starting value -- which is still worth understanding. Read it
> together with `HIERARCHICAL_LAPLACE_MATH_AUDIT.md` (the mathematics) and
> `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` (the removal decision).

**Question asked:** was the reported common calibration slope of 1.0000 (A) freely estimated from the data, or (B) fixed to 1.0 / implemented as an offset / otherwise constrained?

> ## ANSWER: neither, and the distinction is the finding.
>
> The slope is **NOT fixed**. `beta` is an unpenalised free parameter with its own column in the design matrix, and nothing in the code pins it to 1.0.
>
> **But the published 1.0000 was not estimated either.** The optimiser returned it after **exactly one iteration**, having made no numerical movement from its starting value of 1.0. The value in the manuscript was the **starting value the fit accepted**, not a located maximum.

The authors authorised the repair (Option 1). The fit now locates the slope. **This note documents both the original state and the corrected one, and the manuscript's hierarchical numbers have been regenerated to match.** *(Superseded -- see the status box above: the model was subsequently removed from the manuscript entirely, and no hierarchical number is reported in v1.1.0.)*

## 1. Source

| item | value |
|---|---|
| file | `publock_06_07_hospital.py` (published in v1.0.0 as `src/validation/hierarchical_calibration.py`; **now archived, not executed**: `archive/nonproduction/hierarchical_calibration_rejected_historical.py`) |
| section | `SECTION 6C -- HIERARCHICAL CALIBRATION (random hospital intercept)` |
| function | `fit_hier(hid, lp, yv, J, Sigma, alpha0=None, starts=6)` |
| helper | `build_A(hid, lp, J, slot)` |
| estimator | empirical-Bayes Laplace approximation, grid search over tau |
| optimiser | `scipy.optimize.minimize`, `L-BFGS-B`, `maxiter=20000`, `ftol=1e-14`, `gtol=1e-10` |
| data | eICU cohort: 85 hospitals, 1,390 cohort rows, 313 deaths |

## 2. The model formula, as implemented

```
logit(P(Y_ij = 1)) = alpha + u_j + beta * LP_ij
                     u_j ~ N(0, tau^2)

Y_ij   in-hospital mortality for ICU stay i in hospital j (eICU cohort)
LP_ij  linear predictor of the FROZEN FINAL_MODEL_V2 model, transported unchanged
alpha  fixed intercept: the shared calibration-in-the-large shift, logit scale
u_j    hospital random intercept
tau    SD of the random intercepts, selected on a grid by marginal likelihood
beta   COMMON CALIBRATION SLOPE -- a free, unpenalised parameter
```

The pipeline's own log states the formula and the estimator:

```
log("  logit(Y_ij) = alpha + u_j + beta * LP_ij ,  u_j ~ N(0, tau^2)")
log("  LP is the FINAL_MODEL_V2 linear predictor. Fitted by empirical-Bayes Laplace")
log("  with a grid over tau, over ALL hospitals with >=1 event and >=1 non-event.")
```

## 3. The code, and what it showed

**(a) `beta` has its own free column**, separate from `alpha` and from the random intercepts:

```python
def build_A(hid, lp, J, slot):
    A_ = np.zeros((len(hid), 2 + slot.shape[0]))
    A_[:, 0] = 1.0     # column 0 -> alpha, the fixed intercept
    A_[:, 1] = lp      # column 1 -> beta,  the common slope  <-- FREE
    for j in range(J):
        A_[hid == j, 2 + slot[j, 0]] = 1.0   # remaining columns -> u_j
    return A_
```

**(b) The penalty applies ONLY to the random intercepts**, so `beta` is unpenalised -- the first two entries of `R` are zero and `th[2:]` excludes both fixed effects:

```python
R = np.diag(np.concatenate([[0, 0], np.full(ncol, Sinv[0, 0])]))

def obj(th):
    eta = np.clip(A_ @ th, -500, 500)
    ll = np.sum(yv * (-np.log1p(np.exp(-eta))) + (1 - yv) * (-np.log1p(np.exp(eta))))
    return -(ll - 0.5 * th[2:] @ R[2:, 2:] @ th[2:])   # th[2:] excludes alpha, beta
```

**(c) The ORIGINAL starting point -- this is the defect.** Every random intercept started at exactly zero, where the objective is flat and the finite-difference gradient vanishes. `nit = 1` confirms the optimiser stopped immediately:

```python
th0 = np.zeros(2 + ncol)
th0[0] = alpha0   # data-driven start for the fixed intercept
th0[1] = 1.0      # STARTING VALUE for beta
th0[2:] = 0.0     # every random intercept at exactly 0  <-- the flat point
r = minimize(obj, th0, method='L-BFGS-B',
             options=dict(maxiter=20000, maxfun=200000, ftol=1e-14, gtol=1e-10))
th = r.x          # alpha, beta and u_j read straight back out
```

There is no `bounds` argument, no `offset=lp`, and no post-hoc reset. The value reported in Table 4 is whatever `th[1]` held when the optimiser stopped -- which was its starting value.

**(d) The repaired starting points** now include a perturbed one, which is what leaves the flat region:

```python
for k in range(int(starts)):
    s0 = np.zeros(2 + ncol); s0[0] = alpha0; s0[1] = 1.0
    if k == 1:            s0[1] = beta_naive          # method-of-moments beta
    elif k == 2 and starts > 3:
        s0[1] = beta_naive; s0[2:] = rng_fit.normal(0, 0.3, ncol)
    elif k >= 3 or (starts <= 3 and k == starts - 1):
        s0[0] = alpha0 + rng_fit.normal(0, 0.25)      # PERTURBED
        s0[1] = clip(1.0 + rng_fit.normal(0, 0.25), 0.2, 3.0)
        s0[2:] = rng_fit.normal(0, 0.5, ncol)
    starts_vectors.append(s0)
best_r = min((minimize(obj, s, ...) for s in starts_vectors), key=lambda r: r.fun)
```

## 4. What was measured

### 4.1 The original fit accepted its starting values

| fit | alpha | beta | neg. log-lik. | iterations |
|---|---|---|---|---|
| original: single run from beta = 1.0, u_j = 0 | -0.0962280000 | 1.0000000000 | 592.571000 | **1** |
| multi-start, best objective kept | -0.0751360000 | 1.0572680000 | 592.984000 | 18 |

`nit = 1` reproduces the pipeline's own logged output exactly: alpha = -0.0962, beta = +1.0000, tau = 0.0000, "converged=True". That is the signature of an optimiser satisfying its convergence tests at the point it was placed, not of an optimum found.

### 4.2 The likelihood is genuinely flat, so no precision was lost

| profile diagnostic | value |
|---|---|
| profile-likelihood maximum over a beta grid | beta = 1.05 |
| 95% profile interval | 0.95 to 1.20 |
| beta = 1.00 relative to the profile optimum | inside the 95% interval |

So the data cannot distinguish beta = 1 from beta = 1.06. The defect is not that the **number was wrong**; it is that the number was **not located**, and an interval was reported beside it as though it had been.

### 4.3 The cluster bootstrap never moved beta

In the original bootstrap, across every replicate beta had standard deviation **0.0** -- it was identically 1.0 -- while alpha varied normally. The reported beta interval of exactly (1.0000, 1.0000) was therefore a faithful summary of a bootstrap that never perturbed the parameter, not a measure of its uncertainty.

### 4.4 A repair that FAILED, and why it is recorded

The first attempt warm-started the bootstrap from the located point estimate, to save the cost of re-running the multi-start 300 times. **It did not work.** Starting at the point estimate means starting with near-zero intercepts, which is the flat point again, so the gradient vanished and every replicate returned its starting values:

| test | result |
|---|---|
| bootstrap replicates that moved off the warm start | **0 of 6** |

That is the original defect reproduced, not a cure. It is recorded because the obvious optimisation is wrong here for a non-obvious reason, and the next person to touch this code will otherwise try it.

The design that replaced it: the point estimate keeps six starts (it must **find** the optimum); the bootstrap uses three, including the perturbed start that moves, and narrows its tau grid to the neighbourhood of the point estimate rather than re-searching 0.05 to 1.5 in every replicate. Verified before use: the bootstrap now moves both parameters (beta sd 0.052, alpha sd 0.071 over 30 test replicates).

## 5. The corrected values, and one consequence for the manuscript

| quantity | published | corrected |
|---|---|---|
| common calibration slope | 1.0000 | **1.0573** (0.9772 to 1.1657) |
| fixed intercept shift | -0.0962 | **-0.0751** (-0.2222 to 0.0651) |
| between-hospital SD (tau) | 0.000001 | 0.000001 (unchanged) |
| Laplace marginal log-likelihood | 592.571 | 592.984 |

**The slope conclusion is unchanged and in fact better supported.** The corrected slope is 1.0573 with an interval that includes 1, so the model still gives no evidence that the risk gradient was distorted on transport -- now on the strength of a located estimate rather than an assumed one.

**The intercept conclusion is weakened and the manuscript has been changed to say so.** The published interval (-0.2256 to -0.0002) excluded zero by two ten-thousandths. The corrected interval (-0.2222 to 0.0651) **includes** zero. The hierarchical model therefore does not, on its own, establish a non-zero level shift. The direct evidence for the level shift is the held-out O/E ratio of 0.8582 with an interval excluding 1, which is unaffected by this repair. The manuscript now states the distinction explicitly.

**What the repair does not affect:** the primary external validation, the O/E ratio, discrimination, the meta-analysis of hospital AUROC, the recalibration analysis, and every table and figure other than the hierarchical row of Table 4. The change is confined to the OPTIMISATION of one secondary model.

## 6. The function's own docstring predicted this

`fit_hier` carried -- and now carries an expanded version of -- this warning:

```python
"""...
Starting values matter: the previous run returned alpha=0, beta=1 exactly --
the starting point -- because L-BFGS-B stopped on a flat plateau with the
default tolerances. alpha is now initialised from the observed/expected odds
ratio and the tolerances are tightened.
"""
```

An earlier run had returned **both** parameters at their starting values, and the fix re-initialised **alpha** only. `beta` kept a fixed start of 1.0. The remedy was applied to one parameter and not the other, which is exactly the circumstance in which a parameter can be reported at its initialisation unnoticed: `converged=True` is printed, and nothing in the output flags that no movement occurred.

## 7. Verification available to an independent reader

`archive/nonproduction/hierarchical_calibration_rejected_historical.py` contains the fit exactly as used, including the starting values and their multi-start structure, so the hazard and its repair are both visible. It is marked **HISTORICAL IMPLEMENTATION -- NOT USED IN THE FINAL MANUSCRIPT -- DO NOT USE FOR INFERENCE**, it is not part of the reproduction pipeline, and it refuses to execute if run directly.

The patcher that applied the multi-start change, `apply_hierarchical_beta_fix.py` (referred to elsewhere as `fix_hierarchical_beta.py` / `src/model/apply_hierarchical_beta_fix.py`), **is not shipped** and the `src/model/` directory does not exist in this repository. It edited a file at a path that is not present here, so shipping it would have given a reader a script that fails on a missing target. The change history it would have applied is described in this note and in `CHANGELOG.md`, and the repaired code it produced is the code now archived.

## 8. Status of this note

**Superseded by the removal.** This note describes the state after the multi-start repair, when the model was still intended to be reported. The subsequent independent verification found that a mature implementation (`lme4::glmer`) disagreed materially about the variance component, and the model was removed rather than repaired further. See `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` and `HIERARCHICAL_LAPLACE_MATH_AUDIT.md`.

**No number in this note is part of release v1.1.0.** The table in section 5, in particular, is a record of a withdrawn intermediate state, not a result.

`REPRODUCIBILITY.md` and `CHANGELOG.md` both point here, and both label this material as historical.

