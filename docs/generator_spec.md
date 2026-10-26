# Generator spec: FAST synthetic data + pre-registered O2 evaluation

Version: **v1.0 FROZEN** (2026-10-12) · Owner: Patrick · Drafted with Claude · Pre-registered: §11–14 are frozen. The reference copy is `docs/frozen/generator_spec_v1.0.md`; its SHA-256 fingerprint is in `DECISIONS.md` (pre-registration record)

> **Pre-registration rule.** Sections 11–14 (label, noise levels, evaluation plan and
> success criterion, sanity checks) are frozen when this file is saved as v1.0 (a
> read-only copy `docs/frozen/generator_spec_v1.0.md` plus its SHA-256 fingerprint,
> recorded in `DECISIONS.md` and emailed to the supervisor; D-36), **before** any O2
> model is trained. Changes after that are recorded in
> `DECISIONS.md` as deviations, with the reason. Items marked `[DECISION]` must be
> confirmed by Patrick before v1.0.

Parameter values come from `docs/calibration_table.md` (IDs `C-xx`). Every value is
either calibrated (sourced) or an assumption (tested across a range, see §16).

---

## 1. Purpose and limits

**The data supports:**
1. Checking that the whole pipeline works (generator → features → models → app).
2. Comparing forecasting methods *relative to each other*: persistence, rule
   heuristic, Markov chain, Monte Carlo, LR / RF / XGBoost.
3. Seeding the app and the user-study personas.

**The data does not support:** claims of real-world predictive accuracy, or
population statistics about Malaysians. The model learns the generator's
structure; that limitation is stated in the report.

**Not modelled (stated limitations, D-39):**
- **Housing loans.** Housing is treated as rent (spending), not debt, because most of
  FAST's target users rent or live with family. BNM's DSR figures include mortgages, so
  synthetic DSRs are expected to run lower than BNM's medians.
- **Regional differences** (e.g. median wage RM4,445 in KL vs RM1,800 in Kelantan).
  One national distribution per age band is used.
- **EPF Account 3 withdrawals, side income, government cash aid (e.g. STR), inflation
  within the year and income tax.** Each is a minor buffer or cost for this group.
- **Living-arrangement shares** have no national source; they are a tested assumption (C-34).

## 2. Size and time

| Setting | Value |
|---|---|
| Users `N_USERS` | **1,000** `[DECISION A: CONFIRMED by Patrick 2026-10-09]` (alternative was 300 for continuity with FYP1. 1,000 gives narrower confidence intervals and is still tiny to compute) |
| Months | 12, mapped to calendar year 2025 (month 1 = Jan) |
| Label months `t` | 3 … 9 (features need `t-2 ≥ 1`; the label needs `t+3 ≤ 12`) |
| Labelled rows | up to 7 per user → ≈ 7,000 for 1,000 users |

Cost: generation is O(users × months × transactions per month) ≈ 1,000 × 12 × ~40.
It runs in seconds on any machine.

## 3. Generation overview (logic first)

```
INVARIANTS
  G1  same config + same seed → byte-identical outputs
  G2  hidden traits are written only to latent*.parquet, never to observable files
  G3  money is rounded to 2 decimal places; no NaN or inf in any output
  G4  every parameter value comes from config.yaml, which mirrors the calibration table

for each user u:
    sample static attributes (age, employment type, festive month, debt holdings)   §4, §6
    sample hidden traits θ_u                                                        §3a
    initialise cash cushion                                                         §8
    for month m in 1..12:
        income_m      ← base income × noise × regime                               §4
        spending_m    ← essentials + discretionary (× festive) (× correction)       §5
        commitments_m ← PTPTN + vehicle + personal loan + card minimum + BNPL       §6
        family_m      ← monthly family support (not a debt; not in DSR)               §6
        shocks_m      ← life-event deck: Bernoulli per eligible event × k (+ clustering) §7
        hidden_cost_m ← unobserved leakage (noise level)                            §12
        cash_m        ← cash_{m-1} + income − spending − commitments − family − shocks − hidden
        if cash_m < 0: move the deficit to the credit card up to its limit; any rest → shortfall + arrears
        behaviour update: goals, corrective action                                  §9
        emit transactions for month m                                               §10
compute bands, flags, features, labels                                              §6, §9, §11
```

### 3a. Hidden traits (oracle only)

| Trait | Distribution | Drives |
|---|---|---|
| `imp` impulsivity | Beta(2, 5) | Discretionary spending variation; BNPL uptake; consumption ratio ↑ |
| `dis` discipline | Beta(5, 2), Gaussian-copula correlation ρ = −0.4 with `imp` | Corrective action; paying credit cards in full; consumption ratio ↓ |
| `ovc` overconfidence | Beta(2, 4), ρ = +0.3 with `imp` | How far savings targets exceed what is realistic |
| `sigma_inc` income volatility | Employees U(0.03, 0.08); gig from C-18; students U(0.20, 0.40) | Month-to-month income noise |
| BNPL use | Probability of being a BNPL user rises with `imp` (§6, C-12) | BNPL plans |
| `k` shock scale | 1.0: multiplies every event frequency in the life-event deck (C-20, §7); per-event multipliers (gig ×1.8 on vehicle/phone events, students ×2 on laptop) are in the deck | Shocks |

