# Known-answer tests

Synthetic records with fixed expected metric values. The pipeline is run over
them and the metrics must return those values.

The fixtures are **fully synthetic**. No record is sampled from, derived from, or
modelled on a real patient, and no value in them is a real patient measurement.
A fixture that originated from a real record would be a patient-data leak
regardless of how few rows it contained.

## Note on where these tests live

The known-answer fixtures are **generated in code** from fixed constants rather than
sampled, so the fixtures themselves are synthetic and safe. The suite that runs them is
not shipped as a standalone script in this release: the checks are executed by
`tests/metric_validation/independent_metrics_and_verification.py` (the independent metric
comparison) and by `tests/fault_injection/fault_injection_suite.py`, both of which also
read the restricted analysis dataset and therefore need authorised access. There is no
script in this repository that runs the known-answer checks on synthetic data alone, and
this file does not claim otherwise.

No tabular fixture shipping under `tests/` contains any row: verified by
`verify_public_release.py`, which reports 0 restricted-data findings and 3 aggregate
CSV files, all under `metadata/`.
