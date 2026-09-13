# Database setup

## Expected schema

The pipeline expects the MIMIC-IV v3.1 two-schema layout and the standard eICU-CRD and
nwICU layouts.

### MIMIC-IV (v3.1)

Schema-qualified names are used, not a single `mimic` schema:

```text
mimiciv_hosp.patients      mimiciv_hosp.admissions   mimiciv_hosp.labevents
mimiciv_hosp.poe           mimiciv_hosp.emar         mimiciv_hosp.omr
mimiciv_icu.icustays       mimiciv_icu.chartevents   mimiciv_icu.outputevents
```

The two-schema layout is itself a version signal: v2.x installations used a single
`mimic` schema, so the presence of `mimiciv_hosp` and `mimiciv_icu` confirms a v3.x or later
installation.

### eICU-CRD (v2.0)

The standard `eicu_crd` schema, including `patient`, `hospital`, `unitvisitnumber` and
the `vitalsign` and `lab` tables used for predictor extraction.

### nwICU (v0.1.0)

The published schema. Note that nwICU does not provide a usable dialysis flag, which is
recorded in the manuscript as a reason to treat it as a secondary cohort.

## MIMIC-IV version

The analysis used **MIMIC-IV v3.1**. The pipeline requires the v3.x two-schema layout:

```text
mimiciv_hosp.*   and   mimiciv_icu.*
```

A v2.x installation uses a single `mimic` schema instead, so the presence of the two
schemas confirms a v3.x installation is in use. The version is also named in the dataset
citation in the manuscript.

## Credentials

Use environment variables. Copy `.env.example` to `.env`, fill it in, and export it.
**Never commit `.env`.** `src/db.py` reads the variables and opens a read-only session.

## Population of the derived tables

The pipeline expects the source tables to be present in the databases, not pre-derived.
The MIMIC-IV concept tables under `mimiciv_derived` are **not** used by the locked
analysis: predictors are extracted from the raw `chartevents`, `labevents` and
`outputevents` tables so that the aggregation and plausibility rules are explicit and
version-stable.
