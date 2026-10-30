# Advice and explanation wording: review (T-11, D-92)

**Status:** draft by Claude, 2026-10-16, **for Patrick to approve or edit.** The texts live in
`engine/advice.yaml` (advice) and `engine/reasons.yaml` (forecast reasons): edit them directly, or
tell Claude what to change. `pytest tests/test_advice.py` checks that every text still fills in and
that no threshold is typed into a text.

## 1. What changed in the mechanism

| Change | Why |
|---|---|
| Band limits, goals, the income floor and the 3-month window are **placeholders** filled from `shared/thresholds.json` (`{red_pct}`, `{leave_red_pct}`, `{first_goal}`, `{min_income}`, `{window}`...) | Rule 5: one source of truth. Before, "60%", "RM300", "1 month" were typed into the texts and would silently disagree if a threshold changed |
| **R03 has three texts**, picked by the engine: at or above the Red line; below it but held Red by hysteresis (D-05); out of Red this month but waiting for the 2-month confirmation (D-49) | Priya (persona 3) is shown Red at **59%** and was told "Red is 60% or more": a contradiction a participant would notice (answer key B2 flag) |
| **New rule R13** "Your band is improving": shown Yellow while this month alone is Green | Jason (persona 2) is shown Yellow while his month is Green (answer key B1 flag); nothing explained why |
| **Forecast reasons get plain words** for the user's side of the average (`reasons.yaml`); the app shows them under "What raises your risk" / "What keeps your risk low" | The old labels were feature names ("savings rate (last 3 months)") that don't say whether the user's value is high or low |

## 2. Advice texts: old → new

Only changed texts are listed; `{...}` is filled in by the engine.

| Rule | Old | New | Why |
|---|---|---|---|
| R01 | "Your income over the last 3 months is below RM300…" | "Your **typical monthly** income over the last {window} months is below {min_income}…" | The rule uses the 3-month median, not the total |
| R03 (held) | *(same text as above the line)* | "Your debt payments take {dsr_pct} of your income. That's under the Red line of {red_pct}, but once Red, FAST keeps showing Red until it drops below {leave_red_pct}, so the band doesn't flip back and forth. Talking to AKPK…" | Explains hysteresis in one sentence |
| R03 (improving) | *(same text as above the line)* | "Good progress: your debt payments are down to {dsr_pct} of your income, out of the Red range this month. FAST shows the better band once it holds for {confirm_months} months in a row…" | Explains D-49; no AKPK nudge when things are improving |
| R05 title | "Build a 1-month cushion first" | "First goal: {first_goal} saved" | Reads well with any goal; matches R06 |
| R05, R06 | "You have about X months of essentials saved" | "Your cash covers about X months of **essentials and debt payments**" | The cushion divides by essentials **plus** debt payments |
| R08 | "…went over **budget** more than once" | "…went over **your usual level** more than once" | The flag compares with the median of the previous 3 months, not the user's budgets |
| R10 | "chance of money getting tight in the next 3 months" | "chance that **your band gets worse or money runs short** in the next 3 months" | Matches what the model predicts (spec label: band worsening or a shortfall in t+1..t+3) |
| R12 | "{cushion_months} months saved" | "{cushion_months} months of costs saved" | Same reason as R05 |
| R13 | *(new)* | "Your debt payments are down to {dsr_pct} of your income, in the {new_band} range this month. FAST shows {new_band} once it holds for {confirm_months} months in a row, so one good month doesn't flip the band back and forth." | See §1 |

## 3. Reason words (`engine/reasons.yaml`)

"High" = above the training average, "low" = below it. Yes/no features appear only when "yes" (P4).
**Model agrees** = the forecast model's coefficient points the way common sense expects.

