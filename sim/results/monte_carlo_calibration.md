# T-15 Monte Carlo calibration audit

Date: 2026-10-14. Model: D-79 (M1, C1, R2). This is a synthetic-data
coursework audit, not a claim of accuracy for Malaysians. No parameter was
changed after seeing these results. O2's frozen evaluation is unaffected.

Method: `tests/test_monte_carlo.py` generates 120 new medium-noise synthetic
users with generator seed `20261015` and no transactions. At each forecast
date, only that user's observed `MonthRecord`s and public profile fields are
passed to the model. Each forecast uses 500 paths with a fixed per-user seed.
The actual terminal cash cushion is compared with the terminal P10–P90 interval:
first months 1–3 forecasting month 9, then months 1–6 forecasting month 12.
The two horizons therefore refer to separate future periods. Hidden traits and
future observations are used only inside the generator to create the test world,
never as forecast inputs.

| Observed months | Overall | Employee | Gig | Student |
|---|---:|---:|---:|---:|
| 3 | 63/120 = **52.5%** | 39/76 = 51.3% | 9/21 = 42.9% | 15/23 = 65.2% |
| 6 | 62/120 = **51.7%** | 31/76 = 40.8% | 13/21 = 61.9% | 18/23 = 78.3% |

Verdict: P10–P90 does **not** cover close to 80% of these synthetic outcomes.
The 120-user sample is small, especially the 21 gig and 23 student users, but
the overall miss is large. The six-month employee result is particularly weak.
The interval should not be described as an 80% prediction interval in the app.
It is an illustrative range conditional on recent habits and the stated event
deck until the model is improved and recalibrated on a separate audit sample.

Likely contributors are deliberate simplifications: the forecast omits the
generator's job-loss spells, gig slow months, pay rises, clustered shocks,
unlogged costs, behavioural correction, changing debt balances and card credit.
These remain hypotheses about the miss, not measured component attributions.
The game-room projection also needs a current game snapshot with protected
costs; ordinary `MonthRecord`s alone cannot reproduce that state.

Debt comparison is available when APR is supplied explicitly for each debt.
The current `debts` table has `kind`, `outstanding`, and `monthly_payment`, but
no APR, so a live avalanche-versus-snowball comparison cannot use the database
alone. Do not infer an interest rate from debt kind.
