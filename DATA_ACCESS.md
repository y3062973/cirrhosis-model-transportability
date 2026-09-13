# Data access

## This repository contains no patient data

**No source data and no derived patient-level or stay-level data are included in this
repository, and none may be committed to it.** The repository contains analysis code,
the frozen configuration, aggregate model coefficients, and reproducibility materials.

## The three source databases

| database | version used | role in the study | access |
|---|---|---|---|
| MIMIC-IV | **v3.1** | development cohort (4,237 ICU stays, 857 deaths) | PhysioNet, credentialed |
| eICU-CRD | **v2.0** | primary external validation (1,612 ICU stays, 324 deaths, 155 hospitals) | PhysioNet, credentialed |
| nwICU | **v0.1.0** | secondary external validation (349 ICU stays, 75 deaths) | PhysioNet, custodial access |

### Obtaining access

All three are third-party resources. **The authors cannot redistribute them, and this
repository does not contain them.** An independent researcher must obtain their own
authorised access:

- **MIMIC-IV v3.1** - PhysioNet: https://physionet.org/content/mimiciv/3.1/
  (cite: Johnson AEW, Bulgarelli L, Shen L, et al. MIMIC-IV, a freely accessible
  electronic health record dataset. Sci Data. 2023;10(1):1.
  doi:10.1038/s41597-022-01899-x)
- **eICU-CRD v2.0** - PhysioNet: https://physionet.org/content/eicu-crd/2.0/
  (cite: Pollard TJ, Johnson AEW, Raffa JD, et al. The eICU Collaborative Research
  Database, a freely available multi-center database for critical care research.
  Sci Data. 2018;5:180178. doi:10.1038/sdata.2018.178)
- **nwICU v0.1.0** - PhysioNet: https://physionet.org/content/nwicu/0.1.0/
  (DOI: 10.13026/s84w-1829)

Access requires completion of the required training (CITI "Data or Specimens Only
Research" for the PhysioNet credentialed databases) and acceptance of a data-use
agreement that **prohibits redistribution**.

### MIMIC-IV version

The analysis pipeline targeted **MIMIC-IV v3.1**, which is the version named in the
dataset citation. The pipeline uses the v3.x two-schema layout (`mimiciv_hosp` and
`mimiciv_icu`) rather than the single `mimic` schema of v2.x, so a reader can confirm
from the schema that a v3.x installation is required.

## Data governance rules for contributors

1. **Never commit** patient-level or stay-level data, extracts, dumps, caches or
   temporary SQL output. `.gitignore` blocks the common cases; it is not a substitute
   for care.
2. **Never commit** credentials, `.env` files, keys or connection strings. Use the
   environment variables documented in `.env.example`.
3. Derived analysis tables are **as restricted as the source**. A file derived from
   MIMIC-IV is governed by the MIMIC-IV data-use agreement. This is the rule most
   easily broken by accident, because a derived file feels like the authors' own work.
4. Aggregate quantities that cannot identify an individual are publishable: model
   coefficients, phenotype code lists, predictor definitions, and summary performance
   metrics. `metadata/` contains only these.
5. If you are unsure whether a file is restricted, **do not commit it**.
