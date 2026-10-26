# FA1 check: the forecast without age and type of work (D-102)

Exploratory, for the app only (the O2 result is unchanged). The adoption rule was written before any result was computed: every work type and age group must have (1) a mean predicted chance within 2 points of its observed rate and (2) a calibration error (ECE, 5 equal-count bins) at most 0.015 worse than the current model. Both models out of sample, calibrated on training folds only; logistic regression, C = 0.1.

## Verdict: **KEEP forecast_v1** (at least one group fails a condition)

| | Current model (v1, 32 inputs) | Without age and work type (v2, 25 inputs) |
|---|---|---|
| PR-AUC | 0.421 | 0.406 |
| Mean predicted (observed 12.0%) | 12.0% | 12.0% |
| Calibration error (ECE) | 0.006 | 0.004 |

PR-AUC difference v2 − v1: -0.015 [-0.033, +0.004].

## Type of work

| Group | Rows | Observed | v1 mean | v2 mean | v1 ECE | v2 ECE | v1 PR-AUC | v2 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| employee | 4508 | 8.4% | 8.6% | 10.1% | 0.010 | 0.017 | 0.308 | 0.299 | yes |
| gig | 1169 | 16.6% | 16.4% | 12.1% | 0.010 | 0.045 | 0.497 | 0.503 | NO (mean) |
| student | 969 | 22.9% | 22.4% | 20.7% | 0.027 | 0.026 | 0.524 | 0.523 | NO (mean) |

## Age group

| Group | Rows | Observed | v1 mean | v2 mean | v1 ECE | v2 ECE | v1 PR-AUC | v2 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| 18-19 | 903 | 15.2% | 14.5% | 14.3% | 0.012 | 0.013 | 0.499 | 0.465 | yes |
| 20-24 | 2337 | 14.2% | 14.6% | 14.1% | 0.016 | 0.011 | 0.372 | 0.384 | yes |
| 25-29 | 1510 | 11.0% | 11.1% | 10.6% | 0.025 | 0.012 | 0.397 | 0.359 | yes |
| 30-35 | 1896 | 8.5% | 8.3% | 9.4% | 0.020 | 0.014 | 0.489 | 0.457 | yes |

