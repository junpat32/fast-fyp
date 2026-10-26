# O2 results: DEVELOPMENT RUN (debugging only, NOT the pre-registered result)

Generated 2026-10-12 · run time 1.3 min · frozen spec SHA-256 `6849e796c2d27f53c19e8eb3f4ce751b10c5e4109723b176edcb9ef2521f5aa1`

## Success criterion (medium noise, master seed)

**PASS.** Best ML = **Random forest** (PR-AUC 0.573); best baseline = **B2 Markov chain** (0.299). ΔPR-AUC = **+0.274**, 95% CI [+0.192, +0.323] (criterion: lower bound > 0). Label prevalence 11.0%, 2662 rows from 398 users.

Model choice for the app (simplest whose CI overlaps the best): **Logistic regression**.

## PR-AUC by contender and noise level (95% user-level bootstrap CI)

| Contender | medium |
|---|---|
| B0 base rates | 0.282 [0.227, 0.357] |
| B1 rule heuristic | 0.290 [0.226, 0.361] |
| B2 Markov chain | 0.299 [0.240, 0.357] |
| Logistic regression | 0.490 [0.395, 0.584] |
| Random forest | 0.573 [0.453, 0.651] |
| XGBoost | 0.532 [0.426, 0.608] |
| Oracle (hidden traits; reference only) | 0.510 [0.386, 0.601] |

medium: prevalence 11.0%; best ML Random forest vs best baseline B2 Markov chain: Δ +0.274 [+0.192, +0.323]

## Pairwise differences (medium)

| A | B | Δ PR-AUC | 95% CI |
|---|---|---|---|
| B0 base rates | B1 rule heuristic | -0.009 | [-0.050, +0.033] |
| B0 base rates | B2 Markov chain | -0.017 | [-0.041, +0.027] |
| B0 base rates | Logistic regression | -0.208 | [-0.272, -0.132] |
| B0 base rates | Random forest | -0.291 | [-0.347, -0.210] |
| B0 base rates | XGBoost | -0.250 | [-0.304, -0.176] |
| B0 base rates | Oracle (hidden traits; reference only) | -0.228 | [-0.281, -0.148] |
| B1 rule heuristic | B2 Markov chain | -0.008 | [-0.040, +0.046] |
| B1 rule heuristic | Logistic regression | -0.200 | [-0.278, -0.129] |
| B1 rule heuristic | Random forest | -0.282 | [-0.333, -0.206] |
| B1 rule heuristic | XGBoost | -0.241 | [-0.304, -0.163] |
| B1 rule heuristic | Oracle (hidden traits; reference only) | -0.219 | [-0.277, -0.138] |
| B2 Markov chain | Logistic regression | -0.191 | [-0.256, -0.131] |
| B2 Markov chain | Random forest | -0.274 | [-0.323, -0.192] |
| B2 Markov chain | XGBoost | -0.233 | [-0.284, -0.171] |
| B2 Markov chain | Oracle (hidden traits; reference only) | -0.211 | [-0.277, -0.132] |
| Logistic regression | Random forest | -0.083 | [-0.133, -0.029] |
| Logistic regression | XGBoost | -0.042 | [-0.096, +0.005] |
| Logistic regression | Oracle (hidden traits; reference only) | -0.020 | [-0.088, +0.041] |
| Random forest | XGBoost | +0.041 | [+0.002, +0.074] |
| Random forest | Oracle (hidden traits; reference only) | +0.063 | [+0.021, +0.102] |
| XGBoost | Oracle (hidden traits; reference only) | +0.022 | [-0.011, +0.058] |

## Secondary metrics (medium)

| Contender | Recall (positives) | Macro-F1 | Brier raw | Brier calibrated | Confusion [[TN, FP], [FN, TP]] |
|---|---|---|---|---|---|
| B0 base rates | 0.675 | 0.683 | 0.0830 | 0.0830 | [[2014, 356], [95, 197]] |
| B1 rule heuristic | 0.620 | 0.645 | n/a (not a probability) | 0.0855 | [[1955, 415], [111, 181]] |
| B2 Markov chain | 0.675 | 0.683 | 0.1887 | 0.0819 | [[2014, 356], [95, 197]] |
| Logistic regression | 0.531 | 0.711 | 0.1337 | 0.0738 | [[2186, 184], [137, 155]] |
| Random forest | 0.524 | 0.733 | 0.1288 | 0.0688 | [[2231, 139], [139, 153]] |
| XGBoost | 0.620 | 0.723 | 0.1167 | 0.0688 | [[2145, 225], [111, 181]] |
| Oracle (hidden traits; reference only) | 0.620 | 0.716 | 0.1168 | 0.0718 | [[2131, 239], [111, 181]] |

## Label breakdown (medium)

Positives: band worsening only 65 (22%), shortfall only 216 (74%), both 11 (4%).

| Starting band | Rows | Positive rate |
|---|---|---|
| GREEN | 1999 | 8.8% |
| RED | 137 | 24.1% |
| YELLOW | 526 | 15.8% |

### PR-AUC by employment type (medium)

| Type | B0 base rates | B1 rule heuristic | B2 Markov chain | Logistic regression | Random forest | XGBoost | Oracle (hidden traits; reference only) |
|---|---|---|---|---|---|---|---|
| employee | 0.243 | 0.262 | 0.247 | 0.500 | 0.593 | 0.571 | 0.540 |
| gig | 0.524 | 0.444 | 0.503 | 0.602 | 0.697 | 0.635 | 0.623 |
| student | 0.315 | 0.372 | 0.330 | 0.429 | 0.386 | 0.345 | 0.290 |

## Leakage alarms (medium)

- Any model PR-AUC > 0.95: none
- Shuffled-label PR-AUC: Logistic regression 0.102, Random forest 0.110, XGBoost 0.113 (prevalence 0.110; outside ±0.03: none)
- Highest single-feature PR-AUC: months of expenses saved (cushion) 0.436 (over 0.90: none)
- Feature-timestamp test: pass
- **Any alarm: no**

## Chosen hyperparameters (most frequent across outer folds)

```
{
 "lr": {
  "param": 0.1,
  "n_rounds": null
 },
 "rf": {
  "param": 4,
  "n_rounds": null
 },
 "xgb": {
  "param": 3,
  "n_rounds": 21
 },
 "oracle": {
  "param": 3,
  "n_rounds": 29
 }
}
```

Reliability plot: `medium_seed*/reliability.png`. SHAP: `medium_seed*/shap_summary.png`, `medium_seed*/shap_personas.md`.

## Robustness (reported, not pass/fail; hyperparameters reused from the medium run, D-44)

| Noise | Seeds | Median ΔPR-AUC | Share of seeds with Δ > 0 | Median prevalence |
|---|---|---|---|---|
| medium | 1 | +0.128 | 100% | 13.3% |

## Notes

- Comparator (Should): the app's Monte Carlo P(shortfall) is not available yet (T-15 not built); it will be added as a reported comparator, not part of the criterion.
- The oracle uses hidden traits and is a reference ceiling only (CLAUDE.md rule 3).