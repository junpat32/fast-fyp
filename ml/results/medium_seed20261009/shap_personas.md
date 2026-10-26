# SHAP: Logistic regression (medium noise)

## Global importance (mean |SHAP|), top 15

| Rank | Feature | Mean abs SHAP |
|---|---|---|
| 1 | debt payments / income (DSR) | 0.7669 |
| 2 | months of expenses saved (cushion) | 0.6388 |
| 3 | currently Green | 0.4013 |
| 4 | typical monthly income (last 3 months) | 0.3557 |
| 5 | is an employee | 0.2565 |
| 6 | ran out of cash recently | 0.2317 |
| 7 | currently Red | 0.2033 |
| 8 | currently Yellow | 0.1870 |
| 9 | active BNPL plans | 0.1441 |
| 10 | is a student | 0.1420 |
| 11 | new BNPL purchases (last 3 months) | 0.1245 |
| 12 | total debt / yearly income (DTI) | 0.1207 |
| 13 | is a gig worker | 0.1169 |
| 14 | unexpected costs (last 3 months) | 0.1118 |
| 15 | cash trend (last 3 months) | 0.1101 |

## Three persona explanations (top-3 reasons pushing risk up)

Each persona is the positive case with the median predicted risk for its user type.

### Employee (user 792, month 7): predicted risk 61%
- debt payments / income (DSR) = 0.57 (pushes risk up, SHAP +1.881)
- months of expenses saved (cushion) = 1.25 (pushes risk up, SHAP +0.564)
- cash trend (last 3 months) = -912.61 (pushes risk up, SHAP +0.368)

### Gig (user 615, month 3): predicted risk 78%
- months of expenses saved (cushion) = 1.09 (pushes risk up, SHAP +0.623)
- typical monthly income (last 3 months) = 809.71 (pushes risk up, SHAP +0.576)
- is an employee = 0.00 (pushes risk up, SHAP +0.392)

### Student (user 432, month 5): predicted risk 84%
- typical monthly income (last 3 months) = 586.17 (pushes risk up, SHAP +0.664)
- is a student = 1.00 (pushes risk up, SHAP +0.473)
- is an employee = 0.00 (pushes risk up, SHAP +0.392)
