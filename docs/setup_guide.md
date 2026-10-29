# Setup guide: Git, Node, GitHub, Supabase, Render (Patrick)

**Why:** the app (T-16) and the 13 Dec week-9 check are waiting on these accounts and tools.
**Time:** about 75 minutes in one sitting, or one step at a time. **Order matters:** 1 → 5 (Render
needs the GitHub repo; the tests need Supabase).
**Safety:** passwords and keys go **only** into `.env` (never committed) and the Render dashboard.
Never paste a key or password into the chat. What to send Claude is listed at the end of each step.

Dashboards change their menus now and then; if a name below doesn't match exactly, look for the
closest one, or tell Claude what you see.

---

## 1. Git for Windows (10 min)

Git keeps the project's history and is how GitHub and Render get the code (D-97 lifts D-36).

1. Go to **git-scm.com** → *Download for Windows* → the 64-bit installer.
2. Run it and keep the defaults, **except**:
   - *Choosing the default editor*: pick **Use Notepad as Git's default editor** (the default, Vim,
     is hard to exit).
   - *Adjusting the name of the initial branch*: pick **Override … and type `main`**.
3. Open a **new** PowerShell window and check: `git --version` (shows a version number).
4. Tell Git who you are (this goes into every commit; the GitHub no-reply address from step 3 keeps
   your real email private, so you can do this part after step 3):
   ```
   git config --global user.name "Patrick Wong"
   git config --global user.email "YOUR-ID+YOUR-USERNAME@users.noreply.github.com"
   ```

**Tell Claude:** "git installed".

## 2. Node.js LTS (10 min)

Node runs Expo, the app's development server. On the 4 GB laptop, run it with Chrome and other
heavy programs closed.

