# Explanations and subgroup reliability (D-137)

**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/explain_fairness.py` docstring). The frozen O2 result and the app's model are unchanged.

## 1. How the shipped explanations behave

On 6,646 rows, with the app's model and its explanation rules:

- **Fidelity:** contributions plus the intercept reproduce the model's raw score to within 5.3e-15 (exact, as a linear model should).
- **Reference point:** on 16.2% of rows the headline's side (the calibrated chance against the base rate) differs from the side of the summed contributions, because the reasons compare a person with the training *average person* and the headline compares the chance with the *base rate*. The rule P5 shows only reasons pointing the headline's way, so no shown reason contradicts the headline.
- **Reasons shown:** 1: 0.0%, 2: 0.3%, 3: 99.7%.
- **Notes:** none: 47.9%; Your type of work and age group also affect this estimate.: 42.4%; Your type of work and age group, and some other patterns in the data, also affect this estimate.: 3.6%; Some other patterns in the data also affect this estimate.: 6.0%.
- **A top factor left out by W1:** 9.6% of rows (now always disclosed by P9). Features: bnpl_new3 (579), flag_impulsivity (43), savings_rate3 (22).
- **Coverage:** the shown reasons account for a median 55.5% (IQR 38.9%–66.3%) of the contribution pushing the shown way.

## 2. Reliability by group (out of sample)

Judged only with at least 100 users and 30 positive rows. All rows: PR-AUC 0.440, ROC-AUC 0.828, mean predicted − observed +0.0004, recall at 30% 0.41.

### employment type

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| employee | 684 | 4508 | 8.4% | 0.318 [0.239, 0.405] (3.8×) | 0.825 [0.792, 0.853] | +0.002 [-0.010, +0.014] | 0.010 | 0.27 [0.19, 0.34] | 0.39 | no concern found |
| gig | 167 | 1169 | 16.6% | 0.528 [0.355, 0.661] (3.2×) | 0.818 [0.759, 0.866] | -0.002 [-0.031, +0.027] | 0.010 | 0.50 [0.36, 0.61] | 0.47 | no concern found |
| student | 139 | 969 | 22.9% | 0.546 [0.430, 0.641] (2.4×) | 0.769 [0.708, 0.823] | -0.005 [-0.043, +0.032] | 0.027 | 0.58 [0.46, 0.68] | 0.45 | ranking concern |

### age band

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| 18-19 | 134 | 903 | 15.2% | 0.513 [0.366, 0.643] (3.4×) | 0.842 [0.786, 0.893] | -0.006 [-0.038, +0.025] | 0.012 | 0.56 [0.42, 0.68] | 0.48 | no concern found |
| 20-24 | 348 | 2337 | 14.2% | 0.389 [0.297, 0.484] (2.7×) | 0.778 [0.734, 0.818] | +0.004 [-0.017, +0.022] | 0.016 | 0.40 [0.30, 0.48] | 0.38 | ranking concern |
| 25-29 | 228 | 1510 | 11.0% | 0.425 [0.272, 0.573] (3.9×) | 0.832 [0.786, 0.872] | +0.001 [-0.021, +0.022] | 0.025 | 0.34 [0.22, 0.47] | 0.50 | no concern found |
| 30-35 | 280 | 1896 | 8.5% | 0.503 [0.321, 0.648] (5.9×) | 0.869 [0.811, 0.912] | -0.002 [-0.020, +0.016] | 0.020 | 0.38 [0.22, 0.52] | 0.50 | no concern found |

### lives with parents

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| lives away | 535 | 3587 | 12.6% | 0.480 [0.391, 0.568] (3.8×) | 0.835 [0.803, 0.866] | -0.003 [-0.019, +0.011] | 0.013 | 0.41 [0.33, 0.49] | 0.48 | no concern found |
| lives with parents | 455 | 3059 | 11.2% | 0.393 [0.303, 0.488] (3.5×) | 0.821 [0.787, 0.853] | +0.004 [-0.012, +0.020] | 0.008 | 0.41 [0.33, 0.50] | 0.39 | no concern found |

### family support

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| does not | 847 | 5713 | 12.3% | 0.451 [0.374, 0.521] (3.7×) | 0.828 [0.801, 0.852] | +0.001 [-0.012, +0.012] | 0.006 | 0.43 [0.36, 0.49] | 0.44 | no concern found |
| sends money to family | 143 | 933 | 10.2% | 0.356 [0.235, 0.489] (3.5×) | 0.830 [0.768, 0.881] | -0.002 [-0.028, +0.025] | 0.010 | 0.28 [0.16, 0.40] | 0.36 | no concern found |

### type x age

| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| employee 18-19 | 72 | 473 | 30 | too few to judge | | | | | | — |
| employee 20-24 | 212 | 1385 | 11.4% | 0.327 [0.225, 0.461] (2.9×) | 0.771 [0.714, 0.825] | -0.005 [-0.032, +0.017] | 0.034 | 0.29 [0.19, 0.39] | 0.38 | calibration concern, ranking concern |
| employee 25-29 | 183 | 1195 | 8.1% | 0.292 [0.180, 0.444] (3.6×) | 0.820 [0.767, 0.868] | +0.008 [-0.017, +0.030] | 0.010 | 0.23 [0.11, 0.34] | 0.43 | no concern found |
| employee 30-35 | 217 | 1455 | 6.5% | 0.403 [0.206, 0.584] (6.2×) | 0.882 [0.825, 0.923] | -0.002 [-0.022, +0.018] | 0.013 | 0.27 [0.11, 0.44] | 0.44 | no concern found |
| gig 18-19 | 17 | 119 | 23 | too few to judge | | | | | | — |
| gig 20-24 | 42 | 294 | 35 | too few to judge | | | | | | — |
| gig 25-29 | 45 | 315 | 69 | too few to judge | | | | | | — |
| gig 30-35 | 63 | 441 | 67 | too few to judge | | | | | | — |
| student 18-19 | 45 | 311 | 84 | too few to judge | | | | | | — |
| student 20-24 | 94 | 658 | 138 | too few to judge | | | | | | — |

## 3. The 30% warning line: options for unequal recall (descriptive)

Target: the all-rows recall at 30%, 0.41. Option (b)'s lines are chosen on other users (5 folds).

| Type of work | (a) one line: flagged | recall | precision | false-positive rate | (b) own line (median) | flagged | recall | precision | false-positive rate |
|---|---|---|---|---|---|---|---|---|---|
| employee | 5.8% | 0.27 | 0.39 | 3.8% | 20% | 11.6% | 0.45 | 0.32 | 8.6% |
| gig | 17.5% | 0.50 | 0.47 | 11.1% | 38% | 12.4% | 0.40 | 0.53 | 7.0% |
| student | 29.5% | 0.58 | 0.45 | 21.2% | 45% | 15.5% | 0.39 | 0.58 | 8.4% |

(c) Dropping age and type of work was tested and rejected (FA1, D-102): gig workers would be under-warned (12.1% predicted where 16.6% got worse).

## Reading (written by Claude after the run; the tables above are the generated record)

1. **The explanations are faithful to the model.** Each reason is exact model arithmetic (error 5e-15), and no shown
   reason ever points against the headline (P5). Two honest limits for the report: the shown reasons cover about
   half (median 55%) of what pushes the estimate their way, and on 16% of rows the reasons' reference point (the
   average person) and the headline's (the base rate) sit on different sides, so a reason list is "the strongest
   factors in the headline's direction", not "the whole explanation". About half of all forecasts (52%) carry a
   note; 9.6% now say other patterns also matter (P9), mostly because of the model's odd sign on new BNPL plans.
2. **The percentage means the same for every group.** Mean predicted vs observed is within ±0.6 points for every
   judged group, with intervals that include 0, including **gig workers** (the group FA1 would have under-warned)
   and **18–19-year-olds** (the hybrid's problem group, D-130). The only calibration flag is employees aged 20–24
   (ECE 0.034, just over the 0.03 line; its mean gap is −0.5 points).
3. **Ranking is weaker for some groups:** students (ROC-AUC 0.769), people aged 20–24 (0.778) and employees aged
   20–24 (0.771) fall below the all-rows 0.828, though all stay well above chance. Gig and student cells split by
   age are too small to judge.
4. **The 30% warning line treats groups differently because their base rates differ.** One line catches 27% of
   employees who get worse, 50% of gig workers and 58% of students. Lines per type of work would equalise recall
   (about 0.40–0.45) but double the false alarms for employees (3.8% → 8.6%) and make "30%" mean different things
   for different people. With base rates this different, a model cannot be both calibrated in every group and give
   equal error rates (Kleinberg, Mullainathan & Raghavan, 2016; Chouldechova, 2017).
5. **Recommendation:** keep one line and the calibrated percentage (the same "N in 100" for everyone, which is what
   the app shows and the study tests); state the recall gap and its cause in the report; do not drop demographics
   (FA1). The weaker ranking for students and 20–24-year-olds is a stated limitation of a synthetic-only model.
