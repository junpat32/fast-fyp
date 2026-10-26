# Privacy texts (T-19; DRAFT v0.1, 2026-10-15, AI-assisted, for Patrick to review)

Three short screens for the app (Part 1), written in plain words, and the full data inventory behind
them (Part 2, for the report, the ethics application and the user study). Every statement matches
how FAST is built (CLAUDE.md §5 rules 7, 8, 10, 11, 12; `supabase/migrations/…init.sql`; D-76, D-90).
If the design changes, change these texts in the same commit.

---

## Part 1: app screens

### Screen 1: What FAST sees, and what it never sees

**FAST sees only what you tell it.**

What you enter:
- the answers you give when you sign up (your type of work, income, usual costs, debts, savings goal)
- the money in and out that you type (or paste) in
- your monthly check-in (what you have and what you owe at the end of the month)
- what you do in the game (plants, decorations)

What FAST works out from that, for you only: your risk band, health score, forecast and advice,
and your points and garden.

**FAST never sees or asks for:**
- your bank login, password, TAC or OTP
- your full card or bank account numbers
- your IC number
- your contacts, photos, location or text messages

FAST has **no connection to your bank** and **cannot move money**.

If you paste a bank message, your phone removes the sensitive parts **before anything is sent**: TAC
and OTP lines are deleted, account and card numbers are cut to their last 4 digits, and IC numbers
are removed.

### Screen 2: Our scam-safety promise

**FAST will never:**
- ask for your bank password, TAC or OTP
- ask you to transfer money, or to "verify" your account
- call, WhatsApp or SMS you
- send you a link asking you to log in

If anyone claiming to be FAST asks for any of these, **it is a scam**. Do not reply.

**If you think you have been scammed, act fast:**
1. Call the **National Scam Response Centre at 997** straight away. The sooner you call, the better
   the chance your money can be stopped.
2. Call your bank's hotline to block your card or account.
3. Make a police report.

You can check a phone number or bank account before you pay, at PDRM's **Semak Mule** website.

### Screen 3: Your data, who can see it, and how long we keep it

- **Only you** can see your data in the app. The database blocks every account from reading
  anyone else's rows.
