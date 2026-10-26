# engine/: FAST risk engine (what the API and app call)

One call does everything for a user's latest month:

```python
from engine.assess import assess
from engine.features import UserProfile
from engine.state import MonthRecord

result = assess(profile, records)      # records: the user's months, oldest first
```

`result` contains: `band` (shown, with improvement confirmation, D-49), `raw_band_this_month`,
`dsr`, `dti`, `cushion_months`, `insufficient_income`, `health` (score, tier, 4 indicators;
D-48), `forecast` (calibrated 3-month risk, base rate, up to 3 reasons, model version; needs
≥ 3 months), `flags` (user-facing only, S14/D-41), and `advice` (ranked rule-engine items with
rule ids). Only numbers and rule ids, no raw transactions, so it can be summarised for Groq
(CLAUDE.md rule 10).

## Modules

| File | Role |
|---|---|
| `bands.py` | Per-month band rule (canonical; the generator pins it to the frozen v1 thresholds) |
| `state.py` | Monthly state: median-3 income, DSR, DTI, raw and shown band, cushion, savings rate |
| `health.py` | Health score (D-48) |
| `flags.py` | Behavioural flags (canonical; the generator re-exports it) |
| `features.py` | Forecast features for one user; identical to `ml/features.py` (tested on 1,050 user-months: 0 mismatches) |
| `forecast.py` + `reasons.yaml` | Packaged model `ml/artifacts/forecast_v1` → calibrated risk + reasons, each with plain words (D-92) |
| `rules.py` + `advice.yaml` | Rule engine and advice wording; thresholds appear as placeholders (wording: Patrick edits; review in `docs/advice_wording_review.md`) |
| `assess.py` | The single entry point |

Settings: `shared/thresholds.json` (live) and `shared/thresholds_spec_v1.json` (frozen, used by
the generator and for the forecast features so they match what the model was trained on).

## What the app must collect (inputs for T-07 / T-16)

| `MonthRecord` / `UserProfile` field | How the app gets it |
|---|---|
| net income, spending (essential vs other), debt payments, outstanding debt, cash | Transactions + debts entered by the user; essential/discretionary from the category |
| `bnpl_purchases`, `bnpl_new_count`, `bnpl_instalments` | The user marks a purchase as paid with BNPL (3 instalments) |
| `event_costs`, `shock_count` | **The user can mark an expense as "unexpected"**; RM300 or more counts as a shock |
| `savings_target` | **A monthly savings goal**; it stays the same unless the user changes it (this is what the overconfidence flag reads) |
| `personal_loan_balance` | From the debts list |
| `shortfall` | Cash ran out or a payment was missed in the month |
| profile: type, age, lives with parents, sends money to family, **festival celebrated**, semester months (students) | Onboarding (D-35, D-42) |

If an input is missing, the related feature takes its "not present" value. The forecast still
works, but it is less informed than in O2.
