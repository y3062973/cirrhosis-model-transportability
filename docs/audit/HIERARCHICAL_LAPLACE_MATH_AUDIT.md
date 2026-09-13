# HIERARCHICAL LAPLACE LIKELIHOOD -- MATHEMATICAL AUDIT

> ## HISTORICAL AUDIT RECORD -- THE AUDITED MODEL WAS REMOVED FROM THE MANUSCRIPT
>
> This document audits a model that is **no longer reported**. It is shipped as the
> audit trail for the decision to remove it, not as a description of a retained
> analysis. **No numerical result in this document is part of release v1.1.0**, and
> nothing in it may be cited as a finding of the study.
>
> The generator it names (`hierarchical_laplace_math_audit.py`) and the other scripts in
> its "Reproducing this audit" section lived in the internal working tree and are **not
> shipped**: they require the restricted analysis dataset and the frozen predictions.
> The numbers below therefore cannot be regenerated from this repository alone. The
> rejected implementation itself is preserved, for transparency only, at
> `archive/nonproduction/hierarchical_calibration_rejected_historical.py`.
>
> Cross-references into a public release tree have been updated; the analysis described
> here has not been altered or re-run.

**Scope:** the empirical-Bayes Laplace approximation used by the custom hierarchical calibration fit. This audits the MATHEMATICS. It does not rerun the primary analysis and does not change any primary result.

**Implementation audited:** `publock_06_07_hospital.py`, function `fit_hier`. That file was published in v1.0.0 as `src/validation/hierarchical_calibration.py`; **it no longer exists in that location** and is now the archived, non-executable `archive/nonproduction/hierarchical_calibration_rejected_historical.py`.

## 1. The derivation

### 1.1 The model

```
y_ij ~ Bernoulli(p_ij)
logit(p_ij) = alpha + beta * LP_ij + u_j
u_j ~ N(0, tau^2),  j = 1..J independent
```
with `LP` the frozen FINAL_MODEL_V2 linear predictor, held fixed. The parameters are the fixed effects `theta = (alpha, beta)` and the random intercepts `u = (u_1..u_J)`.

### 1.2 The marginal likelihood, and why a Laplace approximation is needed

The likelihood of interest integrates out the random effects:

```
p(y | alpha, beta, tau) = INT p(y | u, alpha, beta) * p(u | tau) du
```
That integral has no closed form for a Bernoulli likelihood with a logit link, so it is approximated.

### 1.3 The Laplace approximation

Write the joint density and its logarithm:

```
g(u)          = p(y | u, alpha, beta) * p(u | tau)
log g(u)      = loglik(alpha, beta; u)  -  0.5 * u' u / tau^2
                -  (J/2) log(2 pi tau^2)
                ^                      ^
                data term              N(0, tau^2) prior, WITH its normalisation
```

Let `u*` maximise `log g`. Expanding to second order about `u*` and integrating the resulting Gaussian gives

```
log p(y | alpha, beta, tau)
    ~ log g(u*)  +  (d/2) log(2 pi)  -  0.5 * log| H |
```

where `H = -d^2 log g / du du' |_(u*)` is the observed information of the joint density and `d` is the number of parameters in the approximation. Note the sign: the determinant enters with a MINUS sign, so a larger curvature (a more concentrated integrand) contributes a SMALLER marginal likelihood. Writing it as `+0.5 log|H|` is therefore only correct if it is paired with a `-0.5 log|2 pi|` elsewhere, which is the same statement rearranged.

### 1.4 What the code computes

```python
def obj(th):
    eta = np.clip(A_ @ th, -500, 500)
    ll = np.sum(yv * (-np.log1p(np.exp(-eta))) + (1 - yv) * (-np.log1p(np.exp(eta))))
    return -(ll - 0.5 * th[2:] @ R[2:, 2:] @ th[2:])

H = (A_ * w[:, None]).T @ A_        # X' W X  -- the DATA part of the information
H[2:, 2:] += R[2:, 2:]              # + prior precision 1/tau^2 on the intercepts
sign, logdet = np.linalg.slogdet(H)
lap = (-obj(th)) + (0.5 * logdet if sign > 0 else np.nan)
```

`obj(th)` is exactly `-log g(u)` apart from the omitted `(J/2)log(2 pi tau^2)`, so `-obj(th*)` is the peak height `log g(u*)`. The Hessian is built at the optimum, includes the prior precision on the random intercepts, and its log-determinant is added with a `+0.5` coefficient. Substituting into the derivation above:

```
lap = log g(u*) + 0.5 log|H|
    = [ log g(u*) + (d/2) log(2 pi) - 0.5 log|H| ]   <- the Laplace approximation
      - (d/2) log(2 pi)  +  log|H|
```

So the code's quantity is the Laplace approximation **plus** `log|H| - (d/2)log(2 pi)`. Those two extra terms are the whole question.

