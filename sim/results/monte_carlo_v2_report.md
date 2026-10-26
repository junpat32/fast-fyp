# D-80 fresh Monte Carlo audit — 14 October 2026

Model and protocol were fixed in `docs/DECISIONS.md` D-80 before these results.
Reproduce with `python -m sim.evaluate_monte_carlo_v2`; full metrics are in
`monte_carlo_v2_audit.json`. The two seeds below are now evaluation data, not
available for further tuning. No generator or frozen O2 files changed.

Revision: use the user's observed education spending for student semester
uplifts; split BNPL from other commitments and schedule new purchases over
three months; include 5% employee monthly pay noise and a path-level
Student-t estimate error for ordinary net cash flow. The latter is one draw
per path held through the horizon, so uncertainty in the estimated average
persists. It does not imply that actual cash flow is Student-t distributed.

Method: independent medium-noise synthetic populations of 200 users each,
generator seeds 49001 and 49002, month 6 origin, six observed months,
1,000 forecast paths, six-month horizon. Only each user's past `MonthRecord`s
and public profile enter the forecast. The terminal true cash cushion is
compared with predicted terminal P10–P90. This is a synthetic-world check,
not evidence of real-world Malaysian predictive performance.

| Seed | Overall | Employee | Gig | Student |
|---|---:|---:|---:|---:|
| 49001 | 142/200 = 71.0% | 93/141 = 66.0% | 20/25 = 80.0% | 29/34 = 85.3% |
| 49002 | 151/200 = 75.5% | 108/148 = 73.0% | 19/23 = 82.6% | 24/29 = 82.8% |
| Combined | **293/400 = 73.25%** | **201/289 = 69.6%** | **39/48 = 81.3%** | **53/63 = 84.1%** |

Misses are asymmetric: 75/400 = 18.75% true outcomes below P10,
32/400 = 8.0% above P90. The median forecast remains optimistic by
0.30 and 0.17 cushion months in the two populations. Terminal interval
widths average 3.59 and 3.26 cushion months, compared with 2.65 in the
old model's 120-user development audit; populations differ, so width change
is descriptive rather than a controlled paired comparison.

Verdict: the revision improved coverage substantially but did **not** meet
the approximate 80% target, especially for employees. The model must not
present P10–P90 as an empirically validated 80% prediction interval.
The positive Student-t error is an assumption with a small per-user sample;
for students it can yield very wide intervals. The remaining below-P10 excess
indicates downward risks are still missing or the centre is optimistic.

Known remaining limitations: the generator has unemployment spells, gig slow
months, pay rises, hidden costs, behavioural correction, shock clustering and
credit-card draws/payoffs; D-14 excludes its regimes/clustering from the app
model. The forecast still holds non-BNPL debt payments roughly constant and
does not represent changing loan balances. Starting BNPL commitments are
approximated from the last two recorded purchase months; a user's actual
active plan schedule would be preferable. The exact Student-t error law is
not validated on real people. No data from other users enters a forecast.

Next choice belongs to Patrick: retain a clearly labelled conditional scenario,
shorten the shown horizon, or commission a further pre-specified design that
addresses employee downside and initial debt/BNPL schedules. Any later audit
requires new, untouched seeds/users and must report interval width, both tails,
median error and calibration by employment type. Shortfall probability, CFaR
and Expected Shortfall have not been calibrated by this cushion-coverage audit.
