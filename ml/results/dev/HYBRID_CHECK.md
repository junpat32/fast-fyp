# Hybrid check: the forecast with the Monte Carlo as an input (D-130)

**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**
Exploratory, for the app only (the O2 result is unchanged). Design and adoption rule written before any result: `ml/check_hybrid.py` docstring. Logistic regression, C = 0.1; 2,662 rows from 398 users.

## Verdict: **KEEP forecast_v1** (at least one condition fails)

| Condition | Result | Holds |
|---|---|---|
| (1) Gain: CI lower bound of v3 − v1 above 0 | +0.016 [-0.010, +0.029] | **no** |
| (2) Calibration in every type of work and age group | see the tables below | **no** |
| (3) Speed: under 0.5 s per assessment | 3 ms | yes |

## PR-AUC (95% user-level bootstrap CI)

| Model | O2 label (prevalence 11.0%) | Shortfall part only (8.5%) |
|---|---|---|
| v1: forecast_v1 (32 inputs) | 0.466 [0.389, 0.575] | 0.462 [0.375, 0.601] |
| v3: hybrid (33 inputs) | 0.481 [0.389, 0.590] | 0.487 [0.374, 0.622] |
| Monte Carlo alone (months t−2..t) | 0.502 [0.400, 0.608] | 0.571 [0.451, 0.668] |

v3 − v1 on the shortfall part: +0.025 [-0.009, +0.043]. Correlation of v1's calibrated chance with the Monte Carlo's: 0.72. Mean predicted: v1 11.2%, v3 11.3%; ECE: v1 0.007, v3 0.008.

## Type of work

| Group | Rows | Observed | v1 mean | v3 mean | v1 ECE | v3 ECE | v1 PR-AUC | v3 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| employee | 1806 | 8.5% | 8.4% | 8.5% | 0.011 | 0.008 | 0.482 | 0.483 | yes |
| gig | 476 | 15.5% | 15.4% | 15.1% | 0.024 | 0.019 | 0.556 | 0.583 | yes |
| student | 380 | 17.1% | 19.7% | 19.9% | 0.075 | 0.064 | 0.405 | 0.419 | NO (mean) |

## Age group

| Group | Rows | Observed | v1 mean | v3 mean | v1 ECE | v3 ECE | v1 PR-AUC | v3 PR-AUC | Passes |
|---|---|---|---|---|---|---|---|---|---|
| 18-19 | 368 | 9.2% | 10.0% | 10.0% | 0.025 | 0.013 | 0.466 | 0.516 | yes |
| 20-24 | 870 | 12.2% | 12.8% | 12.9% | 0.023 | 0.017 | 0.431 | 0.439 | yes |
| 25-29 | 673 | 16.0% | 14.9% | 15.1% | 0.025 | 0.020 | 0.608 | 0.610 | yes |
| 30-35 | 751 | 5.9% | 6.6% | 6.6% | 0.017 | 0.020 | 0.255 | 0.276 | yes |

Caveat (stated before the run): the Monte Carlo draws life events from the same deck the generator used, so on synthetic data it knows the true shock process; for real users the deck is only an estimate.
