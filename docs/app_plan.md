# App plan (T-16): screens, data flow, build order

**Status:** accepted by Patrick in place of drawn wireframes (T-08, 2026-10-15). Decisions
**[A1]–[A6]** are made (§7, D-88). T-16 is in NEXT, built by Claude; it starts once Node LTS is
installed on the laptop.

## 1. Goal and the week-9 rule

The **core flow** must work on the Redmi in Expo Go by **13 Dec 2026**:
login → add a transaction → band / health score / explanation → points.
If it doesn't, the whole Should tier is dropped (CLAUDE.md §7). So the build order (§6) puts the
core flow first and the home scene second.

## 2. Stack (decided; CLAUDE.md §3)

| Need | Choice | Why |
|---|---|---|
| App | Expo (React Native) + TypeScript, tested in Expo Go | Decided; no Android Studio on the 4 GB laptop |
| Navigation | `expo-router` (file-based routes) | Standard for Expo; screens = files, easy to follow |
| Auth + data | `@supabase/supabase-js`, session in AsyncStorage | Supabase's documented Expo setup; RLS protects every table |
| Server data | TanStack Query | Caching, refetch after a change, loading/error states for free |
| Game scene | `@shopify/react-native-skia` + `react-native-reanimated` | Decided; both run in Expo Go |
| Tests | **Node's built-in test runner** for pure logic in `app/src/lib` (placement maths, draw order, time of day; D-104: no jest download on the 4 GB laptop); `jest-expo` only if component tests are needed later | Python keeps pytest |

**Secrets (rule 7):** the app holds only `EXPO_PUBLIC_SUPABASE_URL`, the publishable (anon) key
(public by design; RLS is the protection) and the API's base URL. Groq is called only by the
backend (rule 10).

**Laptop:** run Metro on its own (no other heavy tools open); phone and laptop on the same Wi-Fi.

## 3. Screens (in place of the T-08 wireframes)

Navigation **[A5]** (default): 4 tabs: **Home** · **Money** · **Add (+)** · **Future**; a **More**
item in the header (budgets, debts, profile, privacy, sign out).

