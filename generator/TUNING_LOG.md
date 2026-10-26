# Tuning log (spec §11, §14; fix rule D-45)

Every change made to pass a sanity check is recorded here **before any model is trained**.
Only data-level results are looked at; never model results.

## 2026-10-12: first full run, generator v0 (spec v1.0, master seed 20261009)

**Medium noise (judged):** S1–S13 **all pass on the first run. No tuning was done.**

| Check | Result | Target |
|---|---|---|
| S1 employee net income by age band | max deviation 8.2% (18–19) | ±10% |
| S2 category shares vs HES 2024 | max −0.56 pts (eating out) | ±3 pts |
| S3 borrowers in Red, month 12 | 7.0% | 5–25% |
| S4 starting cushion buckets | 13 / 28 / 20 / 39% | ±5 pts of 13/29/18/40 |
| S5 DSR vs DTI | r = 0.804 | < 0.99 |
| S6 flag firing rates | impulsivity 6.7%, overconfidence 9.8%, delayed correction 8.0% | 5–30% |
| S7 edge cases | insufficient income 3.0%; 33 job losses per 100 employees | ≥ 1%; ≥ 1 per 100 |
| S8 data hygiene | all true | all true |
| S9 positive rate | 13.8% (6,520 rows; 480 excluded) | 10–30% |
| S10 BNPL overdue bracket | quarter-end 6.9%, ever 27.2% | 17% inside |
| S11 BNPL users | 33.1% | 32% ± 5 |
| S12 workers' spending ÷ gross income | 61.1% | 55–68% |
| S13 saved over the year | 60.3% | 50–75% |

**S14 (decision rule, not tuned):** impulsivity ×17.0 passes; overconfidence ×1.8 and
delayed correction ×1.7 are below ×2. **Outcome as pre-registered:** both stay ML features
in O2 but are **not shown to users** as explanations in the app. The generator is not changed
because of S14.

**Low and high noise (information only, D-43):**
- Low: S6 fails (impulsivity 0.2%: calm data has little erratic spending) and S9 = 9.8%.
- High: S1–S13 all pass; S14 impulsivity ×4.9, overconfidence ×1.7, delayed correction ×1.6.

**Noted (later changed, see the next entry):** S7 shows about 33 job losses per 100 employees per year. That
follows from calibrating job loss to DOSM youth unemployment with short spells (1–3 months).
Longer spells with a lower monthly rate would give the same unemployment with fewer people
affected. Spell length is an assumption in spec §4; any change needs Patrick's decision and a
dated note (non-frozen section).

## 2026-10-12: job-loss spells from DOSM data (D-47), before any model was trained

**Why:** realism, not a failing check. The first run had ≈ 33 job-loss episodes per 100
employees per year, because every spell was capped at 3 months. DOSM LFS 2025: 63.7% of
the actively unemployed are out of work < 3 months and 5.6% > 12 months.

**Change** (spec §4, not frozen; inside the §16 tested range):

| Parameter | Old | New |
|---|---|---|
| Job loss, age ≤ 30 | 3.0%/month | 2.25%/month |
| Job loss, age 31–35 | 1.5%/month | 1.1%/month |
| Spell length | 1–3 months | 1–2 (64%), 3–6 (30%), 7–12 (6%) months |

The values come from DOSM (steady-state unemployment 6.1% / 3.0%), not from the label rate.

**Medium noise after the change:** S1–S13 all pass. Changes: S7 24.8 episodes per 100
employees (23.5% of employees affected); S9 12.0% (was 13.8%; 354 rows excluded, was 480);
S13 62.6%. **S14:** impulsivity ×16.5; overconfidence **×1.97**; delayed correction ×1.71.
Overconfidence misses ×2 by 0.03, and **the rule is applied as written**: it stays an ML
feature only and is not shown to users. Nothing was adjusted to push it over the line.

**Low / high (information only):** low S6 and S9 fail as before (impulsivity 0.2%, positive
rate 9.0%); high S1–S13 pass.