All trait parameters are assumptions (§16).

## 4. Demographics and income

| Item | Rule | Source |
|---|---|---|
| Age | Employees and gig workers: uniform **18–35** (includes school-leavers who start work after SPM; D-37). Students: uniform 18–23. Students' part-time work is covered by student income below | Uniform shape: assumption. Age range: FAST target group |
| Employment mix | employee / gig / student = **70 / 15 / 15** `[DECISION B: CONFIRMED 2026-10-09]`. Anchored to DOSM LFS (employees ≈ 75% of employed), ISEAS 2026 / DOSM 2022 (gig ≈ 10% of employment, skewed young), MOHE (≈ 1.1 M Malaysian students in higher education). 65/30/5 is kept as the gig-heavy sensitivity case (§16) | C-22 (calibrated, approximate) |
| Employee gross base income | LogNormal with median = DOSM median for the age band (C-01): 18–19 → **RM1,700** (DOSM "< 20" group), 20–24 → RM1,900, 25–29 → RM2,600, 30–35 → RM3,200 (age 35 uses the 30–34 median), σ_log = 0.35 (C-02). **Floored at the RM1,700 minimum wage** (Minimum Wages Order 2024: employers with ≥ 5 staff from 1 Feb 2025, all employers from 1 Aug 2025; C-36; D-40). The ≈ 5% of formal employees DOSM records below RM1,500 (part-time, exempt) are not modelled | C-01, C-02, C-36 |
| Employee net income | gross × (1 − 0.11 EPF − SOCSO/EIS) (C-07, C-08); income tax ignored at these levels (stated as a limitation) | C-07, C-08 |
| Gig net income | LogNormal, median **RM2,500**, **σ_log = 0.70** across workers (fitted to DOSM's 2022 p-hailing survey: 23.4% earn ≤ RM1,500, 26.8% RM1,501–2,499, 11.7% RM2,500–3,170; C-18; D-40); no EPF deduction | C-18 (calibrated, approximate) |
| Student income | U(RM500, RM1,200), irregular | Assumption |
| Monthly draw | income = base × exp(ε), ε ~ N(−σ²/2, σ²) with σ = `sigma_inc` × noise scale (§12) | — |
| Regimes (world-only) | Employees: **job loss 2.25%/month at age ≤ 30, 1.1%/month at 31–35** → income 0 for a spell of 1–2 months (64%), 3–6 months (30%) or 7–12 months (6%), from DOSM LFS 2025 (63.7% of the actively unemployed out of work < 3 months, 5.6% > 12 months). With a mean spell of ≈ 2.9 months this gives steady-state unemployment ≈ 6.1% and ≈ 3.0%, matching DOSM 2025 (ages 15–30: 6.1–6.2%; all ages: 3.0%). *[Post-freeze clarification 2026-10-12, D-47, before any model run; was 3% / 1.5% with 1–3 month spells; §4 is not frozen and the new rates are inside the §16 range]* **Pay rise about once a year** (1/12 per month, +3–7%, mean ≈ 5%; DOSM median wage growth 5.5% y/y, March 2025). Gig: slow month 8%/month (× 0.5–0.8) (C-25; D-40) | C-25 (job loss and pay rise calibrated to DOSM; spell length and gig slow months assumption) |

The regimes and clustered shocks exist **only in the generator**. The app's Monte
Carlo model does not include them (D-14), so testing calibration against this data
is not circular.

## 5. Spending

| Item | Rule |
|---|---|
| Total spending target | `c_u × disposable income`, where **disposable income = median net income − fixed debt payments (PTPTN, vehicle, personal loan, starting card minimum) − family support**, and `c_u = clip(U(0.75, 1.00) + 0.10·(imp − 0.29) − 0.10·(dis − 0.71), 0.60, 1.05)` (C-23; D-40). 0.29 and 0.71 are the means of the trait distributions. Spending comes out of what is left **after** debts because DOSM's consumption expenditure excludes loan repayments by definition. The range U(0.75, 1.00) is calibrated so that workers' spending ÷ gross income ≈ DOSM's 60.8% (HES 2024 RM5,566 ÷ HIES 2024 RM9,155; check S12) |
| Category shares | HES 2024 **Table 3.6, urban households with head aged 25–34** (C-03), renormalised within each group. Decision F, D-28 |
| Living with parents | Each user lives with parents with p = **0.6 (age 18–24)** or **0.3 (age 25–35)** (C-34, assumption). If so, housing & utilities (04) spending × 0.4 (a contribution to the family home); the saving is **not** redistributed to other categories, so these users have a larger surplus |
| Essential / discretionary split | Of the total spending target: **essentials 59.4%, discretionary 40.6%** (sum of the HES Table 3.6 urban 25–34 shares in each group; D-34). Applied before noise, festive, semester and correction effects |
| Essentials | housing & utilities (04), food at home (01), transport (07), communication (08), health (06), education (10). Low noise: σ = 0.05 |
| Discretionary | eating out (11), personal care & misc. (13), recreation (09), clothing (03), furnishings & household equipment (05), insurance & financial services (12), alcohol & tobacco (02). Noise σ = 0.10 + 0.40 × `imp` (so impulsive users exceed the CV > 0.35 flag) |
| Classification rule | Engel's law on HES 2024 Table 3.15: a group whose share falls from income decile D1 to D10 is a necessity (essential); one whose share rises is discretionary. Stated exceptions, using short-run flexibility (what can be cut next month): **transport** is essential (share rises with income, but commuting can't be cut quickly) and **clothing** is discretionary (share roughly flat, but purchases can be postponed) |
| Festive month | Each user has one festive month `f_u`: March (Hari Raya) **65%**, January (CNY) **19%**, December (Christmas) **9%**, October (Deepavali) **6%**, from Census 2020 religion shares (Islam 63.5%, Buddhism 18.7%, Christianity 9.1%, Hinduism 6.1%, renormalised; C-24, C-35; D-40). In `f_u`, discretionary spending × U(1.2, 1.4) (C-19) |
| Semester start (students) | × 1.15 on discretionary + education in the semester-start months {3, 8, 11} (C-26). If a student's festive month is also a semester start (e.g. March, Raya), **both multipliers apply** (Decision F, D-28) |
| Corrective action | See §9 |
| Monthly budget | The user's budget for month m = 0.95 × median of their **total** spending in the **previous** 3 months (m−3..m−1; fewer at the start; month 1 has no budget) (assumption; D-41). "Overrun" = total spending in m > budget for m |

