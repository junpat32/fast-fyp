# Assumption audit: does each generator number fit the people it is used for?

Written 2026-10-26 (D-139; the 26 Oct brief, Improvement B part A). It checks the main generator settings in
`docs/calibration_table.md` and the frozen spec for **population, year, definition, unit, household vs individual,
gross vs net, and ratio type**, and whether quantities are wrongly assumed independent. **Nothing in the generator is
changed** (O2's data is frozen; D-132); each problem is a stated limitation and, where useful, an idea for a future
generator v2. Primary-source checks marked VERIFY remain Patrick's (WP-15).

Verdicts: **OK** (fits) · **Caveat** (fits with a stated limit) · **Mismatch** (the source describes a different
population or quantity; a limitation to report).

## 1. Setting by setting

| Setting | Source | Population, year, definition | Used for | Verdict and why |
|---|---|---|---|---|
| Wages by age (C-01) | DOSM Employee Wages, Q1 2025, Exhibit 3 | Individuals; formal-sector employees; **gross** monthly wage incl. bonuses and allowances; median; March 2025 | Employees' gross base pay, median by age band | **OK** (VERIFY). Individuals and gross, converted to net with EPF and SOCSO. Age 35 uses the 30–34 median; formal sector only |
| Wage spread (C-02) | DOSM all-ages P10/P90 | All ages, not by age band | σ_log 0.35 within each band | **Caveat**: no published within-band spread; an assumption bounded by data, tested 0.25–0.60 |
| EPF, SOCSO/EIS (C-07, C-08) | EPF Act, PERKESO schedules | Statutory rates | Gross → net | **OK** (VERIFY): flat 11% and 0.7% approximate the wage-band schedules |
| Spending shares (C-03) | DOSM HES 2024 Table 3.6 | **Households**, urban, head aged 25–34; shares of the group's total spending (a ratio of totals) | Every synthetic **individual's** spending mix, the same for everyone | **Mismatch**: household mix (often with children) applied to individuals aged 18–35; one mix for every income, so the synthetic world has **no Engel effect**. Pattern check P1 confirms it: essentials' share rises slightly with income where real data shows it falling (`ml/results/STRUCTURAL.md`) |
| Essential / discretionary split (D-34) | HES Table 3.6 shares | As above | 59.4% / 40.6% for everyone | **Mismatch** (same reason). Low incomes in reality spend a larger share on essentials |
| Spending ÷ income 60.8% (C-23, S12) | HES 2024 mean consumption RM5,566 ÷ HIES 2024 mean gross income RM9,155 | **Households, all ages**; ratio of means; same year (2024) for both | Calibrates the consumption ratio; checked by S12 on workers | **Caveat**. *Ratio type matches*: S12 divides total spending by total gross income (61.2%), like DOSM's ratio of means (the average of individual ratios would be 58.8%). *Income definition*: S12 uses base pay × 12, ignoring job-loss months and pay rises; on income actually received it is **62.9%**, still inside 55–68%. *Population differs*: households (several earners, older heads) vs individuals aged 18–35, who may well spend a larger share of their income; the direction of that bias is not known |
| Living with parents (C-34) | No national source | Assumption (UKM, UiTM studies qualitatively) | 0.6 (18–24) / 0.3 (25–35); housing × 0.4 | **Caveat**: assumption, tested ±0.2; it also shapes the essentials' share by income (P1) |
| Starting cushion (C-09, C-21) | Findex 2025 fin24b | **Household** ("could your household cover expenses…"); **any means of coping** (savings, borrowing, family); ages 15–24 and 25+, blended | Each individual's starting cash in months of costs | **Mismatch, stated**: household and "any resource" measure used as an individual's cash. Drawn **independent of income**; by month 12 the cushion does rise with income (P2 reproduced) |
| Saved over the year (C-10, S13) | Findex save_any_t_d | Individuals, any saving in 12 months | Check only | **OK** as a check (a loose one: "saved any money" ≠ "more cash at month 12 than month 0") |
| Red share (C-05, S3) | BNM FSR 2H 2022 | **Household borrowers incl. mortgages**, all ages | Check only (5–25%) | **Caveat, stated** (§1): no housing loans in the generator, so the lower bound was set below BNM's level |
| BNPL (C-12, S10, S11) | BNM FSR 2H 2022 and 2H 2024 | Users counted by accounts (possibly double-counted); age share and user count from different years | 32% users, 2.7 purchases a month, overdue bracket | **Caveat**: 32% is an upper bound. BNPL use is driven by impulsivity only, **independent of income** although BNM reports 80% of users earn under RM3,000; P5 (users run short more often) is not reproduced |
| Gig income (C-18) | DOSM p-hailing survey 2022 | p-hailing (delivery) riders only; **unclear whether fuel and vehicle costs are deducted** | Gig workers' net income | **Caveat**: if the survey's earnings are before fuel, synthetic gig incomes are too high; year 2022 vs 2025 elsewhere |
| Job loss and spells (C-25, D-47) | DOSM LFS 2025 | Unemployment **rate** (includes first-time job seekers); spell lengths from a stock snapshot (over-represents long spells) | Monthly job-loss chance and spell length | **Caveat**: may overstate job loss slightly; risk is the **same at every income**, though lower-paid jobs are usually less secure |
| Vehicle ownership (C-29) | DOSM HIES 2022 | **Households** (90% own a car) | Each employee's chance of owning a car or motorbike | **Mismatch, stated**: household ownership as individual ownership (upper bound, tested × 0.6) |
| Family support (C-33) | Findex fin28 | Digital transfers to relatives **in another city** | Share sending money monthly | **Caveat**: a lower bound (cash and same-city transfers missing), tested to 0.35 |
| Personal loans (C-32) | Findex fin22a | Borrowed from a bank in the past year (flow) | Share holding a loan (stock) | **Caveat**: a flow used as a stock |
| Credit cards (C-27, C-28) | Findex fin22g; BNM credit card policy | Used a card in the past year; BNM limits apply only up to RM36,000 a year | Holding; limit 2 × gross monthly income for all | **Caveat**: simplifications, tested (0.10–0.25 holding; 3 × limit above RM3,000) |
| Festive months (C-35) | Census 2020 religion shares | Whole population, all ages | Each user's festival | **Caveat**: religion as a proxy for the main festival |
| Semester months (C-26) | MMU 2024 calendar | One university, 2024 | Students' semester starts | **Caveat**: one university's calendar, previous year |
| Life events (C-20) | `docs/life_events.md` | 21 events; prices partly quoted, **all frequencies assumed** | Shocks | **Caveat**: relative frequencies not varied (only the overall scale k) |
| DSR, DTI, bands | Spec §6, D-04–D-06 | Individuals; **net** income; DSR on the 3-month median | Bands and features | **OK**: definitions consistent (DSR ≠ DTI, rule 6) |

## 2. Quantities assumed independent that probably aren't

| Assumed independent | What evidence suggests | Effect on the results |
|---|---|---|
| Spending mix and income | Engel's law: lower incomes spend a larger share on essentials | The essentials'-share feature carries less signal than for real people (P1) |
| Starting cushion and income | Richer people have bigger buffers | Partly self-corrects over the year (P2 reproduced by month 12) |
| Job-loss risk and income | Lower-paid and younger workers lose jobs more often | Shortfalls may be under-concentrated among low earners, although P3 is still reproduced strongly |
| BNPL use and income | BNM: 80% of BNPL users earn under RM3,000 | BNPL looks less linked to strain than it may be (P5 unclear) |
| Life events and income volatility | Unsteady incomes often come with unsteady costs | Tested as alternative world W3: the model's ranking holds, its percentages come out too low |
| Vehicle events and age or income | Older, cheaper vehicles break down more | Not modelled; a minor effect |

Traits that *are* linked on purpose: impulsivity, discipline and overconfidence (Gaussian copula, §3a); spending
and BNPL with impulsivity; corrective action with discipline.

## 3. What this means

1. **The biggest issue is household figures used for individuals** (spending mix, spending ratio, cushion, vehicle
   ownership). The report should say the synthetic people are "individuals calibrated mostly to household
   statistics", which is the honest description.
2. **The spending mix doesn't respond to income** (no Engel effect). Confirmed by pattern check P1; a small effect on
   O2 because the essentials'-share feature carries little weight.
3. **Several risks are independent of income** (job loss, BNPL use, starting cushion). The strong income gradient
   in running short (P3) still appears, because income drives disposable income and saving.
4. **Nothing here changes O2 or the app.** A future generator v2 could make the spending mix, job-loss risk and BNPL
   use depend on income, using individual-level sources (e.g. Findex microdata by income, DOSM LFS by wage band).
5. **Still Patrick's:** the VERIFY checks against primary sources (WP-15).
