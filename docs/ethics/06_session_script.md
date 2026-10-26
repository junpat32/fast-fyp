# Session script and task list (DRAFT v0.3, 2026-10-16, D-95; AI-assisted, for Patrick to review)

The researcher follows this for **every** session (pilot and main study, in person and online), so
every participant hears the same words and does the same tasks. Words in boxes are **read as
written**; everything else is for the researcher. English only (E6). About **50 minutes** (up to 55).

**Neutral by design:** the introduction names the parts of the app but never explains the rules
that the comprehension questions test (how a band changes, what the forecast's number means). If a
participant asks what something means, say: *"I can't explain it, because I'm testing what the app
makes clear on its own. Answer from what you see; it's fine to say you're not sure."*

---

## 1. Before the session (researcher)

| ✓ | Check |
|---|---|
| ☐ | Participant code chosen (**P01, P02…** main study; **T01–T03** pilot). Never a name |
| ☐ | Accounts made: `python -m tools.personas.seed --participant P07` → session card (logins, password, persona order) |
| ☐ | The study build opens on the study phone (in person) or the Expo Go link is ready to send (online) |
| ☐ | The API is awake: open `https://<api>/health` a minute before (shows `{"status":"ok"}`) |
| ☐ | The sign-up card ready: printed (in person) or as an image to send in the chat (online): `docs/study/onboarding_card.md` |
| ☐ | The online form link with the participant code filled in; the task list (§4) printed or ready to share |
| ☐ | A blank notes sheet (§7) with the code, date, mode and persona order filled in |
| ☐ | In person: two paper consent forms. Online: the separate consent form link |

## 2. Welcome and consent (5 min)

> Hi, thanks for coming. I'm Patrick. Today you'll try an app I built for my final year project.
> I'm testing the **app**, not you, so there are no wrong answers. If something is confusing, that's
> exactly what I need to find out.
> Nothing is recorded: no audio, no video, no screen. I'll just take written notes, labelled with a
> code, not your name. You can skip any question or stop at any time, without giving a reason.
> Please read the information sheet, and ask me anything before you decide.

Consent: paper form in person (two copies), or the separate online consent form. Write the code on
the participant's copy. **No consent, no session.**

## 3. Questions about you and the app introduction (6 min)

Participant fills in **Part A** on the form (3 min). Then read:

> FAST is a prototype money app for young Malaysians. In a moment you'll set it up as if you had
> just installed it. After that you'll look at a few **made-up people**, which I call personas. Each
> persona already has six months of made-up history in the app.
> The app has four tabs at the bottom: **Home**, **Money**, **Add** and **Future**. Home shows the
> persona's room and garden. Money shows how they're doing with their debts and savings, and what
> might happen next. Add is where you would record spending. Future shows what their savings could
> look like later on.
> For the personas there is also a bar at the top with the persona's date and **time-travel**
> buttons, which move their story forward a month at a time.
> I won't explain what things mean, because I want to see what the app makes clear by itself.
> And please don't type any of your own personal or money details anywhere in the app.

## 4. The tasks

### 4a. Sign-up task (5–7 min)

Give the card and the first login from the session card (`new.p07@…` and the password). Read:

> First, please set up the app as if you had just installed it. Sign in with this email and password.
> Then follow the app, and use **only the details on this card**. Choose any avatar you like. Tell me
> when you reach the home screen. I'll stay quiet unless you're completely stuck.

**Hints** (note each one): after about 2 minutes stuck, ask *"What would you try next?"*. After 2
more, point to the control. Any pointing counts as **with help**. If they type a real detail by
mistake, stop the task, delete the account straight away (`seed --participant P07 --delete`, then
make the accounts again) and note it; don't look at what was typed.

At the home screen: participant answers **Part S** (one question) on the form.

### 4b. Each persona (about 8 min each)

Use the order on the session card. Do **three** personas; do the fourth only if the session is at
**38 minutes or less** when the third is finished. Read for each persona:

> Now please tap **Switch account** at the top and sign in as **[name]**, with **[email]**. The
> password is the same as before. [Name] is a made-up person. Please do these tasks in your own
> time, and tell me when you've found each one.

Show the task list (the same for every persona):

| # | Task (shown to the participant) | Screen it leads to |
|---|---|---|
| 1 | Find out how [name] is doing with their debts **right now**. | Money: the Band tile |
| 2 | Find what the app thinks could happen to [name] in the **next 3 months**, and why. | Money: the Next 3 months tile and "Why … in 100?" |
| 3 | Find the **one step** the app suggests [name] takes next. | Money: Your next step |
| 4 | Look at [name]'s **Future Self**. | Future |
| 5 | Find out how many months [name] could get by on the money they have now. | Money: the Cushion tile |
| 6 | Go to the home screen and tap something you're curious about. | Home |

*For the researcher (D-108):* the Money screen shows three tiles and one next step; each
explanation is one tap away (ⓘ on a tile, "Read more", "+N more"), and the screen's top line says
"tap ⓘ to explain". How the band changes (B3) is under the Band tile's ⓘ. **Don't point to ⓘ**;
note on the notes sheet (§7) whether the participant opened it without help.

Then read:

> Please answer the questions about [name] on the form now (**Part B**). You can look back at the
> app, but **don't use time travel yet**.

**First persona only, when Part B is done** (task 7, recording spending; D-96):

> Now please record that [name] spent **RM12 on lunch today**. Then find it in [name]'s list for
> this month.

Same hint rule as the sign-up task. If they type a wrong amount, let them notice and fix it
(entries can be edited for 48 hours); note whether they found how. It comes after Part B, so the
new entry can't change any answer. ("Today" is the persona's date, 1 July 2026, shown in the bar.)

