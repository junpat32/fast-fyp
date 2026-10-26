# FAST game design (T-07)

Version: **v1.0 APPROVED** (2026-10-13). Drafted by Claude; **Patrick approved G-01 to G-09**
with two fixes (protected cushion in §7a, "Not this week" on the card in §10) (D-56).
**v1.1** (2026-10-13): from Patrick's art review, the room is 7 × 7 and the garden fills the
screen, growing outward with each garden level (§7, §8; D-58). **v1.2** (2026-10-13): fixed
neighbours' houses behind and to both sides; one big flower bed instead of many small ones (§8;
D-59). **v1.3** (2026-10-13): one "qualifying months" counter (pause and resume, never reset);
the bed grows down the path monthly after G4 until complete; plant tiers by qualifying months;
dig and replant into a seed box (§4, §8, §13; D-61). Straight path, square bed 3 × 3 → 7 × 7,
complete at 14 months (§8; D-62). G1 keeps wild grass with a dug starter bed and herbs from the
unlock; the bed is a rectangle alongside the path, complete at 12 months (§8; D-63); the path loops round
the bed (§8; D-64); the fence stays at G4 (D-65); animated animals at 2/6/18 qualifying months,
chickens first (§8; D-66); chicken coop (D-67). **v1.4** (2026-10-14): the garden opens at a
1-month game cushion (room level 3) and qualifying months need a cushion of 1.0+; the bed grows
at every garden level, by time only, complete at 10 qualifying months (§7, §8, §13; D-68).
Choices: time decides what exists, points (1 choice per 200) decide how much and which:
decorations, plants in bed cells, extra animals (max 4 per type); no prices; free seedlings
(§4, §12, §13; D-69). **v1.5** (2026-10-14): room furniture merged from the batch-2 spec, with
interactive objects (budget board, coin jar, savings plant, the AI assistant as a crate shelf →
bookshelf); "concerned but hopeful" and drooping plants only in really bad months; the tree and
bed plants are bought with choices and grow on growing days; tap-to-plant and spot-picking for
decorations (§4, §7, §8, §9, §12, §13; D-72, D-73, D-74). Art spec: `docs/assets/FAST_ASSET_SPEC_BATCH2.md`.
**v1.6** (2026-10-14): the game-integrity package and reward order (D-75). No points per logged
entry; logging earns a **verified month** (the logs explain the money) and streak milestones;
check-ins earn the least, logging second, good finances the most (tested). Money sections (counted
vs other money, EPF), saving net of borrowing, bigger points for paying debt down to a new low.
Unverified progress waits for the next check-in; a protected cost floor until the user's logging
is trusted; borrowed cash never unlocks anything. The garden opens on the 3rd check-in for
everyone and grows with the user's **own goal** or a 1-month cushion; plants grow unless the month
is really bad, and rest after 2. Server time, edit locks and the check-in window are enforced in
the database (§1, §2, §3, §3a, §4, §5, §7, §7a, §8, §13). The game is replayed from the user's
facts on every request, never stored (§3a; D-76).
The points table (§3) is what the points simulation (T-14b) tests; §12 is the art list for T-22.

---

## 1. Fixed rules (already decided; the design must obey them)

