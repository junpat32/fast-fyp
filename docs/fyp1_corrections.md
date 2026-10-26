# FYP1 → FYP2: corrections found so far (notes for Patrick)

**What this is:** a working list of places where the FYP1 report says something the finished design no
longer does, with the decision behind each change. It serves O6 ("all FYP1 inconsistencies fixed").
These are **notes, not report text**: the FYP2 report is Patrick's writing (CLAUDE.md §6).
Started 2026-10-18 from the FYP1 report's five validation scenarios (chapter 3, "Scenario-Based
Validation Method"); a full pass through FYP1 comes with the report kit. The FYP1 file itself is
never edited.

## From the five validation scenarios (D-103)

The scenarios now run as automated tests (`tests/test_scenarios.py`, `test_fyp1_scenario_1..5`), with
FYP1's inputs and the current design's expected outputs.

| # | FYP1 said | FAST now does | Why (decision) | Point to make in FYP2 |
|---|---|---|---|---|
| 1 | DSR uses **gross** monthly income (all five scenarios) | DSR uses **net** income | CLAUDE.md rule 6; BNM computes DSR on income after statutory deductions (verify against calibration source C-05 before citing) | State the definition once; note FYP1's scenarios were re-read as net income |
| 2 | S2: a Yellow user at DSR 40% gets an advisory about **elevated debt load** | No advice below 50% DSR; the Money screen's band card shows "debt payments take 40% of income" | SC2 (D-103): advice is kept for actions; the share is shown on the band card (D-95) | The information is there, as part of the band, not as advice |
| 3 | S3: **loss aversion** is a detected bias with its own prompt (FYP1's four biases: overconfidence, herding, loss aversion, impulsivity) | Three proxies are computed (impulsivity, overconfidence, delayed correction, the observable stand-in for loss aversion); **only impulsivity is shown**, because the others failed validation; herding is out of scope (Won't) | D-41 (check S14); CLAUDE.md §7 (herding: Won't) | Explain the validation step that removed two flags: a strength, not a gap |
| 4 | S3: in Red, **points accumulation is paused** | Points are **never** paused or taken away; the game rewards check-ins, honest records and a growing cushion | D-11 (never punitive), D-75/D-76 (the game design) | Punishing users in trouble discourages the honest logging the system depends on |
| 5 | S4: DSR **exactly 60% is Yellow** ("boundary inclusive of Yellow") | 60% exactly is **Red** (Red is 60% or more) | CLAUDE.md rule 5; the frozen generator spec (§6), which the O2 experiment used; SC1 (D-103) | The cautious reading of BNM's 60% line: warn at the line, not after it |
| 6 | S5: after Red, the band returns to Yellow in **month 3** (the first better month) | It returns in **month 4**: a better band shows only after holding 2 months; month 3 already says "Good progress…" | D-49 (stops the band flickering, proven on gig incomes in the scenario tests) | Show the trade-off: a month's delay against a band that doesn't flip back and forth |
| 7 | S5: a **"Recovery Champion" badge** after two good months following Red | No such badge (badges: cushion builder, steady saver, honest tracker); planned as T-24's "back on track" bonus (Should tier) | SC3 (D-103); D-75 deferred the game extras | Mention as planned or future work, depending on whether T-24 is built |

## Other FYP1 points to check (noticed in passing, not yet verified)

- FYP1 lists OCR receipt processing and notification parsing as implemented pipelines; in FYP2 they are
  Should-tier items (O5) whose status depends on the week-9 rule.
- FYP1's evaluation plan describes "scenario-based walkthroughs, observational studies"; FYP2 adds the
  pre-registered O2 experiment and the persona user study (O4).
