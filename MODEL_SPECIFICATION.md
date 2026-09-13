# MODEL SPECIFICATION -- FINAL_MODEL_V2

Every coefficient below is the locked value used in the manuscript. The machine-readable
copy is `metadata/model_coefficients.csv`.

## Form

A single **unpenalized maximum-likelihood logistic regression**, fitted in the MIMIC-IV
development cohort.

```text
LP = +7.744199
     + 0.029592 * age
     - 0.379554 * albumin
     + 0.065119 * bilirubin
     + 0.127296 * creatinine
     + 0.001250 * sodium
     - 0.003598 * platelet
     + 0.036929 * wbc
     + 0.019359 * heart_rate
     - 0.034011 * map
     + 0.080323 * resp_rate
     - 0.117754 * spo2
     + 0.050556 * male
     - 0.117565 * miss_albumin
     - 0.039476 * miss_bilirubin

predicted probability   p = 1 / (1 + exp(-LP))       # logistic transformation
```

There is **no penalty, no variable selection, no interaction term and no data-driven
cut-point**. Predictors enter as continuous linear terms. The separation policy was
stop-and-report: a failure to converge would have halted the analysis rather than
triggered an automatic penalty.

## Coefficients

| term | coefficient | standard error |
|---|---|---|
| `const` | 7.744199 | 1.970420 |
| `age` | 0.029592 | 0.003836 |
| `albumin` | -0.379554 | 0.090184 |
| `bilirubin` | 0.065119 | 0.006228 |
| `creatinine` | 0.127296 | 0.023049 |
| `sodium` | 0.001250 | 0.007008 |
| `platelet` | -0.003598 | 0.000639 |
| `wbc` | 0.036929 | 0.005130 |
| `heart_rate` | 0.019359 | 0.002874 |
| `map` | -0.034011 | 0.004345 |
| `resp_rate` | 0.080323 | 0.010976 |
| `spo2` | -0.117754 | 0.017299 |
| `male` | 0.050556 | 0.091744 |
| `miss_albumin` | -0.117565 | 0.102001 |
| `miss_bilirubin` | -0.039476 | 0.142185 |

## Predictor terms

**12 clinical predictors:**

- `age`
- `albumin`
- `bilirubin`
- `creatinine`
- `sodium`
- `platelet`
- `wbc`
- `heart_rate`
- `map`
- `resp_rate`
- `spo2`
- `male`

**2 missing-data indicators:**

- `miss_albumin`
- `miss_bilirubin`

These two terms encode missingness rather than clinical measurements, which is why the
manuscript describes a **12-predictor model with 14 predictor terms and 15 coefficients**
rather than a 14-variable model.

## Measurement and aggregation

All predictors are measured in the **first 24 hours after ICU admission**, under the
frozen window rule `0 < offset <= 1440` minutes. Each variable is reduced to a single
value per stay by a rule applied identically in all three cohorts:

| aggregation | variables |
|---|---|
| minimum | albumin, sodium, platelet count |
| maximum | bilirubin, creatinine, white blood cell count |
| mean | heart rate, mean arterial pressure, respiratory rate, peripheral oxygen saturation |

Values outside predefined physiological plausibility ranges are treated as **missing**,
never winsorised. Peripheral oxygen saturation uses the **mean** rather than the minimum
deliberately: a minimum-based rule combined with a plausibility filter would have
manufactured missingness in patients whose saturation dipped transiently.

## Missing data

Single median imputation using the **median of the development cohort**, with the
imputation values fixed before transport and applied unchanged to the external cohorts,
so no external data contributed to them.

Missing-data indicators were created for **albumin and bilirubin only**, because they
were the only variables with enough missing observations in the development cohort to
identify an indicator without penalisation. The other continuous predictors carry no
indicator. Sex was complete in all cohorts and was never imputed; the outcome was never
imputed.

## What is deliberately not here

No patient-level values, no imputation constants that could identify an individual, and
no dataset. The imputation medians are derived from the development cohort and are
reproduced by running the pipeline against the source data rather than being published
as constants.