| Feature | High | Low | Common sense | Model agrees |
|---|---|---|---|---|
| typical income | …higher than average | …lower than average | high lowers risk | yes |
| income variation | changes a lot month to month | steady | raises | yes |
| essentials share | most spending on essentials, little room | smaller share | raises | yes |
| non-essential swings | jumps around | steady | raises | yes |
| months over usual | spent more than usual in several months | kept to usual level | raises | yes |
| savings rate | save a bigger share than average | smaller share | lowers | **no** |
| DSR | bigger share of income than average | smaller | raises | yes |
| DTI | owe more in total for your income | owe less | raises | yes |
| BNPL plans running | more than average | few or none | raises | yes |
| new BNPL plans | started several recently | few or none | raises | **no** |
| personal loan, lives with parents, sends money to family, ran short, unexpected costs, festive month, semester | (yes only) | | | family support: **no** (tiny) |
| impulsivity flag | spending swings and goes over usual | (yes only) | raises | **no** |
| cushion | bigger than average | smaller | lowers | yes |
| cash trend | growing faster than average | slower, or falling | lowers | yes |

## 4. Decisions for Patrick

| ID | Question | Options | Recommendation |
|---|---|---|---|
| **W1** `[DECISION]` **Decided (a), Patrick 2026-10-16 (D-93)** | Leave out forecast reasons whose model coefficient points against common sense? In `forecast_v1` the savings rate, new BNPL plans, family support and the impulsivity flag do (the model is offsetting related features, e.g. new BNPL plans against BNPL plans running). Today **Priya's top reason is "You started several BNPL plans recently" under *What keeps your risk low***, which is answer key B5. | (a) **Leave them out** (one switch: `explanations.drop_counterintuitive` in `thresholds.json`); Priya's reasons become "non-essential spending is steady", "cash growing faster than average", "income steady". (b) Show them as the model says. (c) Show them with a note | **(a)**. The probability is unchanged (only which reasons are listed); it is a presentation rule like P4, and the report says so. Credit-scorecard practice has the same instinct (variables whose sign contradicts business sense are rejected, though there it happens when the model is built; the O2 model is frozen, so here it can only be the explanation) |
| **W2** | Approve the wording in §2 and §3 (all marked DRAFT) | approve / edit | — |
| **W3** **Decided (a), Patrick 2026-10-16 (D-93)**: `red_note` on the forecast and R10's `text_red`, keyed on the model's own band | For a user already in **Red**, "band gets worse" can't happen, so the forecast only measures running short (Priya: 8% while Red). Participants may find a low number next to Red confusing | (a) Under the forecast for Red users, add: "You're already in Red, so this is the chance of running short of money." (b) Leave it | **(a)**, a single line in the app and the assistant's FACTS |
| **W4** | The assistant's crisis reply (`api/assistant.py` CRISIS_REPLY): Befrienders KL 03-7627 2929 (24 h), Talian HEAL 15555 (8am to midnight), 999, then AKPK | approve / edit (PV5: check again before the study) | approve |

## 5. Notes from the exploratory checks (D-101), for W2

| Note | Suggestion |
|---|---|
| The hardest texts to read are short reason phrases with long words: "non-essential spending jumps around" (Flesch 33), "unexpected costs" (33), "typical monthly income" (40) | "Your spending on **extras** jumps around"; "You had **surprise** costs recently"; "Your **usual** monthly income is lower than average" |
| R13 "Your band is improving" fires for people with **3×** the usual chance of getting worse (they were recently in a worse band) | Add a nudge, e.g. "…flip back and forth. Keep building your cushion meanwhile." |
| No advice addresses three of the forecast's drivers: cash falling over 3 months, total debt for income (DTI), recent unexpected costs | Candidate rules for T-24 (Should): "Your cash has gone down three months in a row", "You owe more than a year's income in total", "After surprise costs, rebuild your cushion first" |