## 6. Debt, DSR, DTI and bands

| Debt type | Who holds it | Monthly payment | Balance |
|---|---|---|---|
| PTPTN | **Employees and gig workers only**, p = 0.45 for age ≥ 23 (assumption). **Students never repay** (repayment starts after graduation; D-38) | from C-14 | Starting balance: loan amount U(RM15,000, RM50,000) (C-14 tenure bands), reduced by repayments already made: balance = loan × (1 − years since age 23 ÷ tenure), tenure 15 years for loans above RM22,000, 10 years below (C-14). Then declines with payments |
| Vehicle ownership | Two separate attributes, `has_car` and `has_motorbike` (C-29, D-35). **Employees:** independent draws, car 0.90, motorbike 0.75 (DOSM household ownership used as a proxy; an upper bound for individuals). **Gig:** one work vehicle, motorbike 0.55 / car 0.45 (≈ 600k p-hailing riders of ≈ 1.12 M gig workers). **Students:** car 0.32 / motorbike 0.13 / none 0.55 (UTM campus survey, n = 31: weak evidence) | — | Ownership decides which vehicle events in the life-event deck apply |
| Vehicle loan | Each owned vehicle carries a hire-purchase loan with p = 0.5 (assumption); **p = 0.1 under age 21** (most drive a family vehicle); **students never carry their own vehicle loan** (the family pays) (D-40, assumption) | from C-17 (motorbike RM150–400, car RM400–900) | Starting balance = instalment × remaining months; tenure motorbike 5 years, car 9 years (C-31), remaining months U(12, tenure). Then declines with payments |
| Credit card | **Eligible** only if age ≥ 21 and gross monthly income ≥ RM2,000 (BNM minimum RM24,000/yr; C-28, D-33). Among eligible employees and gig workers, holders are drawn so that **≈ 15%** of all employees + gig workers hold a card (C-27, D-32); if fewer than 15% are eligible, all eligible users hold one. Students never hold one | max(minimum rate × balance, fixed minimum) (C-16); **each month** pays in full with probability `dis`, otherwise pays the minimum. For gig workers, "gross income" in the eligibility and limit rules means income as received | Revolves at the APR tier (C-15); monthly interest = APR ÷ 12 on the unpaid balance. **Starting state (D-38):** users who pay in full (drawn with probability `dis`) start with balance RM0 and the 15% tier; others start with balance U(10%, 60%) of the limit (C-30) and the 17% tier; the tier then follows the 12-month payment record. **Credit limit = 2 × gross monthly income** (BNM cap for cardholders earning ≤ RM36,000/yr; applied to all holders as a simplification; C-28, D-33) |
| BNPL | Each user (age ≥ 18) is a BNPL user with p = clip(0.32 × `imp` ÷ 0.29, 0, 0.9), so ≈ 32% on average, more if impulsive (C-12). Users make new purchases ~ Poisson(2.7 per month) (C-12) | amount LogNormal(median RM60, σ 0.9), clipped to RM10–2,000 (mean ≈ RM90; BNM average ≈ RM85, C-12); 3 instalments, 0% interest (C-13); late fee U(RM10, RM30) if an instalment can't be paid (C-13). **BNPL is a payment method, not extra spending:** each purchase is part of that month's discretionary spending (capped at the month's discretionary amount); its cost leaves cash as 3 monthly instalments, which count in DSR | Ends after the last instalment |
| Personal loan | Employees and gig workers aged ≥ 21, p = **0.07** (C-32: Findex 2025, 7.2% borrowed from a bank or financial institution in the past year) | instalment U(RM200, RM800) (assumption) | Starting balance = instalment × remaining months, tenure 5 years, remaining U(12, 60) months. Counts in DSR and DTI |
| Family support (not debt) | Employees and gig workers, p = **0.17** (C-33: Findex 2025, 15.3–16.9% sent money to relatives in another city; a lower bound) | fixed monthly transfer U(RM100, RM500) (assumption), recorded as a transfer out | Not a debt: **not** in DSR or DTI; treated as essential (not cut by corrective action). The app must present it as a legitimate commitment, not overspending |

**Definitions (one source of truth, shared with the app):**

```
DSR_m  = total monthly commitments_m ÷ net_income_median3_m      (median of months m-2..m)
DTI_m  = total outstanding debt_m ÷ (12 × net_income_median3_m)

if net_income_median3_m < RM300:  band = INSUFFICIENT_INCOME      # assumption threshold
elif DSR_m < 0.30:                band = GREEN
elif DSR_m < 0.60:                band = YELLOW
else:                             band = RED
hysteresis: if band_{m-1} == RED and 0.55 ≤ DSR_m < 0.60:  band = RED   # leave Red only below 55%
# hysteresis needs a real RED month: if band_{m-1} is INSUFFICIENT_INCOME (or m = 1),
# the plain thresholds apply (Decision E, D-27)
```

*[Note 2026-10-13, D-49: the **app** engine shows a better band only after it has held for 2
months; the generator keeps this per-month v1 rule unchanged (`shared/thresholds_spec_v1.json`).]*

Boundary tests (also in the O1 suite): DSR 0.59 → Yellow; 0.60 → Red; 0.61 → Red;
Red at 0.57 last month and 0.57 now → Red; Red last month and 0.54 now → Yellow;
INSUFFICIENT_INCOME last month and 0.57 now → Yellow; month 1 at 0.57 → Yellow.

## 7. Shocks

| Item | Rule |
|---|---|
| Source | Life-event deck `docs/life_events.md` (21 events, C-20). Decision G, D-29 |
| Occurrence | For each user, month and **eligible** event e: occurs with probability min(1, `k` × p_e × group multiplier × clustering). Clustering = 1.5 if any shock (≥ RM300 event) happened in m−1 (world-only, D-14). Events are independent Bernoulli draws, so more than one can happen in a month |
| Cost | Uniform within the event's cost range |
| Scale `k` | Default 1.0. The **only** shock setting that may be tuned (§11), test range 0.5–1.7 (§16). At `k` = 1 the deck implies ≈ 0.08–0.14 shocks ≥ RM300 per month, consistent with the earlier placeholder of 0.12 |
| Recording | Events appear as transactions in the deck's category (so they are partly observable). `minor` events look like ordinary spending; only `shock` events are counted in the shock-count feature |

## 8. Cash cushion

| Item | Rule |
|---|---|
| Starting cushion | Drawn from the Findex 2025 fin24b distribution for Malaysia (C-09, C-21; D-31), in months of (essentials + commitments): 13% → U(0, 0.5); 29% → U(0.5, 1.5); 18% → U(1.5, 2.5); 40% → U(2.5, 6). Shares are a 39/61 blend of the 15–24 and 25+ groups, renormalised without don't-knows |
| Meaning of "cushion" | All resources the user can draw on (savings, plus help they could borrow or receive), because fin24b counts every means of coping. Stated as a limitation; the own-cash-only case is a §16 sensitivity test |
| Monthly update | cash_m = cash_{m−1} + income − spending − commitments − family support − shock costs − hidden cost (§12) |
| Deficit | If cash_m < 0: move the deficit to the credit card if held, **up to the unused credit limit** (balance ↑). Any deficit left over (no card, or the limit is reached) → `shortfall_m = 1`, cash floors at 0, and unpaid commitments become arrears (counted as outstanding debt). Card holders can therefore still have shortfalls (D-33) |
| Cushion months | cushion_m = cash_m ÷ mean(essentials + commitments over months m−2..m) |

## 9. Behaviour (what makes the flags meaningful)

| Behaviour | Rule |
|---|---|
| Corrective action | If the band worsened or cushion < 1 month at m: with probability `dis`, discretionary spending × (1 − κ), κ ~ U(0.10, 0.25), for the **next 3 months** (m+1..m+3; a new trigger restarts the 3 months) (D-41; was 1 month, which spending noise hid) |
| Saved (observable) | saved_m = income − total spending − debt payments − family support − life-event costs in month m (the unobserved hidden cost is excluded). Savings rate_m = saved_m ÷ income_m (undefined when income is 0) |
| Savings target | target_m = (1 + `ovc`) × mean saved over the previous 3 months, floored at RM50 (month 1: RM50). **Goal stickiness:** if the user missed last month's target, with probability `ovc` they keep last month's target when the new value would be lower (D-41) |
| Goal achievement | achieved_m = saved_m ÷ target_m |

**Behavioural proxy flags (computed from observable data only; D-08, D-09):**

| Flag | Fires when (window m−2..m) |
|---|---|
| Impulsivity | CV (sample standard deviation ÷ mean) of discretionary spending > 0.35 **and** an overrun in ≥ 2 of the 3 months. The user's festive month is excluded from the CV (needs ≥ 2 remaining months). Needs a budget for all 3 months |
| Overconfidence | Goal achievement < 60% for 3 consecutive months **and** the next target (m+1, set from data up to m) is more than 80% of the current one (cut by < 20%) |
| Delayed correction | **Under pressure** (band RED or cushion < 1 month) in both m−1 and m, **and no correction**: the average discretionary spending of m−1 and m is above 95% of the median of m−4..m−2, **and** the average savings rate of m−1 and m is less than 3 points above the average of m−4..m−2 (D-41). Smoothing over 2 months stops ordinary spending noise from looking like a correction; plain YELLOW alone is too common to count as pressure |

Flag months are scored from m = 3 (impulsivity and overconfidence from the first month where every input exists). Flags are validated against the hidden traits by check S14; a flag that fails S14 is not shown to users (§14).

## 10. Transactions and output files

Transactions: per month and category, count ~ Poisson(category rate), amounts split
with a Dirichlet; merchant labels are generic (e.g. `DINING_014`, `PETROL_003`).
**No real brand names.** Categories align with OpenDOSM MCOICOP.
`source` ∈ {manual, ocr, notification}.

| File | Contents | Observable? |
|---|---|---|
| `users.parquet` | user_id, age, age_band, employment_type, festive_month, has_car, has_motorbike, lives_with_parents, family_support (yes/no), debt holdings (yes/no) | Yes |
| `monthly.parquet` | user × month: net income, spending by category, commitments and balances by debt type, BNPL counts, shock count and cost, cash, cushion months, DSR, DTI, band, budget, overrun, savings target, saved, shortfall | Yes |
| `transactions.parquet` | txn_id, user_id, date, amount, direction (in/out), category, merchant label, source | Yes |
| `flags.parquet` | user × month: the three proxy flags | Yes (derived) |
| `labels.parquet` | user_id, t, y, band_t, band_t+3, shortfall within t+1..t+3, exclusion reason | Label |
| `latent.parquet`, `latent_monthly.parquet` | hidden traits; hidden cost; regime states | **No: oracle and audits only** |
| `metadata.json` | spec version, spec SHA-256, config hash, seed, noise level, row counts | — |

## 11. Label and features (frozen at v1.0)

**Label** `[DECISION C: CONFIRMED 2026-10-09]`:

```
band_rank: GREEN 0, YELLOW 1, RED 2
y(u,t) = 1  if  band_rank(t+3) > band_rank(t)                 # debt position worsened
            or  any shortfall in months t+1..t+3              # ran out of cash
          0  otherwise
Rows where band(t) or band(t+3) is INSUFFICIENT_INCOME are excluded (count reported).
```

Rejected alternatives: (a) band only; (b) cushion falls from ≥ 1 to < 1 month.
The chosen label matches what the app's Monte Carlo estimates (probability of a
shortfall), so the two can be compared directly.

