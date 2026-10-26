# Expected months to recover (Markov chain, D-143)

Plan: the docstring of `sim/markov_recovery.py`, committed before this run. Exploratory; synthetic data only. Raw numbers: `markov_recovery.json`.

## Part A: what the chain says (fitted on all 1,000 users)

### Months to recover (Green with at least 1 month of cushion)

| Start state | User-months in data | Mean months | Median months | Within 3 | Within 6 | Within 12 |
|---|---:|---:|---:|---:|---:|---:|
| Green, cushion under 1 month | 1,756 | 6.6 | 3 | 50% | 72% | 88% |
| Yellow, cushion under 1 month | 758 | 19.5 | 13 | 9% | 24% | 48% |
| Yellow, cushion 1-3 months | 900 | 19.5 | 13 | 15% | 28% | 48% |
| Yellow, cushion 3+ months | 576 | 15.9 | 9 | 24% | 40% | 60% |
| Red, cushion under 1 month | 233 | 27.9 | 22 | 4% | 9% | 25% |
| Red, cushion 1-3 months | 235 | 28.3 | 23 | 4% | 10% | 25% |
| Red, cushion 3+ months | 151 | 27.9 | 22 | 6% | 13% | 28% |

### Months to leave Red

| Start state | User-months in data | Mean months | Median months | Within 3 | Within 6 | Within 12 |
|---|---:|---:|---:|---:|---:|---:|
| Red, cushion under 1 month | 233 | 11.6 | 8 | 24% | 43% | 66% |
| Red, cushion 1-3 months | 235 | 12.4 | 9 | 22% | 39% | 63% |
| Red, cushion 3+ months | 151 | 14.0 | 11 | 17% | 33% | 57% |

## Part B: do held-out users recover as fast as the chain says?

Overall: **not consistent** (20 cells with at least 30 start months).

### Recovered

| Start state | Within | Start months (users) | Chain says | Observed (95% CI) | Verdict |
|---|---:|---:|---:|---:|---|
| Green, cushion under 1 month | 3 months | 1,390 (348) | 50% | 46% (42%–51%) | consistent |
| Yellow, cushion under 1 month | 3 months | 552 (140) | 10% | 6% (3%–9%) | too fast |
| Yellow, cushion 1-3 months | 3 months | 695 (160) | 16% | 10% (7%–14%) | too fast |
| Yellow, cushion 3+ months | 3 months | 431 (98) | 24% | 17% (12%–24%) | too fast |
| Red, cushion under 1 month | 3 months | 164 (39) | 4% | 0% (0%–0%) | too fast |
| Red, cushion 1-3 months | 3 months | 168 (44) | 5% | 0% (0%–0%) | too fast |
| Red, cushion 3+ months | 3 months | 128 (23) | 7% | 1% (0%–3%) | too fast |
| Green, cushion under 1 month | 6 months | 1,000 (314) | 72% | 66% (61%–72%) | too fast |
| Yellow, cushion under 1 month | 6 months | 370 (115) | 24% | 11% (6%–16%) | too fast |
| Yellow, cushion 1-3 months | 6 months | 468 (134) | 28% | 13% (8%–19%) | too fast |
| Yellow, cushion 3+ months | 6 months | 278 (79) | 40% | 21% (13%–30%) | too fast |
| Red, cushion under 1 month | 6 months | 102 (33) | 11% | 0% (0%–0%) | too fast |
| Red, cushion 1-3 months | 6 months | 102 (31) | 12% | 0% (0%–0%) | too fast |
| Red, cushion 3+ months | 6 months | 98 (21) | 15% | 0% (0%–0%) | too fast |

### Out of Red

| Start state | Within | Start months (users) | Chain says | Observed (95% CI) | Verdict |
|---|---:|---:|---:|---:|---|
| Red, cushion under 1 month | 3 months | 164 (39) | 26% | 13% (6%–24%) | too fast |
| Red, cushion 1-3 months | 3 months | 168 (44) | 23% | 14% (7%–23%) | consistent |
| Red, cushion 3+ months | 3 months | 128 (23) | 20% | 5% (0%–11%) | too fast |
| Red, cushion under 1 month | 6 months | 102 (33) | 45% | 21% (7%–37%) | too fast |
| Red, cushion 1-3 months | 6 months | 102 (31) | 42% | 25% (11%–41%) | too fast |
| Red, cushion 3+ months | 6 months | 98 (21) | 36% | 6% (0%–17%) | too fast |

