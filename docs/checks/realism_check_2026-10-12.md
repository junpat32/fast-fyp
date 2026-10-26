# Market-realism check of the generator spec (2026-10-12)

**What:** a throwaway prototype (`proto_sim_2026-10-12.py`, pure Python, 3,000 users,
seed 20261009) of `generator_spec.md` v0.4, run before and after the fixes in D-40.
It is **not** the generator (T-05): no transactions, no trait copula, no overconfidence flag.

**Why:** to test whether the synthetic population behaves like young Malaysians,
using real-world anchors, before the spec is frozen.

**Integrity note (pre-registration):** only data-level statistics were looked at.
No model was trained. The label positive rate was seen (as the §11 tuning rule allows),
but the consumption ratio was chosen to match **DOSM's spending ÷ income ratio**, not the
positive rate.

## Results

| Measure | Real-world anchor | v0.4 (before) | v0.5 (after D-40) |
|---|---|---|---|
| Workers' spending ÷ gross income | DOSM 2024: 60.8% (HES RM5,566 ÷ HIES RM9,155) | 69.5% | **61.8%** ✓ |
| Users who saved over the year | Findex 2025: 58.8% (25+) to 72.7% (15–24) | 40.4% ✗ | **59.4%** ✓ |
| Person-months with a cash shortfall | (no direct anchor) | 21.4% (implausibly high) | 6.6% |
| BNPL users | BNM ≈ 32% (C-12) | 32.9% | 31.9% ✓ |
| BNPL overdue: quarter-end / ever in 12 months | BNM Q4 2022: 17% of users | 23% / 43% | **7% / 27%** (17% lies between) ✓ |
| Median DSR of borrowers (month 12) | BNM 33% **incl. mortgages** | 26.5% | 22.4% (lower, as expected without mortgages) ✓ |
| Borrowers in Red (month 12) | BNM up to 25% | 15.2% | 7.0% (inside S3's 5–25%) ✓ |
| Insufficient-income person-months | S7 ≥ 1% | 1.2% | 2.8% ✓ |
| Employees earning < RM2,000 gross | DOSM all ages: 27.4% (young should be higher) | 32.6% | 32.1% ✓ |
| Label positive rate (medium noise) | S9 plausibility band 10–30% | 32.8% ✗ | 12.8% ✓ (seed 7: 14.0%) |
| Positive rate by type: employee / gig / student | Gig and students should be more fragile | 35 / 26 / 32% | 10 / 16 / 21% ✓ |

## What the fixes were (D-40)

1. Spending is taken from disposable income (after debt payments and family support),
   because DOSM consumption excludes loan repayments by definition.
2. The consumption ratio is recalibrated to U(0.75, 1.00) to match DOSM's 60.8%.
3. Students carry no vehicle loan of their own; under-21s rarely do (p = 0.1).
4. Festive months are weighted by Census 2020 religion shares instead of equally.
5. The gig income spread (σ_log 0.70) is fitted to DOSM's 2022 p-hailing income bands.
6. Employee pay is floored at the RM1,700 minimum wage (2025).
7. Job loss is calibrated to DOSM unemployment: 3%/month at ≤ 30, 1.5% at 31–35.
8. A pay rise happens about once a year (+3–7%), matching DOSM wage growth of 5.5%.
9. Check S10 is reworded (point-in-time vs cumulative), and S12 and S13 are added.

## Remaining known gaps

- Cushions polarise over the year (the middle buckets thin out). That's plausible but
  not validated: there's no Malaysian panel data on cushions.
- The prototype ignores the imp/dis correlation and transactions, so the real generator
  will differ slightly. The S-checks in spec §14 are the binding test.

Outputs: `proto_output_current.txt`, `proto_output_fixed.txt`.
