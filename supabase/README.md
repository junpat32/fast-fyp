# FAST database (T-12)

`migrations/20261014000000_init.sql` is the whole schema: 11 tables and one view, Row Level
Security on every table, money as `NUMERIC(12,2)`, rows deleted with their user, the game's time
and edit rules (D-75), and a nightly 36-month retention job. **No points or levels are stored**:
the API replays them from the user's own facts (D-76). Supabase is never run locally (CLAUDE.md §4).

## Apply it (Patrick, once the project exists)

1. Create the Supabase project in **Singapore**.
2. *Database → Extensions*: make sure **pg_cron** can be enabled (the script enables it).
3. *SQL editor*: paste the migration file and **Run**.
4. *Authentication → Users → Add user*, twice: two **test** users with made-up emails.
5. In the project's `.env` (never committed): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and the two test
   users' emails and passwords (see `.env.example`).
6. `.venv\Scripts\python -m pytest tests/test_rls.py -q`: the live proof (O3) that user B reads
   0 of user A's rows, can't change or delete them, can't write in A's name (entries, game
   actions), can't see A's game days, and that there is no points table to write. Until then
   these tests skip.
7. *Authentication* settings (security review, D-93; `docs/security_review.md`):
   - **Anonymous sign-ins: off** (the default). Anonymous users get the role `authenticated`, so the
     API and RLS would treat them as signed-in users.
   - **Allow new users to sign up: off during the user study** (personas are made by the admin
     script; S-7). Otherwise anyone with the app could make many accounts and use up the shared
     Groq quota. Turn it on only while you record the sign-up demo.
   - Confirm email: on. Minimum password length: 10 or more.

## Load the study personas (admin, before the pilot; D-90)

1. Add to `.env` (never committed): `SUPABASE_SERVICE_ROLE_KEY` (*Project settings → API*; the one
   admin key, used only by this script) and `PERSONA_PASSWORD` (the password for the four persona
   logins, used only for piloting and demos). Make it long and random.
2. `.venv\Scripts\python -m tools.personas.build` (only if the personas changed), then
   `.venv\Scripts\python -m tools.personas.seed`. It creates `persona_01..04@personas.fast.test` and
   loads a year of their rows. `--reset` loads them again from scratch; `--delete` removes them.
3. Each persona's clock starts on 1 July 2026; time travel moves it a month at a time
   (`POST /v1/study/time-travel`). Only persona accounts can time-travel; the database guards the flag.

**For each participant (SR1, D-94)**, never the shared four:

| When | Command | What it does |
|---|---|---|
| Before the session | `python -m tools.personas.seed --participant P07` | Five accounts for P07 alone: `new.p07@…` (empty, for the sign-up task) and a fresh copy of each persona (`aina.p07@…`), one random password; prints the session card (logins, password, persona order) and saves it in `data/sessions/p07.md` (never committed) |
| After the sign-up task | `python -m tools.personas.onboarding --participant P07` | What P07 saved against the card: share of details correct, minutes; paste the last line into the results sheet |
| After the session | `python -m tools.personas.seed --participant P07 --delete` | Deletes P07's accounts (and everything in them) and the session card |
| End of the study | `python -m tools.personas.seed --delete-all-participants` | Removes any participant accounts left over |

Use **P01, P02, …** for the main study and **T01–T03** for the pilot: codes only, never names.

## Design

| Table group | Who can write | Why |
|---|---|---|
| profiles, debts, budgets | the user, own rows only | the user's own data; the game's sign-up numbers (income, starting money and debt, goal, and its copy of the situation) lock after 48 hours |
| transactions | the user: add any time, edit or delete within **48 hours** | entries may be saved offline up to 24 hours before they arrive |
| monthly_checkins | the user: add, edit within **48 hours**, **never delete** | one per month, only for months since sign-up, from the month's last day until 7 days after it; the server stores the month's logged totals on it, and what was logged since the month ended (so the game uses month-end balances, D-77) |
| life_event_answers, goal_changes, activity_days, game_actions | the user: add and read only | the card's week and every arrival time come from the server; a "No spending today" tap counts on the day the phone saved it, within 24 hours |
| assessments, bias_flags | the user, own rows only | caches of what the engine computed; changing them only affects the user's own view |
| view `game_days` | (read only) | one row per day for the logging streak and cards; `security_invoker`, so each user sees only their own days |

- **The game (D-76):** `GET /v1/game` reads these facts with the user's own token and replays
  them through `engine/game.py`; `POST /v1/game/actions` saves an action only if the replay
  allows it, and the replay skips any invalid row anyway. Nothing derived is stored, so there is
  nothing a user could write to give themselves points.
- `user_id` defaults to `auth.uid()`, so the app never sends it; RLS `with check` refuses a row
  in someone else's name.
- Policies use `(select auth.uid())` so it is evaluated once per query, not per row.
- Time (C3, the Instagram pattern): `created_at` is always the **server's** clock (a trigger
  overwrites whatever the client sends). A purchase can have any date, but what it earns goes by
  when it arrived. A check-in stores the month's logged totals from entries that arrived before
  it (or before an edit), so adding old entries later can't change a past month.
- **Admin scripts** (the service-role key, or the SQL editor) skip the time checks, so the
  user-study personas can be seeded with past months. The service-role key never goes in the
  app or the backend (CLAUDE.md rule 8).
- Retention: transactions, assessments, bias flags and card answers older than 36 months are
  deleted nightly at 03:30 Malaysia time, after the dates the game needs are copied to
  `activity_days`. Check-ins and game actions are kept, so a replay never loses a reward.
- The 48-hour edit window comes from `shared/game.json` (`edit_window_hours`); a test keeps the
  SQL equal to it, and the API shows a check-in's points as pending until it closes.
- `tests/test_schema.py` checks these rules in the SQL itself on every test run, with no database.
