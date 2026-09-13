# Reproducibility

## What is reproducible, and what is not

**Reproducible by an independent researcher with their own database access:** the entire
analysis, from the raw tables to every table and figure in the manuscript.

**Not reproducible from this repository alone:** the cohorts. The three databases are
credentialed and cannot be redistributed, so the cohorts must be rebuilt locally after
obtaining access. `docs/DATABASE_SETUP.md` describes the expected schema.

## Determinism

| element | how determinism is achieved |
|---|---|
| analysis configuration | frozen in `config/final_analysis_config.py`; its hash is recorded with every output |
| random seeds | fixed in the configuration; every bootstrap draws from a seeded generator |
| model coefficients | fitted once and stored in `metadata/model_coefficients.csv` |
| table and figure generation | reads the stored results; recomputes nothing |
| provenance | every released artefact carries a sidecar recording the configuration hash, the dataset hash and the producing script |

The configuration hash of the locked analysis is recorded in the manuscript's Methods.
If a run reproduces that hash and the dataset hash, the numbers should match.

## Verification performed

Three independent checks were run, and all three are included here so a reader can repeat
them rather than take them on trust:

1. **Known-answer tests.** A set of synthetic records with fixed expected metric values,
   run through the pipeline to confirm the metrics return those values.
2. **Fault injection.** Deliberate data-quality violations are introduced and the suite
   confirms they are detected. An earlier version of this suite was tautological -- its
   checks were `lambda: True` -- and was rewritten; the current suite fails when it
   should.
3. **Independent metric implementation.** Every performance metric is implemented a
   second time, importing none of the primary metric code, and the two implementations
   are compared.

## Note on the removed hierarchical calibration fit

**Release v1.1.0 removed the hierarchical calibration analysis from the manuscript.** A
mixed-effects logistic calibration model with a random intercept per hospital had been used
to estimate a common calibration slope and a between-hospital variance component. It was
withdrawn because an audit found that its custom Laplace criterion omitted the Gaussian
prior normalisation `-(J/2) log(2 pi tau^2)` -- a term that is not constant in tau -- and
because an independent implementation (`lme4::glmer`) disagreed materially about the
variance component (`tau = 0.1088` against the custom fit's `1e-06`).

**No numerical result from that model is part of this release.** The hospital-level
evidence is reported descriptively, as observed-to-expected ratios per hospital. No formal
hierarchical calibration-heterogeneity conclusion is reported, so neither a "uniform
shift" nor a "proven heterogeneity" reading is supported.

The script that carried this fit, `src/validation/hierarchical_calibration.py` in v1.0.0,
**no longer exists** in the pipeline. The retained hospital-level analyses -- per-hospital
AUROC analysis, random-effects AUROC meta-analysis, descriptive hospital-level summaries
and leave-one-hospital-out recalibration -- are in
`src/validation/hospital_analysis_and_recalibration.py`, which performs no mixed-effects
fitting at all.

The history is kept deliberately: a reader should be able to see the defect, the
attempted repair and the decision to remove rather than repair further.

Read `docs/audit/HIERARCHICAL_CALIBRATION_FINAL_COMPARISON.md` (the decision),
`docs/audit/HIERARCHICAL_LAPLACE_MATH_AUDIT.md` (the mathematics) and
`docs/audit/HIERARCHICAL_CALIBRATION_IMPLEMENTATION_NOTE.md` (the earlier defect) before
relying on anything from that model for anything. The rejected implementation itself is at
`archive/nonproduction/hierarchical_calibration_rejected_historical.py`, disabled and clearly
marked.

## Environment

Python 3.14, with the versions pinned in `requirements.txt`. No GPU or cluster is
required; the full pipeline runs on a single machine. The leave-one-hospital-out
recalibration bootstrap is the slowest step that runs on data.

## Verifying this release

```bash
python verify_public_release.py
```

Checks checksums, required files, compilation, the absence of restricted data and every
documentation reference, with **no database access and no patient-level data required**.
The three internal release-audit scripts (`src/reporting/final_release_check.py`,
`src/reporting/release_verification.py`, `src/validation/publication_lock.py`) are
provenance tooling rather than reproduction steps and cannot run here; see `README.md`.

