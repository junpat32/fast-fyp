# ml/: O2 experiment (T-06)

Implements the **pre-registered** evaluation in `docs/frozen/generator_spec_v1.0.md` §11 and §13.
The success criterion, metrics and baselines were fixed before any result existed; this code
only executes them.

## Run

```bash
.venv\Scripts\python -m ml.run_o2 --dev        # debugging on a separate dataset (seed 999, 400 users)
.venv\Scripts\python -m ml.run_o2              # the real run: medium (criterion), low, high, robustness
.venv\Scripts\python -m pytest -q              # includes tests/test_ml.py
```

Sensitivity analysis (T-25, spec §16, reported only; needs the real run's `metrics.json` first):

```bash
.venv\Scripts\python -m ml.run_sensitivity --list      # the 67 settings
.venv\Scripts\python -m ml.run_sensitivity --dev       # quick check, ~1 minute
.venv\Scripts\python -m ml.run_sensitivity             # full run -> ml/results/SENSITIVITY.md
.venv\Scripts\python -m ml.run_sensitivity --resume    # continue a stopped run
```

Pre-registered reporting items the report showed only for medium noise, or not at all, and the
Monte Carlo comparator (D-98; neither re-runs any model):

```bash
.venv\Scripts\python -m ml.report_addendum             # seconds -> ml/results/O2_ADDENDUM.md
.venv\Scripts\python -m ml.mc_comparator               # ~35 minutes -> ml/results/mc_comparator.json
.venv\Scripts\python -m ml.report_addendum             # again, to add the comparator
```

Exploratory checks, decided after seeing O2 (D-101; fairness, a model without demographics, the
health score, the advice, readability; about 30 seconds):

```bash
.venv\Scripts\python -m ml.exploratory                 # -> ml/results/EXPLORATORY.md
```

Results: `ml/results/O2_REPORT.md` (summary, kept as generated on 2026-10-12),
`ml/results/O2_ADDENDUM.md` (the rest of the pre-registered items), `ml/results/<noise>_seed20261009/`
(metrics.json, out-of-fold predictions, reliability plot; medium also has the SHAP summary and persona
explanations), `ml/results/robustness.csv`, `ml/results/run_log.txt`.

## Integrity steps

1. `run_o2` refuses to run if a dataset's `metadata.json` doesn't carry the frozen spec's SHA-256.
2. All pipeline code was written and debugged on a **development dataset** (seed 999, 400 users,
   `ml/results/dev/`). The real run is the first contact with the master-seed data.
3. Before the real run the datasets were regenerated and verified **byte-identical** (21/21 files).
4. Hidden traits are read only by the oracle model and the S14 audit (CLAUDE.md rule 3).

## Modules

| File | Role | Spec |
|---|---|---|
| `features.py` | Features X(u,t) from months t−2..t; `check_no_lookahead` | §11 |
| `baselines.py` | B0 base rates, B1 rule score, B2 Markov chain | §13 |
| `models.py` | LR / RF / XGB / oracle, inner-CV tuning, F1 threshold, isotonic calibration | §13, D-44 |
| `evaluate.py` | PR-AUC, user-level bootstrap, pairwise CIs, single-feature leakage check | §13 |
| `report.py` | Report tables, reliability plot, SHAP summary + personas | §13 |
| `run_o2.py` | Orchestration (main runs, leakage alarms, robustness) | §13, §15 |
| `o2_config.yaml` | All settings | §13 |

## Implementation choices the spec left open

| Choice | Reason |
|---|---|
| Flags not yet scorable (early months) count as "not fired" | They can't have fired without enough history |
| Calendar group = two binaries (festive / semester start in t+1..t+3) | §11 lists "festive or semester month" as one group |
| `active BNPL plans` at t = purchases in months t−1 and t (3-instalment plans still owing) | Follows from the 3-instalment structure |
| `cash slope` = (cash_t − cash_{t−2}) / 2 | The least-squares slope over 3 equally spaced months |
| XGBoost early-stopping patience 20 rounds; refit with the median best iteration of the inner folds | Early stopping on the inner validation fold is specified; there's no validation set at refit |
| B1 threshold and calibration chosen on the training rows directly | B1 has no fitted parameters, so there's nothing to overfit |
| Shuffled-label alarm uses each model's chosen hyperparameters | Tests the pipeline, not the tuning |
| Robustness seeds = `SeedSequence(20261009).spawn(20)` → `generate_state(1)[0]` | §15 names the spawn; the generator takes an integer seed |
| SHAP on the best ML model refit on all rows (explanation, not evaluation); summary on a sample of 800 rows; linear model contributions = coefficient × standardised value | Standard; keeps the run light on the 4 GB laptop |
| Persona = the positive case with the median predicted risk for each user type | "Typical" rather than cherry-picked cases |
| Monte Carlo comparator: not available until T-15 | §13 lists it as "Should", reported only |
