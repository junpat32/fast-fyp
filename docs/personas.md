# Study personas (T-18, D-90)

Four synthetic users from the O2 dataset (`data/synthetic/medium_seed20261009`), built by `tools/personas/build.py` into the app's own rows and loaded by `tools/personas/seed.py`. **Synthetic only** (rule 12); the names are for the study script and are never stored. **Proposed for Patrick's review.**

Timeline: January-December 2026. The study clock starts on **1 July 2026** (six months behind it) and time travel moves it a month at a time to 1 January 2027. Every number below is what the app shows at that study date (computed with the API's own functions).

## Aina (persona_01, synthetic user 357)

A 21-year-old student living with her parents. Little debt, a few Buy Now Pay Later plans, and money that often runs out before the allowance comes.

Sign-up: student, born 2005, lives with parents, vehicle: car, declared income RM860, typical costs RM480, debts: none. Login: `persona_01@personas.fast.test`.

| Study date | Band | DSR | Cushion (months) | Health | Forecast risk | Main reasons | Points | Room | Garden | Plants | Verified months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-01 | YELLOW | 0.30 | 0.0 | 37.4 (Vulnerable) | 68% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 575 | 2 | 1 | 3 | 3 of 6 |
| 2026-08-01 | YELLOW | 0.17 | 0.0 | 25.0 (Vulnerable) | 98% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 610 | 2 | 1 | 4 | 3 of 7 |
| 2026-09-01 | GREEN | 0.20 | 0.0 | 25.0 (Vulnerable) | 98% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 645 | 2 | 1 | 4 | 3 of 8 |
| 2026-10-01 | GREEN | 0.17 | 0.0 | 25.0 (Vulnerable) | 77% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 725 | 2 | 1 | 4 | 4 of 9 |
| 2026-11-01 | GREEN | 0.22 | 0.2 | 26.4 (Vulnerable) | 85% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 800 | 2 | 1 | 4 | 5 of 10 |
| 2026-12-01 | YELLOW | 0.35 | 0.4 | 57.0 (Coping) | 41% | ran out of cash recently (raises); months of expenses saved (cushion) (raises) | 880 | 2 | 1 | 4 | 6 of 11 |
| 2027-01-01 | YELLOW | 0.27 | 0.4 | 75.0 (Coping) | 41% | months of expenses saved (cushion) (raises); typical monthly income (last 3 months) (raises) | 960 | 2 | 2 | 5 | 7 of 12 |

## Jason (persona_02, synthetic user 887)

A 28-year-old e-hailing driver paying off the car he works with. His income changes a lot from month to month, and repairs come out of nowhere.

Sign-up: gig, born 1998, lives on their own, vehicle: car, declared income RM1,550, typical costs RM1,440, debts: Car loan. Login: `persona_02@personas.fast.test`.

| Study date | Band | DSR | Cushion (months) | Health | Forecast risk | Main reasons | Points | Room | Garden | Plants | Verified months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-01 | YELLOW | 0.19 | 1.4 | 61.4 (Coping) | 28% | unexpected costs (last 3 months) (raises); months of expenses saved (cushion) (raises) | 2275 | 4 | 2 | 4 | 6 of 6 |
| 2026-08-01 | GREEN | 0.19 | 0.4 | 53.3 (Coping) | 41% | months of expenses saved (cushion) (raises); unexpected costs (last 3 months) (raises) | 2540 | 4 | 2 | 5 | 7 of 7 |
| 2026-09-01 | YELLOW | 0.33 | 0.7 | 54.1 (Coping) | 26% | months of expenses saved (cushion) (raises); debt payments / income (DSR) (raises) | 2935 | 4 | 3 | 6 | 8 of 8 |
| 2026-10-01 | YELLOW | 0.29 | 0.8 | 56.9 (Coping) | 33% | months of expenses saved (cushion) (raises); debt payments / income (DSR) (raises) | 3260 | 4 | 3 | 7 | 9 of 9 |
| 2026-11-01 | YELLOW | 0.33 | 0.0 | 48.5 (Coping) | 26% | months of expenses saved (cushion) (raises); debt payments / income (DSR) (raises) | 3525 | 4 | 3 | 8 | 10 of 10 |
| 2026-12-01 | YELLOW | 0.26 | 0.8 | 60.5 (Coping) | 39% | months of expenses saved (cushion) (raises); debt payments / income (DSR) (raises) | 3910 | 4 | 4 | 9 | 11 of 11 |
| 2027-01-01 | YELLOW | 0.36 | 1.0 | 60.0 (Coping) | 19% | debt payments / income (DSR) (raises); months of expenses saved (cushion) (raises) | 4300 | 4 | 4 | 10 | 12 of 12 |

## Priya (persona_03, synthetic user 662)

A 25-year-old office worker with a car loan and a motorbike loan. Her debt payments take more than half of her pay.

Sign-up: employee, born 2001, lives with parents, vehicle: both, declared income RM1,900, typical costs RM1,460, debts: Car loan, Motorbike loan. Login: `persona_03@personas.fast.test`.

| Study date | Band | DSR | Cushion (months) | Health | Forecast risk | Main reasons | Points | Room | Garden | Plants | Verified months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-01 | RED | 0.59 | 1.0 | 44.1 (Coping) | 8% | how much non-essential spending jumped around (lowers); cash trend (last 3 months) (lowers) | 2210 | 3 | 2 | 4 | 6 of 6 |
| 2026-08-01 | RED | 0.61 | 1.4 | 63.5 (Coping) | 7% | months spending above 95% of your usual level (last 3) (lowers); cash trend (last 3 months) (lowers) | 2580 | 3 | 3 | 5 | 7 of 7 |
| 2026-09-01 | RED | 0.56 | 1.5 | 74.3 (Coping) | 4% | months spending above 95% of your usual level (last 3) (lowers); unexpected costs (last 3 months) (lowers) | 2895 | 3 | 3 | 6 | 8 of 8 |
| 2026-10-01 | RED | 0.53 | 1.8 | 78.0 (Coping) | 9% | share of spending on essentials (lowers); unexpected costs (last 3 months) (lowers) | 3320 | 3 | 4 | 7 | 9 of 9 |
| 2026-11-01 | YELLOW | 0.54 | 1.8 | 78.0 (Coping) | 14% | debt payments / income (DSR) (raises); months of expenses saved (cushion) (raises) | 3690 | 3 | 4 | 8 | 10 of 10 |
| 2026-12-01 | RED | 0.65 | 1.9 | 74.2 (Coping) | 7% | unexpected costs (last 3 months) (lowers); how much non-essential spending jumped around (lowers) | 4000 | 3 | 4 | 9 | 11 of 11 |
| 2027-01-01 | RED | 0.64 | 2.0 | 74.5 (Coping) | 7% | how much non-essential spending jumped around (lowers); unexpected costs (last 3 months) (lowers) | 4420 | 3 | 4 | 10 | 12 of 12 |

## Daniel (persona_04, synthetic user 905)

A 34-year-old employee with a motorbike loan, a credit card and BNPL plans. Things look fine, until the second half of the year.

Sign-up: employee, born 1992, lives on their own, vehicle: both, declared income RM2,030, typical costs RM1,290, debts: Motorbike loan, Credit card. Login: `persona_04@personas.fast.test`.

| Study date | Band | DSR | Cushion (months) | Health | Forecast risk | Main reasons | Points | Room | Garden | Plants | Verified months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-01 | YELLOW | 0.33 | 1.2 | 83.8 (Healthy) | 2% | months spending above 95% of your usual level (last 3) (lowers); unexpected costs (last 3 months) (lowers) | 2160 | 3 | 2 | 4 | 5 of 6 |
| 2026-08-01 | YELLOW | 0.40 | 1.1 | 69.8 (Coping) | 7% | total debt / yearly income (DTI) (lowers); cash trend (last 3 months) (lowers) | 2300 | 3 | 3 | 5 | 6 of 7 |
| 2026-09-01 | YELLOW | 0.39 | 1.2 | 68.4 (Coping) | 7% | total debt / yearly income (DTI) (lowers); how much income varied (lowers) | 2675 | 3 | 3 | 6 | 7 of 8 |
| 2026-10-01 | YELLOW | 0.39 | 1.3 | 66.5 (Coping) | 7% | months spending above 95% of your usual level (last 3) (lowers); total debt / yearly income (DTI) (lowers) | 3040 | 3 | 4 | 7 | 8 of 9 |
| 2026-11-01 | YELLOW | 0.39 | 0.0 | 45.6 (Coping) | 10% | months spending above 95% of your usual level (last 3) (lowers); total debt / yearly income (DTI) (lowers) | 3110 | 3 | 4 | 8 | 8 of 10 |
| 2026-12-01 | INSUFFICIENT_INCOME | 9.99 | 0.0 | 33.3 (Vulnerable) | - | - | 3180 | 3 | 4 | 9 | 8 of 11 |
| 2027-01-01 | INSUFFICIENT_INCOME | 9.99 | 0.0 | 25.0 (Vulnerable) | - | - | 3215 | 3 | 4 | 10 | 8 of 12 |

