# O2 results (pre-registered evaluation, spec v1.0 §13)

Generated 2026-10-12 · run time 13.8 min · frozen spec SHA-256 `6849e796c2d27f53c19e8eb3f4ce751b10c5e4109723b176edcb9ef2521f5aa1`

The pipeline was written and debugged on a separate development dataset (seed 999, 400 users). This run is the first time it touched the master-seed datasets.

## Success criterion (medium noise, master seed)

**PASS.** Best ML = **Logistic regression** (PR-AUC 0.440); best baseline = **B0 base rates** (0.284). ΔPR-AUC = **+0.156**, 95% CI [+0.096, +0.212] (criterion: lower bound > 0). Label prevalence 12.0%, 6646 rows from 990 users.

Model choice for the app (simplest whose CI overlaps the best): **Logistic regression**.

## PR-AUC by contender and noise level (95% user-level bootstrap CI)

| Contender | medium | low | high |
|---|---|---|---|
| B0 base rates | 0.284 [0.239, 0.342] | 0.237 [0.191, 0.299] | 0.363 [0.318, 0.415] |
| B1 rule heuristic | 0.232 [0.194, 0.275] | 0.190 [0.151, 0.238] | 0.308 [0.269, 0.348] |
| B2 Markov chain | 0.263 [0.228, 0.304] | 0.222 [0.183, 0.265] | 0.354 [0.316, 0.392] |
| Logistic regression | 0.440 [0.370, 0.513] | 0.362 [0.287, 0.439] | 0.516 [0.460, 0.572] |
| Random forest | 0.422 [0.365, 0.484] | 0.395 [0.320, 0.474] | 0.552 [0.504, 0.600] |
| XGBoost | 0.431 [0.376, 0.490] | 0.404 [0.327, 0.483] | 0.563 [0.514, 0.609] |
| Oracle (hidden traits; reference only) | 0.435 [0.379, 0.493] | 0.407 [0.333, 0.483] | 0.553 [0.507, 0.600] |

medium: prevalence 12.0%; best ML Logistic regression vs best baseline B0 base rates: Δ +0.156 [+0.096, +0.212]

low: prevalence 9.0%; best ML XGBoost vs best baseline B0 base rates: Δ +0.167 [+0.109, +0.222]

high: prevalence 17.3%; best ML XGBoost vs best baseline B0 base rates: Δ +0.200 [+0.164, +0.235]

## Pairwise differences (medium)

| A | B | Δ PR-AUC | 95% CI |
|---|---|---|---|
| B0 base rates | B1 rule heuristic | +0.052 | [+0.026, +0.087] |
| B0 base rates | B2 Markov chain | +0.021 | [-0.005, +0.059] |
| B0 base rates | Logistic regression | -0.156 | [-0.212, -0.096] |
| B0 base rates | Random forest | -0.137 | [-0.183, -0.089] |
| B0 base rates | XGBoost | -0.147 | [-0.192, -0.096] |
| B0 base rates | Oracle (hidden traits; reference only) | -0.150 | [-0.192, -0.103] |
| B1 rule heuristic | B2 Markov chain | -0.031 | [-0.056, -0.003] |
| B1 rule heuristic | Logistic regression | -0.208 | [-0.263, -0.152] |
| B1 rule heuristic | Random forest | -0.190 | [-0.236, -0.145] |
| B1 rule heuristic | XGBoost | -0.199 | [-0.242, -0.162] |
| B1 rule heuristic | Oracle (hidden traits; reference only) | -0.203 | [-0.244, -0.166] |
| B2 Markov chain | Logistic regression | -0.177 | [-0.227, -0.126] |
| B2 Markov chain | Random forest | -0.158 | [-0.202, -0.118] |
| B2 Markov chain | XGBoost | -0.168 | [-0.209, -0.132] |
| B2 Markov chain | Oracle (hidden traits; reference only) | -0.171 | [-0.209, -0.134] |
| Logistic regression | Random forest | +0.019 | [-0.030, +0.060] |
| Logistic regression | XGBoost | +0.009 | [-0.038, +0.051] |
| Logistic regression | Oracle (hidden traits; reference only) | +0.005 | [-0.039, +0.045] |
| Random forest | XGBoost | -0.010 | [-0.042, +0.023] |
| Random forest | Oracle (hidden traits; reference only) | -0.013 | [-0.045, +0.016] |
| XGBoost | Oracle (hidden traits; reference only) | -0.003 | [-0.018, +0.012] |