The study answer keys were regenerated after W1 and W3 (Priya's B5 is now "Your non-essential spending
is steady"; her B4 accepts "run short of money").

New text from W3 (draft, part of W2): R10 `text_red` "Based on patterns like yours, there is about a
{risk_pct} chance of money running short in the next 3 months. Building your cushion now helps most.";
the forecast's `red_note` "You're already in Red, so this is the chance of running short of money."

## 6. Short lines, shown first (D-108; DRAFT, part of W2)

The redesigned Money screen shows one line per advice item and puts the title and full text behind
"Read more". Rule for each line: **the action first**, at most 70 characters (tested), the reason in
a few words only if it fits. Placeholders are filled from the same values as the full text.

| Rule | Short line |
|---|---|
| R01 | Log your income so FAST can show your band. |
| R02 | Before payday, list what's due and cover essentials first. |
| R03 | Talk to AKPK (free debt counselling) about your repayments. |
| R03 (improving) | Keep going: a better band shows after {confirm_months} good months. |
| R04 | Avoid new instalments for now: Red starts at {red_pct}. |
| R05 | Save about {gap_to_first} more to reach {first_goal} of costs. |
| R06 | Save about {gap_to_next} more to reach {next_goal} of costs. |
| R07 | Finish your BNPL plans before starting new ones. |
| R08 | Try a weekly limit for non-essential spending. |
| R09 | Festive spending is normal; plan next year's early. |
| R10 | Build your cushion now: a tight month may be ahead. |
| R11 | Pause one regular expense: you spent more than you earned. |
| R12 | Keep it up: your cushion is growing. |
| R13 | Keep going: {new_band} shows after {confirm_months} months in a row. |

Points to look at: R08 keeps "non-essential" (§5 suggests "extras"; change both together or
neither); R13 has no cushion nudge yet (§5); R09 and R12 are not actions in the strict sense, on
purpose (reassurance, not a task). The B9 answer key now quotes these lines, so an edit here means
regenerating it (`python -m tools.personas.answer_key`, a test checks it).

## 7. Verdict words under the tiles (D-109; DRAFT, part of W2)

| Tile | Words | When (from `shared/thresholds.json`) |
|---|---|---|
| Next 3 months | **high** (red) | chance ≥ 30 in 100, the limit that triggers R10 |
| | **above average** (amber) / **about average** (grey) / **below average** (green) | otherwise, against the average shown under ⓘ, on the rounded numbers |
| | *(none)*; the tile reads "people like you run short" | already Red (W3: the average isn't like for like) |
| Cushion | **goal: 1 month** (grey) | under the first goal (R05's test) |
| | **✓ first goal** (green) / **✓ 3-month goal** (green) | from 1 month / from 3 months (R06's test) |

Points to look at: "above average" in amber can apply to someone only slightly above (e.g. 13 vs
12); the alternative is an "about average" band of ±N points, which would be a new constant for
`thresholds.json`. "below average" is green, which some may read as "safe"; the ⓘ panel says "an
estimate, not a certainty".
## 8. The weekly life-event cards (D-117; DRAFT, part of W2)

Source: `engine/cards.yaml` (the API sends it; the app shows it on the Future screen). Costs and
how often each event comes up are the generator's (`generator/config.yaml`), so they match the
synthetic data.

| Card | Title | Text |
|---|---|---|
| L02 | Your motorbike needs a big repair | The engine or clutch needs work after months of riding. |
| L04 | Your car needs a big repair | The aircon compressor gives out, or an accident leaves you paying the excess. |
| L06 | Your phone screen cracked | It slipped out of your hand. The repair depends on the phone. |
| L08 | Your laptop stops working | It won't switch on, and you need it for work or study. |
| L10 | A toothache won't go away | The dentist says it needs a filling or an extraction. |
| L12 | Your family needs help | A parent is in hospital, or the house back home needs an urgent repair. |
| L16 | The fridge breaks down | Or the washing machine, or the water heater. It can't wait. |
| L18 | An online deal turns out to be a scam | The money is gone. If it ever happens for real, call the National Scam Response Centre on 997 at once. |

Under the badge (Covered / Partly covered / Not covered yet): "Your money now would pay for all of
it." / "...for part of it." / "A cushion is what helps here, a little at a time."

| Answer | The card's reply |
|---|---|
| I'd use my savings | That's exactly what a cushion is for. Keeping one ready makes a week like this easier. |
| I'd cut back next month | Cutting back for a month works for smaller costs. A cushion means you wouldn't have to. |
| I'd set a small savings goal for it | A small goal adds up. You can set one at your next check-in. |
| Not this week | No problem. A new card comes next week. |

Points to look at: the deck follows `life_events.md`'s suggestion for the app and leaves out the
funeral card (L13) on purpose; L12 (family emergency) and L18 (scam) may also feel heavy, so either
can be dropped from the `deck` line with no code change; the 997 line in L18 should be checked
again before the study (like the crisis reply, W4).

## 9. Explanation wording (D-137; DRAFT, part of W2)

**The new notes** (shown under the reasons; the money helper gets them too):

| When | Note (draft) |
|---|---|
| Type of work or age group is a top factor (P6, unchanged) | "Your type of work and age group also affect this estimate." |
| A top factor was left out as counter-intuitive (P9, new) | "Some other patterns in the data also affect this estimate." |
| Both | "Your type of work and age group, and some other patterns in the data, also affect this estimate." |

**The headings sound causal.** The model knows patterns, not causes (D-133), but "What raises your risk" reads
as cause and effect. Options for the two headings on the Money screen's "Why N in 100?" card:

| Option | Above the base rate | Below it | Trade-off |
|---|---|---|---|
| A (today) | What raises your risk | What keeps your risk low | Shortest and clearest; sounds causal |
| B | What pushes your chance up | What keeps your chance down | About the estimate, not the person's fate; still plain |
| C | Linked with a higher chance | Linked with a lower chance | Most accurate; a little more abstract |

Claude's suggestion: **B** (accurate enough, still plain). The study's B5 asks for "the main reason the app gives",
so the key does not change with the heading.

## 10. Debt interest rate and "Which to pay off first?" (D-144; DRAFT, part of W2)

New lines on the debt form and the Debts screen. The numbers come from `lib/debt-plan.ts`; only the words are
for review.

| Where | Draft text |
|---|---|
| Debt form, field | Interest rate (optional) … % a year (placeholder "not sure") |
| Debt form, hint | From your statement or loan letter. Leave it empty if you're not sure: FAST won't guess it. |
| Debt form, error | Type a yearly rate from 0 to 100, e.g. 18 or 3.5 |
| Card title | Which to pay off first? |
| A rate missing | Add the interest rate to {debt names} to compare two ways of paying off your debts. |
| Extra field | Extra you could pay each month |
| Budget line | Paying RM{budget} a month in all: |
| Each way | **Highest rate first:** debt-free in {N} months, RM{X} in interest · **Smallest balance first:** … |
| Never cleared | not cleared within 30 years at these payments |
| Verdict | Both ways cost about the same here. / Highest rate first saves about RM{d} in interest. / Smallest balance first saves about RM{d} in interest here. |
| Caveat | An estimate from the rates you typed, with these payments kept the same. A loan quoted at a flat rate costs more than its rate suggests. |

Points for Patrick: "Highest rate first" and "Smallest balance first" avoid the jargon (avalanche, snowball). The
card never says which to choose; it states the interest difference. The flat-rate caveat matters for car loans
(hire purchase quotes a flat rate, so the comparison understates their interest).

## 11. UI polish, batch 1 (D-152; DRAFT, part of W2)

| Where | Was | Draft now |
|---|---|---|
| Add, quick add, placeholder | Type or say it, e.g. "RM12 lunch" (cut off on narrow phones) | e.g. "RM12 lunch" |
| Add, quick add, hint | Tap the keyboard's mic to say it. Works for money in too: "salary 2800". | Type it, or tap the keyboard's mic and say it. Works for money in too: "salary 2800". |
| Future, subtitle | Where your habits are taking you in the next 6 months | The next 6 months, if recent habits continue |
| Debts, summary card (new line) | (none) | + RM{instalments} in Buy Now Pay Later instalments from what you log |
| Debts, summary card | Your band counts {dsr}% of your income going to debts ({band}, as of {date}): this list plus the Buy Now Pay Later instalments from what you log. | Your band counts RM{payments} a month, {dsr}% of your income, in {month} ({band}). |

The Debts change answers a reading problem: with only BNPL instalments, the card said "RM0.00 to the debts on this
list" and then "30% of your income", which looked contradictory.

## 12. Sign-in, batch 2 (D-153; DRAFT, part of W2)

| Where | Was | Draft now |
|---|---|---|
| Sign-in, password box, button | (none) | Show / Hide |
| Sign-in, the same button, read aloud by a screen reader | (none) | Show the password / Hide the password |

No other wording changed in batch 2: the rest is colour, outlines and the keyboard's Next and Go keys.
