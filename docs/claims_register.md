# Claims register: what FAST's results can and cannot claim

Created 2026-10-26 (D-133). One row per result the report or the app might state, with its evidence,
its status, the wording to use and the wording to avoid. Update a row when a result changes; add a
row for every new result. The report's text is Patrick's; this register is the checklist he writes
against.

## Status key

| Status | Meaning |
|---|---|
| **Confirmatory** | Tested exactly as pre-registered in the frozen spec (12 Oct 2026, SHA-256 in DECISIONS) |
| **Pre-specified, reported** | Planned before results (spec §13–16) but reported only, never pass/fail |
| **Exploratory** | Decided or run after the O2 results were seen (where noted, its rule was written before its own run) |
| **Synthetic-only** | Holds in the synthetic world built by the generator; no real people or real outcomes involved |
| **Checked against real aggregates** | Compared with published Malaysian or international statistics (not individuals) |
| **Verified (software)** | Shown by automated tests of the code |
| **Pending validation** | Planned but not yet run |
| **Inconclusive** | Run, but the result cannot separate the alternatives |

## Results

| ID | Claim, as it may be stated | Status | Evidence | Do not say |
|---|---|---|---|---|
| CR-01 | On synthetic data calibrated to Malaysian statistics, the best ML model (logistic regression) ranked 3-month deterioration better than the best pre-registered baseline: PR-AUC 0.440 vs 0.284, Δ +0.156 [+0.096, +0.212] (medium noise) | Confirmatory; synthetic-only | `ml/results/O2_REPORT.md` | "FAST predicts Malaysians' financial trouble with X accuracy"; any real-world accuracy |
| CR-02 | ML beat the best baseline in 60 of 60 robustness datasets (20 seeds × 3 noise levels, median Δ about +0.18) and in 67 of 67 one-at-a-time sensitivity settings (Δ +0.147 to +0.201) | Pre-specified, reported; synthetic-only | `O2_REPORT.md`, `ml/results/SENSITIVITY.md` | "robust in the real world" |
| CR-03 | A latent-trait-informed benchmark (XGBoost given the hidden traits) scored 0.435, no better than the models without them: the observable features capture what the hidden traits add for that model class | Pre-specified reference; synthetic-only | `O2_REPORT.md` | "ceiling", "the best possible score", "all predictive information is used" (D-133) |
| CR-04 | The app's Monte Carlo P(shortfall in 3 months) ranked the O2 rows about as well as the model: 0.427 vs 0.440, Δ −0.013 [−0.058, +0.030]; the expectation stated before the run (Monte Carlo below the model) did not hold | Pre-specified comparator (design fixed before the run); synthetic-only | `ml/results/O2_ADDENDUM.md` §5, D-99 | "the Monte Carlo is as accurate as ML" (they predict different targets: the Monte Carlo only shortfalls) |
| CR-05 | The four-part health score ranked who got worse about as well as the model: 0.416 vs 0.440, Δ +0.024 [−0.022, +0.067] | Exploratory; synthetic-only | `ml/results/EXPLORATORY.md` §3 | "as good as ML" (the interval allows a gap of up to 0.067) |
| CR-06 | Removing age and type of work from the forecast failed a calibration rule written in advance: gig workers would be told 12.1% where 16.6% got worse | Exploratory (rule before run); synthetic-only | `ml/results/FORECAST_V2_CHECK.md`, D-102 | "demographic features are fair/unfair" in general |
| CR-07 | Adding the Monte Carlo as a model input gave no clear gain: +0.013 [−0.004, +0.032], and worse calibration for 18–19-year-olds | Exploratory (rule committed before run); synthetic-only; **inconclusive** for a small gain | `ml/results/HYBRID_CHECK.md`, D-130 | "combining gives no gain" |
| CR-08 | The generator matched 13 selected real-world anchors (S1–S13: wages by age, spending shares, Red share, cushion buckets, DSR ≠ DTI, flag rates, edge cases, hygiene, positive rate, BNPL overdue and share, spending ÷ income, share saving) at medium noise without tuning | Checked against real aggregates (13 criteria only) | `generator/TUNING_LOG.md` | "the synthetic data is realistic" or "representative of young Malaysians"; anything about relationships between quantities (not yet checked) |
| CR-09 | Of three behaviour flags, only impulsivity tracked its hidden trait strongly enough (×16.5 lift) to be shown to users; overconfidence (×1.97) and delayed correction (×1.71) stay model inputs only, as pre-registered | Confirmatory decision rule (S14); synthetic-only | `generator/TUNING_LOG.md` | "FAST detects impulsive people" (it tracks the generator's trait) |
| CR-10 | Forecast reasons are the model's exact contributions (coefficient × standardised value, in log-odds, relative to the training average, before calibration): they show how the model reached its estimate | Verified (software) | `engine/forecast.py`, tests | "X causes your risk"; "this adds N% to your risk" |
| CR-11 | The Future Self's 10th–90th percentile range covered 73.25% of fresh synthetic outcomes (employees 69.6%); misses fall mostly below the range | Exploratory audit (protocol fixed before results); synthetic-only | `sim/results/monte_carlo_v2_report.md`, D-81 | "80% prediction interval"; "validated range" |
| CR-12 | FAST shows Red at a DSR of 60% or more, following PIDM's guidance that banks generally accept DSR below 60%; lenders set their own limits | Design convention (D-04) | `docs/calibration_table.md` C-06 | "banks reject above 60%"; "all banks use 60%" |
| CR-13 | The risk engine passes its O1 suite (30 scenario tests incl. the five FYP1 scenarios) and 10 property-based tests on generated cases; the property tests found and led to a fix of a health-tier display bug | Verified (software) | `tests/test_scenarios.py`, `tests/test_properties.py`, D-131 | "the engine is correct" in general |
| CR-14 | Under the game rules, none of 17 simulated reporting strategies earned more than honest reporting in any month or unlocked anything earlier; two known limits remain (a small lie inside the tolerance every month; a constant balance lie) | Simulation; synthetic-only | `sim/results/points_sim.md`, D-75–D-78, D-89 | "FAST cannot be cheated" |
| CR-15 | Warning advice fires for people who later got worse more often (R02 5.6×, R05 5.0×, R11 3.0×); encouragement mostly for people who didn't (R12 0.2×) | Exploratory; synthetic-only | `EXPLORATORY.md` §4 | "the advice helps people" (not measured) |
| CR-16 | Participants understand and can use FAST (O4: SUS ≥ 68, comprehension ≥ 70% over B1–B9 per persona and B12); secondary: usefulness and intention to use (Part F), trust calibration (D8) | **Pending validation** (persona study; ethics paused until 15 Nov) | `docs/ethics/` v0.4, analysis plan in the protocol §9 | any result before the study; "users would adopt FAST" (intention is not use) |
| CR-17 | FAST's forecast predicts real people's outcomes | **Not tested** (rule 12: synthetic data only); future work | Design: `docs/study/future_validation_protocol.md` | any real-world predictive claim |
| CR-18 | The money helper refuses product picks and only quotes supplied numbers (O5) | **Pending validation** (offline tests pass; the live red-team run needs a Groq key) | `tools/assistant_eval/`, `tests/test_assistant.py` | "the assistant is safe" |
| CR-19 | On the O2 rows, the app's model ranked and calibrated better than B0, cushion months and a cash-runway baseline; against the health score and the Monte Carlo it ranked the whole list better (ROC-AUC +0.072 and +0.026) but the difference at the top of the list (PR-AUC) and in probability accuracy (Brier) was inconclusive | Exploratory (plan committed before the run); synthetic-only; **inconclusive** for the health score and the Monte Carlo | `ml/results/SECONDARY_COMPARISON.md`, D-134 | "ML outperforms all transparent methods"; "the health score is as good as ML" |
| CR-20 | The O2 forecast is mainly a short-term cash-shortfall (liquidity) risk estimate: 72% of positives are shortfalls only; band worsening (PR-AUC 0.084 at 3.3% prevalence) and DSR rising 5+ points (0.127 at 8.5%) are predicted weakly | Exploratory; synthetic-only | `SECONDARY_COMPARISON.md` §5 | "FAST predicts debt problems" |
| CR-21 | The Monte Carlo's own shortfall probability is too high on average (+2.2 points) and too extreme (calibration slope 0.71); it is not shown as a percentage in the app (D-100) | Exploratory; synthetic-only | `SECONDARY_COMPARISON.md` §3 | any Monte Carlo percentage as a calibrated chance |

## Known caveats to state with the results

| ID | Caveat | Where it applies |
|---|---|---|
| CV-01 | S12's anchor (DOSM 60.8% = mean household consumption ÷ mean household gross income, all ages) is applied to **individuals aged 18–35**, using base pay × 12 rather than income actually received. The ratio types match (totals ÷ totals), the populations do not. Reviewed in the assumption audit (D-132 phase 4) | CR-08 |
| CV-02 | Relationships between quantities (thin cushion → shortfalls, unsteady income → trouble) are assumptions of the generator; the ML learns them | CR-01–CR-07 |
| CV-03 | 72% of positives are cash shortfalls only, so O2 mainly measures foreseeing shortfalls (stated before the run, spec §11) | CR-01 |
| CV-04 | The 21 life-event frequencies are unsourced relative to each other; only their overall scale `k` was varied | CR-02, CR-11 |
| CV-05 | The Monte Carlo draws events from the same deck the generator uses, an advantage it will not have with real users | CR-04, CR-07, CR-11 |

## Seed register

Population seeds already used (never reuse for a fresh evaluation):

| Seed | Use |
|---|---|
| 20261009 | Master dataset (O2, sensitivity, personas, all exploratory checks); `SeedSequence(20261009).spawn(20)` for the robustness seeds |
| 999 | Development dataset (debugging only) |
| 20261015, 31001, 31002 | Monte Carlo v1 audit and investigation |
| 49001, 49002 | Monte Carlo v2 fresh audit (D-80) |
| 1, 2, 7, 123, 4242 | Unit tests |

Reserved for the 26 Oct round (D-132); each block is used only for the purpose named:

| Block | Purpose |
|---|---|
| 61001–61049 | Alternative-mechanism worlds (structural robustness) |
| 62001–62009 | Monte Carlo recalibration (calibration data) |
| 63001–63009 | Monte Carlo final evaluation (used once, after the rule is committed) |
