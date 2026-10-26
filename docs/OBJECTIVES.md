# OBJECTIVES: FAST FYP2 (GOST + SMARTER)

Status: proposed for FYP2. The targets have not yet been confirmed with the
supervisor; confirmation is planned before the O2 run (~25 Oct 2026). Until then,
treat the thresholds as provisional but **do not change them after seeing results**.

Here, SMARTER = Specific, Measurable, Achievable, Relevant, Time-bound,
**Evaluated** (the evidence artefact), **Reviewed** (a checkpoint plus the action
taken if it fails).

## Goal

Show that an explainable, behaviour-aware financial risk system with
non-competitive gamification can make personal financial risk understandable and
actionable for young Malaysian adults, delivered as a validated, defensible FAST
prototype.

## Objectives

| # | Objective (specific, measurable, dated) | Evaluated by | Reviewed: checkpoint → action if failing |
|---|---|---|---|
| **O1** | Risk engine passes **100%** of an automated scenario suite of **≥12 cases** (the 5 FYP1 scenarios, the 59/60/61% boundary, zero income, gig-income band flapping, festive months) by **15 Nov 2026** | pytest report; table of scenario inputs, expected and actual outputs | Every commit: a failing test blocks new features |
| **O2** | On regenerated monthly data (spec: `generator_spec.md`), the best of LR/RF/XGB beats the best baseline (persistence-with-base-rates, rule heuristic, Markov chain) at predicting 3-month deterioration: **ΔPR-AUC 95% bootstrap CI lower bound > 0 in the medium-noise regime**. Every prediction has top-3 SHAP reasons. By **25 Oct 2026** | Results table across 3 noise levels with CIs; reliability plot; SHAP summary; 20-seed robustness | 25 Oct: if ML does not beat the baselines, report it honestly and use the rules plus Monte Carlo. It is still a valid, pre-registered finding |
| **O3** | On Android, the full core flow works: login → add transaction → band + health score + explanation → points. RLS is on for every table; **0 rows** readable by another user. By **13 Dec 2026** | Demo video (recorded on the phone); RLS test log | 13 Dec (week-9 rule): if failing, drop the whole Should tier |
| **O4** | Persona user study (n = 15–20) reaches **mean SUS ≥ 68** and **≥ 70% correct** on risk-comprehension questions, with no real financial data collected. By **10 Jan 2027** | SUS with CI; accuracy per question; trust and future-self stress items; demographics; consent forms | 30 Dec pilot (n = 3): if SUS < 60 or comprehension < 50%, fix the top 3 issues before the main study |
| **O5** *(Should)* | Parser reaches **≥ 90%** per-field accuracy (amount, merchant, date) on **≥ 100** real-format messages from **≥ 5** Malaysian providers. OCR accuracy on receipt totals measured on **≥ 50** receipts (target set after a 10-receipt pilot). Assistant refuses product or investment picks in **≥ 29/30** red-team prompts and **≥ 95%** of the numbers it quotes appear in its supplied context. By **27 Dec 2026** | Per-field and per-provider accuracy tables; red-team log with every failure | Week-9 rule decides whether O5 goes ahead at all |
| **O6** | Report submitted with Turnitin **≤ 10%** per chapter and all FYP1 inconsistencies fixed. **3 Feb 2027** (official deadline reported as end of Feb) | Turnitin report; checklist of fixed issues | Chapters are drafted while building, not crammed in January |

SUS 68 is the commonly used benchmark. The 70% comprehension and 90% parser
targets are design choices with no published standard.

## Strategies

| # | Strategy | Serves |
|---|---|---|
| S1 | **Separation of concerns:** rules say where the user is now (band); ML flags likely deterioration; Monte Carlo shows the range of futures; the Markov chain is a probabilistic baseline | O1, O2 |
| S2 | **Tests first, thresholds in config:** one constants file; scenarios become pytest tests | O1 |
| S3 | **Pre-registered experiment:** generator spec, baselines, noise levels and success criteria committed before any results | O2 |
| S4 | **Core flow first, then expand by priority:** Must items first; week-9 cut rule | O3, O5 |
| S5 | **Persona-based evaluation:** pre-loaded synthetic histories; measures understanding, not behaviour change | O4 |
| S6 | **Deterministic first, LLM as fallback:** regex before LLM; the assistant only uses supplied facts, and its numbers are checked | O5 |
| S7 | **Write as you build:** chapters drafted alongside the work | O6 |

## Additional techniques (approved for the build; supervisor confirmation pending)

| Technique | Role | Priority |
|---|---|---|
| Monte Carlo (≈1,000 paths × 6 months) | Future Self projection; life-event stress test; CFaR and Expected Shortfall | Must |
| Markov chain over band × cushion states | O2 baseline; expected months to recover | Must (cheap) |
| Points-system simulation (honest vs gaming users) | Proves the gamification fix | Must (cheap) |
| Debt repayment simulation (avalanche vs snowball) | Red-band advice content | Should |
| Bootstrap CIs, 20-seed robustness | Evaluation robustness | Must |
