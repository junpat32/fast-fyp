# Study protocol (DRAFT v0.3, 2026-10-16: sign-up task and per-participant study accounts added, D-94; AI-assisted, for Patrick to review)

## 1. Study details

| Item | Details |
|---|---|
| Title | Evaluating how understandable and usable FAST is: a persona-based study of a gamified, explainable personal financial risk app for young Malaysian adults |
| Researcher | Patrick Wong Jun Wen, BSc Computer Science (Hons) Artificial Intelligence, [faculty], Multimedia University. [student ID], [MMU email] |
| Supervisor | [supervisor's name, title], [faculty], [email] |
| Type of study | Undergraduate Final Year Project (FYP2), usability and comprehension evaluation |
| Planned dates | Pilot (3 participants): about 30 Dec 2026. Main study (15–20 participants): 30 Dec 2026 to 10 Jan 2027. Only after ethics approval |
| Funding | None |

## 2. Background and aim

Many young Malaysian adults carry debt (for example PTPTN loans, car loans and Buy Now Pay Later
plans) with little emergency savings. FAST (Financial Advisory and Safety Tracker) is a mobile
app prototype that shows a user's financial risk in plain language: a risk band based on the
debt-service ratio, a health score, a 3-month forecast with its main reasons, a range of possible
futures, and a non-competitive game (a home and garden that grow as the user builds a cash
cushion).

**Aim:** to find out whether people aged 18–35 can **understand** FAST's risk information and find
the app **usable**. The study measures understanding, not changes in behaviour, so it uses
**fictional personas** with ready-made histories. No participant's own financial information is
asked for or used.

**Objectives (as pre-set in the FYP's objectives, O4):**
1. Usability: mean System Usability Scale (SUS) score of at least 68.
2. Comprehension: at least 70% of risk-comprehension questions answered correctly.
3. Secondary: participants' trust in the explanations, and whether the "Future Self" screen causes
   stress (the design aims for it not to).

## 3. Design

A single-session usability study with a short questionnaire, in two rounds:
- **Pilot** (3 participants): checks timing and wording. If the mean SUS is below 60 or
  comprehension is below 50%, the three biggest problems are fixed before the main study. Pilot
  data is reported separately and not pooled with the main study.
- **Main study** (15–20 participants).

Each participant first sets up the app as a new user would (the **sign-up task**), typing the
made-up details from a printed or on-screen card into an empty study account. They then explore
3–4 fictional personas (for example a student living with parents, a gig rider with irregular
income, and an office worker paying a car loan), in a balanced order that changes between
participants. Each persona has a ready-made history of 6 months, created by a synthetic data
generator, and a "time-travel" control to see how the persona's situation develops. No real
person's data is used, and the participant never types anything about themselves.

## 4. Participants

| Item | Details |
|---|---|
| Number | 3 (pilot) + 15–20 (main) |
| Inclusion | Aged 18–35; living in Malaysia; able to read English; able to use a smartphone |
| Exclusion | Under 18; anyone who took part in the pilot (for the main study); anyone who designed or tested FAST |
| Recruitment | Convenience and snowball sampling: a short message (in `02_participant_information_sheet.md`) shared online (MMU student groups, the researcher's networks) and on campus (the same message on a notice or handed out). People reply to the researcher if interested; nobody is asked twice after saying no |
| Voluntariness | The researcher is a student with no authority over anyone. Taking part or not has no effect on grades, assessments or friendships, and this is stated in the information sheet |
| Thank-you | None (E2) |

## 5. Procedure (about 50 minutes, up to 55)

| Step | What happens | Time |
|---|---|---|
| 1 | Welcome; participant reads the information sheet, asks questions, and gives consent if willing (signs the paper form in person, or completes the separate online consent form) | 5 min |
| 2 | Short demographic questions (age group, study or work status, experience with money apps) | 3 min |
| 3 | Short introduction to the app (its four parts and the time-travel bar; it does not explain the rules the questions test), read from the session script (`06_session_script.md`) so everyone hears the same | 3 min |
| 4 | **Sign-up task:** sign in to the empty study account and set up the app with the made-up details on the card (`docs/study/onboarding_card.md`), then one question on how easy it was (Part S) | 5–7 min |
| 5 | **For each persona** (three; a fourth if time allows), in the order on the session card: six short tasks (the same for every persona, e.g. "Find out how this persona is doing with their debts right now"), then that persona's comprehension questions (Part B), then time travel a month or two forward. Part B comes before time travel, so every participant answers about the same screens. For the first persona only, after Part B: record one made-up expense ("RM12 on lunch today") and find it in the list | 24–30 min |
| 6 | SUS, trust items and Future Self items | 5 min |
| 7 | Open feedback; debrief sheet given | 3 min |

**Study accounts (D-94):** before each session the researcher makes accounts for that participant
alone: one empty account for the sign-up task and a fresh copy of each persona, all with made-up
email addresses that contain only the participant code, and one random password. Every participant
therefore starts from exactly the same screens, two sessions can never affect each other, and the
accounts are **deleted after the session**, so nobody can use them again.

**Setting (E1):** sessions are held **in person or online**, whichever the participant prefers.
- *In person:* a quiet room on campus, [location]. The app runs on a study phone provided by the
  researcher (Android, Expo Go); the researcher signs in to the participant's study accounts.
- *Online:* a video call (MMU's Microsoft Teams preferred; the camera is optional). The participant
  installs the free Expo Go app on their own phone, opens the study build from a link the researcher
  sends, and signs in with the study accounts the researcher gives them for this session.

Either way, participants never create an account of their own and never enter personal details in
the app: in the sign-up task they type only the made-up details on the card.

**Recording (E3):** no audio, video or screen recording, online calls included; the researcher
writes notes on where people get stuck, using participant codes only.

**Questionnaire (E4):** answered on an online form (MMU's Microsoft Forms preferred) that asks
for the participant code only, never a name or email. Consent is given separately (paper, or a
separate online consent form), so answers are never stored with names.

**AI assistant (E5):** the study build includes FAST's AI assistant. Questions typed into it and the
persona's summarised figures are sent to an external AI service (Groq). Participants are asked not
to type any personal information into it. Only persona data is ever involved. If the assistant is
not ready by the feature freeze (27 Dec 2026), it is left out and the committee is told.

## 6. Risks and how they are reduced

| Risk | Likelihood | How it is reduced |
|---|---|---|
| Mild discomfort when seeing debt or money stress, even for fictional personas | Low | Personas are clearly fictional; no participant is asked about their own finances; any question can be skipped; the participant can stop at any time; the debrief lists free help (AKPK, Bank Negara Malaysia's free credit counselling agency) |
| Feeling tested or embarrassed by wrong answers | Low | The information sheet and script say the app is being tested, not the person |
| Privacy | Low | No real financial data; no names on answers (participant codes); consent kept separately; no recording, online calls included (E3) |
| Online sessions on the participant's own phone | Low | Only the free Expo Go app and study accounts made for that participant are used; nothing personal is entered; the accounts are deleted after the session; the call is not recorded |
| Typing real details in the sign-up task by mistake | Low | The card is shown throughout the task and the script says to use only its details; the app asks for no name, IC or bank details; the account and everything in it are deleted after the session |
| Pressure to take part (people who know the researcher) | Low | Recruitment by open invitation, online or on campus; no reminders after a "no"; no effect on grades or relationships |
| Personal information typed into the AI assistant | Low | Participants are told not to (E5); the app sends only summarised persona context |

Overall this is a **minimal-risk** study: no deception, no vulnerable groups, no physical risk, no
sensitive personal data collected.

## 7. Consent and withdrawal

Informed consent is taken before any data is collected (`03_consent_form.md`): signed on paper in
person, or on a separate online consent form for online sessions.
Participants may stop at any time without giving a reason, and may ask for their answers to be
removed until **[date analysis starts, e.g. 11 Jan 2027]**; after that the answers are part of
the anonymised summary and can no longer be found by name.

## 8. Data

See `05_data_management_plan.md`. In short: demographics in broad groups, questionnaire answers,
task notes, sign-up task results; all linked to a participant code; consent kept separately; no real financial data;
deleted at the end of the project, when the final FYP result is released (E7).

## 9. Analysis

- SUS: scored in the standard way (0–100); mean with a 95% confidence interval; compared with
  the benchmark of 68.
- Comprehension: percentage correct overall and per question; compared with the 70% target.
- Trust and Future Self items: medians and distributions (5-point scales).
- The advice's usefulness (B10 realistic, B11 actionable, per persona) and the personas' realism (D7):
  medians and distributions; secondary, not O4 targets (D-101).
- Sign-up task (secondary, not an O4 target): share of participants who finished without help, the
  median time, the share of the card's details saved correctly (read from the study account before
  it is deleted), and the median ease rating (Part S).
- Tasks: the share of participants who completed each task unaided, with a hint, or not at all
  (including recording an expense).
- Open answers and task notes: grouped into common themes (usability problems, confusing terms).
- Results are reported only as group summaries; quotes are anonymous and checked so nobody can be
  identified from them.

## 10. Use of results

The results go into the FYP report (and possibly a poster or presentation at MMU). No individual
can be identified in any of them.
