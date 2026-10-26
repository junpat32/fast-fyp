# Points simulation (T-14b, D-75 to D-77 rules)

One synthetic employee (RM3,000 take-home, about RM2,200 essentials + PTPTN, a RM12,000 PTPTN
loan, RM5,000 in ASB, saving about RM250 a month) reported to the app in 17 ways over 24 months. Every strategy lives the same true life; only what it tells the app differs. Snapshots are 7 days after each month end, when every check-in window has closed.

| Strategy | Points at 6 / 12 / 24 months | Check-in / learning / logging / health at 24 | Verified months | Room level 2 / 3 reached (month) | Garden months at 24 | Months ahead of honest | What stops it |
|---|---|---|---|---|---|---|---|
| honest | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | - |
| forgetful | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | tolerance: max(RM100, 10% of income) |
| late_checker | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | - (money and debt as at month end, D-77) |
| padder | 1165 / 2415 / 4500 | 500 / 520 / 120 / 3360 | 0 | 2 / 7 | 21 | 0 | no points per entry (P1); made-up spending breaks the match (R1) |
| hider | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | saving comes from balances, not logs (G4) |
| cost_hider | 1165 / 2415 / 4500 | 500 / 520 / 120 / 3360 | 0 | 1 / 7 | 21 | 0 | costs at least what the balances show was spent, until verified (S1) |
| borrower | 1805 / 3375 / 6940 | 500 / 520 / 1080 / 4840 | 24 | 1 / 4 | 21 | 0 | borrowing isn't saving (C2); borrowed cash unlocks nothing (S2) |
| debt_liar | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | debt points only as far as logged payments (R5) |
| debt_liar_logs | 1165 / 2415 / 4500 | 500 / 520 / 120 / 3360 | 0 | 2 / 7 | 21 | 0 | made-up payments break the match, so no debt points (R1, R5) |
| spike_liar | 1985 / 3555 / 7480 | 500 / 520 / 1000 / 5460 | 22 | 1 / 4 | 21 | 0 | unverified progress waits a month and the money was gone (C1, G6) |
| fleksibel_mover | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | counted money is one total (C6) |
| backdater | 1135 / 2885 / 6810 | 440 / 520 / 920 / 4930 | 20 | 1 / 8 | 18 | 0 | check-in window and sign-up date (C3) |
| stale | 2165 / 2955 / 3210 | 180 / 520 / 440 / 2070 | 8 | 1 / 4 | 5 | 0 | no check-in, no progress |
| section_liar | 1965 / 4065 / 8280 | 500 / 520 / 800 / 6460 | 17 | 1 / 3 | 21 | 16 | not stopped: a small lie inside the tolerance (known limit) |
| balance_liar | 2125 / 4085 / 8020 | 500 / 520 / 1040 / 5960 | 23 | 2 / 2 | 21 | 13 | not stopped: verification checks changes, not how much there is (known limit) |
| month_shifter | 1465 / 2615 / 4700 | 500 / 520 / 120 / 3560 | 0 | 2 / 2 | 21 | 0 | the fake entries break every month's match, so it loses points; levels early (known limit) |
| income_hider | 2165 / 3975 / 7900 | 500 / 520 / 1080 / 5800 | 24 | 1 / 4 | 21 | 0 | tiers use the larger of confirmed and declared income (I1, G13); a little gets through in a gig worker's above-average months (known limit) |

**Cheats:** the best any cheat does against honest in any month is +0 points (hider, debt_liar, fleksibel_mover only tie, because what they change doesn't matter to the rules); no cheat reaches a room level or a garden month earlier than honest (yes).
The backdater's 4 late or pre-sign-up check-ins were all rejected.

**Checking in late changes nothing** (D-77): the late checker earned exactly what honest earned in every month (yes).

**Known limit: a lie told every month.** Verification checks how money *changes*; it can't see a lie about how much there *is* while the lie stays the same:
- section_liar (a small lie inside the tolerance): +380 points over 24 months, saving points only (the money it moved to the bank is real, so its cushion is real).
- balance_liar (RM1,000 more than it has, every month): unverified only in month 1, then verified; +120 points, room level 3 in month 2 (honest: 4). Claiming the same extra at sign-up would cost it nothing at all.
- month_shifter (the same lie through made-up entries dated after month end): never verified, so -3200 points, but room level 3 in month 2.
- income_hider (leaves equal amounts of salary and spending out, confirms a lower income): 24 months verified; +0 points (it was +2,580 before I1, D-89: the same saving and debt payments were bigger shares of a smaller income). The tiers now use the larger of the confirmed income and the income declared at sign-up, so the lie no longer pays for a steady salary. A gig worker can still gain a little (+60 points over 24 months): in months above the declared average, hiding income lowers the tier's denominator to the declared level. Levels are never affected, and in the real app a lower income also raises the debt-service ratio and can worsen the band.
Only outside evidence can catch these: balances in pasted bank notifications (the parser, a Should) or bank integration (a Won't). With no leaderboards, such a user only fools themselves.

**False alarms:** the forgetful but honest user (8% of spending never logged) had 24 of 24 months verified.

**Tolerance trade-off** (what-if; shared/game.json keeps 10%). A tighter tolerance only shrinks the lie that gets through; it never removes it, and it flags more honest users:

| Tolerance (share of income) | section_liar vs honest at 24 | Forgets 8%: verified months | Forgets 12%: verified months |
|---|---|---|---|
| 10% | +380 | 24 / 24 | 11 / 24 |
| 7% | -820 | 23 / 24 | 0 / 24 |
| 5% | -940 | 0 / 24 | 0 / 24 |

## Reward order and fairness across people

| Person (honest) | Check-in / learning / logging / health points at 24 | Garden months at 24 | Room level at 24 |
|---|---|---|---|
| employee | 500 / 520 / 1080 / 5800 | 21 | 5 |
| student | 500 / 520 / 1080 / 4600 | 21 | 5 |
| gig | 500 / 520 / 1080 / 3320 | 21 | 5 |
| non_saver | 500 / 520 / 1080 / 2870 | 6 | 2 |

**Rough patch** (RM1,800 car repair in month 10, a really bad Red month in 14): points, room level and garden months never go down (yes); 20 garden months at 24 vs 21 without it.
