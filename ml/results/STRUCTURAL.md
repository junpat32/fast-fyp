# Structural robustness: real patterns and alternative worlds (D-139)

**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/structural.py` docstring). Nothing was tuned; the generator's default output is unchanged. Synthetic-to-synthetic: a stress test, not real-world validation.

## Part A: does the synthetic world reproduce published relationships it wasn't tuned to?

| ID | Published direction | Source | Difference in that direction (95% CI) | Reading |
|---|---|---|---|---|
| P1 | Essentials' share of spending falls as income rises | DOSM HES 2024 Table 3.15 (Engel's law; D-28) | -0.015 [-0.022, -0.005] | opposite |
| P2 | The cushion at month 12 rises with income | Findex 2025, resilience by income group (verify) | +1.132 [+0.476, +1.775] | reproduced |
| P3 | Running short at least once falls with income | Lusardi, Schneider & Tufano (2011) | +0.465 [+0.385, +0.540] | reproduced |
| P4 | Running short rises with income volatility | Farrell & Greig (2016), JPMorgan Chase Institute (US) | +0.361 [+0.292, +0.421] | reproduced |
| P5 | BNPL users run short more often than non-users | BNM Financial Stability Review on BNPL (low confidence; verify) | -0.009 [-0.064, +0.051] | unclear |

By income quintile (1 = lowest): mean monthly net income, essentials' share, cushion at month 12, share running short:

| Quintile | Income (RM) | Essentials' share | Cushion (months) | Ran short |
|---|---|---|---|---|
| 1 | 860 | 55.8% | 3.12 | 55.0% |
| 2 | 1,498 | 56.3% | 3.04 | 38.0% |
| 3 | 1,915 | 57.0% | 3.58 | 20.0% |
| 4 | 2,573 | 57.5% | 3.41 | 19.0% |
| 5 | 4,299 | 57.3% | 4.25 | 8.5% |

By income volatility (tercile of the observed CV): 1: CV 0.05, ran short 12.3%; 2: CV 0.13, ran short 23.7%; 3: CV 0.43, ran short 48.3%. BNPL: non-users ran short 28.4%; users ran short 27.5%.

## Part B: the frozen app model in alternative worlds

| World | Label rate (shortfall share) | Model PR-AUC (95% CI) | ROC-AUC | Mean pred. − observed | Slope | Frozen B0 | Cushion months | Model − B0 (95% CI) | Reading |
|---|---|---|---|---|---|---|---|---|---|
| default (seed 61001) | 12.8% (79%) | 0.491 [0.423, 0.550] | 0.860 | -0.003 | 1.04 | 0.329 | 0.466 | +0.162 [+0.117, +0.203] | reference |
| default (seed 61002) | 13.3% (81%) | 0.425 [0.366, 0.477] | 0.837 | -0.003 | 0.89 | 0.338 | 0.468 | +0.087 [+0.040, +0.127] | reference |
| W1 stress spending (seed 61001) | 17.3% (85%) | 0.580 [0.524, 0.632] | 0.868 | -0.041 | 1.14 | 0.434 | 0.585 | +0.146 [+0.102, +0.187] | holds, but degrades |
| W2 persistent income shocks (seed 61001) | 13.5% (79%) | 0.508 [0.444, 0.571] | 0.861 | -0.007 | 1.04 | 0.349 | 0.505 | +0.159 [+0.112, +0.201] | holds |
| W3 correlated expenses (seed 61001) | 23.9% (91%) | 0.674 [0.636, 0.710] | 0.874 | -0.076 | 1.13 | 0.497 | 0.634 | +0.177 [+0.143, +0.213] | holds, but degrades |

## Reading (written by Claude after the run; the tables above are the generated record)

**Part A.** Three of five published relationships are reproduced without having been tuned in: richer people end
the year with bigger cushions (P2), run short far less often (P3: 55% in the lowest income fifth vs 8.5% in the
highest), and unsteady incomes run short far more often (P4: 12% vs 48%). Two are not:
- **P1 is the opposite of real life.** Essentials take a slightly *larger* share of spending as income rises
  (55.8% → 57.3%), where Engel's law (DOSM HES 2024 Table 3.15) says it falls. The generator gives everyone the
  same spending mix (D-34's fixed 59.4% essentials), and living with parents (housing × 0.4) is commoner among
  the young, low-income users, which lowers their essentials' share. **Limitation:** the synthetic spending mix
  doesn't respond to income, so the essentials'-share feature carries less signal than it might for real people.
  The forecast's weight on it is small (12th of the drivers by SHAP), so the O2 result is barely affected.
- **P5 unclear:** BNPL users run short about as often as non-users. In the generator BNPL is only a way of paying
  for spending that would happen anyway (D-39), so it doesn't add strain; the source for the expected direction
  is weak anyway (verify).

**Part B.** In every alternative world the frozen model still beats the frozen rule baseline (B0) and ranks people
as well as in the default world (ROC-AUC 0.86–0.87). What changes is the **level**: where things go wrong more often
(stress spending: 12.8% → 17.3%; correlated expenses: → 23.9%), the model's percentages come out **4–8 points too
low**, so it would under-warn. Persistent income shocks barely move anything. Seed-to-seed variation is large
(the default world's PR-AUC is 0.491 on one seed and 0.425 on another), so single-world differences under about
0.07 in PR-AUC shouldn't be read as effects.

**Lesson for the report and for real use:** the model's *ranking* travels well across these behaviour changes, its
*calibration* does not. A model trained on one world must have its overall level re-checked (recalibration-in-the-
large) wherever it is used, which is the first step of the real-world validation protocol
(`docs/study/future_validation_protocol.md` §6). This is synthetic-to-synthetic evidence only.
