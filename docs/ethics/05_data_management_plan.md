# Data management plan (DRAFT v0.3, 2026-10-16: sign-up task and per-participant study accounts, D-94; AI-assisted, for Patrick to review)

Follows Malaysia's **Personal Data Protection Act 2010 (PDPA)** principles: collect only what is
needed, tell people what happens to it, keep it secure, keep it no longer than needed, and let
people withdraw.

## What is collected

| Data | Why | Identifies a person? |
|---|---|---|
| Consent (name, signature or typed name, date): paper in person, a separate online consent form online | Proof of consent | **Yes**: kept separately, never linked to answers except through the code list |
| Participant code list (code ↔ name) | Lets a participant withdraw before the cut-off date | **Yes**: kept with the consent forms; destroyed at the withdrawal cut-off [date] |
| Demographics in broad groups (age group, study/work status, app experience) | Describing the sample | No (broad groups only) |
| Questionnaire answers (comprehension, SUS, trust, Future Self, comments) | The study's measures (O4) | No (code only); comments are checked and anything identifying is removed |
| Researcher's task notes (where people got stuck) | Finding usability problems | No (code only) |
| Sign-up task results (finished with or without help, minutes, share of the card's made-up details saved correctly) | Testing the app's onboarding | No (code only); read from the study account before it is deleted |

**Not collected:** any real income, savings, debt, bank, card or IC details; contact details
beyond what a participant chooses to use when replying to the invitation; audio, video or screen
recordings, online calls included (E3). Inside the app, participants only ever see synthetic
personas (CLAUDE.md rule 12).

## Where it is kept

| Data | Storage |
|---|---|
| Consent and code list | Paper forms in a locked drawer; online consent responses exported to an encrypted folder and deleted from the form service; always separate from answers |
| Answers (E4) | An **online form** (MMU's Microsoft Forms preferred over personal accounts) that collects the participant code only, no names or emails. Responses are exported to a spreadsheet on the researcher's password-protected laptop (one backup on its second drive) and then deleted from the form service. Not on public cloud storage |
| Task notes | Written with participant codes only; typed into the same spreadsheet |
| Online sessions (E1) | A video call that is not recorded; the participant's own phone runs Expo Go signed in to study accounts made for that participant |
| Study accounts in the app (D-94) | The app's database (Supabase, Singapore region). For each participant: a copy of each persona and one empty account for the sign-up task, with made-up email addresses that contain only the participant code. **Synthetic data only**: the personas and the card's made-up details, no participant data. **Deleted after the session** (with everything in them), once the sign-up task's result has been noted against the code. The session card with the accounts' password stays on the researcher's laptop and is deleted with the accounts |
| AI assistant (E5) | Typed questions and summarised persona figures go to Groq; participants are told not to type personal information |

Access: the researcher and the supervisor only.

## How long it is kept

- Code list: destroyed on **[withdrawal cut-off date]**, after which answers are fully anonymous.
- Anonymised answers and notes: kept until **the end of the project** (when the final FYP result
  is released), then deleted, unless MMU's policy requires longer (E7).
- Consent forms: kept for [MMU's required period], then destroyed securely.

## Withdrawal

Until the cut-off date, a participant can ask for their answers to be removed by quoting their
code; the answers and the code-list entry are deleted. After it, answers can't be traced to anyone.

## Reporting

Only group results (means, percentages, ranges) and anonymous quotes appear in the FYP report or
any presentation. With 15–20 participants, small groups are merged (e.g. age groups) so that nobody
can be identified from a combination of answers.