Justification (each part of the composite has support; page numbers to be added):
predicting *deterioration* rather than a level follows the IFRS 9 "significant increase
in credit risk" idea; the DSR component follows BNM's use of DSR > 60% to mark vulnerable
borrowers (C-05); the shortfall component follows Lusardi, Schneider & Tufano (2011) on
financial fragility; combining debt burden with liquid buffers follows Ampudia,
van Vlokhoven & Żochowski (2016).

Known properties, stated in advance: (1) a user already in RED can only become positive
through a shortfall (ceiling effect); (2) Green→Yellow and Yellow→Red count equally;
(3) the label mixes two mechanisms. Hence the component breakdown in §13;
(4) the band is compared only at t+3, not at every month in between, so short band
"flapping" is not counted as deterioration (a dip with real cash trouble is still caught by
the shortfall part); (5) in the prototype ≈ 78% of positives were shortfall-only, so O2
mainly tests whether ML can **foresee cash shortfalls**, which the rule-based band cannot.

Horizon: 3 months, short enough to act on, and with 12 months of data it leaves 7 label
months per user (a 6-month horizon would leave 4). Reviewed with Patrick 2026-10-12 (D-42).

**Positive rate** `[DECISION D: CONFIRMED 2026-10-09]`: **no target.** The positive
rate is an *outcome* of the calibrated parameters, not something the generator is tuned
to hit. It must fall inside the plausibility band **10–30%** at medium noise (check S9;
anchors: BNM up to 25% of borrowers above 60% DSR, C-05; Findex emergency funds, C-09).

