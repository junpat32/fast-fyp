# Secondary comparison: ML against simpler methods, and what the outcome measures (D-134)

**Exploratory** (D-132 N6): planned after the O2, Monte Carlo and health-score results were seen; the plan and the reading rule were committed before this run (`ml/secondary.py` docstring). The frozen O2 result is unchanged. 6,646 rows from 990 users; 95% user-level bootstrap intervals.

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

| Method | T1: O2 label (12.0%) | T2: shortfall part (9.1%) | T3: band-worse part (3.3%) | T4: DSR up 5+ points (8.5%) |
|---|---|---|---|---|
| Logistic regression (the app's model) | 0.440 [0.370, 0.513] | 0.432 [0.351, 0.514] | 0.084 [0.061, 0.128] | 0.127 [0.109, 0.154] |
| XGBoost | 0.431 [0.376, 0.490] | 0.446 [0.382, 0.511] | 0.055 [0.045, 0.075] | 0.111 [0.096, 0.131] |
| Oracle (hidden traits; reference) | 0.435 [0.379, 0.493] | 0.452 [0.390, 0.517] | 0.055 [0.044, 0.073] | 0.110 [0.095, 0.131] |
| B0 base rates (best O2 baseline) | 0.284 [0.239, 0.342] | 0.297 [0.245, 0.364] | 0.033 [0.027, 0.042] | 0.090 [0.079, 0.104] |
| Monte Carlo P(shortfall) | 0.427 [0.362, 0.498] | 0.479 [0.408, 0.556] | 0.035 [0.028, 0.047] | 0.092 [0.079, 0.108] |
| Health score | 0.416 [0.351, 0.480] | 0.476 [0.404, 0.548] | 0.032 [0.026, 0.042] | 0.090 [0.077, 0.104] |
| Cushion months | 0.376 [0.323, 0.435] | 0.416 [0.358, 0.478] | 0.033 [0.026, 0.043] | 0.090 [0.078, 0.103] |
| Cash runway | 0.284 [0.246, 0.325] | 0.296 [0.257, 0.339] | 0.032 [0.026, 0.039] | 0.088 [0.076, 0.100] |

## 2. The O2 label: ML against each method (reading rule fixed before the run)

Differences are logistic regression minus the method. Margins for "comparable": PR-AUC ±0.05, ROC-AUC ±0.03, Brier ±0.003.

| Method | ΔPR-AUC | ΔROC-AUC | ΔBrier (negative = ML better) | Ranking (PR) | Ranking (ROC) | Probability (Brier) |
|---|---|---|---|---|---|---|
| XGBoost | +0.009 [-0.038, +0.051] | -0.007 [-0.021, +0.008] | +0.0022 [-0.0004, +0.0052] | inconclusive | comparable | inconclusive |
| Oracle (hidden traits; reference) | +0.005 [-0.039, +0.045] | -0.009 [-0.023, +0.006] | +0.0013 [-0.0013, +0.0039] | comparable | comparable | inconclusive |
| B0 base rates (best O2 baseline) | +0.156 [+0.096, +0.212] | +0.084 [+0.062, +0.109] | -0.0072 [-0.0112, -0.0037] | ML better | ML better | ML better |
| Monte Carlo P(shortfall) | +0.013 [-0.030, +0.058] | +0.026 [+0.008, +0.046] | -0.0011 [-0.0044, +0.0021] | inconclusive | ML better | inconclusive |
| Health score | +0.024 [-0.022, +0.067] | +0.072 [+0.051, +0.097] | -0.0019 [-0.0051, +0.0013] | inconclusive | ML better | inconclusive |
| Cushion months | +0.064 [+0.020, +0.108] | +0.054 [+0.034, +0.077] | -0.0031 [-0.0063, +0.0001] | ML better | ML better | inconclusive |
| Cash runway | +0.156 [+0.104, +0.208] | +0.119 [+0.099, +0.142] | -0.0100 [-0.0142, -0.0065] | ML better | ML better | ML better |

## 3. Probabilities on the O2 label

| Method | ROC-AUC | Brier | Brier skill | ECE (10 bins) | Mean predicted − observed | Calibration slope |
|---|---|---|---|---|---|---|
| Logistic regression (the app's model) | 0.828 | 0.0855 | +0.189 | 0.0062 | +0.0004 | 1.03 |
| XGBoost | 0.836 | 0.0832 | +0.210 | 0.0079 | +0.0053 | 1.03 |
| Oracle (hidden traits; reference) | 0.837 | 0.0842 | +0.202 | 0.0083 | +0.0047 | 1.05 |
| B0 base rates (best O2 baseline) | 0.744 | 0.0926 | +0.121 | 0.0105 | -0.0001 | 0.99 |
| Monte Carlo P(shortfall) | 0.802 | 0.0865 | +0.179 | 0.0130 | +0.0003 | 0.94 |
| Health score | 0.757 | 0.0874 | +0.171 | 0.0092 | +0.0000 | 0.95 |
| Cushion months | 0.774 | 0.0886 | +0.160 | 0.0097 | +0.0002 | 0.94 |
| Cash runway | 0.709 | 0.0955 | +0.094 | 0.0103 | +0.0001 | 0.93 |

The Monte Carlo's own probability, **uncalibrated, against the shortfall part** it estimates (prevalence 9.1%): Brier 0.0646, ECE 0.0279, mean predicted − observed +0.0215, slope 0.71.

## 4. Usefulness at a decision line (O2 label)

Net benefit = true positives / n − false positives / n × t / (1 − t): above 0 and above "warn everyone" means warnings at that line do more good than harm (Vickers & Elkin 2006). 30% is the app's R10 line.

| Method | Net benefit at 10% | 20% | 30% | Flagged at 30% | Recall at 30% | Precision at 30% |
|---|---|---|---|---|---|---|
| Logistic regression (the app's model) | +0.0666 | +0.0390 | +0.0219 | 11.3% | 0.41 | 0.44 |
| XGBoost | +0.0658 | +0.0404 | +0.0286 | 10.6% | 0.43 | 0.49 |
| Oracle (hidden traits; reference) | +0.0683 | +0.0396 | +0.0228 | 9.2% | 0.36 | 0.47 |
| B0 base rates (best O2 baseline) | +0.0545 | +0.0322 | +0.0076 | 1.9% | 0.09 | 0.57 |
| Monte Carlo P(shortfall) | +0.0615 | +0.0357 | +0.0266 | 9.3% | 0.39 | 0.50 |
| Health score | +0.0528 | +0.0347 | +0.0258 | 9.0% | 0.38 | 0.50 |
| Cushion months | +0.0554 | +0.0343 | +0.0244 | 8.8% | 0.36 | 0.49 |
| Cash runway | +0.0475 | +0.0218 | +0.0111 | 7.5% | 0.25 | 0.40 |
| Warn everyone | +0.0220 | -0.1003 | -0.2575 | 100% | 1.00 | — |

## 5. What the outcome measures

Positives of the O2 label: shortfall only 576 (72%), band worse only 194 (24%), both 26 (3%). Rows starting in Red whose band got worse: 0 (Red can't get worse).

| Starting band | Rows | O2 label | Shortfall | Band worse | DSR up 5+ points | Mean predicted (lr) | lr PR-AUC, O2 label | lr PR-AUC, shortfall |
|---|---|---|---|---|---|---|---|---|
| GREEN | 5023 | 10.8% | 7.5% | 3.6% | 8.2% | 11.2% | 0.401 | 0.389 |
| YELLOW | 1260 | 14.0% | 11.4% | 3.0% | 9.4% | 13.1% | 0.477 | 0.461 |
| RED | 363 | 21.8% | 21.8% | 0.0% | 9.6% | 19.8% | 0.661 | 0.661 |

**Debt pressure the label misses:** 345 rows (5.2% of all rows; 61% of the rows whose DSR rose 5+ points) had DSR rise by 5+ points (median 7.5 points) with no band change and no shortfall, so the O2 label called them negative. By starting band: GREEN 246, YELLOW 76, RED 23.

Share of rows with no cash fall in the window (unlimited runway): 67.7%.

## Reading (written by Claude after the run; the tables above are the generated record)

1. **Against the pre-registered baseline and the two one-number baselines, ML is clearly better** on ranking and
   on probability accuracy: B0 and the cash runway lose on every measure; cushion months loses on both rankings
   and is borderline on Brier (−0.0031 [−0.0063, +0.0001]). The cash runway is weak because cash fell in only
   about a third of the windows (67.7% had no fall, so no runway limit).
2. **Against the health score and the Monte Carlo, ML's edge is modest and only partly shown.** ML ranks the whole
   list better (ROC-AUC +0.072 over the health score, +0.026 over the Monte Carlo, both intervals above 0), but at the
   top of the list (PR-AUC) and in probability accuracy (Brier) the intervals include 0 **and** reach past the
   "comparable" margins, so the rule says **inconclusive**: these data can't tell a small ML advantage from none.
   Neither "ML is better" nor "they are equivalent" can be claimed for these two.
3. **Calibration:** the app's model is the best calibrated (ECE 0.006, slope 1.03, mean predicted within 0.04
   points of observed). The others reach similar Brier scores only after isotonic calibration on other users.
   The Monte Carlo's **own** probability of a shortfall is too high on average (+2.2 points) and too extreme
   (slope 0.71), which supports D-100's choice not to show it as a percentage.
4. **Usefulness at the app's 30% line:** every method beats "warn everyone" and "warn no one" at 10%, 20% and 30%.
   At 30% the app's model flags 11.3% of people, catching 41% of those who get worse (precision 44%); XGBoost, the
   Monte Carlo and the health score have slightly higher net benefit there (no intervals were planned for net
   benefit, so the ordering is descriptive only).
5. **What the outcome measures: liquidity risk, not debt pressure.** 72% of positives are shortfalls only. On the
   shortfall part the transparent methods rank at least as well as the model (Monte Carlo 0.479, health score
   0.476, model 0.432, which was trained on the composite label). On band worsening (3.3% of rows) every method is
   weak (model 0.084, about 2.5× chance), and on DSR rising 5+ points (8.5%) the model reaches only 0.127 (1.5×
   chance). 345 rows (5.2%) had debt pressure rise by 5+ points with no band change and no shortfall, so the label
   called them negative: **the forecast is best described as a short-term cash-shortfall (liquidity) risk estimate.**
6. **Recommendation for the app** (wording is Patrick's, W2): keep the one validated percentage, but describe it
   mainly as the chance of running short of money (its R10 text already names both parts); do **not** add an ML
   debt-pressure prediction (too weak and unvalidated); show debt pressure through what is already measured
   today, the band and the DSR share, plus, if wanted, a transparent "debt share rising" advice rule (like R14's
   "cash going down"), with no model.
