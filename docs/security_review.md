# Security review before the first deploy (D-93)

**Date:** 2026-10-16. **By:** Claude, at Patrick's request. **Scope:** the backend (`api/`), the
database migration (`supabase/migrations/20261014000000_init.sql`), the admin scripts
(`tools/personas/seed.py`), configuration (`render.yaml`, `.env.example`, `.gitignore`) and the
repository (secrets). The app is not built yet; notes for it are in §4.
**Method:** reading the code and the SQL line by line against CLAUDE.md rules 7–11, the OWASP API
Security Top 10 (2023) and Supabase's own security advice; a search of every text file for keys.
Nothing was attacked or run against a live system. The migration has never run on a real database,
so `tests/test_rls.py` (live) has to confirm the database findings once the project exists.

## 1. Findings

Severity is for this project: synthetic data only, one small server, a study with a few dozen people.

| ID | Severity | Where | What could happen | Status |
|---|---|---|---|---|
| S-1 | **Medium** | Database: `profiles` | A user could delete their own profile row and create a new one. That reopens the sign-up numbers (declared income, counted money, savings goal) that lock after 48 hours, and resets the sign-up date. Re-entering a lower declared income undoes the I1 fix against hiding income | **Fixed.** No DELETE policy on `profiles`; the whole account is deleted with `delete_my_account()` (S-2) |
| S-2 | **Medium** | Privacy promise (PDPA) | Privacy Screen 3 says "Delete your account at any time", but no way existed: removing a user from `auth.users` needs the admin key, which the app and API never hold | **Fixed** (to confirm live): `public.delete_my_account()` deletes the caller's account and, by cascade, every row; personas can't use it. *About 75% sure* Supabase lets the `postgres` owner delete from `auth.users` in a function; if the live test fails, the fallback is deletion on request by the researcher (an admin script), which PDPA also allows |
| S-3 | Low–medium | Database: `assessments`, `bias_flags` | Policy "all" let a user rewrite or delete saved assessments, which decide the game's "really bad" months (plants droop) | **Fixed.** Read and add only. Residual: a technical user could add a fake row for a month before the server saves the real one. Accepted: the impact is cosmetic and FAST already trusts what users enter |
| S-4 | Low–medium | API: `/v1/game` | The game used only saved assessments, and those were saved only when the Money screen was opened. A month never assessed counted as Green: plants didn't droop in a really bad month, then drooped later | **Fixed.** `/v1/game`, `/v1/game/actions` and `/v1/future` assess and save missing months first (each month with its own data, M4). The persona builder does the same, so `docs/personas.md` matches the app |
| S-5 | Low | Database: `study_now(uid)` | A security-definer function, callable by any signed-in user through the API's `/rpc/` route. Given another account's id, it revealed whether that account is a persona and its study date | **Fixed.** It answers only for the caller |
| S-6 | **Medium** (availability) | Database + API | No limit on rows. The API reads all of a user's rows on every request, so one account adding millions of entries could exhaust the 512 MB server for everyone | **Fixed.** Daily caps per user: 200 entries, 100 game actions, 20 goal changes (admin scripts exempt) |
| S-7 | **Medium** | Supabase settings | With open sign-ups, anyone with the app could create many accounts. The assistant's cap is 30 questions *per account*, so they could use up the shared Groq quota and leave participants with fallback answers | **For Patrick** (dashboard): sign-ups off during the study; anonymous sign-ins off. Added to `supabase/README.md` step 7 |
| S-8 | **Medium** | The user study | Every persona has the same password, and participants use it on their own phones (E1). Afterwards they could still sign in, change a persona's data, or change its password and lock you out. Two overlapping sessions on one persona would also move each other's study date | **Fixed (SR1 (a), Patrick 2026-10-16, D-94):** each participant gets their own five accounts with one random password, deleted after the session (`seed.py --participant`) |
| S-9 | Low | API | `/docs` and `/openapi.json` published the full endpoint list to anyone | **Fixed.** Off unless `FAST_API_DOCS=1` |
| S-10 | Low (usability) | Database, study mode | Persona entries are stamped on the study date, so the 48-hour edit window (real clock) has already passed: a participant can't fix a typo in a session | **Fixed (D-96):** the entries' edit and delete policies compare with the user's own clock (`study_now`: the real clock, or a persona's study date). Check-ins keep the real clock, so a persona's seeded latest check-in stays locked |
| S-11 | Info | Dependencies | Versions are pinned, but no vulnerability audit has been run | **For later:** turn on GitHub's Dependabot alerts when the repo exists (no install on the laptop) |
| S-12 | Info | Free tier | The rate limits live in the server's memory; Render's free tier sleeps after idle time, which resets them | Accepted for coursework. *Production vs coursework:* a shared store (e.g. Redis) and an always-on instance |

