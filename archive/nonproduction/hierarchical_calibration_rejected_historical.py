# =============================================================================
# HISTORICAL IMPLEMENTATION -- NOT USED IN THE FINAL MANUSCRIPT -- DO NOT USE FOR INFERENCE
# =============================================================================
#
# ARCHIVED AUDIT ARTEFACT. NOT PRODUCTION ANALYSIS CODE. NOT EXECUTED BY ANY PART OF
# THE PUBLIC REPRODUCTION PIPELINE. DO NOT RUN IT, DO NOT IMPORT IT, AND DO NOT USE
# ANY NUMBER IT PRODUCES FOR ANY PURPOSE.
#
# WHAT THIS FILE IS
# -----------------
# The complete internal implementation of the custom hierarchical (mixed-effects)
# logistic calibration model that the working tree's `publock_06_07_hospital.py`
# carried as "section 6C": a random intercept per hospital with a common calibration
# slope, fitted by an empirical-Bayes Laplace approximation over a grid of the
# between-hospital variance component `tau`.
#
# WHY IT IS HERE
# --------------
# The model was audited and **REMOVED from the manuscript as unreliable** in
# publication/release v1.1.0. The audit found, in order of severity:
#
#   1. The custom Laplace criterion was mathematically incomplete. It omitted the
#      Gaussian prior normalisation term `-(J/2) log(2 pi tau^2)`. That term is NOT
#      constant in tau -- it diverges as tau approaches zero -- so the reported
#      variance component was not selected by the approximation it was reported as.
#   2. An independent, mature implementation (`lme4::glmer`, R 4.6.0, lme4 2.0.6)
#      converged cleanly and estimated `tau = 0.109`, against this fit's `1e-06` with
#      all 85 random intercepts exactly zero. The two implementations disagreed
#      materially about the quantity of interest.
#   3. An earlier run of the same code returned the common slope at the optimiser's
#      starting value of 1.0 after a single iteration, with a degenerate confidence
#      interval at (1, 1), because every random intercept also started at zero. It was
#      repaired to a multi-start optimisation (the repair is visible in `fit_hier`
#      below, including its AUTHORISED FIX comment block); it was then withdrawn
#      entirely when the independent fit disagreed.
#
# The reasoning, the mathematics and the three-way comparison are documented in:
#   * `docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md`
#   * `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md`
#   * `docs/audit/LOCKED_RELEASE_CODE_VERIFICATION.md`
#
# WHAT THIS FILE IS NOT
# ---------------------
# * It is NOT part of the reproduction pipeline. The retained hospital-level analyses
#   live in `src/validation/hospital_analysis_and_recalibration.py`, which contains no
#   mixed-effects fitting at all.
# * It produced NO result reported in manuscript v3.2 or in release v1.1.0. No
#   hierarchical numerical result is part of v1.1.0.
# * It must NOT be cited as the final reported model, and nothing in it may be
#   described as a retained analysis.
#
# WHY IT IS PRESERVED AT ALL
# --------------------------
# Transparency. A reader is entitled to see exactly what was fitted, what went wrong,
# and how the removal decision was reached, rather than being told only the
# conclusion. Preserving the rejected code in an unambiguous archive is the honest
# option; deleting it would leave the audit record unverifiable.
#
# THE ARCHIVED CODE BELOW IS HISTORICAL. IT IS RETAINED FOR AUDIT ONLY. IT HAS NOT BEEN
# RE-VERIFIED, ITS DEPENDENCIES ARE NOT PINNED FOR IT, AND EXECUTING IT IS UNSUPPORTED.
#
# -----------------------------------------------------------------------------
# Original filename in the working tree: `publock_06_07_hospital.py` (section 6C)
# Published in v1.0.0 as:                 `src/validation/hierarchical_calibration.py`
# Archived in v1.1.0 as:                  `archive/nonproduction/hierarchical_calibration_rejected_historical.py`
# State archived:                         post-repair (multi-start), pre-removal
# -----------------------------------------------------------------------------
# =============================================================================



def main() -> None:
    """HISTORICAL FIT -- retained for audit only. Refuses to run."""
    raise SystemExit(
        "REFUSING TO RUN: this is the rejected hierarchical calibration model,"
        " archived for audit history only. It is not part of the reproduction"
        " pipeline and no number it produces may be used for inference. See the"
        " header of this file and docs/audit/ for the audit that removed it."
    )


