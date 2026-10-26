# Monte Carlo coverage: the conformal adjustment (phase 5, D-142), 26 October 2026

The plan, the primary checks and the decision rule are in the docstring of `sim/recalibrate_monte_carlo.py`,
committed before any run (`82f4f11`). The offsets were fitted once on seeds 62001–62009 and committed
(`0bfa1c1`, `sim/monte_carlo_conformal.json`, SHA-256 `cd9306aa…6b13a`) before any evaluation population
existed. The evaluation ran once on seeds 63001–63006 (`15a639a`, `monte_carlo_conformal_eval.json`).
Exploratory (D-132 N6): the D-80 audit's 73.25% was known beforehand. Synthetic data only; this says
nothing about real people.

## What was done

The Monte Carlo is unchanged. Each end of its P10–P90 cushion range is moved by an offset learnt on
9,000 held-out synthetic users (asymmetric split conformal, `sim/conformal.py`). There is one offset pair
per cell: employment type × months of history (3–6) × months ahead (1–6). Each tail aims at 10%, so the
range aims at 80%. An offset can be negative, which narrows a range that was too wide. The middle path
(P50) is not moved.

## Primary result (default world, 6 months of history, 6 months ahead)

| Group | Users | Raw coverage | Adjusted coverage (95% CI) | Below P10: raw → adj | Above P90: raw → adj | Mean width (months): raw → adj | Interval score: raw → adj |
|---|---:|---:|---:|---:|---:|---:|---:|
| All | 3,000 | 72.2% | **79.2%** (77.7–80.7) | 18.0% → 11.5% | 9.8% → 9.2% | 3.33 → 3.69 | 6.12 → 5.79 |
| Employee | 2,085 | 69.3% | **79.1%** (77.3–80.8) | 20.6% → 11.2% | 10.2% → 9.6% | 2.44 → 2.93 | 5.50 → 5.02 |
| Gig | 471 | 76.6% | **76.6%** (72.6–80.2) | 13.8% → 13.8% | 9.6% → 9.6% | 4.52 → 4.52 | 6.74 → 6.74 |
| Student | 444 | 81.3% | **82.4%** (78.6–85.7) | 10.6% → 10.6% | 8.1% → 7.0% | 6.26 → 6.35 | 8.37 → 8.39 |

| Check | Rule | Result | |
|---|---|---|---|
| P1 | overall coverage 77–83% | 79.2% | holds |
| P2 | every employment type ≥ 74% | lowest: gig 76.6% | holds |
| P3 | each tail ≤ 13% | below 11.5%, above 9.2% | holds |
| P4 | interval score no worse than raw | 5.79 vs 6.12 | holds |

All four hold, so by the pre-set rule the API now shows the adjusted range.

## Every history length and month ahead (all users; adjusted, raw in brackets)

| History \ months ahead | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|
| 3 months | 81.4% (78.8%) | 81.9% (78.6%) | 81.4% (77.3%) | 82.3% (77.1%) | 82.2% (76.7%) | 81.2% (75.6%) |
| 4 months | 81.6% (78.5%) | 81.5% (77.0%) | 81.4% (76.3%) | 81.1% (75.4%) | 80.3% (73.8%) | 79.8% (73.8%) |
| 5 months | 81.6% (78.4%) | 81.1% (76.8%) | 80.5% (75.2%) | 80.4% (74.6%) | 79.8% (72.3%) | 79.8% (73.1%) |
| 6 months | 81.4% (78.7%) | 80.8% (76.4%) | 80.2% (75.2%) | 81.2% (74.9%) | 79.8% (72.6%) | 79.2% (72.2%) |

Across the 24 cells, adjusted coverage runs from 79.1% to 83.1% for employees (raw 69.3–80.0%),
76.6% to 81.3% for gig workers (raw 75.2–80.0%) and 77.2% to 83.8% for students (raw 75.9–82.9%).

## Shifted worlds (phase 4's alternative mechanisms; no exchangeability, so a test of shift)

| World | Users | Raw | Adjusted (95% CI) | Employees: raw → adj | Below P10: raw → adj | Interval score: raw → adj | Verdict (≥ 74%) |
|---|---:|---:|---:|---:|---:|---:|---|
| Default | 3,000 | 72.2% | 79.2% (77.7–80.7) | 69.3% → 79.1% | 18.0% → 11.5% | 6.12 → 5.79 | — |
| W1 stress spending | 1,000 | 75.5% | 81.1% (78.6–83.4) | 74.1% → 82.2% | 15.6% → 10.3% | 5.66 → 5.43 | holds |
| W2 persistent income shocks | 1,000 | 73.9% | 80.6% (78.0–82.9) | 72.1% → 81.8% | 16.0% → 10.1% | 5.62 → 5.36 | holds |
| W3 correlated expenses | 1,000 | 65.9% | 75.4% (72.6–78.0) | 60.2% → 73.5% | 28.5% → 19.2% | 7.60 → 6.77 | holds |

## Reading (added after the run)

1. **The adjustment fixes the gap where it was.** The D-80 misses were employees falling below the range.
   Their low end now moves down by 0.13 months one month ahead, rising to 0.63 months six months ahead.
   Employee coverage rises from 69% to 79%, and the share below the range nearly halves (20.6% → 11.2%).
2. **It is not bought with width alone.** The range is 0.36 months wider on average (3.33 → 3.69), and the
   interval score, which charges for both width and misses, improves (6.12 → 5.79). For gig workers and
   students the range barely changes, because it already covered about 80% in the calibration data.
3. **Gig workers stay a little under target.** At six months ahead with six months of history they are at
   76.6% (72.6–80.2), above the pre-set floor of 74% but below 80%. Their offsets are almost exactly zero:
   many gig workers have no cash left in both the forecast's low end and the outcome, so their scores tie
   at zero, and in the calibration data they were already at 81.4%. The 4.8-point gap between the two
   populations is about two standard errors; it is reported, not tuned away.
4. **Coverage holds under two of three shifts and weakens under the third.** With stress spending (W1) or
   persistent income shocks (W2) the adjusted range still covers about 81%. With correlated expenses (W3),
   where trouble is commoner, it covers 75.4% overall and 73.5% for employees, with 19% of outcomes below
   the range. The offsets carry the default world's assumptions: when the world is worse than the one they
   were learnt on, the low end is too high again. Real people are a different world again (C5, CV-05).
5. **The middle path is still optimistic.** The adjustment moves the ends, not the centre: the median
   forecast stays 0.29 months above the outcome at six months ahead, as in D-80.

## What may and may not be said

- **May:** "On fresh synthetic users like the ones it was calibrated on, the adjusted range covered 79.2% of
  outcomes six months ahead (77.7–80.7%), up from 72.2%. In three alternative synthetic worlds it covered
  75–81%."
- **May not:** "an 80% prediction interval", "a validated range", or any claim about real people. The app
  keeps "if recent habits continue" (D-81) and shows no percentage on the Future screen (D-100).
- **Not covered:** the shortfall probability, CFaR and Expected Shortfall (not shown as percentages, D-100);
  forecasts made in months other than June (the generator's year has 12 months, so the evaluated window is
  July to December); real people (rule 12).