Only if S9 fails: adjust **first** the shock scale `k` (§7, within 0.5–1.7), and only then
the consumption-ratio range (within its §16 range), and the latter **only if S12 (spending ÷
income vs DOSM) still passes afterwards** (D-45), looking **only** at label prevalence
(never at model results), until it is inside the band. Record every adjustment and its reason in `generator/TUNING_LOG.md` before any
model is trained. Then freeze.

**Features** X(u,t), using months t−2..t only:

| Group | Features |
|---|---|
| Income | median3, CV3, employment_type, age_band |
| Spending | essential share, discretionary CV3, overrun count3, savings rate3 |
| Debt | DSR_t, DTI_t, band_t (one-hot), active BNPL plans, new BNPL in last 3 months, has personal loan |
| Household | lives with parents, pays family support (in the app both are **asked at onboarding**, not inferred; D-42) |
| Liquidity | cushion months_t, slope of cash over 3 months, shortfall in last 3 months |
| Behaviour | impulsivity, overconfidence and delayed-correction flags |
| Shocks | count in last 3 months |
| Calendar (allowed future info) | festive or semester month within t+1..t+3 |

Invariant test: a unit test fails if any feature reads a month > t.

## 12. Noise levels (frozen at v1.0)

| Level | Income/spending noise scale | Hidden cost (not visible in any feature) |
|---|---|---|
| Low | × 0.5 | 0% of income |
| **Medium (primary)** | × 1.0 | 3% of income × LogNormal(0, 0.5) |
| High | × 1.5 | 6% of income × LogNormal(0, 0.5) |

