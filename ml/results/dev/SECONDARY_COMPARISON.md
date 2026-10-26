# Secondary comparison: ML against simpler methods, and what the outcome measures (D-134)

**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**

**Exploratory** (D-132 N6): planned after the O2, Monte Carlo and health-score results were seen; the plan and the reading rule were committed before this run (`ml/secondary.py` docstring). The frozen O2 result is unchanged. 2,662 rows from 398 users; 95% user-level bootstrap intervals.

## What each method predicts

| Method | Output | Target it was built for | Horizon | Inputs |
|---|---|---|---|---|
| Logistic regression, XGBoost | probability (calibrated inside the training folds) | the O2 label | 3 months | 32 features, months t−2..t |
| Oracle | probability | the O2 label | 3 months | the same + hidden traits (reference only) |
| B0 base rates | probability | the O2 label | 3 months | band and cushion bucket at t |
| Monte Carlo | probability of a shortfall | **shortfalls only** | 3 months | the user's last ≤ 6 months |
| Health score | 0–100 score of **today** | none (describes the present) | — | months t−2..t |
| Cushion months | months of costs covered by cash | none | — | month t |
| Cash runway | months until cash runs out at its recent pace | none | — | months t−2..t |

Methods without a probability of the O2 label get one by isotonic regression fitted on other users (5 folds).

## 1. Ranking: PR-AUC on each target