Then, for every persona, when Part B (and task 7) is done:

> Now use time travel to move [name] **one month forward**, and tell me what changed. Then move
> forward once more.

Note what they notice. Don't reset anything: the next persona is a different account.

**Money helper (only for the second persona, and only if the assistant is in the study build):**

> Please ask the money helper one question you have about [name]'s situation. Remember not to type
> anything about yourself.

Note the question's topic (not word for word) and whether the answer helped.

## 5. Ease of use, trust and the Future Self (5 min)

> Thank you, that's the app part done. Please answer the last parts of the form, **C to F**, about the
> app as a whole.

## 6. Debrief (3 min)

Give the debrief (in `02_participant_information_sheet.md`), and read:

> Thank you for taking part. Everything you saw was made up. If any of the money situations felt close
> to home, the debrief has free, confidential help from AKPK. If you want your answers removed, you
> can ask me until [date], quoting your code, **P__**.

## 7. After the session (researcher, the same day)

| ✓ | Step |
|---|---|
| ☐ | `python -m tools.personas.onboarding --participant P07` → paste its last line into the results sheet |
| ☐ | `python -m tools.personas.seed --participant P07 --delete` (the accounts, everything in them, and the session card) |
| ☐ | Type the notes sheet into the results spreadsheet (code only); file the consent form separately |
| ☐ | Online: ask the participant to remove the FAST link from Expo Go (optional; the accounts no longer exist) |

### Notes sheet (one per participant)

| Field | Entry |
|---|---|
| Code · date · in person / online · persona order | P__ · ____ · ____ · _-_-_-_ |
| Sign-up task | ☐ finished unaided ☐ with help ☐ not finished · stuck at: ____ |
| Persona 1 (__): tasks 1–6 | for each: ✓ unaided / H with hint / ✗ not found · opened an ⓘ / "Read more" unaided? ☐ · notes: ____ |
| Persona 1: task 7 (record RM12 lunch, find it) | ✓ / H / ✗ · typo made? ☐ · fixed it unaided? ☐ · notes: ____ |
| Persona 2 (__): tasks 1–6 · money helper | same · helper question topic: ____ · helpful? ____ |
| Persona 3 (__): tasks 1–6 | same |
| Persona 4 (__) (only if time) | same, or "skipped (time)" |
| Time travel | what they noticed: ____ |
| Problems seen | (usability problems, confusing words, crashes) ____ |

## 8. If something goes wrong

| Problem | What to do |
|---|---|
| The app crashes or freezes | Close and reopen Expo Go; sign in again. Note it as a problem seen |
| An account is broken | `seed --participant P07 --delete`, then make them again; restart that task |
| The API is slow to answer | Wait 30 seconds and retry; note it |
| The money helper says it can't answer | Fine: note it and carry on (it falls back to the app's own advice) |
| The participant seems upset by a persona's situation | Pause; remind them it's made up and they can stop; offer the debrief and AKPK |
| Running out of time | Skip the fourth persona, then the money helper; never skip Parts C–F |

## 9. Results spreadsheet columns

`code, mode, date, persona_order, personas_done, S1, signup_result, signup_minutes, signup_accuracy,
p1_tasks…p4_tasks, record_expense (task 7), helper_topic, time_travel_notes, problems, then the form's
Part B–F answers`.
Comprehension is scored against `docs/study/answer_keys.md`; SUS as in Part C.