The hidden cost stands in for **unlogged spending** in the real app (cash purchases nobody
records, small forgotten payments, money lent to friends). No Malaysian figure for
under-logging was found; real under-logging may be larger than 3–6%, which is a stated
limitation and the reason the high level exists. The levels are stress-test settings, not
calibrated facts: what is reported is the **trend** across levels. Medium is the
calibrated setting at which all realism anchors were matched (D-43).

## 13. O2 evaluation plan (pre-registered, frozen at v1.0)

| Item | Plan |
|---|---|
| Split | `GroupKFold(5)` by user_id; out-of-fold (OOF) predictions pooled |
| Tuning | Inner `GroupKFold(3)` on training folds only. Grids: LR C ∈ {0.1, 1, 10} (standardised, L2); RF 300 trees, max_depth ∈ {4, 8, None}; XGB max_depth ∈ {3, 5}, learning rate 0.1, ≤ 300 rounds with early stopping on the inner validation fold |
| Imbalance | `class_weight="balanced"` / `scale_pos_weight` |
| B0 persistence-with-base-rates | P̂(y \| band_t, cushion bucket {<1, 1–3, ≥3 months}) estimated on training folds |
| B1 rule heuristic | score = 1[DSR ≥ 0.5] + 1[cushion < 1.5] + number of active flags + 1[active BNPL ≥ 2]; no fitting |
| B2 Markov chain | States = band × cushion bucket (9). Transition matrix from training-fold users with Laplace smoothing α = 1. Score = probability, over 3 steps, of reaching a worse band or the lowest cushion bucket (that bucket made absorbing) |
| Models | LR, RF, XGBoost |
| Ceiling (oracle) | XGBoost with the hidden traits added; reference only |
| Comparator (Should) | App Monte Carlo P(shortfall in 3 months); reported, not part of the criterion |
| Primary metric | PR-AUC on OOF predictions |
| Secondary | Minority-class recall and macro-F1 at a threshold chosen to maximise F1 on the **inner-CV out-of-fold predictions of the training folds** (never on the test fold; D-44); Brier score; reliability plot |
| Calibration (reported, not part of the criterion) | Brier score and reliability plot also reported **after isotonic calibration** fitted on the inner-CV predictions of the training folds. Class weighting inflates raw probabilities, so the app must not show a probability without this step (D-44) |
| Confidence intervals | User-level bootstrap (resample users), 1,000 resamples, 95% percentile intervals |
| **Success criterion (O2)** | **Medium noise, master seed: the 95% CI lower bound of [PR-AUC(best ML) − PR-AUC(best of B0–B2)] > 0.** "Best" = highest OOF PR-AUC point estimate (this selection makes the comparison slightly optimistic; all pairwise differences are reported too). The effect size (ΔPR-AUC point estimate) is always reported alongside the pass/fail result; no minimum effect size is required (D-44) |
| Robustness (reported, not pass/fail) | 20 generator seeds × 3 noise levels: median ΔPR-AUC and share of seeds with Δ > 0. **No re-tuning:** each model reuses the hyperparameters chosen most often across the 5 outer folds of the main run (ties → the simpler setting); XGBoost uses the median best iteration from the main run (D-44) |
| Leakage alarms (stop and audit) | Any model PR-AUC > 0.95 · shuffled-label PR-AUC not within ±0.03 of prevalence · any single-feature model PR-AUC > 0.90 · the feature-timestamp unit test fails |
| Model choice for the app | Simplest model whose CI overlaps the best (LR > RF > XGB) |
| Always reported | All models × all noise levels, confusion matrices, Brier scores, reliability plots, SHAP global summary + 3 persona explanations, every failure; label prevalence, plus a **breakdown of positives by component** (band-worsening only / shortfall only / both) **and by starting band**; PR-AUC per employment type |

If the criterion is not met, the result is reported as a valid negative finding and
the app relies on rules + Monte Carlo (O2 review step).

## 14. Sanity checks before any modelling (frozen at v1.0)