- It is stored in **Singapore** (Supabase), and FAST's server runs there too (Render).
- **The AI assistant** gets only a short summary (your band, a few ratios, and which advice rule
  applies) and the question you type, with card, account, IC and phone numbers and emails removed
  first. It never gets your transactions, shop names, your name or your email, so please don't type
  them. FAST doesn't keep your questions or the answers. The AI service (Groq) may process them
  outside Malaysia. *(Added 2026-10-16 with the assistant backend, D-92; for Patrick's review.)*
- **No ads, no selling, no sharing** with lenders or anyone else.
- **How long:** the details of your entries are deleted after **36 months**. Each month's check-in
  totals, and the dates you logged, are kept for your game (so your levels never go down).
- You can **edit or delete an entry for 48 hours** after adding it; after that it is locked so your
  past months stay as they were.
- **Delete your account** at any time and everything about you is deleted with it.

FAST only knows what you enter. It can't check it against your bank, so its results are only as
good as your entries.

---

## Part 2: data inventory (for the report and the ethics application)

**During the FYP user study, only made-up personas are used** (rule 12; D-90). No participant enters
their own financial information: the sign-up task uses a card of made-up details, and each
participant's study accounts are deleted after the session (D-94).

### What is stored

| Data (table) | What it holds | Why | Kept |
|---|---|---|---|
| Login (Supabase Auth) | email; the password is stored only as a hash by Supabase | signing in | until the account is deleted |
| Profile (`profiles`) | type of work, birth year, lives with parents, sends money to family, festival month, vehicle, usual monthly costs, declared income, money and debt at sign-up, savings goal; for study personas, the study date | the risk engine's inputs; the game's sign-up numbers (locked after 48 hours) | until the account is deleted |
| Entries (`transactions`) | date, in or out, amount, category, flags (essential, BNPL, on credit, debt payment, own transfer, unexpected), an optional note (120 characters), how it was entered | the month's spending and income | **36 months**, then deleted nightly |
| Debts (`debts`) | type, label, monthly payment, amount owed, start and end dates | DSR (debt payments ÷ income) and DTI (debt ÷ yearly income) | until deleted by the user |
| Budgets (`budgets`) | category and monthly limit | budget tracking | until deleted by the user |
| Monthly check-ins (`monthly_checkins`) | money by section (cash and bank, EPF Fleksibel, emergency savings, other savings), voluntary EPF, total owed, income, bills on time, ran short; the month's logged totals, frozen by the server | the game's verified months and cushion; the band | **kept** (the game replays them; never deleted, editable for 48 hours) |
| Weekly cards (`life_event_answers`) | the week, the card, the answer | learning points | 36 months (the date is kept for the streak) |
| Logging days (`activity_days`) | dates you logged or tapped "No spending today" | the logging streak | kept |
| Goal changes, game actions | new goals; plants, decorations, animals | the game | kept |
| Results (`assessments`, `bias_flags`) | the engine's results per month | showing them quickly; the game's "really bad month" | 36 months |

**Points, levels and the garden are never stored**: the server works them out again from the facts
above on every request (D-76), so nothing can be written to award points.

### What is never collected

Bank logins or passwords, TAC or OTP codes, full card or account numbers, IC numbers, contacts,
photos, location, SMS messages, real names (the email is the only identifier).

### Who can access it

| Who | What | How it is enforced |
|---|---|---|
| The user | their own rows only | Row Level Security on every table (`user_id = auth.uid()`; rule 8) |
| FAST's server | the same rows as the user, using the user's own sign-in | the server never uses the admin key for users' requests (rule 8) |
| The administrator (the researcher) | everything, for maintenance and for loading the study personas | the service-role key, kept out of the code and the app (rule 7), used only by admin scripts |
| The AI service (Groq) | a summary: band, ratios, the rule that fired; plus the user's question, redacted on the server (IC, card, account and phone numbers, emails, TAC/OTP lines) | built into the server (`api/assistant.py`, D-92); never transactions, merchant names, names or emails (rule 10); questions and answers are not stored by FAST |
| Anyone else | nothing | no ads, analytics or data sharing in the app |

### Personal Data Protection Act 2010 (PDPA) checklist

| Principle | How FAST meets it |
|---|---|
| General: only what is needed | no bank access, no IC, no contacts or location; sign-up asks only what the engine uses |
| Notice and choice | Screens 1 to 3 at sign-up; nothing is collected before the user agrees |
| Disclosure | no sharing; the AI gets a summary only; storage in Singapore and Groq abroad are stated (cross-border transfer, s129) |
| Security | RLS on every table, the user's own sign-in for every request, secrets never in the app (`EXPO_PUBLIC_*` holds only public keys), redaction on the phone before upload (rule 11) |
| Retention | details deleted after 36 months; account deletion removes everything (on delete cascade) |
| Data integrity | entries editable for 48 hours; the server stamps arrival times (C3) |
| Access | the user sees all their data in the app and can delete their account |

### Things to confirm before release (Patrick)

| ID | Item | Note |
|---|---|---|
| PV1 | Groq's processing location and its data-retention terms | Check Groq's current privacy policy and say exactly where data goes |
| PV2 | NSRC 997 and Semak Mule details | Check both are current at the time of the study |
| PV3 | A contact for privacy questions | Add the researcher's email to Screen 3 |
| PV4 | The paste-in parser (Should) | If it is not built, drop the "paste a bank message" sentence from Screen 1 |
| PV5 | The assistant's crisis reply (D-92) | Befrienders KL 03-7627 2929 (24 hours), Talian HEAL 15555 (8am to midnight), 999: checked 2026-10-16; check again before the study |