## 2. Checked and fine (no change)

| Area | What was checked |
|---|---|
| Sign-in (`api/auth.py`) | Signature, expiry, audience, issuer and role checked. The algorithm comes from the key type, which blocks the algorithm-confusion attack. The user id comes only from the verified token. PyJWT 2.15 refetches unknown signing keys at most every 30 s, so junk tokens can't make the server hammer Supabase |
| Row Level Security | On all 11 tables, with policies only for signed-in users and only their own rows. The `game_days` view runs with the reader's rights. The API queries with the user's own token, never the admin key (rule 8) |
| Write rules | The server sets every arrival time; check-ins have a window and are never deleted; entries lock after 48 hours; sign-up numbers lock; a user can't make an account a persona; the game is replayed from facts, so there are no points to write (D-76) |
| Injection | PostgREST filters use the token's validated UUID; request bodies are typed, bounded and reject unknown fields; no SQL is built from user input (the one dynamic statement uses the table's own name and bound values) |
| Secrets | No keys in any file (searched for Supabase, Groq and OpenAI key patterns); `.env` git-ignored and absent; the admin key only in `tools/personas/seed.py`; settings hide the JWT secret and the Groq key from logs; `render.yaml` marks every secret `sync: false` |
| The assistant | Groq is called only by the server; it receives a summary built from numbers, never transactions, notes, names, emails or ids (rule 10). So a note typed into an entry can't smuggle instructions to the model. Questions are redacted on the server too, never stored, and capped per day |
| Money | `NUMERIC(12,2)` everywhere (rule 9) |

## 3. Decisions for Patrick

| ID | Question | Options | Recommendation |
|---|---|---|---|
| **SR1** **Decided (a), 2026-10-16 (D-94); also an empty account for a new sign-up task** | How participants get persona accounts | (a) **A fresh copy of the personas for each participant** (`persona_01+p07@…`), each with its own random password, deleted after the session: no shared logins, no clashes between overlapping sessions. A small change to `seed.py`. (b) The four shared accounts, reseeded with a new password after every session; sessions never overlap | **(a).** Online sessions (E1) make overlap and leftover logins likely |
| SR2 | GitHub repo visibility | private / public | **Private.** No secrets are in it, but the persona login emails are, and Turnitin may match your report against your own public specs and decision log |

## 4. Notes for the app build (T-16)

- Only `EXPO_PUBLIC_SUPABASE_URL`, the anon key and the API URL go in the app (rule 7); never the Groq key or the admin key. **Built (D-145):** `api/config.ts` refuses an admin key (legacy `service_role` JWT or `sb_secret_…`) and plain http except to the API on a local network.
- Redact on the phone before anything is uploaded (rule 11), and use the same rules as `api/assistant.py` `redact()`.
- More → Delete account calls `supabase.rpc("delete_my_account")`, then signs out. **Built (D-145)**, after a second tap.
- For persona accounts (`GET /v1/study` → `persona: true`), hide "change password", "change email" and "delete account". **Built (D-145)** for delete; the app has no change-password or change-email screen.
- The Supabase session is kept in AsyncStorage (Supabase's documented Expo setup). That's acceptable with synthetic personas. *Production vs coursework:* encrypt it (Expo SecureStore holds the key). **Built (D-145)** as described; sign-out clears it on this phone only.