All checks are judged on the **medium-noise dataset generated with the master seed**.
Results at low and high noise are reported for information only, not as pass/fail (D-43).

| ID | Check | Pass condition |
|---|---|---|
| S1 | Employee median net income by age band | within ±10% of DOSM median (C-01) × net factor |
| S2 | Aggregate category shares, measured on **non-festive, non-semester-start months, excluding life-event transactions and users living with parents** (HES measures normal spending of independent households; D-34, D-39) | within ±3 percentage points of HES 2024 Table 3.6 urban 25–34 (C-03) for each category |
| S3 | Share of borrowers in Red at month 12 | 5–25%. Upper bound from BNM (up to 25%, C-05). The lower bound is set below BNM's level because synthetic DSRs exclude housing loans and are expected to run lower (§1) |
| S4 | Starting cushion distribution at month 1 | Share in each of the 4 buckets (< 0.5, 0.5–1.5, 1.5–2.5, ≥ 2.5 months) within ±5 points of the C-21 target (13 / 29 / 18 / 40%) |
| S5 | DSR vs DTI | not identical; Pearson r < 0.99 |
| S6 | Each proxy flag | fires in 5–30% of user-months |
| S7 | Edge cases present | ≥ 1% of user-months have insufficient income; ≥ 1 job-loss episode per 100 employees |
| S8 | Data hygiene | no NaN/inf; money at 2 dp; balances ≥ 0 where required |
| S9 | Positive rate (medium noise) | 10–30% (plausibility band; not a target, see §11) |
| S10 | BNPL overdue: BNM's 17% of users with overdue payments (point-in-time, Q4 2022; C-12) must lie **between** the synthetic share overdue at quarter-end months (a lower bound, since the generator clears arrears at once) and the share ever overdue in 12 months (an upper bound) | 17% inside [quarter-end share, 12-month share] |
| S11 | Share of users who are BNPL users | within ±5 points of 32% (C-12) |
| S12 | Workers' total spending ÷ gross income over the year | 55–68% (DOSM 2024: HES RM5,566 ÷ HIES RM9,155 = 60.8%; C-23) |
| S13 | Share of users whose cash at month 12 exceeds month 0 ("saved over the year") | 50–75% (Findex 2025: saved any money 72.7% at 15–24, 58.8% at 25+; C-10) |
| S14 | **Flag validity (audit with hidden traits, D-41).** For each flag: its firing rate in the riskiest quarter of its hidden trait (top `imp` for impulsivity, top `ovc` for overconfidence, bottom `dis` for delayed correction) ÷ its rate in the safest quarter | ≥ 2 (a "lift" of at least ×2) |

A failure of S1–S13 means fixing the generator and rerunning. Record it in
`generator/TUNING_LOG.md`. Never look at model results while fixing checks.

**Fix rule (D-45):** a fix may only move a parameter **within its §16 tested range** (or
correct a coding bug). Every fix is logged with the check that failed, the parameter
changed, the old and new values, and the reason. Moving a parameter outside its tested
range, or changing a pass condition, is a **deviation** recorded in `DECISIONS.md`.
Where checks conflict, the real-world anchors (S1–S4, S10–S13) take priority over the
plausibility bands (S3, S6, S9).

**S14 is a decision rule, not a tuning target.** A failure does **not** lead to changes in
the generator (that would shape the data to suit the flags). Instead, the failing flag
**stays an ML feature** (O2 is unaffected) but is **not shown to users** as an
explanation in the app, and the result is reported in Ch.5. Hidden traits are used here
for auditing only, never as model inputs (CLAUDE.md rule 3).

## 15. Reproducibility

- Master seed `20261009`; the 20 robustness seeds come from
  `numpy.random.SeedSequence(20261009).spawn(20)`; use `numpy.random.default_rng`.
- All parameters in `generator/config.yaml`; `metadata.json` records the spec version,
  the spec's SHA-256 fingerprint, config hash, seed and noise level (no git; D-36).
- Command: `python -m generator.run --config generator/config.yaml --noise medium --seed 20261009`.

## 16. Assumptions register (each tested across a range)

