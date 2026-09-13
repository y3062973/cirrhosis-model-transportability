"""FINAL_REBUILD -- provenance stamping and metric primitives.

Every output produced by this package goes through `stamp()` (CSV/JSON companions)
or `stamp_figure()` (PNG/PDF meta sidecars) so that a result file can never be
read without knowing which config, dataset and script produced it.

Metric primitives (AUROC, O/E, calibration slope, Brier) are implemented here for
the PRIMARY path. PHASE 17 requires a SECOND, independent implementation that does
NOT import these functions; that lives in `independent_metrics.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

import repo  # noqa: E402
repo.add_src_to_path()

# `FR` is the repository root, used for the dependency lock file. It is NOT
# this file's own directory: a per-file root made every stage resolve its
# data and outputs relative to itself. See PIPELINE_PATH_AUDIT.md.
FR = str(repo.REPO_ROOT)

# ---------------------------------------------------------------- citation syntax
# A citation marker is a bracketed list of working R-identifiers, or of plain numbers
# once the reference audit has renumbered them.
#
# It must NOT match a bracketed number that is part of a factual identifier. The ethics
# approval number supplied by the authors is "2025[327]" and is reproduced literally,
# bracket for bracket, because the manuscript has to carry the number exactly as the
# committee issued it. Rewriting an approval number to suit a parser is not an acceptable
# repair. The lookbehind spans the year between the label and the bracket, so
# "approval No. 2025[327]" is excluded at source and no reference 327 is invented.
#
# This lives in one place on purpose: the assembler and the reference auditor both need
# it, and when they each carried their own copy the auditor crashed on the approval
# number while the assembler did not.
CITATION_RE = re.compile(
    r"(?<!approval No\. 20\d\d)(?<!approval no\. 20\d\d)"
    r"\[(R\d+(?:,R\d+)*|\d+(?:,\d+)*)\]")


def citations(text: str) -> list[str]:
    """Every reference id cited in `text`, in order of first appearance."""
    seen: list[str] = []
    for m in CITATION_RE.finditer(text):
        for tok in m.group(1).split(","):
            if tok not in seen:
                seen.append(tok)
    return seen


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def git_commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=FR, capture_output=True,
                           text=True, timeout=20)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return "NO_GIT_REPOSITORY"


def package_versions() -> dict:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for m in ["numpy", "pandas", "scipy", "sklearn", "statsmodels", "psycopg2",
              "matplotlib", "openpyxl", "PyYAML"]:
        try:
            mod = __import__(m)
            out[m] = getattr(mod, "__version__", "unknown")
        except Exception:
            out[m] = "NOT_INSTALLED"
    return out


def lock_hash() -> str:
    p = os.path.join(FR, "requirements.txt")
    return sha256_file(p) if os.path.exists(p) else "NO_LOCKFILE"


def dataset_hash(path: str) -> str:
    return sha256_file(path) if path and os.path.exists(path) else "NA"


def stamp(out_path: str, script: str, inputs: dict | None = None, extra: dict | None = None) -> str:
    """Write a companion .meta.json next to an output file. Returns its path."""
    meta = {
        "output_file": os.path.basename(out_path),
        "output_sha256": sha256_file(out_path) if os.path.exists(out_path) else "MISSING",
        "script": script,
        "config_version": cfg.VERSION,
        "config_sha256": cfg.CONFIG_HASH,
        "git_commit": git_commit(),
        "package_lock_sha256": lock_hash(),
        "packages": package_versions(),
        "inputs": {k: {"path": v, "sha256": dataset_hash(v)} for k, v in (inputs or {}).items()},
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": cfg.RANDOM_SEED,
    }
    if extra:
        meta.update(extra)
    mp = out_path + ".meta.json"
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return mp


def announce(script: str) -> None:
    print("=" * 100)
    print(f"FINAL_REBUILD  script={script}")
    print(f"  config      : {cfg.VERSION}")
    print(f"  config hash : {cfg.CONFIG_HASH}")
    print(f"  git commit  : {git_commit()}")
    print(f"  lock hash   : {lock_hash()[:32]}")
    print("=" * 100)


# ===================================================================== metrics (primary impl)
def expit(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def auroc(y, p) -> float:
    """Rank-based AUROC with mid-ranks for ties."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    y, p = y[ok], p[ok]
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p), float)
    sp = p[order]
    i = 0
    while i < len(sp):
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def brier(y, p) -> float:
    y = np.asarray(y, float); p = np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    return float(np.mean((p[ok] - y[ok]) ** 2))


def oe_ratio(y, p) -> float:
    y = np.asarray(y, float); p = np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    mp = p[ok].mean()
    return float(y[ok].mean() / mp) if mp > 0 else np.nan


def fit_logistic(X, y, max_iter=200, tol=1e-11):
    """UNPENALIZED maximum-likelihood logistic regression by IRLS.

    Returns (beta, converged, se). No penalty is ever applied. Callers must handle
    non-convergence by stopping and reporting, per cfg.SEPARATION_POLICY.
    """
    X = np.asarray(X, float); y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(max_iter):
        eta = np.clip(X @ b, -500, 500)
        mu = expit(eta)
        w = np.maximum(mu * (1 - mu), 1e-12)
        z = eta + (y - mu) / w
        XtW = X.T * w
        try:
            nb = np.linalg.solve(XtW @ X, XtW @ z)
        except np.linalg.LinAlgError:
            return b, False, np.full(X.shape[1], np.nan)
        if not np.all(np.isfinite(nb)):
            return b, False, np.full(X.shape[1], np.nan)
        if np.max(np.abs(nb - b)) < tol:
            b = nb
            break
        b = nb
    else:
        return b, False, np.full(X.shape[1], np.nan)
    eta = np.clip(X @ b, -500, 500)
    mu = expit(eta)
    w = np.maximum(mu * (1 - mu), 1e-12)
    try:
        cov = np.linalg.inv((X.T * w) @ X)
    except np.linalg.LinAlgError:
        return b, True, np.full(X.shape[1], np.nan)
    return b, True, np.sqrt(np.abs(np.diag(cov)))


def cal_slope_intercept(y, p):
    """Calibration slope and intercept from logit(Y) = a + b*logit(p)."""
    lp = logit(p)
    X = np.column_stack([np.ones(len(lp)), lp])
    b, conv, se = fit_logistic(X, y)
    if not conv:
        return np.nan, np.nan, np.nan, np.nan
    return float(b[1]), float(b[0]), float(se[1]), float(se[0])


def metrics(y, p) -> dict:
    s, a, sse, ase = cal_slope_intercept(y, p)
    y = np.asarray(y, float); p = np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    return dict(n=int(ok.sum()), events=int(y[ok].sum()),
                auroc=auroc(y, p), brier=brier(y, p), oe=oe_ratio(y, p),
                mean_predicted=float(p[ok].mean()), observed=float(y[ok].mean()),
                calib_slope=s, calib_intercept=a)
