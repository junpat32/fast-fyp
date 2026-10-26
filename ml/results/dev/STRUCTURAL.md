# Structural robustness: real patterns and alternative worlds (D-139)

**DEVELOPMENT RUN (small worlds, seed 999): for debugging only, never reported.**

**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/structural.py` docstring). Nothing was tuned; the generator's default output is unchanged. Synthetic-to-synthetic: a stress test, not real-world validation.

## Part A: does the synthetic world reproduce published relationships it wasn't tuned to?

| ID | Published direction | Source | Difference in that direction (95% CI) | Reading |
|---|---|---|---|---|
| P1 | Essentials' share of spending falls as income rises | DOSM HES 2024 Table 3.15 (Engel's law; D-28) | -0.015 [-0.030, +0.003] | unclear |
| P2 | The cushion at month 12 rises with income | Findex 2025, resilience by income group (verify) | +1.218 [-0.185, +2.362] | unclear |
| P3 | Running short at least once falls with income | Lusardi, Schneider & Tufano (2011) | +0.433 [+0.266, +0.559] | reproduced |
| P4 | Running short rises with income volatility | Farrell & Greig (2016), JPMorgan Chase Institute (US) | +0.400 [+0.290, +0.500] | reproduced |
| P5 | BNPL users run short more often than non-users | BNM Financial Stability Review on BNPL (low confidence; verify) | -0.016 [-0.136, +0.118] | unclear |

By income quintile (1 = lowest): mean monthly net income, essentials' share, cushion at month 12, share running short:

| Quintile | Income (RM) | Essentials' share | Cushion (months) | Ran short |
|---|---|---|---|---|
| 1 | 919 | 55.4% | 3.16 | 58.3% |
| 2 | 1,508 | 56.7% | 3.77 | 36.7% |
| 3 | 1,897 | 57.2% | 2.89 | 26.7% |
| 4 | 2,470 | 58.2% | 2.55 | 11.7% |
| 5 | 4,158 | 56.9% | 4.38 | 15.0% |

By income volatility (tercile of the observed CV): 1: CV 0.05, ran short 12.0%; 2: CV 0.12, ran short 25.0%; 3: CV 0.45, ran short 52.0%. BNPL: non-users ran short 30.2%; users ran short 28.6%.

## Part B: the frozen app model in alternative worlds

| World | Label rate (shortfall share) | Model PR-AUC (95% CI) | ROC-AUC | Mean pred. − observed | Slope | Frozen B0 | Cushion months | Model − B0 (95% CI) | Reading |
|---|---|---|---|---|---|---|---|---|---|
| default (seed 999) | 13.4% (80%) | 0.471 [0.408, 0.543] | 0.861 | +0.001 | 0.97 | 0.291 | 0.421 | +0.180 [+0.127, +0.231] | reference |
| W1 stress spending (seed 999) | 20.2% (88%) | 0.600 [0.547, 0.679] | 0.866 | -0.056 | 1.02 | 0.448 | 0.578 | +0.153 [+0.097, +0.219] | holds, but degrades |
| W2 persistent income shocks (seed 999) | 14.7% (81%) | 0.507 [0.443, 0.590] | 0.862 | -0.010 | 0.94 | 0.331 | 0.465 | +0.177 [+0.128, +0.244] | holds |
| W3 correlated expenses (seed 999) | 26.9% (94%) | 0.683 [0.628, 0.736] | 0.874 | -0.088 | 1.03 | 0.551 | 0.650 | +0.133 [+0.079, +0.188] | holds, but degrades |