1. Go to **nodejs.org** → download the version marked **LTS** (Windows installer, `.msi`).
2. Run it and keep the defaults, **except**: on the page *Tools for Native Modules*, **leave the box
   unticked**. (It installs Chocolatey, Python and Visual Studio build tools: several GB you don't need.)
3. In a **new** PowerShell window: `node -v` and `npm -v` (both show version numbers).

**Tell Claude:** "node installed" (Claude checks the version works with the current Expo).

## 3. GitHub: a private repository (10 min)

1. Sign in at **github.com** (or create an account).
2. *Settings → Emails*: tick **Keep my email addresses private** and copy the
   `…@users.noreply.github.com` address for step 1.4.
3. Top right **+** → **New repository**:
   - Name: `fast-fyp`
   - **Private** (SR2: Turnitin, and the persona logins)
   - Leave **README, .gitignore and licence unticked** (the project already has them)
   - **Create repository**.
4. In the new repo: *Settings → Advanced security* (or *Code security*) → **Dependabot alerts:
   Enable** (S-11: GitHub warns you about vulnerable packages).

**Tell Claude:** "repo created: github.com/YOUR-USERNAME/fast-fyp". Claude then makes the first
commit and pushes it. The first push opens a **GitHub sign-in window in your browser**: you sign in
there (Claude never sees it).

## 4. Supabase: the database and logins (25 min)

1. Sign in at **supabase.com** (*Continue with GitHub* is simplest) → **New project**:
   - Name: `fast-fyp` · Plan: Free · Region: **Southeast Asia (Singapore)**. The region box says
     *Auto* at first, which can pick another continent (it chose Ireland once): click **Need a specific
     region?** under it and pick Singapore. A project can't change region later.
   - *Security*: Data API **on**, automatically expose new tables **on**, automatic RLS **on**.
     *Advanced*: **Postgres** (not OrioleDB).
   - Database password: let it generate one and save it in your password manager (the code
     doesn't need it).
2. *Database → Extensions*: switch on **pg_cron** (the nightly clean-up job needs it). Then **SQL
   Editor** → *New query* → paste the whole file `supabase/migrations/20261014000000_init.sql` →
   **Run** (confirm the "destructive operations" warning: that's the clean-up job's delete lines). It
   should end with one result, `schedule: 1`. *Table Editor* should now show 11 tables. If it shows an
   error, send Claude the error text.
3. **Authentication settings** (security review S-7):
   - *Sign In / Providers*: Email **on**; **Confirm email on**; **Allow anonymous sign-ins off**.
   - **Allow new users to sign up: off.** Accounts are made by you in the dashboard or by the persona
     script; turn it on only for a while when testing the app's "Create account".
   - Password settings: minimum length **10**.
4. **Two test users** (for the live security test): *Authentication → Users → Add user → Create new
   user*, twice, ticking **Auto Confirm User**:
   - two made-up addresses on a domain that never delivers, e.g. `demo-a@example.com` and
     `demo-b@example.com` (no real names), each with its own strong password. Claude can generate the
     passwords straight into `.env` without showing them; then copy them from there.
5. **Create `.env`**: in PowerShell in the project folder run `Copy-Item .env.example .env`, then open
   `.env` in Notepad and fill in:

   | Line in `.env` | Where to find it |
   |---|---|
   | `SUPABASE_URL` | *Project Settings → Data API*, or the project's home page: the base address `https://….supabase.co`. The Data API page shows it with `/rest/v1/` on the end; drop that (the code drops it too, D-147) |
   | `SUPABASE_ANON_KEY` | *Project Settings → API Keys*: the **anon / publishable** key (public by design) |
   | `SUPABASE_JWT_SECRET` | *Project Settings → JWT Keys*: only if the current key is the **legacy HS256 shared secret**, copy that secret; if the current key is **ECC (P-256)**, leave it empty |
   | `RLS_TEST_A_EMAIL`, `_PASSWORD`, `RLS_TEST_B_…` | the two test users from 4.4 |
   | `SUPABASE_SERVICE_ROLE_KEY` | *API Keys*: the **service_role / secret** key. **Admin only**: used solely by the persona script (rule 8). Never in the app, never on Render |
   | `PERSONA_PASSWORD` | make one up (long, random); only for the four shared demo personas |

   *About the keys (about 70% sure):* Supabase is moving from the "legacy" `anon`/`service_role` keys
   to new "publishable"/"secret" keys. If the dashboard offers both, use the **legacy** ones (the code
   was written and tested with them). If only the new ones exist, use those, and tell Claude if a step
   below answers "401" so the code can be adjusted.
6. Run the live security test:
   ```
   .venv\Scripts\python -m pytest tests/test_rls.py -q
   ```
   Expected: **4 passed**. If not, send Claude the output (it contains no keys).

**Tell Claude:** "supabase done" and the test result.

## 5. Render: the API online (15 min)

1. Sign in at **render.com** with **GitHub**; when asked, give Render access to the `fast-fyp`
   repository only.
2. **New → Blueprint** → pick `fast-fyp`. Render reads `render.yaml` and proposes the `fast-api`
   service (Singapore, free plan for now; Starter during the study, P1).
3. Fill in the secret values it asks for (the same as in `.env`): `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` (empty if you left it empty), `GROQ_API_KEY` (empty for
   now: the assistant then answers "not configured" and the app shows "coming soon"). **Not** the
   service_role key.
4. **Apply**. The first build takes 5–10 minutes. Then open
   `https://fast-api-….onrender.com/health`: it should show `{"status":"ok"}`.
   If the build fails, send Claude the build log (no keys in it). The likeliest cause is the Python
   version (`render.yaml` asks for 3.14.8, D-70); Claude then adjusts it.

**Tell Claude:** "render done" and the service's address (`https://fast-api-….onrender.com`; not secret).

## 6. The app in live mode (10 min; can come before Render)

The app runs on sample data until it has three public settings (D-145). They are bundled into the app,
so **only public values**: never the service_role key, never the Groq key (the app refuses an admin key).

1. In PowerShell in the `app` folder: `Copy-Item .env.example .env`, then fill in `app\.env` in Notepad:
   `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` (the same values as `SUPABASE_URL` and
   `SUPABASE_ANON_KEY` in the main `.env`), and `EXPO_PUBLIC_API_URL`:
   - after step 5: the Render address;
   - before it: this laptop. Connect the laptop to the **phone's hotspot** (café Wi-Fi blocks the phone
     from reaching the laptop), find its IPv4 address with `ipconfig`, and in another PowerShell in the
     project folder run `.venv\Scripts\python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`;
     the setting is then `http://<that address>:8000`. Windows may ask whether Python may use the
     network; that is your call (private networks are enough for the hotspot).
2. Restart Metro with the cache cleared: `npx expo start -c`, and open the app in Expo Go. If PowerShell says *running
   scripts is disabled*, use `npx.cmd expo start -c` (the same command, without changing the script policy). If Expo Go says
   the project is *incompatible*, its SDK is newer than the app's: install the matching Expo Go from **expo.dev/go** (Android:
   uninstall the store's copy first, and turn off its auto-update), until the app is upgraded (CX-4).
3. Sign in with an account of its own (`demo-app@example.com`, made like the test users in step 4.4): keep the two test
   users for the security test, which expects them to have no profile. The app shows the sign-up steps; finish them, then add an
   entry and open Money: that is the core flow (13 Dec check).
4. Back to sample data: rename `app\.env` (e.g. to `app\.env.off`) and restart with `npx expo start -c`.

If the app shows "FAST isn't set up yet", one setting is missing or wrong; it names which.

**Tell Claude:** "app live" and what you saw (no keys).

## Optional: the Groq key (5 min, for the assistant's red team)

**console.groq.com** → *API Keys* → *Create API key* → paste it into `.env` as `GROQ_API_KEY` (and into
Render's environment when you want the assistant online). Then run
`.venv\Scripts\python -m tools.assistant_eval.run` (about 10 minutes) and send Claude
`tools/assistant_eval/results/REDTEAM.md`.

---

## After setup: what Claude does next

| Step | Claude |
|---|---|
| Git + GitHub | First commit of the project as it is (the frozen spec and its SHA-256 stay the pre-registration record), push to `fast-fyp`; from then on small commits with clear messages |
| Supabase | Run the live security test; load the personas for a first look (`tools.personas.seed`) |
| Render | Check the online API against Supabase with a test user |
| Node | **Start the app (T-16)**: the Expo project, login, onboarding, add transaction, Money screen, points: the core flow for 13 Dec |

Keep the dated HDD backups (robocopy) going for `data/`, which git doesn't hold; GitHub becomes the
off-laptop copy of everything else.