| Rule | Source |
|---|---|
| Points come from **preparedness** (building a cushion), not activity volume | D-11 |
| **No points per logged entry**; logging is rewarded for being accurate, and honest overspend entries never cost anything | D-11, D-75 |
| **Reward order:** a check-in earns the least, logging second, good financial health the most | D-75 (tested) |
| Logging streak and budget streak are separate | D-11 |
| No reward for entering Red; no pausing of points in Red; **no negative points ever** | D-11 |
| The Future Self is **never shown suffering** | D-12 |
| Non-competitive: no leaderboards, no loot boxes, **no random rewards** | CLAUDE.md §7 (Won't) |
| An honest user always earns ≥ a gaming user (tested in T-14b) | T-14b |
| Bands improve only after 2 months (D-49); only validated flags are shown (D-41) | D-49, D-41 |
| Morning / afternoon / night by palette (D-52); garden progression is Must (D-53) | D-52, D-53 |

**The key insight:** in FYP1, a user who *hid* spending earned 150 points vs 45 for an honest
user. Any reward based on **logged spending** (e.g. "stayed within budget") can be gamed by not
logging. So in this design, points come only from things hiding spending cannot improve:
saving measured from the **money the user reports** at the check-in, debt paid down, bills paid
on time, keeping a cushion, and logs that **match** the money (padding or hiding entries breaks
the match). Nothing is paid per entry (D-75).

---

## 2. Core loop

| Rhythm | What the user does | What they get |
|---|---|---|
| **Daily** (~1 min) | Log transactions, or tap "No spending today" | Logging streak (milestone points at 7 / 30 / 100 days); accurate logs make the month **verified** |
| **Weekly** (~1 min) | Answer the life-event card ("Could you cover a RM600 motorbike repair?") | Fixed card points; a nudge toward the cushion |
| **Monthly** (~3 min) | Check-in: update the money sections (cash/bank/e-wallets, EPF Fleksibel, emergency savings, other savings) and what is owed, confirm bills paid | Band, health score, forecast; verified, saving, debt, bills and cushion points; milestones; room/garden level check |

---

## 3. Points table `[G-01]`

v1.6 (D-75). Three tiers, in a fixed order: **a check-in earns the least, logging second, good
financial health the most.** `tests/test_game.py` fails if the numbers in `shared/game.json` break
the order.

| Tier | Action | Points | Limit | Why |
|---|---|---|---|---|
| **Check-in** (least) | Sign-up (the first check-in) | +20 and **1 free choice** | once | Something to choose on day one |
| | Monthly check-in | +20 | once per month | Keeps the data current |
| Learning | Life-event card answered | +5 | once per week | Fixed amount: the event is random, the reward is not |
| **Logging** (second) | **Verified month**: the logs explain the change in money (§3a) | +40 | once per month | Rewards accurate logging, not volume |
| | Logging streak of 7 / 30 / 100 days | +20 / +40 / +60 | once each | The habit, early on |
| | Each logged entry, overspends included | 0 | | Padding can't pay; honesty never costs (D-11) |
| **Good finances** (most) | All bills paid on time | +30 | once per month | The "bills on time" indicator (D-48) |
| | Saved **≥ 5% / ≥ 10%** of income | +60 / +120 | once per month | % of income keeps it fair across incomes |
| | **Debt paid down to a new low**, ≥ 5% / ≥ 10% of income | +80 / +160 | once per month | Paying debt off counts more than saving |
| | **Cushion kept**: 1+ / 3+ months | +40 / +80 | once per month | Keeping a buffer you built is good health too |
| | Cushion milestone: 0.5 / 1 / 2 / 3 months (**game cushion**, §7a) | +50 / +100 / +150 / +200 | once each, ever | Celebrates reaching each target |
| | Entering or leaving any band | 0 | | No reward for Red, no penalty (D-11) |

**Most a month can give:** check-in 20 · cards 25 · logging 40 (plus streak one-offs) · good
finances **390** (plus milestones). An employee on RM3,000 who saves about 8% and pays PTPTN earns
over 2 years about 500 from check-ins, 520 from cards, 1,080 from logging and **5,800 from good
finances** (`sim/results/points_sim.md`).

**Definitions** (all from the monthly check-in, never from logged spending, so hiding a purchase
can't help):
- **change in money** = change in counted + other money (§7a) + voluntary EPF (the 90% that goes
  outside Fleksibel) − compulsory EPF paid into Fleksibel. Moving money between the user's own
  pockets changes nothing.
- **saving** = change in money − **new borrowing** (any rise in debt; in a month when debt rose,
  logged debt payments count as re-borrowed). Borrowing is never saving (C2).
- **debt points** go to a **new low** in total debt only (borrow-and-repay earns nothing), and only
  as far as debt payments were **logged in a verified month** (R5), so a made-up debt can't be
  "paid down" for points.
- In a month that isn't verified, **saving points and a goal-met garden month wait for the next
  check-in** and count if the money is still there (a one-month spike earns nothing).

**Known limitation (stated in the report): lies told every month.** Verification checks how money
*changes*, so it can't catch:
- a **small lie** each month within the verification tolerance (§3a): about +380 saving points over
  2 years in the simulation; a tighter tolerance only shrinks it and flags more honest users;
- a **constant lie about how much there is** (e.g. RM1,000 more than the user has, every month):
  verified from month 2, about +120 points and room levels about 2 months early; made at sign-up too,
  it is never caught (D-77);
- **hiding income**: leaving equal amounts of salary and spending out of the logs and confirming a
  lower income stays verified, and the same saving and debt payments become bigger shares of
  income, so both tiers go up: about +2,580 points over 2 years (+33%); levels are not affected,
  and a lower income also makes the user's own risk band look worse. A mitigation is waiting for
  Patrick's decision (DECISIONS, pending I).

Only outside evidence can: balances in pasted bank notifications (the parser, a Should) or bank
integration (a Won't). Because FAST has no leaderboards, such a user only fools themselves.

### 3a. Verified months and time rules (D-75)

**Verified month (option 2):** at the check-in the app compares the change in money with
**logged money in − logged money out** for that month. The month is **Verified ✓** when something
was logged, the logged money in covers the month's income, and the two agree within **RM100 or
10% of income**, whichever is bigger. "Logged out" is money that left the user's pockets:
spending paid now and debt payments. Purchases on credit or BNPL count when they are paid; moving
money between one's own pockets (including EPF top-ups) is neither in nor out; a loan payment
taken from salary is logged as part of the salary in and as a payment out. An unverified month
is never a penalty: the app asks kindly ("Did you pay for something in cash you didn't log?"),
and the month's progress simply waits for the next check-in.

**Time (C3, the Instagram pattern), enforced in the database (C4):**
- The **server's clock** decides when something arrived. A purchase can have any date, but what
  it earns goes by when it arrived. Entries and "No spending today" taps saved offline count, on
  the day the phone saved them, if they reach the server within 24 hours.
- Points a check-in earned are shown as **pending** while it can still be edited (48 hours,
  `shared/game.json` `edit_window_hours`), so a correction never looks like points going down.
- A month's logged money is summed by the server, at the check-in, from that month's entries that
  had **arrived by then** (an edit within 48 hours sums again), and kept on the check-in, so adding
  old entries later can't change a past month (D-76).
- A check-in is only for a month **since sign-up**, made **from its last day until 7 days after
  it**; one per month (D-77). The user gives today's balances and what they owe; the server takes
  off what was logged after the month ended, so the game uses money and debt **as at the end of the
  month**, the same period as the month's entries, whatever day the check-in is made. (Without it, a
  salary paid on the 1st would land in the wrong month for someone checking in on the 5th.)
- Check-ins and entries can be **edited for 48 hours**, then they lock. Check-ins are **never
  deleted**; entries can be deleted within the 48 hours. Sign-up numbers (income, starting money
  and debt, goal) lock after 48 hours; a new goal applies from the next month.
- Points are **never stored** (D-76): the server replays the user's facts (sign-up, check-ins,
  logging days, cards, goal changes, game actions) on every request, so nothing can be forged and
  a month's points are final once its 48-hour edit window closes. The replay **skips invalid
  rows** (and lists them) instead of failing, so one bad row can never break a user's game. The
  game keeps its own copy of the sign-up situation, so a later change (a student starts work)
  can't lower past levels.

---

## 4. What points are for `[G-02]`

| Option | Verdict |
|---|---|
| A. Score only | Points feel meaningless |
| B. A shop where points are spent | ❌ Recreates a spending loop in an app about spending less |
| **C. Every 200 points unlocks a decoration choice** (pick 1 of 2–3: curtain colour, wall art, desk plant…). Cosmetic only, never lost | **Recommended:** a sense of progress and personal choice, no spending mechanic, nothing random |

Room and garden **levels** are not bought with points; they follow the cushion (§7, §8), so the
home reflects real preparedness.

**Choices (D-61, D-69): time decides what exists; points decide how much and which.**

| Earned by | Unlocks |
|---|---|
| **Time** (qualifying months, §8) | Garden levels, bed size, **which plants exist** (tiers 1–4), **which animals exist** (slots at 2, 6, 18 months) |
| **Points**: every 200 points = **1 choice** | One of: a **room decoration**; a **chosen plant in a bed cell**; **one more animal** of a type the user already has (e.g. a second chicken) |

Rules:
1. **Every unlock costs exactly 1 choice; nothing has a price.** Points never go down and choices
   never expire (they bank up). This is not a shop: there is no saving up for an expensive item,
   the consumer habit FAST exists to counter.
2. **Rarity comes only from time**: a rare plant means "kept my buffer for 2 years", never
   "collected points".
3. **At most 4 animals per type** (screen clutter, older phones).
4. **The bed never looks empty**: new bed cells sprout free seedlings; a choice replaces a seedling
   with the plant the user picks. When the bed is full, a choice swaps a plant: the dug-up plant
   goes to a **seed box** and can be replanted later, so nothing is ever lost.
5. **The tree and bed plants are bought with choices** (D-74); each grows **seedling → young →
   full** on **growing days** (a day counts when the latest monthly result is not **really bad**,
   D-75; was "not Red"): 7, then 14
   growing days (~3 weeks); the tree's 7 stages take ~14 growing days each. **Planting:** tap a bed
   cell, pick a plant, it is planted. **Decorations:** the garden highlights 2–3 suitable free spots
   and the user taps one; it can be moved later the same way.
6. A typical honest month earns about 170–300 points (§3), so about 1 choice a month, plus the
   welcome choice on day one. Before the garden opens (the first 2 check-ins) choices go to room
   decorations; the room has about 11 options (colour variants of curtains, rugs, wall art, desk
   plants), and after the garden opens the bed's 30 cells and extra animals absorb the rest.

---

## 5. Streaks `[G-03]`

| Streak | Counts | Rewards | Breaking it |
|---|---|---|---|
| **Logging streak** | Days with an entry or a "No spending today" tap | +20 / +40 / +60 at 7 / 30 / 100 days, once each; badge at 30 days (§6) | Counter resets; **1 free rest day per week** doesn't break it; no point loss; gentle message |
| **Budget streak** | Weeks within the user's weekly budget | **None** (shown for awareness only) | Counter resets; no point loss |

The budget streak earns nothing on purpose: anything rewarded for "staying within budget"
invites hiding spending.

---

## 6. Badges (choose 3) `[G-04]`

| Badge | Earned when | Gaming-proof? | Recommended |
|---|---|---|---|
| **Cushion Builder** | Cushion reaches 1 month | ✅ balance-based | ✅ |
| **Steady Saver** | Saved ≥ 5% of income 3 months in a row | ✅ balance-based | ✅ |
| **Honest Tracker** | 30-day logging streak | ✅ a streak, not entry counts; overspends count | ✅ |
| Storm Ready | 4 life-event cards answered | ✅ but weak (just clicking) | |
| Debt Lighter | Band improves (Red→Yellow or Yellow→Green), held 2 months | ⚠️ depends on logged debts | |
| Bills Champ | 3 months of bills on time | ✅ | |

---

## 7. Room levels (follow the cushion) `[G-05]`

**Levels never go down**: unlocked furniture stays (non-punitive, D-11/D-12); the current
situation shows through the character's mood (§9) and the dashboard.

### 7a. The game cushion (protected against hiding spending)

All game rewards (room levels, milestones, cushion kept, the cushion route into the garden,
Cushion Builder) use the **game cushion** (v1.6, D-75):

```
counted money  = cash + bank + e-wallets + EPF Fleksibel + savings marked for emergencies (C6)
other money    = savings and investments not marked for emergencies (e.g. ASB): saving only
                 (EPF Persaraan and Sejahtera are shown, never counted)
game cushion (months) = counted money ÷ protected monthly costs

protected monthly costs:
  logging trusted (2 of the last 3 months verified):
      max( logged essentials + debt payments, average of the last 3 VERIFIED months,
           typical monthly costs declared at sign-up (60% of net income if "not sure") )
  otherwise:
      max( the above,
           the plausibility floor for the user's situation (option 1),
           what the balances show was spent: income − saving, 3-month average (S1) )

cushion for unlocks = (counted money − borrowed cash still held) ÷ protected monthly costs   (S2)
confirmed cushion   = cushion for unlocks in a verified month,
                      else the lower of it and the last check-in's (C1)
```

Room levels, milestones, cushion-kept points and the garden's cushion route use the **confirmed**
cushion, so one unexplained spike unlocks nothing; it unlocks at the next check-in if the money is
still there. The coin jar shows the plain game cushion.

**Plausibility floor (option 1):** the monthly essentials + debt payments that only the lowest
10% spend less than, in the DOSM-calibrated synthetic population (2,000 users; ~70% confident
they are realistic, since DOSM publishes household averages, not individual minimums):

| Situation | Floor (P10) | Typical (median) |
|---|---|---|
| Employee, own place / with parents | RM910 / RM630 | RM1,480 / RM1,120 |
| Gig worker, own place / with parents | RM590 / RM480 | RM1,380 / RM1,130 |
| Student, own place / with parents | RM310 / RM220 | RM450 / RM380 |

If a user declares less, the app asks gently ("Most people in your situation spend at least
RM910 a month on essentials and loan payments. Is RM600 right?") and the game uses the floor until
their own logging is trusted.

Why: logged costs shrink if a user stops logging, which would inflate the cushion and level them
up faster: the FYP1 flaw through a side door. Until logging is verified, the costs can't fall below
what the balances show was spent, so **hiding costs makes the cushion smaller, not bigger**; once
verified, a genuinely frugal user's own costs count. Borrowed cash is real money but owed, so it
never unlocks anything; it stops counting as borrowed as debt is paid down. The dashboard and
forecast keep using the normal cushion from logged data (engine/state.py); only the game uses this
version.

| Level | Unlocks at | What appears |
|---|---|---|
| 1 Starter | Start | Mattress on the floor, folding table, worn wood floor, bare window, kitchen counter with sink, shoe rack by the door; **interactive:** crate shelf (opens the AI assistant), budget board, coin jar, savings plant (D-72) |
| 2 Settling in | 0.5 month | Single bed with simple bedding, desk, office chair, desk lamp |
| 3 Home | 1 month | Wardrobe, rug, wall shelf, potted plant, light wood floor |
| 4 Comfortable | 2 months | Two-seat sofa, coffee table, **bookshelf** (the crate shelf grows into it; still opens the assistant), compact fridge, stove, curtains |
| 5 Cosy | 3 months | Wall art, floor lamp, big plant, window view |

**Interactive objects** (D-72): tapping one opens its screen. Budget board → budgets; coin jar →
savings (5 fills: current game cushion 0 / 0.5 / 1 / 2 / 3+ months); savings plant → savings
history (grows with the total months saved ≥ 5%: 1, 2, 3, 6; never shrinks; droops in really bad
months); crate shelf, later bookshelf → the AI assistant. **Decoration choices** (§4): dining table
and chair, storage cabinet, and about 11 colour variants of curtains, rugs, wall art, desk plants
and bedding. Dropped for now: receipt scanner, risk warning lamp (`docs/assets/DROPPED_ITEMS.md`).

Room: **7 × 7 tiles** (D-58, was about 5 × 5) with a kitchenette corner (kitchen tile floor),
back walls with windows and one door, and front walls cut away to a low stub so the room stays
visible. The **garden door** is a gap in the front stub that opens with the garden (the 3rd
check-in, D-75).

---

## 8. Garden levels (follow sustained preparedness) `[G-06]`

**Opens on the 3rd monthly check-in, for everyone** (D-75; was a 1-month cushion, D-68, which
tied the garden to income and costs). The garden is **personal**: different people have different
standards of financial health (Patrick, P2). Everything in the garden follows **one counter:
qualifying months** (D-61). After the garden opens, a monthly check-in qualifies when the user
**met their own monthly goal** (money set aside + debt paid down, as far as logged) **or** holds a
**confirmed cushion of 1 month or more** (§7a). An unverified goal-met month waits for the next
check-in and counts if the money is still there. A month without a check-in does not count, so an
old balance can't be reused. The counter is a **running total that pauses and resumes**: a month
that misses pauses it, it never resets, and nothing already unlocked is lost. Using the safety net
in an emergency must not wipe out years of progress (D-11/D-12). The room keeps the
same-for-everyone targets (0.5 to 3 months: levels 2–5 and milestones). The real app runs on real
months; the user study uses time-travel.

**Own goals** (set at sign-up, changeable from the next month):

| User | Goal | Suggested |
|---|---|---|
| Employee | An amount a month | 10% of income |
| Gig worker | A **share of that month's income** (income varies) | 5% |
| Student | An amount a month | RM30 |
| Everyone | At least **2% of income or RM10, whichever is higher** | |

**Really bad months** (D-73, C5): plants stop growing and droop only when the month is really bad
(Red band AND ran short or forecast risk ≥ 2× the usual), not for Red alone, so someone in Red who
is paying loans down still sees their garden grow. **After 2 really bad months in a row** the
plants **rest calmly** instead of drooping, and the app suggests **AKPK** (BNM's free debt
counselling agency) (I3).

The house stands in a **neighbourhood** (D-59): five neighbours' terrace houses behind it and to
both sides, each painted a muted colour (peach, sage, pale blue; D-60), with paved porches, a
washing line, air-con units and a motorbike, and lit windows at night. Neighbours are **fixed
scenery**: they have no gardens and nothing about them ever changes with anyone's progress, so
there is nothing to compare yourself with.

**View** (D-60): the home screen opens fitted to the screen width at 2×; pinch to zoom to 3× and
drag to look around.

The garden **fills the screen below the house** (D-58). Before the unlock the house stands in
untended wild ground. Each garden level tends a **bigger plot** (from 1 cell behind the house
forward), behind a fence that moves outward; at G4 the fence's front corner sits just above the
app's bottom bar (D-65).
A **straight path** runs from the garden door (on screen it heads down-left, out to the street).
**One rectangular flower bed** lies **alongside the path**, so the path leads to the plants and the
character can walk to them (D-63); the **path loops all the way round the bed**, so every plant can
be reached, and the loop moves outward as the bed grows (D-64). At the unlock the yard is claimed, not dug up: the wild grass
stays inside the new fence, and a small **starter bed** is freshly dug beside the path and planted
with herb seedlings. The bed grows with **time, never with points** (D-68): bigger at **every
garden level**, then **one row per qualifying month** after G4, alternately along the path and
across it, until **bed complete**. The size of the garden shows how long the buffer has been kept.

| Qualifying months | Level | Plot grows | What appears | Bed (across × along the path) | Plant tier available (§4) |
|---|---|---|---|---|---|
| 0 (opens) | G1 | 4 cells | Wild grass inside a simple wooden fence, stepping-stone path | 2 × 2, freshly dug, herb seedlings | **1: herbs** (serai, pandan, chilli) |
| 2 | G2 | 6 cells | Mown lawn (basic grass), planter beds (soil); first animal slot | 2 × 3, improved soil | — |
| 4 | G3 | 9 cells | Healthy grass, paved path, stone edging round the bed, small plants in planters | 3 × 3 | **2: flowering** (bunga raya, bougainvillea) |
| 6 | G4 | 14 cells (fence near the bottom of the screen) | Lush grass, nice paved path, small tree, bench; second animal slot | 3 × 4 | — |
| 7–9 | G4 | — | The bed grows one row a month | 3 × 5, 4 × 5, 4 × 6 | — |
| 10 | G4 | — | **Bed complete** | **5 × 6** | — |
| 12 | G4 | — | | | **3: prized** (orchids, frangipani tree) |
| 18 | G4 | — | Third animal slot | | — |
| 24 | G4 | — | Dig up and swap for rarer plants; it never ends | — | **4: rare** |

Example (D-75): a user taking home RM3,000 with RM2,400 typical costs, saving RM300 a month
(their 10% goal) from zero: the garden opens at the 3rd check-in (month 3); G2 at month 5, G4 at
month 9; bed complete at month 13; prized plants at month 15; rare plants at month 27. Their room
reaches level 3 (a 1-month cushion) at month 8.

**Animals (D-66):** animated animals live in the garden and walk the lawn and paths. An **animal
slot** opens at **2, 6 and 18 qualifying months** and the user **chooses** which animal (first set:
**chickens, ayam kampung**; dogs only ever optional). Animals never get hungry, sick or sad and
never leave, whatever happens to the user's money. They are drawn at about 1.5× real size so
they read on a phone, wander and peck by day, and **sleep at night** (§11). Choosing chickens
adds a **reban ayam** (chicken coop) beside the house; the chickens sleep in front of it (D-67).

**Plants and decorations** (D-74): new bed cells sprout free seedlings; the user **taps a bed
cell, picks a plant** (from the unlocked tiers, paid with a choice) and it is planted, then grows
seedling → young → full on growing days (§4). The **tree** (7 stages) is also bought with a choice.
Decorations go on spots the user picks from 2–3 highlighted ones. Tier plants: herbs (serai, pandan,
chilli); flowering (bunga raya, bougainvillea, ixora); prized (orchids, frangipani); rare (torch
ginger, jade vine on the garden arch). In **really bad months** plants droop visibly but never die,
disappear or drop a stage (§9, D-73).

The bed **fills itself** with free seedlings as it grows (Must); the user's choices replace them.
The same tap screen handles **digging up and swapping** (the dug-up plant goes to the seed box), so
it is part of the core app (T-16; T-23 folded in, D-74). The data (which plant is in which bed
cell, its growth stage, and the seed box) comes from T-14b.

The user study uses personas with 6-month histories and **time-travel** (Must), so
participants can see the room and garden progress without waiting months.

---

## 9. Future Self `[G-07]`

| Part | Design |
|---|---|
| **You now** | The character in the current room. Mood from the health tier: Healthy → relaxed and smiling; Coping → calm; Vulnerable → **focused and determined** (never sad, D-12). **Only in a really bad month** (Red band AND ran short of money or forecast risk ≥ 2× the usual): **concerned but hopeful, with one next step on screen** (D-73) |
| **You in 6 months** | The same character in the room level the **median Monte Carlo path** (T-15) reaches, plus an illustrative range: "if recent habits continue, between X and Y months of savings" (P10–P90). The synthetic terminal range covered 73.25% on a fresh 400-user audit (D-81); never label it a validated 80% prediction interval or claim real-world coverage. |
| Comparison screen | Side by side, "You now" and "You in 6 months". *Optional (Should):* a slider, "What if I save RM100 more a month?" |
| Horizons, labelled on screen | The forecast answers "a tight month in the **next 3 months**?"; the Future Self answers "where are my habits taking me in **6 months**?" Both screens state their horizon |

---

## 10. Life-event card `[G-08]`

| Step | Design |
|---|---|
| 1. Draw | Once a week, from the shock-size events in `docs/life_events.md`, weighted by the user's profile (vehicle, student, gig) and each event's frequency |
| 2. Show | "Your phone screen cracked. Repairs usually cost RM150–800." |
| 3. Check | Against the user's cushion: **Covered** / **Partly covered** / **Not covered yet**, with no alarming language |
| 4. Choose | "I'd use my savings" · "I'd cut spending next month" · "Set a small savings goal for this" (pre-fills a goal). No wrong answer |
| 5. Reward | +10 points, fixed. The card is **hypothetical**: it never changes the real balance |
| Skip | **"Not this week"**: no points, no penalty, the card returns next week (for users in a hard month) |

---

## 11. Time of day `[G-09]`

By the phone's clock: **morning** 06:00–11:59, **afternoon** 12:00–18:59, **night**
19:00–05:59 (D-52). At night, unlocked lamps glow, windows are lit and animals sleep (D-66).
Visual only; no gameplay effect.

---

## 12. Art list implied by this design (for T-22, D-55)

| Group | Pieces |
|---|---|
| Structural/terrain kit | **41, built** (floors, back walls, cut-away front walls + garden door, trims, wild ground + garden ground, 3 paths, borders, planters, fences; D-58) |
| Neighbourhood | **6, built**: 3 terrace houses, washing line, air-con unit, motorbike (D-59) |
| **Batch 2 spec** | `docs/assets/FAST_ASSET_SPEC_BATCH2.md` (binding; D-72) |
| Room furniture (levels 1–5) + interactive objects | About 30 pieces (§7), plus about 11 colour variants as decoration choices; budget board, coin jar (5 fills), savings plant (stages + droop), crate shelf → bookshelf |
| Garden | Bed plants: 10 varieties × 3 stages × normal/droop, seedlings; tree in 7 stages; shrubs and garden plants (~6); decorations (~13) |
| Characters | **6 chibi avatars** (56 px) built from shared parts, **6 skin tones**, glasses; idle, 4-frame walk, moods (incl. concerned but hopeful, celebrating), sitting, using phone: **~20 frames each** |
| Animals (D-66) | Chickens at 1.5× real size: walk 4, peck 4, idle 2, sleep 8 per view (test built); more animals later (Could) |
| Animal homes (D-67) | Chicken coop, **built** |
| **Total** | **About 160 pieces plus ~120 character frames** (48 built), each × 3 times of day |

---

## 13. What the points simulation (T-14b) must show

v1.6 (D-75, D-77): one synthetic employee's true life (`sim/points_sim.py`), reported 17 ways over
24 months; results in `sim/results/points_sim.md`, checked by `tests/test_points_sim.py`.

| Simulated user | Behaviour | Required | Result |
|---|---|---|---|
| Honest | Logs everything, including overspends | Baseline | 24/24 months verified |
| Forgetful (honest) | Forgets 8% of spending | Still verified (few false alarms) | 24/24 verified |
| **Padder** | 40 entries a day, made-up amounts | Honest ≥ padder, every month | Never verified; far behind |
| **Hider** | Hides impulse purchases | Honest ≥ hider | Ties (hiding changes nothing) |
| **Cost-hider** | Declares low costs, never logs essentials | No level, garden month or milestone earlier (§7a) | Never earlier; behind on points |
| **Borrower** | Borrows RM2,000 before odd-month check-ins, repays after | No gain (C2, S2) | Behind |
| **Debt liar** | Declares a fake RM40,000 debt "falling" RM2,000 a month | No gain (R5) | Ties |
| Debt liar with fake payments | The same, with made-up payment entries | No gain | Never verified; far behind |
| **Spike liar** | Reports RM10,000 extra for one month | No unlock, no gain (C1) | Behind |
| Fleksibel mover | Moves EPF Fleksibel to the bank | No gain (C6) | Ties |
| **Backdater** | Skips 3 months, then tries late and pre-sign-up check-ins | Rejected (C3) | All 4 rejected |
| **Stale balance** | Stops checking in after month 8 | No progress from it (D-61) | No garden months after |
| Late checker (honest) | Checks in 5 days after each month ends | Earns exactly the same (D-77) | Identical every month |
| Section liar (known limit) | Hides RM300 a month moved out of ASB | Reported, bounded | About +380 points over 2 years |
| Balance liar (known limit) | Claims RM1,000 more, every month | Reported | Verified from month 2; +120 points; room level 3 two months early |
| Month shifter (known limit) | The same lie through fake entries dated after month end | No points gain | Never verified; −3,200 points; room level 3 two months early |
| Income hider (known limit) | Leaves RM1,100 of salary and of spending out, confirms RM1,900 income | Reported | Verified; +2,580 points (saving and debt tiers); levels unchanged |
| Reward order | Employee, student, gig worker, non-saver | Check-in < logging < good finances | Holds for all four |
| Garden fairness | Student and gig worker with their own goals | About as many garden months as an employee | Holds |
| Non-saver vs saver | Same logging, different saving | Saver earns clearly more | Holds |
| **Shock month** | Car repair, then a really bad Red month | Nothing unlocked is lost; counter pauses | Holds |
| **Really bad month** | Red band and ran short of money | Plants droop, stop growing, lose no stage; rest after 2 in a row (D-73, I3) | Unit-tested |

---

## 14. Decisions (approved by Patrick 2026-10-13, D-56)

| ID | Decision | Approved |
|---|---|---|
| G-01 | Points table | §3 as written |
| G-02 | What points are for | C: decoration choice every 200 points |
| G-03 | Streaks | Logging streak (1 rest day/week); budget streak, no rewards |
| G-04 | 3 badges | Cushion Builder, Steady Saver, Honest Tracker |
| G-05 | Room levels | §7 (5 levels by the **game cushion**, never downgrade) |
| G-06 | Garden levels | §8 (4 levels by months at 3+ game cushion) |
| G-07 | Future Self | §9 (moods never sad; 6-month median room; optional slider; horizons labelled) |
| G-08 | Life-event card | §10 (weekly, hypothetical, fixed +10, "Not this week" skip) |
| G-09 | Time of day | §11 |
