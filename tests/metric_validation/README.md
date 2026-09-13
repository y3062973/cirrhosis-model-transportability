# Independent metric verification

Every performance metric (AUROC, AUPRC, Brier score, O/E ratio, calibration
slope and intercept, ICI, Emax) is implemented a second time, importing none of
the primary metric code, and the two implementations are compared on synthetic
data with known answers. `independent_metrics_and_verification.py` is that second
implementation.

Run it from the repository root:

```bash
python tests/metric_validation/independent_metrics_and_verification.py
```

It needs no database access and no patient-level data: the comparison is computed on
synthetic fixtures with fixed expected values.

