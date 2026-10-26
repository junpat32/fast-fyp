# Hybrid check: the forecast with the Monte Carlo as an input (D-130)

Exploratory, for the app only (the O2 result is unchanged). Design and adoption rule written before any result: `ml/check_hybrid.py` docstring. Logistic regression, C = 0.1; 6,646 rows from 990 users.

## Verdict: **KEEP forecast_v1** (at least one condition fails)

| Condition | Result | Holds |
|---|---|---|
| (1) Gain: CI lower bound of v3 − v1 above 0 | +0.013 [-0.004, +0.032] | **no** |
| (2) Calibration in every type of work and age group | see the tables below | **no** |
| (3) Speed: under 0.5 s per assessment | 3 ms | yes |

## PR-AUC (95% user-level bootstrap CI)

| Model | O2 label (prevalence 12.0%) | Shortfall part only (9.1%) |
|---|---|---|
| v1: forecast_v1 (32 inputs) | 0.421 [0.354, 0.493] | 0.403 [0.327, 0.486] |
| v3: hybrid (33 inputs) | 0.434 [0.367, 0.503] | 0.429 [0.351, 0.511] |
| Monte Carlo alone (months t−2..t) | 0.411 [0.347, 0.479] | 0.457 [0.386, 0.531] |

v3 − v1 on the shortfall part: +0.026 [+0.004, +0.049]. Correlation of v1's calibrated chance with the Monte Carlo's: 0.70. Mean predicted: v1 12.0%, v3 12.1%; ECE: v1 0.006, v3 0.007.

## Type of work

| Group | Rows | Observed | v1 mean | v3 mean | v1 ECE | v3 ECE | v1 PR-AUC | v3 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| employee | 4508 | 8.4% | 8.6% | 8.7% | 0.010 | 0.007 | 0.308 | 0.352 | yes |
| gig | 1169 | 16.6% | 16.4% | 16.9% | 0.010 | 0.019 | 0.497 | 0.487 | yes |
| student | 969 | 22.9% | 22.4% | 22.3% | 0.027 | 0.029 | 0.524 | 0.525 | yes |

## Age group

| Group | Rows | Observed | v1 mean | v3 mean | v1 ECE | v3 ECE | v1 PR-AUC | v3 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| 18-19 | 903 | 15.2% | 14.5% | 14.5% | 0.012 | 0.031 | 0.499 | 0.507 | NO (ECE) |
| 20-24 | 2337 | 14.2% | 14.6% | 14.6% | 0.016 | 0.008 | 0.372 | 0.392 | yes |
| 25-29 | 1510 | 11.0% | 11.1% | 11.6% | 0.025 | 0.027 | 0.397 | 0.411 | yes |
| 30-35 | 1896 | 8.5% | 8.3% | 8.3% | 0.020 | 0.011 | 0.489 | 0.496 | yes |

Caveat (stated before the run): the Monte Carlo draws life events from the same deck the generator used, so on synthetic data it knows the true shock process; for real users the deck is only an estimate.