## Secondary metrics (medium)

| Contender | Recall (positives) | Macro-F1 | Brier raw | Brier calibrated | Confusion [[TN, FP], [FN, TP]] |
|---|---|---|---|---|---|
| B0 base rates | 0.604 | 0.642 | 0.0927 | 0.0926 | [[4781, 1069], [315, 481]] |
| B1 rule heuristic | 0.521 | 0.591 | n/a (not a probability) | 0.0976 | [[4581, 1269], [381, 415]] |
| B2 Markov chain | 0.604 | 0.642 | 0.2208 | 0.0940 | [[4781, 1069], [315, 481]] |
| Logistic regression | 0.499 | 0.679 | 0.1671 | 0.0855 | [[5255, 595], [399, 397]] |
| Random forest | 0.579 | 0.690 | 0.1409 | 0.0831 | [[5153, 697], [335, 461]] |
| XGBoost | 0.503 | 0.688 | 0.1595 | 0.0832 | [[5297, 553], [396, 400]] |
| Oracle (hidden traits; reference only) | 0.533 | 0.683 | 0.1549 | 0.0842 | [[5205, 645], [372, 424]] |

## Label breakdown (medium)

Positives: band worsening only 194 (24%), shortfall only 576 (72%), both 26 (3%).

| Starting band | Rows | Positive rate |
|---|---|---|
| GREEN | 5023 | 10.8% |
| RED | 363 | 21.8% |
| YELLOW | 1260 | 14.0% |

### PR-AUC by employment type (medium)

| Type | B0 base rates | B1 rule heuristic | B2 Markov chain | Logistic regression | Random forest | XGBoost | Oracle (hidden traits; reference only) |
|---|---|---|---|---|---|---|---|
| employee | 0.237 | 0.194 | 0.201 | 0.318 | 0.378 | 0.392 | 0.387 |
| gig | 0.425 | 0.272 | 0.336 | 0.528 | 0.489 | 0.462 | 0.483 |
| student | 0.428 | 0.405 | 0.453 | 0.546 | 0.452 | 0.476 | 0.483 |

## Leakage alarms (medium)

- Any model PR-AUC > 0.95: none
- Shuffled-label PR-AUC: Logistic regression 0.119, Random forest 0.121, XGBoost 0.122 (prevalence 0.120; outside ±0.03: none)
- Highest single-feature PR-AUC: months of expenses saved (cushion) 0.380 (over 0.90: none)
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
  "n_rounds": 22
 },
 "oracle": {
  "param": 3,
  "n_rounds": 16
 }
}
```

Reliability plot: `medium_seed*/reliability.png`. SHAP: `medium_seed*/shap_summary.png`, `medium_seed*/shap_personas.md`.

## Robustness (reported, not pass/fail; hyperparameters reused from the medium run, D-44)

| Noise | Seeds | Median ΔPR-AUC | Share of seeds with Δ > 0 | Median prevalence |
|---|---|---|---|---|
| medium | 20 | +0.186 | 100% | 12.5% |
| low | 20 | +0.177 | 100% | 8.9% |
| high | 20 | +0.190 | 100% | 17.4% |

## Notes

- Comparator (Should): the app's Monte Carlo P(shortfall) is not available yet (T-15 not built); it will be added as a reported comparator, not part of the criterion.
- The oracle uses hidden traits and is a reference ceiling only (CLAUDE.md rule 3).