def _archived_code_for_audit_reference_only() -> None:
    """The historical implementation, verbatim except for indentation."""
    import io
    import os
    import sys
    import warnings

    import numpy as np
    import pandas as pd
    from scipy import stats
    from scipy.special import expit

    warnings.filterwarnings("ignore")
    FR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, FR)
    import final_analysis_config as cfg  # noqa: E402
    import provenance as prov  # noqa: E402

    DATA = os.path.join(FR, "data")
    TABLES = os.path.join(FR, "tables")
    LOGS = os.path.join(FR, "logs")
    LOG = io.StringIO()
    OUT = "hospital_mortality"
    MIN_N, MIN_D = cfg.MIN_HOSPITAL_N, cfg.MIN_HOSPITAL_DEATHS


    def log(m=""):
        m = str(m).encode("ascii", "replace").decode("ascii")
        print(m)
        LOG.write(m + "\n")


    def ici(p, y, bins=10):
        """Integrated Calibration Index: mean |observed - predicted| over deciles."""
        p = np.asarray(p, float); y = np.asarray(y, float)
        q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
        if len(q) < 3:
            return np.nan
        idx = np.clip(np.digitize(p, q[1:-1]), 0, len(q) - 2)
        tot = 0.0
        for b in np.unique(idx):
            m = idx == b
            tot += m.sum() * abs(y[m].mean() - p[m].mean())
        return float(tot / len(p))


    def emax(p, y, bins=10):
        """Maximum absolute decile-level observed-minus-predicted difference."""
        p = np.asarray(p, float); y = np.asarray(y, float)
        q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
        if len(q) < 3:
            return np.nan
        idx = np.clip(np.digitize(p, q[1:-1]), 0, len(q) - 2)
        worst = np.nan
        for b in np.unique(idx):
            m = idx == b
            d = abs(y[m].mean() - p[m].mean())
            worst = d if not np.isfinite(worst) else max(worst, d)
        return float(worst)


    prov.announce("publock_06_07_hospital.py")
    A = pd.read_csv(os.path.join(DATA, "analysis_dataset.csv"), low_memory=False)
    P = pd.read_csv(os.path.join(DATA, "predictions.csv"), low_memory=False)
    A = A.merge(P[["centre", "stay_id", "p_model"]], on=["centre", "stay_id"], how="left")
    e = A[(A.centre == "eICU")].dropna(subset=["hospitalid", "p_model"]).copy()
    e["hospitalid"] = e.hospitalid.astype(int)
    y = e[OUT].values.astype(float)
    p = e.p_model.values.astype(float)
    hid = e.hospitalid.values
    log(f"  eICU: n={len(e):,}  events={int(y.sum()):,}  hospitals={e.hospitalid.nunique()}")

    # ===================================================================== 6A descriptive
    log("\n" + "=" * 100)
    log("SECTION 6A -- PER-HOSPITAL DESCRIPTIVE ANALYSIS")
    log("=" * 100)
    rows = []
    for h, g in e.groupby("hospitalid"):
        yy = g[OUT].values.astype(float)
        pp = g.p_model.values.astype(float)
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        auc = prov.auroc(yy, pp) if (n1 >= 2 and n0 >= 2) else np.nan
        sl = prov.cal_slope_intercept(yy, pp)[0] if (n1 >= 5 and n0 >= 5
                                                     and pp.std() > 0) else np.nan
        rows.append(dict(hospitalid=int(h), n=len(g), deaths=n1,
                         observed=float(yy.mean()), mean_predicted=float(pp.mean()),
                         oe=float(yy.mean() / pp.mean()) if pp.mean() > 0 else np.nan,
                         auroc=auc, calib_slope=sl,
                         teachingstatus=g.teachingstatus.iloc[0] if "teachingstatus" in g else None,
                         region=g.region.iloc[0] if "region" in g else None,
                         numbedscategory=g.numbedscategory.iloc[0] if "numbedscategory" in g else None))
    hl = pd.DataFrame(rows)
    hl["estimable_auroc"] = hl.auroc.notna()
    hl = hl.sort_values("n", ascending=False).reset_index(drop=True)
    hl.to_csv(os.path.join(DATA, "publock_hospital_descriptive.csv"), index=False,
              encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "publock_hospital_descriptive.csv"), "publock_06_07_hospital.py")
    log(f"  hospitals total                     : {len(hl)}")
    log(f"  with an estimable AUROC             : {int(hl.estimable_auroc.sum())}")
    for tag, sub in [("N>=20 & deaths>=5 (PRIMARY)", hl[(hl.n >= MIN_N) & (hl.deaths >= MIN_D)]),
                     ("N>=30 sensitivity", hl[(hl.n >= 30) & (hl.deaths >= MIN_D)])]:
        log(f"  {tag:<32} k={len(sub):>3}  stays={int(sub.n.sum()):>6,}  "
            f"deaths={int(sub.deaths.sum()):>5,}  "
            f"median AUROC={sub.auroc.median():.3f}  median O/E={sub.oe.median():.3f}")
    prim = hl[(hl.n >= MIN_N) & (hl.deaths >= MIN_D) & hl.auroc.notna()].copy()
    log(f"\n  primary per-hospital summary (k={len(prim)}):")
    log(f"    AUROC  median {prim.auroc.median():.3f}  "
        f"IQR {prim.auroc.quantile(.25):.3f}-{prim.auroc.quantile(.75):.3f}  "
        f"range {prim.auroc.min():.3f}-{prim.auroc.max():.3f}")
    log(f"    O/E    median {prim.oe.median():.3f}  "
        f"IQR {prim.oe.quantile(.25):.3f}-{prim.oe.quantile(.75):.3f}")
    log(f"    slope  median {prim.calib_slope.median():.3f}")

    # ===================================================================== 6B meta-analysis
    log("\n" + "=" * 100)
    log("SECTION 6B -- RANDOM-EFFECTS META-ANALYSIS OF PER-HOSPITAL AUROC")
    log("=" * 100)


    def hanley_se(auc, n1, n0):
        auc = min(max(auc, 1e-6), 1 - 1e-6)
        q1 = auc / (2 - auc)
        q2 = 2 * auc ** 2 / (1 + auc)
        se = np.sqrt((auc * (1 - auc) + (n1 - 1) * (q1 - auc ** 2) +
                      (n0 - 1) * (q2 - auc ** 2)) / (n1 * n0))
        return se / (auc * (1 - auc))       # logit scale


    def dl_meta(yi, sei):
        yi, sei = np.asarray(yi, float), np.asarray(sei, float)
        wi = 1 / sei ** 2
        fe = float(np.sum(wi * yi) / np.sum(wi))
        Q = float(np.sum(wi * (yi - fe) ** 2))
        k = len(yi)
        dfree = k - 1
        C = float(np.sum(wi) - np.sum(wi ** 2) / np.sum(wi))
        tau2 = max(0.0, (Q - dfree) / C) if C > 0 else 0.0
        wr = 1 / (sei ** 2 + tau2)
        re = float(np.sum(wr * yi) / np.sum(wr))
        se_re = float(np.sqrt(1 / np.sum(wr)))
        I2 = max(0.0, (Q - dfree) / Q) * 100 if Q > 0 else 0.0
        pQ = float(1 - stats.chi2.cdf(Q, dfree)) if dfree > 0 else np.nan
        return dict(k=k, pooled_logit=re, se=se_re, tau2=float(tau2), tau=float(np.sqrt(tau2)),
                    Q=Q, df=dfree, p_Q=pQ, I2=I2,
                    pooled=float(expit(re)),
                    ci_lo=float(expit(re - 1.96 * se_re)),
                    ci_hi=float(expit(re + 1.96 * se_re)))


    meta_rows = []
    for tag, sub in [("primary N>=20", prim),
                     ("sensitivity N>=30", hl[(hl.n >= 30) & (hl.deaths >= MIN_D) & hl.auroc.notna()]),
                     ("all estimable", hl[hl.auroc.notna()])]:
        sei = np.array([hanley_se(a, int(d), int(n - d))
                        for a, n, d in zip(sub.auroc, sub.n, sub.deaths)])
        yi = np.log(np.clip(sub.auroc, 1e-6, 1 - 1e-6) /
                    (1 - np.clip(sub.auroc, 1e-6, 1 - 1e-6)))
        m = dl_meta(yi, sei)
        m["analysis"] = tag
        meta_rows.append(m)
        log(f"\n  {tag}")
        log(f"    k={m['k']}  pooled AUROC = {m['pooled']:.4f} "
            f"({m['ci_lo']:.4f}, {m['ci_hi']:.4f})")
        log(f"    tau^2 = {m['tau2']:.5f}  tau = {m['tau']:.4f}")
        log(f"    Q = {m['Q']:.2f} (df {m['df']}, p = {m['p_Q']:.4g})   I^2 = {m['I2']:.1f}%")
    meta = pd.DataFrame(meta_rows)[["analysis", "k", "pooled", "ci_lo", "ci_hi",
                                    "tau2", "tau", "Q", "df", "p_Q", "I2"]]
    meta.to_csv(os.path.join(DATA, "publock_hospital_meta.csv"), index=False,
                encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "publock_hospital_meta.csv"), "publock_06_07_hospital.py")

    # ===================================================================== 6C hierarchical
    log("\n" + "=" * 100)
    log("SECTION 6C -- HIERARCHICAL CALIBRATION (random hospital intercept)")
    log("=" * 100)
    log("  logit(Y_ij) = alpha + u_j + beta * LP_ij ,  u_j ~ N(0, tau^2)")
    log("  LP is the FINAL_MODEL_V2 linear predictor. Fitted by empirical-Bayes Laplace")
    log("  with a grid over tau, over ALL hospitals with >=1 event and >=1 non-event.")


    def slots_for(J, flags):
        slot = np.full((J, 2), -1, dtype=np.int64)
        col = 0
        for j in range(J):
            slot[j, 0] = col
            col += 1
        return slot, col


    def build_A(hid, lp, J, slot):
        A_ = np.zeros((len(hid), 2 + slot.shape[0]))
        A_[:, 0] = 1.0
        A_[:, 1] = lp
        for j in range(J):
            A_[hid == j, 2 + slot[j, 0]] = 1.0
        return A_


    def fit_hier(hid, lp, yv, J, Sigma, alpha0=None, starts=6):
        """Empirical-Bayes Laplace fit of alpha, beta and the random intercepts.

        Starting values matter here, and this has now bitten twice. An early run returned
        alpha=0, beta=1 exactly -- the starting point -- because L-BFGS-B stopped on a flat
        plateau. That was fixed for alpha only, by initialising it from the observed/expected
        odds ratio; beta kept a fixed start of 1.0. The run that produced the published table
        then again returned beta = 1.0000 after ONE iteration, with every random intercept
        still at zero, and the cluster bootstrap inherited a degenerate (1, 1) interval.

        The fit now runs `starts` starting points -- including the original configuration, a
        moment-based beta, and at least one with the random intercepts perturbed away from
        zero -- and keeps the best objective, so the reported slope is a located maximum
        rather than an accepted initialisation.
        """
        from scipy.optimize import minimize
        slot, ncol = slots_for(J, None)
        A_ = build_A(hid, lp, J, slot)
        Sinv = np.linalg.inv(Sigma)
        R = np.diag(np.concatenate([[0, 0], np.full(ncol, Sinv[0, 0])]))

        def obj(th):
            eta = np.clip(A_ @ th, -500, 500)
            ll = np.sum(yv * (-np.log1p(np.exp(-eta))) + (1 - yv) * (-np.log1p(np.exp(eta))))
            return -(ll - 0.5 * th[2:] @ R[2:, 2:] @ th[2:])

        if alpha0 is None:
            mean_p = float(np.clip(np.mean(expit(lp)), 1e-6, 1 - 1e-6))
            obs = float(np.clip(np.mean(yv), 1e-6, 1 - 1e-6))
            alpha0 = float(np.log(obs / (1 - obs)) - np.log(mean_p / (1 - mean_p)))
        # ------------------------------------------------------------------------
        # AUTHORISED FIX (author decision, Option 1).
        #
        # This was a SINGLE run from a fixed starting point:
        #     th0[0] = alpha0 ;  th0[1] = 1.0 ;  th0[2:] = 0
        # With every random intercept starting at exactly 0 the objective is flat and the
        # finite-difference gradient vanishes, so L-BFGS-B returned after ONE iteration with
        # beta still at its starting value. The reported slope was an accepted initialisation,
        # and the bootstrap interval was degenerate at (1, 1) for the same reason.
        #
        # beta is a free unpenalised parameter (column 1 of A, excluded from the penalty), so
        # the correct repair is to LOCATE it: several starts, at least one with the
        # intercepts perturbed, keeping the best objective.
        # ------------------------------------------------------------------------
        rng_fit = np.random.default_rng(20250901)
        _lp_arr = np.asarray(lp)
        mu_p = float(np.clip(np.mean(expit(1.0 * _lp_arr)), 1e-6, 1 - 1e-6))
        ob_p = float(np.clip(np.mean(yv), 1e-6, 1 - 1e-6))
        _den = np.log(mu_p / (1 - mu_p))
        beta_naive = float(np.clip(np.log(ob_p / (1 - ob_p)) / _den, 0.2, 3.0)) \
            if abs(_den) > 1e-9 else 1.0

        starts = max(1, int(starts))
        starts_vectors = []
        for k in range(starts):
            s0 = np.zeros(2 + ncol)
            s0[0] = alpha0
            s0[1] = 1.0
            if k == 1:
                s0[1] = beta_naive
            elif k == 2 and starts > 3:
                s0[1] = beta_naive
                s0[2:] = rng_fit.normal(0.0, 0.3, ncol)
            elif k >= 3 or (starts <= 3 and k == starts - 1):
                # the perturbed start: the one that actually leaves the flat point
                s0[0] = alpha0 + rng_fit.normal(0.0, 0.25)
                s0[1] = float(np.clip(1.0 + rng_fit.normal(0.0, 0.25), 0.2, 3.0))
                s0[2:] = rng_fit.normal(0.0, 0.5, ncol)
            starts_vectors.append(s0)

        best_r = None
        for th0 in starts_vectors:
            rr = minimize(obj, th0, method="L-BFGS-B",
                          options=dict(maxiter=20000, maxfun=200000,
                                       ftol=1e-14, gtol=1e-10))
            if best_r is None or rr.fun < best_r.fun:
                best_r = rr
        r = best_r
        th = r.x
        eta = np.clip(A_ @ th, -500, 500)
        mu = expit(eta)
        w = np.maximum(mu * (1 - mu), 1e-9)
        H = (A_ * w[:, None]).T @ A_
        H[2:, 2:] += R[2:, 2:]
        sign, logdet = np.linalg.slogdet(H)
        lap = (-obj(th)) + (0.5 * logdet if sign > 0 else np.nan)
        return th, lap, A_, r


    J = int(hid.max()) + 1
    lp = prov.logit(p)
    keep = np.ones(J, bool)
    agg = e.groupby("hospitalid")[OUT].agg(["size", "sum"])
    for h, r_ in agg.iterrows():
        j = int(np.searchsorted(np.unique(hid), h))
    # rebuild contiguous ids over eligible hospitals
    elig_ids = agg[(agg["sum"] >= 1) & ((agg["size"] - agg["sum"]) >= 1)].index.astype(int)
    emask = np.isin(hid, elig_ids)
    e2 = e[emask].copy()
    e2["hid"] = pd.Categorical(e2.hospitalid).codes
    Je = int(e2.hid.max()) + 1
    lp2 = prov.logit(e2.p_model.values.astype(float))
    y2 = e2[OUT].values.astype(float)
    log(f"  hospitals contributing: {Je}   patients: {len(e2):,}   deaths: {int(y2.sum()):,}")

    best = None
    for tau in np.concatenate([[1e-6], np.arange(0.05, 1.51, 0.05)]):
        th, lap, A_, r_ = fit_hier(e2.hid.values, lp2, y2, Je, np.array([[max(tau, 1e-6) ** 2]]))
        if not np.isfinite(lap):
            continue
        if best is None or lap > best[1]:
            best = (th, lap, tau, A_, r_)
    th, lap, tau_hat, A_, r_ = best
    alpha, beta = float(th[0]), float(th[1])
    log(f"\n  alpha (fixed intercept) = {alpha:+.4f}")
    log(f"  beta  (common slope)    = {beta:+.4f}")
    log(f"  tau   (SD of u_j)       = {tau_hat:.4f}")
    log(f"  Laplace marginal loglik = {lap:.3f}   converged={r_.success}")

    # cluster bootstrap on alpha/beta
    rng = np.random.default_rng(cfg.RANDOM_SEED + 2)
    bt_a, bt_b, bt_t = [], [], []
    uniq_h2 = np.unique(e2.hospitalid.values)
    for _ in range(300):
        sel = rng.choice(uniq_h2, size=len(uniq_h2), replace=True)
        idx = np.concatenate([np.where(e2.hospitalid.values == h)[0] for h in sel])
        eb = e2.iloc[idx].copy()
        eb["hid"] = pd.Categorical(eb.hospitalid).codes
        Jb = int(eb.hid.max()) + 1
        if eb[OUT].nunique() < 2:
            continue
        # --- bootstrap configuration -------------------------------------------------
        #
        # The bootstrap re-fits 300 times, so it must be cheaper than the point estimate
        # without reintroducing the defect. Two changes, both justified by the data:
        #
        #  * `starts=3` instead of 6. The third start is the PERTURBED one, retained because
        #    it is the start that actually leaves the flat point. Warm-starting from the point
        #    estimate was tried first and rejected: it begins with near-zero intercepts, the
        #    gradient vanishes, and every replicate returned its starting values (measured:
        #    0 of 6 test replicates moved).
        #
        #  * the tau search is narrowed to the neighbourhood of the point estimate. tau is
        #    estimated at the boundary of the parameter space with a degenerate interval, so
        #    re-searching 0.05 to 1.5 in every replicate spends the whole budget where the
        #    estimate says the answer is not. Five candidates are kept so a replicate can
        #    still prefer a small non-zero tau.
        _t0 = max(tau_hat, 1e-6)
        _taus = np.unique(np.clip(np.array([1e-6, _t0, _t0 + 0.01, 0.02, 0.05]),
                                  1e-6, None))
        bb = None
        for tt in _taus:
            thb, lapb, _, _ = fit_hier(eb.hid.values, prov.logit(eb.p_model.values.astype(float)),
                                       eb[OUT].values.astype(float), Jb,
                                       np.array([[max(tt, 1e-6) ** 2]]), starts=3)
            if np.isfinite(lapb) and (bb is None or lapb > bb[1]):
                bb = (thb, lapb, tt)
        if bb:
            bt_a.append(bb[0][0]); bt_b.append(bb[0][1]); bt_t.append(bb[2])
    if bt_b:
        log(f"\n  cluster bootstrap ({len(bt_b)} replicates):")
        log(f"    alpha = {alpha:+.4f}  95% CI ({np.percentile(bt_a,2.5):+.4f}, "
            f"{np.percentile(bt_a,97.5):+.4f})")
        log(f"    beta  = {beta:+.4f}  95% CI ({np.percentile(bt_b,2.5):+.4f}, "
            f"{np.percentile(bt_b,97.5):+.4f})")
        log(f"    tau   = {tau_hat:.4f}  95% CI ({np.percentile(bt_t,2.5):.4f}, "
            f"{np.percentile(bt_t,97.5):.4f})")

    # random intercepts
    u = th[2:]
    ri = pd.DataFrame(dict(hospitalid=sorted(e2.hospitalid.unique()), u=u,
                           n=e2.groupby("hospitalid").size().values,
                           deaths=e2.groupby("hospitalid")[OUT].sum().values))
    ri.to_csv(os.path.join(DATA, "publock_hospital_random_intercepts.csv"), index=False,
              encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "publock_hospital_random_intercepts.csv"),
               "publock_06_07_hospital.py")
    log(f"\n  random-intercept distribution: median {np.median(u):+.4f}  "
        f"SD {np.std(u, ddof=1):.4f}  range {u.min():+.3f} to {u.max():+.3f}")

    hier = pd.DataFrame([dict(model="random intercept only", alpha=alpha, beta=beta,
                              tau=tau_hat, laplace_loglik=lap, k_hospitals=Je, n=len(e2),
                              alpha_lo=float(np.percentile(bt_a, 2.5)) if bt_a else np.nan,
                              alpha_hi=float(np.percentile(bt_a, 97.5)) if bt_a else np.nan,
                              beta_lo=float(np.percentile(bt_b, 2.5)) if bt_b else np.nan,
                              beta_hi=float(np.percentile(bt_b, 97.5)) if bt_b else np.nan)])

    # ===================================================================== 搂7 recalibration
    log("\n" + "=" * 100)
    log("SECTION 7 -- RECALIBRATION VALIDATION (leave-one-hospital-out)")
    log("=" * 100)
    loho = {k: np.full(len(e), np.nan) for k in ["m0", "m1", "m2"]}
    uniq_h = np.unique(hid)
    for h in uniq_h:
        te = hid == h
        tr = ~te
        if te.sum() == 0 or tr.sum() == 0 or len(np.unique(y[tr])) < 2:
            continue
        ltr, lte = prov.logit(p[tr]), prov.logit(p[te])
        ytr = y[tr]
        # Model 1: intercept-only
        a = 0.0
        for _ in range(200):
            mu = expit(ltr + a)
            wsum = float(np.sum(mu * (1 - mu)))
            if wsum < 1e-12:
                break
            step = float(np.sum(ytr - mu)) / wsum
            a += np.clip(step, -1, 1)
            if abs(step) < 1e-12:
                break
        loho["m1"][te] = expit(lte + a)
        # Model 2: intercept + slope
        X = np.column_stack([np.ones(len(ltr)), ltr])
        b2, conv, _ = prov.fit_logistic(X, ytr)
        loho["m2"][te] = expit(b2[0] + b2[1] * lte)
        loho["m0"][te] = p[te]
    ok = ~np.isnan(loho["m0"])
    log(f"  held-out predictions available for {int(ok.sum()):,} of {len(e):,} patients "
        f"across {len(uniq_h)} hospitals")


    def nll(yv, pv):
        pv = np.clip(pv, 1e-12, 1 - 1e-12)
        return float(-np.sum(yv * np.log(pv) + (1 - yv) * np.log(1 - pv)))


    rows7 = []
    for k, lbl in [("m0", "Model 0 original"), ("m1", "Model 1 intercept-only"),
                   ("m2", "Model 2 intercept+slope")]:
        mm = prov.metrics(y[ok], loho[k][ok])
        mm["ici"] = ici(loho[k][ok], y[ok])
        mm["emax"] = emax(loho[k][ok], y[ok])
        mm["nll"] = nll(y[ok], loho[k][ok])
        rows7.append(dict(model=lbl, n=mm["n"], events=mm["events"],
                          auroc=round(mm["auroc"], 4), brier=round(mm["brier"], 4),
                          oe=round(mm["oe"], 4), calib_intercept=round(mm["calib_intercept"], 4),
                          calib_slope=round(mm["calib_slope"], 4),
                          ici=round(mm["ici"], 4), emax=round(mm["emax"], 4),
                          nll=round(mm["nll"], 2)))
    rec = pd.DataFrame(rows7)
    log("\n  POOLED HELD-OUT PERFORMANCE")
    log(rec.to_string(index=False))
    log("\n  changes vs Model 0:")
    for i in (1, 2):
        log(f"    {rec.model[i]:<26} dBrier {rec.brier[i]-rec.brier[0]:+.5f}   "
            f"dO/E {rec.oe[i]-rec.oe[0]:+.4f}   dNLL {rec.nll[i]-rec.nll[0]:+.2f}")

    # cluster bootstrap on the differences
    NB7 = 2000
    rng3 = np.random.default_rng(cfg.RANDOM_SEED + 3)
    ok_idx = np.where(ok)[0]
    by_h3 = {h: ok_idx[hid[ok_idx] == h] for h in np.unique(hid[ok_idx])}
    d_oe1, d_oe2, d_b1, d_b2, d_ll1, d_ll2 = [], [], [], [], [], []
    for _ in range(NB7):
        sel = rng3.choice(list(by_h3), size=len(by_h3), replace=True)
        idx = np.concatenate([by_h3[h] for h in sel])
        yb = y[idx]
        if len(np.unique(yb)) < 2:
            continue
        o0 = yb.mean() / loho["m0"][idx].mean()
        o1 = yb.mean() / loho["m1"][idx].mean()
        o2 = yb.mean() / loho["m2"][idx].mean()
        d_oe1.append(o1 - o0); d_oe2.append(o2 - o0)
        b0 = prov.brier(yb, loho["m0"][idx])
        d_b1.append(prov.brier(yb, loho["m1"][idx]) - b0)
        d_b2.append(prov.brier(yb, loho["m2"][idx]) - b0)
        l0 = nll(yb, loho["m0"][idx])
        d_ll1.append(nll(yb, loho["m1"][idx]) - l0)
        d_ll2.append(nll(yb, loho["m2"][idx]) - l0)
    cis = []
    for nm, arr, obs in [("dO/E model1 vs model0", d_oe1, rec.oe[1] - rec.oe[0]),
                         ("dO/E model2 vs model0", d_oe2, rec.oe[2] - rec.oe[0]),
                         ("dBrier model1 vs model0", d_b1, rec.brier[1] - rec.brier[0]),
                         ("dBrier model2 vs model0", d_b2, rec.brier[2] - rec.brier[0]),
                         ("dNLL model1 vs model0", d_ll1, rec.nll[1] - rec.nll[0]),
                         ("dNLL model2 vs model0", d_ll2, rec.nll[2] - rec.nll[0])]:
        arr = np.array(arr, float)
        lo, hi = np.percentile(arr, [2.5, 97.5])
        exc = bool(lo > 0 or hi < 0)
        cis.append(dict(comparison=nm, observed=float(obs), ci_lo=float(lo), ci_hi=float(hi),
                        excludes_zero=exc, n_boot=len(arr)))
        log(f"    {nm:<26} {obs:+.5f}  95% CI ({lo:+.5f}, {hi:+.5f})  "
            f"{'EXCLUDES 0' if exc else 'includes 0'}")
    ci7 = pd.DataFrame(cis)
    ci7.to_csv(os.path.join(DATA, "publock_recalibration_ci.csv"), index=False,
               encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "publock_recalibration_ci.csv"), "publock_06_07_hospital.py")

    # export the held-out predictions so the figure script can plot the three curves
    pd.DataFrame(dict(centre="eICU", stay_id=e.stay_id.values, hospitalid=hid,
                      outcome=y, p_m0=loho["m0"], p_m1=loho["m1"], p_m2=loho["m2"])
                 ).to_csv(os.path.join(DATA, "recalibration_cv_predictions.csv"), index=False,
                          encoding="utf-8-sig")
    prov.stamp(os.path.join(DATA, "recalibration_cv_predictions.csv"),
               "publock_06_07_hospital.py")
    log(f"\n  wrote held-out predictions for {int(ok.sum()):,} patients "
        f"(recalibration_cv_predictions.csv)")

    claim_ok = bool((ci7.set_index("comparison").loc["dO/E model1 vs model0", "excludes_zero"])
                    and rec.oe[1] > rec.oe[0])
    log(f"\n  intercept-only update improves held-out O/E with a CI excluding 0: {claim_ok}")
    log(f"  -> the manuscript MAY state that simple intercept updating corrected")
    log(f"     calibration-in-the-large out of sample: {claim_ok}")
    if not claim_ok:
        log("  -> the claim is NOT supported by this run and must be deleted.")

    # ===================================================================== outputs
    with pd.ExcelWriter(os.path.join(TABLES, "Table4_hospital_level.xlsx"),
                        engine="openpyxl") as xl:
        hl.to_excel(xl, sheet_name="all_hospitals", index=False)
        prim.to_excel(xl, sheet_name="primary_N20", index=False)
        hl[(hl.n >= 30) & (hl.deaths >= MIN_D)].to_excel(xl, sheet_name="sensitivity_N30",
                                                         index=False)
        meta.to_excel(xl, sheet_name="meta_analysis_AUROC", index=False)
        hier.to_excel(xl, sheet_name="hierarchical_calibration", index=False)
        ri.to_excel(xl, sheet_name="random_intercepts", index=False)
    prov.stamp(os.path.join(TABLES, "Table4_hospital_level.xlsx"), "publock_06_07_hospital.py")

    with pd.ExcelWriter(os.path.join(TABLES, "Table5_recalibration.xlsx"),
                        engine="openpyxl") as xl:
        rec.to_excel(xl, sheet_name="held_out_performance", index=False)
        ci7.to_excel(xl, sheet_name="bootstrap_differences", index=False)
    prov.stamp(os.path.join(TABLES, "Table5_recalibration.xlsx"), "publock_06_07_hospital.py")

    with io.open(os.path.join(LOGS, "PUBLOCK_06_07_hospital.log"), "w", encoding="utf-8") as fh:
        fh.write(LOG.getvalue())
    log("\nSECTION 6-7 DONE")



if __name__ == "__main__":  # pragma: no cover
    main()