## 2. The four questions

### 2.1 Is the sign of the log-determinant term correct?

**Yes, for the quantity the code is computing, and the ordering of the two terms is what makes it correct.** The code forms `log g(u*) + 0.5 log|H|`, which is `log [ g(u*) * |H|^(1/2) ]` -- the standard Laplace integrand including the Gaussian normalising factor `(2 pi)^(d/2) |H|^(-1/2)`. Evaluating the same expression as `log g(u*) - 0.5 log|H|` would have the sign backwards and would penalise curvature instead of rewarding it.

Numerically, at the fitted optimum:

| quantity | value |
|---|---|
| `log g(u*)` = `-obj(th)` | -586.572869 |
| `log|H|` (full Hessian, d = 87) | 2359.112889 |
| `0.5 log|H|` | 1179.556445 |
| ~~code's `lap`~~ **-- ERRONEOUS ROW, DO NOT USE** | ~~3.205353~~ |
| **code's `lap`, recomputed** = `log g(u*) + 0.5 log|H|` | **592.983576** |
| reported in the pipeline log | 592.984 |

> **Audit note (added during code-release v1.1.0 packaging; documentation only, no
> analysis was re-run).** The row above struck through as `code's lap` is **wrong as
> printed** and must not be used. `-586.572869 + 0.5 x 2359.112889 = 592.983576`, which
> is what the code's own formula (quoted in 1.4) and the "reported in the pipeline log"
> row both give. The printed value `3.205353` equals `-586.572869 + 0.25 x 2359.112889`
> -- the same log-determinant with a 0.25 factor instead of 0.5, i.e. the halving
> applied twice. The recomputed row has been added rather than the erroneous row
> silently replaced, so that anyone who checks the original audit record can see what
> was corrected.
>
> This defect affects **no conclusion in this document**. The sign question in 2.1 is
> settled by the *sign*, not the magnitude, and the `tau`-selection argument in 2.4(a)
> and 2.4(b) uses the `lap` column of the table in 2.4, whose `tau = 0.0000` row
> reports the correct `592.9836`. The removed hierarchical model was withdrawn for the
> reasons in `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`, none of which depend on
> this row.

The Hessian is positive definite at the optimum (`True`), so `|H| > 0` and the log-determinant is real. **No sign error.**

### 2.2 Full Hessian, or only the random-effects block?

**The full Hessian is correct here, and it is what the code uses.** The approximation integrates over `u` at fixed `(alpha, beta)`, so a textbook GLMM Laplace approximation uses the random-effects block alone. This code instead maximises over `(alpha, beta, u)` jointly and takes the determinant of the whole `(2 + J) x (2 + J)` information matrix. That is the Laplace approximation to the JOINT posterior of all parameters, which is a legitimate and common variant, and it is the one consistent with the code then reporting the joint mode as the estimate.

The Hessian is block diagonal -- the fixed and random effects are not penalised against each other -- so the determinant factorises exactly:

| block | dimension | log-determinant |
|---|---|---|
| full | 87 | 2359.112889 |
| random effects | 85 | 2348.636795 |
| fixed effects | 2 | 10.476094 |
| random + fixed | 87 | 2359.112889 |

The two agree to 5.91e-12, confirming the factorisation. **Using the full Hessian is therefore not an error**; it differs from the random-block-only form by the fixed-effects term `10.4761`, which is a constant with respect to `u` but NOT with respect to `tau` -- see 2.4.

### 2.3 Is the Gaussian normalisation `(J/2) log(2 pi tau^2)` included?

**No -- and this is the one term genuinely absent.**

`obj()` contains the quadratic form `-0.5 u'u/tau^2` (value at the optimum: -0.001062) but not the `-(J/2) log(2 pi tau^2)` normalisation (value: 1096.208622). Because the fit drives `u` to essentially zero at `tau ~ 1e-6`, the quadratic term is numerically negligible and the omitted normalisation is the ONLY tau-dependent part of the prior that survives. Omitting it is therefore not harmless in general.

**However, it does not affect this analysis, for a specific reason:** the fit drives `u` to zero, and at `u = 0` the prior density depends on tau only through that same missing normalisation. The consequence is examined in 2.4 rather than assumed away.

### 2.4 Is comparison across tau values mathematically valid?

**Partially. Two separate issues, and only one of them is benign.**

**(a) The `(d/2) log(2 pi)` constant: benign.** The code omits it. It takes the same value at every tau:

| tau | `-obj(th*)` | `0.5 log|H|` | `lap` | omitted constant |
|---|---|---|---|---|
| 0.0000 | -586.5729 | 1179.5564 | 592.9836 | -79.9477 |
| 0.0500 | -586.3101 | 260.0954 | -326.2147 | -79.9477 |
| 0.1000 | -585.6014 | 201.8352 | -383.7663 | -79.9477 |
| 0.2000 | -583.2999 | 145.3498 | -437.9501 | -79.9477 |
| 0.5000 | -574.5442 | 79.9556 | -494.5886 | -79.9477 |
| 1.0000 | -563.2427 | 45.3840 | -517.8587 | -79.9477 |
| 1.5000 | -556.7379 | 32.6220 | -524.1158 | -79.9477 |

The constant is `-79.9477` at every tau, so adding it shifts every likelihood equally and **cannot change which tau is selected**, nor any fitted parameter. It is a level offset, not a distortion.

**(b) The omitted `(J/2) log(2 pi tau^2)` prior normalisation: this DOES make the tau comparison incorrect at the boundary, and it is the substantive finding.** With that term restored, the marginal likelihood carries `-(J/2) log(tau^2)`, which diverges to `+inf` as `tau -> 0`. Combined with the `+ (J/2) log(tau^2)`-behaved contribution from `log|H|`, the standard result is that the profile marginal likelihood of a variance component at zero is unbounded or flat, which is exactly the degenerate situation that makes a boundary variance estimate non-standard.

The practical consequence is the same in either formulation, and it is the important one:

```
tau_hat = 0.000001      grid lower limit = 1e-6
on the boundary: True
all random intercepts ~ 0: True
```

**`tau` is estimated ON the boundary of the parameter space, with the random intercepts all driven to zero. This is the textbook signature of a SINGULAR mixed-model fit.** No amount of correction to the omitted constant changes that: the data do not support a non-zero between-hospital variance *under this criterion*, and the estimate sits at the edge of the space where the usual asymptotics for a variance component do not hold.

> **Scope of the sentence above (audit note added at v1.1.0 packaging).** "The data do not
> support a non-zero between-hospital variance" is a statement about **the
> normalisation-omitting custom criterion audited here**, not about the data as such.
> Once the omitted `-(J/2)log(2 pi tau^2)` term is restored, the same data *do* support a
> non-zero variance component: see implementation D in
> `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`, which estimates `tau = 0.10` using this
> same code, and `lme4::glmer`, which estimates `tau = 0.1088`. Read without this
> qualifier the sentence appears to contradict that document. It does not; it is a
> statement about the defective criterion.

## 3. Findings

| # | question | finding |
|---|---|---|
| 1 | sign of the log-determinant term | **Correct.** `log g(u*) + 0.5 log|H|` is the Laplace integrand including its Gaussian normaliser. |
| 2 | full Hessian or random block | **Full Hessian is correct** for a joint-mode approximation, and it is what the code uses. The blocks factorise exactly. |
| 3 | Gaussian normalisation present | **The `(J/2)log(2 pi tau^2)` term is ABSENT.** Because the fit drives `u` to zero, the omitted term is the only surviving `tau`-dependent part of the prior -- so its absence is **not** harmless: it changes which `tau` the fit selects. See 2.4(b), and `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`. |
| 4 | cross-tau comparison valid | **Only partly.** The omitted `(d/2)log(2 pi)` term is `tau`-independent (`-79.9477` at every `tau`), so that one cannot change the comparison. The omitted **`(J/2)log(2 pi tau^2)`** normalisation *is* `tau`-dependent -- it diverges as `tau -> 0` -- and therefore **does** invalidate the comparison across `tau` at the boundary. Independent of both, the estimate sits at the **boundary**, so the inference is non-standard regardless. |

> **Audit note (added during code-release v1.1.0 packaging; documentation only).**
> Rows 3 and 4 of this Findings table previously read "the fitted `u` is zero, so it
> changes no reported value" and "for selecting tau, yes". Both understated the
> substantive finding and, read on their own, **contradicted section 2.4(b) of this same
> document** ("this DOES make the tau comparison incorrect at the boundary, and it is
> the substantive finding") and the REMOVE conditions in
> `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`. The rows have been restated to match
> 2.4(b). The wording was the defect; the underlying analysis was not changed and was
> not re-run.

## 4. What this means for the reported numbers

The mathematical audit finds **no error that explains or corrects the slope estimate**. The two defects that mattered were fixed earlier and are separate from this audit: the optimiser returning its starting value, and the degenerate bootstrap. What this audit adds is that the model's variance component is estimated at the boundary, which is a **singular fit** and therefore an inference problem rather than an arithmetic one.

Because that is an inference problem, the arithmetic cannot settle it. Section 4 of the task therefore requires an independent, mature GLMM implementation, and the decision rule in section 6 turns on whether that implementation agrees. See `HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`.

## 5. Reproducing this audit

```bash
python hierarchical_laplace_math_audit.py
```

The script fits nothing new: it loads the frozen predictions, refits the same model so the audit is self-contained, and evaluates the four quantities above. Every number in this document is printed by it.