| Parameter | Default | Range tested | Calibration ID |
|---|---|---|---|
| Wage spread σ_log | 0.35 | 0.25–0.60 (widened 2026-10-09, D-30) | C-02 |
| Employment mix | 70/15/15 | 65/30/5 (gig-heavy), 80/10/10 | C-22 |
| Gig median / CV | RM2,500 / 0.15–0.35 | ±20% / 0.10–0.45 | C-18 |
| Consumption ratio (of disposable income) | U(0.75, 1.00) | U(0.70, 0.95), U(0.80, 1.05) | C-23 |
| Job loss probability | 2.25% (≤ 30) / 1.1% (31–35) per month (D-47; ×0.75 of the frozen 3% / 1.5%, inside this range) | ×0.5–×1.5 of the frozen values | C-25 |
| Gig income spread σ_log | 0.70 | 0.50–0.90 | C-18 |
| Festive multiplier | ×1.2–1.4 | ×1.1–1.6 | C-19 |
| Shock scale `k` (life-event deck) | 1.0 | 0.5–1.7 (also the S9 tuning dial) | C-20 |
| Life-event frequencies (relative) | `life_events.md` | Not varied individually (stated limitation) | C-20 |
| Student semester multiplier | ×1.15 | ×1.05–1.30 | C-26 |
| Festive + semester stacking | Allowed | Not varied | C-19, C-26 |
| BNPL user share / purchase rate | 32% / 2.7 per month | 20–45% / 1.5–4 per month | C-12 |
| Personal loan holding / instalment | 0.07 / RM200–800 | 0.03–0.15 / ±30% | C-32 |
| Family support holding / amount | 0.17 / RM100–500 | 0.17–0.35 (Findex is a lower bound) / ±50% | C-33 |
| Living with parents | 0.6 (18–24) / 0.3 (25–35); housing × 0.4 | each ±0.2; housing × 0.2–0.6 | C-34 |
| Vehicle payments | RM150–400 / RM400–900 | ±30% | C-17 |
| Vehicle ownership (employees) | car 0.90 / motorbike 0.75 (household proxy) | both × 0.6 (individual ownership below household) | C-29 |
| Vehicle ownership (students) | car 0.32 / motorbike 0.13 | car 0.15–0.45 | C-29 |
| Vehicle loan given ownership | 0.5 | 0.3–0.7 | C-17 |
| Pay rise / gig slow-month probabilities | 1/12 / 8% per month | ×0.5–×2 | C-25 |
| Trait distributions and correlations | §3a | ρ ±0.2 | — |
| Insufficient-income threshold | RM300 | RM200–500 | — |
| Starting cushion mapping | Findex buckets (§8) | Every bucket shifted down one level (own cash only); top cap 4 or 9 months instead of 6 | C-21 |
| Credit card holding | 0.15 | 0.10–0.25 | C-27 |
| Credit limit | 2 × gross monthly income | 3 × for incomes above RM3,000/month (no BNM cap there) | C-28 |
| Budget rule | 0.95 × median of previous 3 months | 0.90–1.00 | — |
| Correction duration / size | 3 months / κ U(0.10, 0.25) | 1–3 months / κ U(0.05, 0.15) | — |
| Goal stickiness probability | `ovc` | 0.5 × `ovc`, 0 (off) | — |
| Starting card balance (non-payers) | U(10%, 60%) of limit | U(0%, 30%), U(30%, 90%) | C-30 |
| Vehicle loan tenure | motorbike 5 / car 9 years | car 7 years | C-31 |

Sensitivity results (one-at-a-time) are reported in Ch.5 if time allows (Should).

## 17. Open items (status at the v1.0 freeze)

- [x] Decisions A–D confirmed (Patrick, 2026-10-09)
- [x] Decisions E–G confirmed (Patrick, 2026-10-09): hysteresis edge case, spending shares and classification, life-event deck with `k`
- [x] σ_log test range widened to 0.25–0.60 (Decision H, 2026-10-09)
- [x] Starting cushion from Findex fin24b; credit card holding 0.15 (Decisions I, J, 2026-10-09)
- [x] Market-realism additions (2026-10-09, D-39): family support, personal loans, living with parents, BNPL from BNM data, limitations in §1
- [x] Structural gaps closed (2026-10-09): credit limit and eligibility (D-33), essential/discretionary split and S2 (D-34), vehicle ownership (D-35), ages 18–35 for workers (D-37), PTPTN/card/loan starting states (D-38)
- [x] Read-through of §11–14 with Patrick (2026-10-12): D-42 (label), D-43 (noise; checks judged at medium), D-44 (evaluation details), D-45 (fix rule)
- [x] S6 flag test and flag validity audit (2026-10-12, D-41): delayed correction redefined, §9 wording pinned down, trait footprints strengthened, S14 added as a decision rule. **This was the last prototype check (stopping rule); next step is the freeze**
- [x] Market-realism check with a prototype simulation (2026-10-12, D-40): spending from disposable income, consumption ratio calibrated to DOSM, students/under-21 vehicle loans, festive weights by religion, gig spread from DOSM, minimum-wage floor, age-based job loss, annual pay rise, checks S10 (reworded), S12, S13 added
- [x] Final consistency pass (2026-10-09): BNPL as a payment method (no double counting), monthly pay-in-full draw, gig income for card rules, S3 lower bound 5% (consistent with the §1 housing-loan limitation)
- [x] Freeze (2026-10-12): saved as v1.0, read-only copy in `docs/frozen/`, SHA-256 in `DECISIONS.md`; email to supervisor drafted for Patrick to send (D-36)

**Open after the freeze (not blocking; none of them is in the frozen §11–14):**
- Calibration rows still marked VERIFY (EPF, SOCSO/EIS, PTPTN, card rates, BNPL terms,
  festive weights, etc.): Patrick checks the primary sources before the report. A corrected
  value goes into `calibration_table.md` and `config.yaml` with a dated note, within the
  §16 tested range (D-45).
- Life-event deck edited by Patrick from real experience (T-04): same rule.
- Page numbers for the §11 label references: a clarification of justification text, not a
  change to the plan.
