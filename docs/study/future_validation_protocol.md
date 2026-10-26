# Future real-world validation of FAST's forecast (design only)

Status: **design only** (D-135, 2026-10-26). Not part of the current ethics application, not run, no
participants and no real data (CLAUDE.md rule 12 keeps the FYP synthetic). It describes what a
responsible test of FAST's predictions on real people would need, for the report's future work and for
anyone continuing the project. **A small pilot of it would test procedures only and must never be
presented as predictive validation.**

## 1. The question

Does FAST's forecast (forecast_v1, frozen as shipped) predict whether a real young Malaysian adult's
situation gets worse in the next 3 months, and are its percentages calibrated ("12 in 100" really
meaning about 12 in 100)? Secondary: do the transparent methods (health score, cushion months, the
Monte Carlo) do as well on real outcomes, as on synthetic ones (D-134)? Does the Future Self range
cover real outcomes at its stated rate?

## 2. Design

A **prospective observational cohort**:

1. Freeze the model before anyone enrols: record its version and file fingerprint (as the O2 spec was).
2. Write and fingerprint the analysis plan (this file's §6, made exact) before any outcome is seen.
3. At each month end, the app saves the user's assessment with the model version. FAST already does
   this once per checked-in month (D-88 A2, the `assessments` table), so the logging is largely built.
4. Three months later, record the outcome from the user's check-ins. Compare, never adjust the model
   during the study.

## 3. Participants and consent

| Item | Plan |
|---|---|
| Who | Adults aged 18–35 living in Malaysia who already manage money on a smartphone |
| Exclusions | People in formal debt management (AKPK DMP) at enrolment, for their protection; anyone involved in building FAST |
| Recruitment | Open invitation (campus, online communities); no targeting of people known to be in difficulty |
| Consent | Written, specific to real financial data: what is collected, why, who sees it, how long it is kept, that FAST gives education not financial advice, and that withdrawal deletes their data |
| Incentive | Modest and fixed (not tied to outcomes or to logging volume) |
| Withdrawal | At any time, with deletion (FAST's `delete_my_account()`, D-93) |

## 4. Data, kept to the minimum

| Collected | Not collected |
|---|---|
| Monthly totals the model needs: net income received, debt repayments, total owed, counted money (cash, bank, e-wallets), essential and total spending, "ran short this month?" | Merchant names, transaction descriptions, account or card numbers, IC numbers, names on any analysis file |
| The profile facts the model uses: type of work, age group, living with parents, sends money to family, festival | Free-text notes (redacted on the phone already, rule 11, and not exported) |
| The assessment FAST showed (band, forecast, model version) | Anything from bank integrations (FAST has none) |

Pseudonymous codes on every analysis file; the code-to-person key kept apart; deletion at a fixed date
after the study ends; storage in the existing Supabase setup (RLS on every table, rule 8; Singapore region).

## 5. The outcome

Exactly the O2 label, so the comparison is fair: the band (FAST's per-month rule from the frozen spec)
at t+3 worse than at t, **or** a shortfall (the check-in's "ran short this month?" or a missed payment)
in t+1..t+3; months with income too low to judge are excluded, as in O2. Its weaknesses are stated in
advance: self-reported shortfalls; missed check-ins (loss to follow-up). Windows with a missing
outcome are left out and counted; completers and drop-outs are compared on their starting figures.

## 6. Sample size and analysis

**Size.** External validation needs at least about 100 people who get worse and 100 who don't
(Vergouwe et al., 2005), and usually more for a precise calibration slope (Riley et al., 2021). At
about 12% of 3-month windows getting worse, that is roughly 850+ windows; because one person's windows
are related, plan on **about 300–400 people followed for at least 6 months**, a rough planning figure to
be recalculated with Riley's method before starting.

**Analysis** (fixed in advance, reported in full, failures included; TRIPOD+AI, Collins et al., 2024):

| Question | Measure |
|---|---|
| Does it rank people correctly? | PR-AUC and ROC-AUC with person-level bootstrap intervals, against B0 (base rates re-estimated on the first months only), the health score, cushion months and the Monte Carlo |
| Are its percentages right? | Calibration-in-the-large, calibration slope, reliability plot, expected calibration error (Van Calster et al., 2019); by type of work and age group where a group has at least 50 people and 10 events |
| If it is off, can it be fixed? | Recalibrate (first the overall level, then the slope) on the first half of the follow-up; judge the result on the second half only (temporal validation; Debray et al., 2015; Steyerberg, 2019) |
| Is the Future Self range honest? | Where real outcomes fall within each forecast's spread (PIT histogram) and the share inside the 10th–90th percentiles, by group (Gneiting et al., 2007) |
| Are warnings useful? | Net benefit at 10%, 20% and 30% (decision curves) |

## 7. Ethics and safety

- Full ethics committee review: real personal financial data puts it above the persona study's minimal risk.
- A data protection impact assessment; Malaysia's PDPA 2010 as amended in 2024 (check which provisions
  are in force when the study starts).
- FAST stays educational: no product recommendations (D-15), no automated decisions about anyone, and
  the data is never used for credit decisions.
- A distress procedure: the app's crisis reply and AKPK details; the researcher's contact for concerns.
- Security: encryption in transit and at rest, access limited to the analysis team, breach response
  agreed in advance.

## 8. A pilot first (feasibility only)

20–30 people for 2–3 months to test recruitment, how many keep checking in, data quality and how much
effort the check-ins take. Reported as feasibility, **never as evidence about the forecast's accuracy**.

## 9. References

- Collins, G. S., et al. (2024). TRIPOD+AI statement. *BMJ*, 385, e078378.
- Debray, T. P. A., et al. (2015). A new framework to enhance the interpretation of external validation
  studies of clinical prediction models. *Journal of Clinical Epidemiology*, 68(3), 279–289.
- Gneiting, T., Balabdaoui, F., & Raftery, A. E. (2007). Probabilistic forecasts, calibration and
  sharpness. *Journal of the Royal Statistical Society: Series B*, 69(2), 243–268.
- Riley, R. D., et al. (2021). Minimum sample size for external validation of a clinical prediction
  model with a binary outcome. *Statistics in Medicine*, 40(19), 4230–4251.
- Steyerberg, E. W. (2019). *Clinical prediction models* (2nd ed.). Springer.
- Van Calster, B., et al. (2019). Calibration: the Achilles heel of predictive analytics. *BMC
  Medicine*, 17, 230.
- Vergouwe, Y., et al. (2005). Substantial effective sample sizes were required for external
  validation studies of predictive logistic regression models. *Journal of Clinical Epidemiology*,
  58(5), 475–483.

(Check each reference against the original before citing it in the report.)
