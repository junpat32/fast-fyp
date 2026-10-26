# Study questionnaire (DRAFT v0.3, 2026-10-16: Part S for the sign-up task, D-94; 2026-10-17: B10–B11 and D7, D-101; AI-assisted, for Patrick to review)

Participant code: **P__**   Persona order: [from the participant's session card, e.g. C-D-B-A: a
balanced order (Williams design) so each persona comes before and after each other equally often]

The comprehension questions below are fixed now; their **answer keys** are written once the
personas exist (T-18), before the pilot. Answers are scored correct or incorrect against the key.

## Part A: about you (tick one in each)

1. **Age group:** ☐ 18–20 ☐ 21–24 ☐ 25–29 ☐ 30–35
2. **Right now I mainly:** ☐ study ☐ work for an employer ☐ do gig or freelance work ☐ other: ____
3. **Do you use any app to track money or spending?** ☐ No ☐ Sometimes ☐ Regularly
4. **Before today, had you heard of a "debt-service ratio" (the share of income that goes to loan repayments)?** ☐ No ☐ Heard of it ☐ Know what it means

(No question asks about your own income, savings or debts.)

## Part S: the sign-up task (right after setting up the app with the card)

Single Ease Question (Sauro & Dumas, 2009), free to use.

| # | Question | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| S1 | Overall, how difficult or easy was it to set up the app? (1 = very difficult, 7 = very easy) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Researcher only (not on the participant's form):* finished without help ☐ yes ☐ with help ☐ not
finished; where they got stuck: ________. Time and saved details come from
`python -m tools.personas.onboarding --participant P__`, run before the accounts are deleted.

## Part B: understanding the app (for each persona)

Answer right after that persona's tasks, from what the app shows. It's fine to look back at the
app, but don't use time travel until you've answered.

| # | Question | Measures |
|---|---|---|
| B1 | What is this persona's risk band right now? ☐ Green ☐ Yellow ☐ Red ☐ "Not enough income data" | Reading the band |
| B2 | Roughly what share of this persona's income goes to loan repayments each month? ☐ under 30% ☐ 30% to under 60% ☐ 60% or more | Understanding what the band means (DSR) |
| B3 | If this persona's repayments went up and their band got **worse**, when would the app show it? ☐ straight away ☐ after it lasts 2 months ☐ never | The band's update rule (worse at once, better after 2 months) |
| B4 | The forecast says there is a ___% chance of things getting worse in the next **3 months**. What does it mean? ☐ It will definitely get worse ☐ Out of 100 people like this, about ___ would get worse ☐ It's the persona's health score | Understanding a probability |
| B5 | What is the **main reason** the app gives for this persona's forecast? (write it) ________ | Reading the explanation |
| B6 | The "Future Self" shows this persona's savings in 6 months as a range (e.g. "between 1 and 3 months of savings"). Why a range and not one number? ☐ The app isn't finished ☐ The future is uncertain, so it shows likely lows and highs ☐ It's the persona's goal | Understanding uncertainty (Monte Carlo) |
| B7 | How many months could this persona cover their essential costs with the money they have now? ☐ less than 1 ☐ 1–2 ☐ 3 or more | Understanding the cushion |
| B8 | What makes this persona's garden grow? ☐ spending more ☐ logging lots of entries ☐ meeting their own saving goal or keeping a cushion, month after month ☐ beating other users | Understanding what the game rewards |
| B9 | Which **one** step does the app suggest this persona takes next? (write it) ________ | Reading the advice |
| B10 | The step the app suggests is realistic for this persona. ☐ 1 strongly disagree ☐ 2 ☐ 3 ☐ 4 ☐ 5 strongly agree | Usefulness of the advice: realistic (an opinion, **not scored** for comprehension) |
| B11 | If I were this persona, I would know how to do the suggested step. ☐ 1 strongly disagree ☐ 2 ☐ 3 ☐ 4 ☐ 5 strongly agree | Usefulness of the advice: actionable (an opinion, **not scored**) |

Comprehension (O4's 70% target) is scored on **B1–B9** only. B10–B11 are opinions about the advice (D-101).

## Part C: ease of use (System Usability Scale)

The System Usability Scale (Brooke, 1996), free to use with acknowledgement; "system" replaced
by "app". 1 = strongly disagree, 5 = strongly agree.

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| C1 | I think that I would like to use this app frequently. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C2 | I found the app unnecessarily complex. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C3 | I thought the app was easy to use. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C4 | I think that I would need the support of a technical person to be able to use this app. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C5 | I found the various functions in this app were well integrated. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C6 | I thought there was too much inconsistency in this app. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C7 | I would imagine that most people would learn to use this app very quickly. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C8 | I found the app very cumbersome to use. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C9 | I felt very confident using the app. | ☐ | ☐ | ☐ | ☐ | ☐ |
| C10 | I needed to learn a lot of things before I could get going with this app. | ☐ | ☐ | ☐ | ☐ | ☐ |

Scoring (researcher): odd items score − 1, even items 5 − score; sum × 2.5 = 0–100.

## Part D: trust in the explanations

Written for this study. 1 = strongly disagree, 5 = strongly agree. (R) = reverse-scored.

| # | Statement |
|---|---|
| D1 | I understood why the app gave each persona the risk band it did. |
| D2 | The reasons the app gave for its forecasts made sense to me. |
| D3 | I would trust this app's warnings about my own money. |
| D4 | The app seemed to hide how it reached its answers. (R) |
| D5 | I would still check important money decisions myself rather than rely only on the app. |
| D6 | The app's advice felt realistic for young Malaysians. |
| D7 | The personas seemed like real young Malaysians. |

## Part E: the Future Self screen

Written for this study; checks the design goal that the Future Self motivates without causing
stress. 1 = strongly disagree, 5 = strongly agree.

| # | Statement |
|---|---|
| E1 | Seeing a persona's Future Self made the effect of saving easier to understand. |
| E2 | The Future Self screen made me feel anxious. (R) |
| E3 | The Future Self screen felt encouraging rather than judging. |
| E4 | I would like to see my own Future Self in an app like this. |

## Part F: your comments (optional)

1. What was the most confusing part of the app?
2. What was the most useful part?
3. Anything else you'd change?

Thank you!