| Method | T1: O2 label (11.0%) | T2: shortfall part (8.5%) | T3: band-worse part (2.9%) | T4: DSR up 5+ points (8.1%) |
|---|---|---|---|---|
| Logistic regression (the app's model) | 0.490 [0.406, 0.602] | 0.495 [0.401, 0.628] | 0.069 [0.046, 0.144] | 0.137 [0.106, 0.182] |
| XGBoost | 0.532 [0.429, 0.615] | 0.544 [0.432, 0.648] | 0.088 [0.050, 0.145] | 0.151 [0.110, 0.201] |
| Oracle (hidden traits; reference) | 0.510 [0.416, 0.609] | 0.525 [0.436, 0.638] | 0.063 [0.045, 0.096] | 0.125 [0.095, 0.164] |
| B0 base rates (best O2 baseline) | 0.282 [0.220, 0.354] | 0.287 [0.221, 0.374] | 0.032 [0.020, 0.047] | 0.105 [0.084, 0.132] |
| Monte Carlo P(shortfall) | 0.517 [0.407, 0.620] | 0.592 [0.456, 0.687] | 0.032 [0.021, 0.050] | 0.103 [0.074, 0.138] |
| Health score | 0.507 [0.407, 0.609] | 0.566 [0.466, 0.672] | 0.038 [0.025, 0.064] | 0.116 [0.083, 0.161] |
| Cushion months | 0.470 [0.375, 0.564] | 0.517 [0.418, 0.606] | 0.037 [0.024, 0.056] | 0.106 [0.078, 0.138] |
| Cash runway | 0.334 [0.264, 0.397] | 0.362 [0.287, 0.424] | 0.029 [0.019, 0.040] | 0.089 [0.073, 0.113] |

## 2. The O2 label: ML against each method (reading rule fixed before the run)

Differences are logistic regression minus the method. Margins for "comparable": PR-AUC ±0.05, ROC-AUC ±0.03, Brier ±0.003.

| Method | ΔPR-AUC | ΔROC-AUC | ΔBrier (negative = ML better) | Ranking (PR) | Ranking (ROC) | Probability (Brier) |
|---|---|---|---|---|---|---|
| XGBoost | -0.042 [-0.094, +0.019] | +0.006 [-0.019, +0.034] | +0.0050 [-0.0001, +0.0088] | inconclusive | inconclusive | inconclusive |
| Oracle (hidden traits; reference) | -0.020 [-0.077, +0.048] | +0.019 [-0.010, +0.053] | +0.0020 [-0.0032, +0.0072] | inconclusive | inconclusive | inconclusive |
| B0 base rates (best O2 baseline) | +0.208 [+0.147, +0.296] | +0.112 [+0.074, +0.157] | -0.0092 [-0.0166, -0.0039] | ML better | ML better | ML better |
| Monte Carlo P(shortfall) | -0.027 [-0.081, +0.048] | +0.034 [-0.004, +0.091] | +0.0021 [-0.0046, +0.0073] | inconclusive | inconclusive | inconclusive |
| Health score | -0.016 [-0.074, +0.054] | +0.051 [+0.016, +0.091] | +0.0008 [-0.0046, +0.0063] | inconclusive | ML better | inconclusive |
| Cushion months | +0.020 [-0.034, +0.094] | +0.052 [+0.017, +0.089] | -0.0004 [-0.0062, +0.0050] | inconclusive | ML better | inconclusive |
| Cash runway | +0.156 [+0.070, +0.260] | +0.121 [+0.084, +0.164] | -0.0105 [-0.0187, -0.0037] | ML better | ML better | ML better |

## 3. Probabilities on the O2 label

| Method | ROC-AUC | Brier | Brier skill | ECE (10 bins) | Mean predicted − observed | Calibration slope |
|---|---|---|---|---|---|---|
| Logistic regression (the app's model) | 0.874 | 0.0738 | +0.245 | 0.0173 | +0.0026 | 0.94 |
| XGBoost | 0.868 | 0.0688 | +0.296 | 0.0164 | +0.0096 | 1.04 |
| Oracle (hidden traits; reference) | 0.854 | 0.0718 | +0.265 | 0.0132 | +0.0053 | 0.90 |
| B0 base rates (best O2 baseline) | 0.761 | 0.0830 | +0.150 | 0.0265 | +0.0007 | 0.92 |
| Monte Carlo P(shortfall) | 0.840 | 0.0717 | +0.266 | 0.0126 | -0.0002 | 0.92 |
| Health score | 0.823 | 0.0730 | +0.252 | 0.0137 | +0.0006 | 0.89 |
| Cushion months | 0.821 | 0.0741 | +0.241 | 0.0157 | -0.0000 | 0.87 |
| Cash runway | 0.752 | 0.0843 | +0.137 | 0.0187 | +0.0003 | 0.88 |

The Monte Carlo's own probability, **uncalibrated, against the shortfall part** it estimates (prevalence 8.5%): Brier 0.0511, ECE 0.0217, mean predicted − observed +0.0214, slope 0.90.

## 4. Usefulness at a decision line (O2 label)

Net benefit = true positives / n − false positives / n × t / (1 − t): above 0 and above "warn everyone" means warnings at that line do more good than harm (Vickers & Elkin 2006). 30% is the app's R10 line.

| Method | Net benefit at 10% | 20% | 30% | Flagged at 30% | Recall at 30% | Precision at 30% |
|---|---|---|---|---|---|---|
| Logistic regression (the app's model) | +0.0643 | +0.0455 | +0.0272 | 10.4% | 0.46 | 0.48 |
| XGBoost | +0.0656 | +0.0486 | +0.0356 | 10.2% | 0.51 | 0.54 |
| Oracle (hidden traits; reference) | +0.0658 | +0.0478 | +0.0317 | 11.0% | 0.50 | 0.50 |
| B0 base rates (best O2 baseline) | +0.0591 | +0.0406 | +0.0167 | 20.8% | 0.67 | 0.36 |
| Monte Carlo P(shortfall) | +0.0649 | +0.0493 | +0.0338 | 11.9% | 0.54 | 0.50 |
| Health score | +0.0572 | +0.0409 | +0.0337 | 7.7% | 0.42 | 0.61 |
| Cushion months | +0.0587 | +0.0453 | +0.0324 | 9.0% | 0.45 | 0.55 |
| Cash runway | +0.0513 | +0.0222 | +0.0176 | 4.3% | 0.23 | 0.59 |
| Warn everyone | +0.0108 | -0.1129 | -0.2719 | 100% | 1.00 | — |

## 5. What the outcome measures

Positives of the O2 label: shortfall only 216 (74%), band worse only 65 (22%), both 11 (4%). Rows starting in Red whose band got worse: 0 (Red can't get worse).

| Starting band | Rows | O2 label | Shortfall | Band worse | DSR up 5+ points | Mean predicted (lr) | lr PR-AUC, O2 label | lr PR-AUC, shortfall |
|---|---|---|---|---|---|---|---|---|
| GREEN | 1999 | 8.8% | 6.4% | 2.9% | 7.1% | 9.6% | 0.381 | 0.363 |
| YELLOW | 526 | 15.8% | 12.7% | 3.4% | 10.5% | 14.3% | 0.619 | 0.657 |
| RED | 137 | 24.1% | 24.1% | 0.0% | 13.1% | 22.6% | 0.777 | 0.777 |

**Debt pressure the label misses:** 140 rows (5.3% of all rows; 65% of the rows whose DSR rose 5+ points) had DSR rise by 5+ points (median 8.1 points) with no band change and no shortfall, so the O2 label called them negative. By starting band: GREEN 97, YELLOW 36, RED 7.

Share of rows with no cash fall in the window (unlimited runway): 67.7%.