| Screen | What it shows (top to bottom) | Data |
|---|---|---|
| **Login** | FAST logo, email + password, "Sign in", "Create account" | Supabase Auth |
| **Onboarding** (5 short steps) | 1 income type (employee / gig / student) and net monthly income · 2 typical monthly costs (or "not sure") · 3 vehicle, lives with parents, sends money to family (+ amount), festival celebrated, semester months (students) · 4 debts incl. BNPL (type, balance, monthly payment) and money sections · 5 savings goal (employee amount, gig share, student amount); then choose avatar, skin tone, glasses | Supabase inserts (`profiles`, `debts`, `goal_changes`); asked, never inferred (D-35, D-42) |
| **Home** | The isometric room and garden filling the screen; the avatar walking, sitting or asleep (night); a small top bar: points, choices to spend, band chip; tap objects: budget board → Budgets, coin jar → Savings, savings plant → Savings history, shelf → assistant ([A6]); tap a bed cell → pick a plant; "Place decoration" highlights 2–3 spots | `GET /v1/game`, `POST /v1/game/actions`, `assets/isometric/*` |
| **Money** (dashboard) | Band card (Green / Yellow / Red, or "insufficient income data"), health score with its 4 indicators, the 3-month forecast with up to 3 reasons (the explanation: each reason's `text` under "What raises your risk" or "What keeps your risk low" by its `direction`, D-92; or `forecast_note` when there is none), the top advice items, labelled with `assessed_month` (the latest complete month); this month's entries are listed on the Add screen (D-112) | `GET /v1/assess` (built, A2) + `transactions` |
| **Add (+)** | Amount (RM), in/out, category, date, note; for purchases "Paid with" (cash, bank or e-wallet / credit card = bought on credit / BNPL) and "unexpected"; debt payments and own transfers are categories (D-112); "Save"; a "No spending today" button; this month's list (fix or delete for 48 hours). Categories: `shared/categories.json` (the API reads `family`, `education`, `fees`) | Supabase insert, then refresh game + assess |
| **Future** | "You now" vs "You in 6 months": two avatars (the future one never concerned, D-12), the range of possible savings in months of costs (P10–P90), labelled "if recent habits continue" (D-81); a life-event card when one is due. **No percentage here** (F1, D-100): the only chance shown in the app is the Money screen's forecast, so two similar-sounding numbers can't be confused; the API's `shortfall_probability` stays for analysis but isn't displayed | `GET /v1/future` (built, A3) |
| **Monthly check-in** | Opens on the month's last day for 7 days (D-77): money sections, total owed, bills on time, "ran short this month?"; shows the month-end figures the server works out; "Verified ✓" when the month adds up | Supabase insert `monthly_checkins` + `GET /v1/game` |
| **Budgets / Debts** | List + edit per category; debts with balance, monthly payment and an optional interest rate; "Which to pay off first?" (highest rate first against smallest balance first, from the typed rates only, D-144) | Supabase |

### What the user study needs on screen (D-95)

The comprehension questions (`docs/ethics/04_questionnaire.md` Part B) and the session's six tasks
(`docs/ethics/06_session_script.md` §4b) only work if these are visible without anyone explaining
them. Each is a build requirement for steps 4–7:

| Question / task | Must be on screen | Where | Data |
|---|---|---|---|
| B1, task 1 | The band, in words and colour | Money: Band tile | `band` |
| B2 | Debt payments as a share of income, e.g. "Debt payments take 59% of income" | Money: Band tile ("N% of income to debts") | `dsr` |
| B3 | How the band changes: "A worse band shows at once; a better one after 2 months in a row" | Money: the Band tile's ⓘ (D-108); plus R03/R13 advice when it applies | `shared/thresholds.json` |
| B4, task 2 | The forecast as a chance: "8 out of 100 people like this…" next to the % | Money: Next 3 months tile ("N in 100", verdict under it, D-109); `red_note` and the base rate under its ⓘ | `forecast.probability`, `red_note` |
| B5, task 2 | The reasons under "What raises your risk" / "What keeps your risk low" | Money: "Why N in 100?" (top reason shown, "+N more") | `forecast.reasons[].text`, `direction` |
| B6, task 4 | The range (P10–P90) and "if recent habits continue"; no percentage (F1) | Future: the "If recent habits continue" card (sentence + chart; "Why a range?" one tap away, D-110) | `GET /v1/future` |
| B7, task 5 | "Your money covers about 1.0 months of costs" | Money: Cushion tile (verdict under it: goal / ✓ first goal, D-109) | `cushion_months` |
| B8, task 6 | What grows the garden: "Your garden grows when you meet your saving goal or keep a cushion, month after month" | Home: tapping the garden or savings plant opens a short card | `shared/game.json` |
| B9, task 3 | The top advice item first, as its short line | Money: Your next step ("Read more" for the full text) | `advice[0].short` |
| Task 7 (first persona): record "RM12 on lunch today", find it, fix a typo | The Add screen's date defaults to the persona's today (the server's `as_of`); the entry shows in this month's list; tapping it allows edit or delete within 48 hours **by the same clock** (the database allows it for personas, S-10) | Add (+): the "This month" list under the form (D-112) | `transactions` |

## 4. Data flow

```
Phone (Expo)  ── Supabase Auth ──►  session (JWT)
   │  reads/writes own rows with the user's token (RLS: user_id = auth.uid())
   ├──────────────► Supabase Postgres (transactions, debts, budgets, check-ins, game actions)
   │
   └── JWT ──► FastAPI on Render ── user's own token ──► Supabase (reads the user's facts)
                 GET  /v1/game          the game replayed up to today (D-76)
                 POST /v1/game/actions  taps: plant, place decoration, no-spend day
                 GET  /v1/assess        band, health, forecast + reasons, advice (built, A2)
                 GET  /v1/future        Monte Carlo six-month range (built, A3)
                 POST /v1/assistant     the money helper: Groq sees a summary only (built, D-92)
```

After any write, invalidate the `game` and `assess` queries so the screens refresh.

## 5. Drawing the home scene

All layout data already exists (T-22); the app only follows it:

| File | Use |
|---|---|
| `assets/isometric/manifest.json` | Every piece: file per time of day, canvas, footprint origin, cells |
| `scenes/home_g0..4.json` | Garden ground, structures in drawing order, animal homes, tree spot, free decoration cells |
| `scenes/room.json` | Furniture per room level with layers, decorations and their spots, interactive pieces |
| `characters.json` | Avatar frames (view, head offset for glasses), 6 skin tones |

- **Placement:** each piece at `map_origin + ((gx − gy) × 32, (gx + gy) × 16) − footprint_origin`.
- **Order:** ground → rugs → structures sorted by front cell + layer (room.json explains it).
- **Time of day:** morning 06:00–11:59, afternoon 12:00–18:59, night 19:00–05:59: load that set of PNGs.
- **View:** fitted to the screen width at 2×, pinch to 3× and drag (D-60).
- **Taps:** convert the touch point to a cell (inverse of the placement formula), then check the
  pieces on that cell from the front back.
- **Skin tones (A1: a colour-swap shader, Patrick 2026-10-15):** a small Skia runtime shader
  (SkSL, `RuntimeEffect`) replaces the 3 skin colours of the drawn tone with the chosen tone's
  colours for the current time of day (`characters.json` → `skin_tones`). Exact matching is safe:
  every kit pixel is an exact palette colour, with no anti-aliasing. One set of PNGs serves all 6
  tones. Fallback if the shader misbehaves in Expo Go: the kit can export sprite sheets per tone.
  **Built (D-125)** as a character sheet recoloured on the phone from the atlas's pixels (not a GPU
  shader): the same exact swap, plus the glasses, checked pixel for pixel against the kit.
- **Draw order:** sort by front cell plus layer, then `depth_sort` (a piece wholly behind another
  along gx or gy goes first; D-88, the fix for the sofa drawn over the coffee table).

**Production vs coursework:** loading ~400 separate PNGs is fine for the study; a production app
would pack them into texture atlases.

**App icon, splash, badges** (D-91; `assets/app/`, made by `tools/asset_generation/app_icons.py`):
`app.json` → `"icon": "../assets/app/icon.png"`, `"android": {"adaptiveIcon": {"foregroundImage":
"../assets/app/adaptive-icon.png", "backgroundColor": "#E8DFC9"}}`, splash image
`../assets/app/splash.png` on `#E8DFC9`, web favicon `favicon.png`. Badges: the same medals as app
sprites (D-127), `badge_<name>` when earned, `badge_<name>_locked` before, `badge_<name>_small` in the
Home points pill (names as in `shared/game.json` "badges").

**Privacy and scam-safety screens:** the texts in `docs/privacy_texts.md` (D-91), shown at sign-up
and from More.

**Security notes for the build** (D-93, `docs/security_review.md` §4): More → Delete account calls
`supabase.rpc("delete_my_account")` then signs out; for persona accounts hide change password, change
email and delete account; redact on the phone with the same rules as `api/assistant.py` `redact()`;
show the forecast's `red_note` under the forecast when present (W3).

## 6. Build order (each step ends with something that runs on the phone)

| # | Step | Target |
|---|---|---|
| 1 | Expo project in `app/`, routes and tabs, Supabase login. **Login built (D-145)**: live mode from `app/.env`, tested with fakes; first real sign-in once the project exists (setup guide step 6) | early Nov |
| 2 | Onboarding (minimal fields first). **Built (D-124)** in sample mode; saving to Supabase joins with login | mid Nov |
| 3 | Add transaction + this month's list | mid Nov |
| 4 | Money screen from `/v1/assess`: band, score, explanation | late Nov |
| 5 | Points and "Verified ✓" from `/v1/game` → **core flow done** | **by 13 Dec (week 9)** |
| 6 | Home scene: room by level, avatar animation, night sleep, taps | Dec |
| 7 | Check-in, budgets, debts, Future screen, life-event card. **Built** (D-110, D-117, D-118, D-121) | Dec |
| 8 | Plant in bed cells, place decorations, avatar select. **Built:** planting (D-115), decorations, the tree and chickens (D-120); avatar select waits for onboarding | Dec |
| 9 | The study mode (A4; backend **built**, D-90): when `GET /v1/study` says `persona: true`, show the persona's date at the top and a time-travel bar (back / next month / start), calling `POST /v1/study/time-travel`; use the server's `as_of` as "today" everywhere (default dates, the time of day for the scene). Plus a shareable study build for online sessions (E1: participants open it in Expo Go on their own phones, e.g. through an EAS Update link). **Per-participant accounts (D-94):** each participant signs in to five accounts in one session (an empty one for the sign-up task, then a copy of each persona), so in the study build put **"Switch account"** (sign out and back to the login screen) in the study bar, not only under More. The sign-up task uses the normal onboarding (step 2) on the empty account, so onboarding must be finished and stable by the pilot; check its wording against `docs/study/onboarding_card.md`. **Built (D-119):** the study bar on every tab (persona, date, ‹ ›) and time travel in sample data mode; left for when login exists: show it from `GET /v1/study`, "Switch account" in it, and the shareable build | before 27 Dec freeze |

## 7. Decisions (made by Patrick, 2026-10-15, D-88)

| ID | Question | Decision |
|---|---|---|
| A1 | Skin tones: sprite sheets from the kit, or a runtime shader? | **Colour-swap shader** in the app (§5) |
| A2 | `/v1/assess` reads the user's months from Supabase on the server (like `/v1/game`) | **Yes; built** (`GET /v1/assess`, `api/money.py`) |
| A3 | `GET /v1/future` returning the Monte Carlo range for the Future screen | **Yes; built** |
| A4 | Personas + time travel: persona accounts seeded by an admin script (service_role, admin only); a "study date" stored on those accounts only, which the server uses as "today" | **Yes, persona accounts only, never normal users** (to build in step 9) |
| A5 | Navigation: 4 tabs + More | **Yes** |
| A6 | Before the Groq assistant exists (T-17, Should), the shelf opens a "coming soon" card | **Yes.** The backend exists now (D-92): the shelf opens a chat card calling `POST /v1/assistant` (question ≤ 500 characters, redacted on the phone first, rule 11); on 503 it shows the "coming soon" card. Show `answer`; a "What the AI saw" link shows `shared_with_assistant`; under the box: "Don't type names, card or IC numbers." **Built (D-123)**, also opened from the Money screen; the crisis reply shows on the phone too |

## 8. What has to exist before step 1

| Need | Who |
|---|---|
| Supabase project, migration run, 2 test users (`supabase/README.md`) | Patrick |
| GitHub repo (also needed for Render) and Render account | Patrick |
| API deployed to Render (Starter plan during the study, about RM60 for Dec–Jan: P1) | Claude, once the accounts exist |
| **Node LTS installed on the laptop** (not there yet, checked 2026-10-15) | Patrick |
