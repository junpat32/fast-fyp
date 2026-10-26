# SHAP: Random forest (medium noise)

## Global importance (mean |SHAP|), top 15

| Rank | Feature | Mean abs SHAP |
|---|---|---|
| 1 | months of expenses saved (cushion) | 0.0899 |
| 2 | debt payments / income (DSR) | 0.0527 |
| 3 | savings rate (last 3 months) | 0.0386 |
| 4 | ran out of cash recently | 0.0377 |
| 5 | cash trend (last 3 months) | 0.0370 |
| 6 | typical monthly income (last 3 months) | 0.0270 |
| 7 | share of spending on essentials | 0.0168 |
| 8 | new BNPL purchases (last 3 months) | 0.0157 |
| 9 | is an employee | 0.0123 |
| 10 | total debt / yearly income (DTI) | 0.0122 |
| 11 | how much income varied | 0.0119 |
| 12 | active BNPL plans | 0.0108 |
| 13 | delayed-correction flag | 0.0058 |
| 14 | is a student | 0.0054 |
| 15 | lives with parents | 0.0039 |

## Three persona explanations (top-3 reasons pushing risk up)

Each persona is the positive case with the median predicted risk for its user type.

### Employee (user 145, month 7): predicted risk 76%
- months of expenses saved (cushion) = 0.24 (pushes risk up, SHAP +0.130)
- debt payments / income (DSR) = 0.29 (pushes risk up, SHAP +0.063)
- savings rate (last 3 months) = -0.12 (pushes risk up, SHAP +0.045)

### Gig (user 221, month 7): predicted risk 79%
- months of expenses saved (cushion) = 0.53 (pushes risk up, SHAP +0.131)
- savings rate (last 3 months) = -0.58 (pushes risk up, SHAP +0.062)
- delayed-correction flag = 1.00 (pushes risk up, SHAP +0.032)

### Student (user 41, month 7): predicted risk 64%
- debt payments / income (DSR) = 0.27 (pushes risk up, SHAP +0.069)
- typical monthly income (last 3 months) = 604.91 (pushes risk up, SHAP +0.056)
- new BNPL purchases (last 3 months) = 9.00 (pushes risk up, SHAP +0.030)
