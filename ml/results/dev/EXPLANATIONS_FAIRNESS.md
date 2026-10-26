# Explanations and subgroup reliability (D-137)

**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**

**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/explain_fairness.py` docstring). The frozen O2 result and the app's model are unchanged.

## 1. How the shipped explanations behave

On 2,662 rows, with the app's model and its explanation rules:

- **Fidelity:** contributions plus the intercept reproduce the model's raw score to within 3.6e-15 (exact, as a linear model should).
- **Reference point:** on 19.2% of rows the headline's side (the calibrated chance against the base rate) differs from the side of the summed contributions, because the reasons compare a person with the training *average person* and the headline compares the chance with the *base rate*. The rule P5 shows only reasons pointing the headline's way, so no shown reason contradicts the headline.
- **Reasons shown:** 2: 0.5%, 3: 99.5%.
- **Notes:** none: 49.4%; Your type of work and age group, and some other patterns in the data, also affect this estimate.: 4.1%; Your type of work and age group also affect this estimate.: 41.8%; Some other patterns in the data also affect this estimate.: 4.7%.
- **A top factor left out by W1:** 8.8% of rows (now always disclosed by P9). Features: bnpl_new3 (208), flag_impulsivity (19), savings_rate3 (8).
- **Coverage:** the shown reasons account for a median 56.1% (IQR 38.0%–67.3%) of the contribution pushing the shown way.

## 2. Reliability by group (out of sample)

Judged only with at least 100 users and 30 positive rows. All rows: PR-AUC 0.490, ROC-AUC 0.874, mean predicted − observed +0.0026, recall at 30% 0.46.

### employment type

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| employee | 275 | 1806 | 8.5% | 0.500 [0.383, 0.655] (5.9×) | 0.901 [0.873, 0.933] | -0.001 [-0.020, +0.014] | 0.011 | 0.39 [0.28, 0.52] | 0.50 | no concern found |
| gig | 68 | 476 | 74 | too few to judge | | | | | | — |
| student | 55 | 380 | 65 | too few to judge | | | | | | — |

### age band

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| 18-19 | 55 | 368 | 34 | too few to judge | | | | | | — |
| 20-24 | 131 | 870 | 12.2% | 0.461 [0.324, 0.595] (3.8×) | 0.847 [0.781, 0.898] | +0.006 [-0.021, +0.032] | 0.023 | 0.47 [0.31, 0.61] | 0.43 | no concern found |
| 25-29 | 103 | 673 | 16.0% | 0.617 [0.475, 0.758] (3.8×) | 0.890 [0.846, 0.929] | -0.011 [-0.042, +0.025] | 0.025 | 0.54 [0.40, 0.72] | 0.56 | no concern found |
| 30-35 | 109 | 751 | 5.9% | 0.266 [0.110, 0.455] (4.5×) | 0.857 [0.773, 0.903] | +0.008 [-0.015, +0.032] | 0.017 | 0.20 [0.06, 0.30] | 0.33 | no concern found |

### lives with parents

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| lives away | 207 | 1393 | 14.4% | 0.598 [0.487, 0.717] (4.2×) | 0.884 [0.844, 0.919] | -0.004 [-0.030, +0.025] | 0.013 | 0.52 [0.43, 0.64] | 0.51 | no concern found |
| lives with parents | 191 | 1269 | 7.2% | 0.320 [0.222, 0.406] (4.4×) | 0.841 [0.771, 0.878] | +0.010 [-0.011, +0.025] | 0.025 | 0.33 [0.23, 0.41] | 0.40 | no concern found |

### family support

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| does not | 328 | 2191 | 11.4% | 0.473 [0.366, 0.574] (4.1×) | 0.865 [0.838, 0.898] | +0.006 [-0.012, +0.024] | 0.012 | 0.45 [0.35, 0.52] | 0.45 | no concern found |
| sends money to family | 70 | 471 | 42 | too few to judge | | | | | | — |

### type x age

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| employee 18-19 | 30 | 193 | 8 | too few to judge | | | | | | — |
| employee 20-24 | 74 | 476 | 39 | too few to judge | | | | | | — |
| employee 25-29 | 84 | 540 | 82 | too few to judge | | | | | | — |
| employee 30-35 | 87 | 597 | 24 | too few to judge | | | | | | — |
| gig 18-19 | 7 | 49 | 7 | too few to judge | | | | | | — |
| gig 20-24 | 20 | 140 | 21 | too few to judge | | | | | | — |
| gig 25-29 | 19 | 133 | 26 | too few to judge | | | | | | — |
| gig 30-35 | 22 | 154 | 20 | too few to judge | | | | | | — |
| student 18-19 | 18 | 126 | 19 | too few to judge | | | | | | — |
| student 20-24 | 37 | 254 | 46 | too few to judge | | | | | | — |

## 3. The 30% warning line: options for unequal recall (descriptive)

Target: the all-rows recall at 30%, 0.46. Option (b)'s lines are chosen on other users (5 folds).

| Type of work | (a) one line: flagged | recall | precision | false-positive rate | (b) own line (median) | flagged | recall | precision | false-positive rate |
|---|---|---|---|---|---|---|---|---|---|
| employee | 6.6% | 0.39 | 0.50 | 3.6% | 23% | 8.9% | 0.48 | 0.46 | 5.2% |
| gig | 16.2% | 0.58 | 0.56 | 8.5% | 49% | 11.1% | 0.47 | 0.66 | 4.5% |
| student | 21.6% | 0.49 | 0.39 | 15.9% | 33% | 21.3% | 0.48 | 0.38 | 15.9% |

(c) Dropping age and type of work was tested and rejected (FA1, D-102): gig workers would be under-warned (12.1% predicted where 16.6% got worse).

