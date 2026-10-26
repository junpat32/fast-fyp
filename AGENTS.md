# AGENTS.md: handoff for Codex (FAST, FYP2)

Updated 2026-10-14 by Claude Code for Codex. Read this file, then **`CLAUDE.md`** (the project's
binding rules: they apply to you exactly as to Claude; wherever it says "Claude", read "the AI
agent"), then `docs/TASKS.md` and `docs/app_plan.md`.

## 0. Hard rule: no art

**Patrick's instruction (2026-10-14): Codex does not touch the art.** All art is Claude's,
made in code (D-55, D-84 to D-86); image generation is banned (D-83).

- **Never edit, add, delete, regenerate or "fix"** anything in `tools/asset_generation/`,
  `assets/isometric/`, `tools/asset_generation/previews/` or `docs/assets/`. Don't run the asset
  build. Don't generate, draw, download or trace images of any kind (no image tools, no stock art,
  no icon packs drawn as game art).
- **Read-only use is fine:** the app loads the PNGs and JSON in `assets/isometric/` exactly as they
  are (`manifest.json`, `scenes/*.json`, `characters.json`).
- **If the app needs art that doesn't exist** (app icon, splash screen, badge icons, the skin-tone
  sprite sheets of decision A1, a missing pose): use a plain placeholder (a coloured box or text),
  and add a line to `docs/TASKS.md` under T-22 saying what is needed, for Claude to make.
- If you think a piece looks wrong, write it down for Patrick; don't change it.

## 1. Non-negotiables (summary; CLAUDE.md is the full text)

- **Machine:** Windows 10, 4 GB RAM (often < 1 GB free), PowerShell 5.1, Python 3.14.8 in `.venv`.
  **Never** run Docker, local Supabase, Android Studio or emulators, PyTorch, EasyOCR, JupyterLab.
  Node/Metro is allowed **on its own** (close other heavy tools). The phone runs the app in
  **Expo Go** on the same Wi-Fi. Check `node -v` first; if Node is missing, ask Patrick to install
  the LTS version (don't install system software yourself).
- **Git from D-97** (D-36 lifted 2026-10-17): once Patrick has installed Git and created the private
  GitHub repo (`docs/setup_guide.md`), make small commits with clear messages; never commit `.env`
  or `data/`. Until the first push, and afterwards for `data/`, back up to a new dated folder:
  `robocopy "C:\Users\User\Desktop\FYP 2" "D:\FYP2_backup\<date>_<time>-<what>" /E /XD .venv __pycache__ .pytest_cache .test_tmp node_modules`
  (exit codes 0–7 mean success).
- **Tests:** `.venv\Scripts\python -m pytest -q`: currently **2,591 passed, 4 skipped** (the skipped
  ones are live Supabase tests). Never leave it red. The app (`app/`, D-104): `npm test` (Node's own
  test runner for `src/lib`) and `npm run typecheck`; Node is at `C:\Program Files\nodejs`.
- **CLAUDE.md §5 rules 1–12** (no label leakage, split by user, frozen files in `docs/frozen/`
  (never edit), one thresholds file, DSR ≠ DTI, **no secrets in the repo or the app bundle**
  (`EXPO_PUBLIC_*` is public), RLS everywhere, NUMERIC money, Groq only from the backend and only
  with summaries, redaction on the phone, **synthetic data only**).
- **Human-only (CLAUDE.md §6):** art approval, `[DECISION]` items, real messages/receipts, the FYP
  report text, submitting the ethics application. Propose; Patrick decides.
- **Bookkeeping after significant work:** update `docs/TASKS.md`; append to `docs/ai_use_log.md`
  (Tool column: **Codex**); record design changes in `docs/DECISIONS.md` (next ID: **D-128**).

## 2. How Patrick works

He is the FYP student and decides. Plain language, tables, a clear **verdict** with reasons. When
he asks questions ("any issues?", "where are we?"), **answer only, take no actions**. Put open
questions as a short ID table with a recommended default. Flag problems and uncertainty (< 80%
confident) even when not asked. Malaysian context by default (MYR, BNM, EPF, PTPTN, AKPK, BNPL).

## 3. Your task: T-16, the Expo app (core flow first)

**Start only when Patrick has moved T-16 to NEXT** (or tells you to in his prompt).

**The plan is `docs/app_plan.md`:** screens (in place of wireframes), data flow, how to draw the
home scene from the kit's files, the 9-step build order and decisions **A1–A6**.

- **Week-9 rule:** login → add transaction → band / score / explanation → points must work on the
  phone by **13 Dec 2026**, or the Should tier is dropped. Build steps 1–5 of the plan first.
- **Decisions:** use Patrick's answers to A1–A6. If he hasn't answered, use the defaults only for
  A5 and A6 (app-only, easy to change); don't make the backend changes A2–A4 without his answer.
- **Layout:** the app lives in `app/` (create it with the current Expo template; TypeScript,
  `expo-router`). Metro must reach `../assets/isometric` and `../shared` (set `watchFolders` in
  `metro.config.js`); never copy thresholds or game constants into the app by hand (rule 5:
  `shared/thresholds.json` and `shared/game.json` are the single sources).
- **Backend:** the API exists (`api/main.py`: `/v1/me`, `/v1/assess`, `/v1/future`, `GET /v1/game`,
  `POST /v1/game/actions`, `/v1/study`, `POST /v1/assistant`). Keep the user ID from the token only. API changes get pytest tests
  like `tests/test_api.py` and `tests/test_game_api.py`.
- **Inputs the app must collect:** the T-16 row in `docs/TASKS.md` and `engine/README.md`.
- **Blocked on Patrick:** the Supabase project (run `supabase/migrations/20261014000000_init.sql`,
  2 test users, see `supabase/README.md`), a GitHub repo and a Render account (deploy). Until then
  you can build the skeleton, screens and logic, with login wired to the env variables.

## 4. Where the project stands (14 Oct 2026)

| Area | Status | Key files |
|---|---|---|
| Synthetic data + O2 experiment | Done, **criterion passed** (review: Patrick) | `generator/`, `ml/`, `ml/results/O2_REPORT.md` |
| Risk engine (O1, due 15 Nov) | Built; waiting for Patrick's 5 FYP1 scenarios and advice wording | `engine/`, `shared/thresholds.json` |
| Game (T-14b) | Built, in review | `engine/game.py`, `shared/game.json`, `sim/points_sim.py`, `docs/game_design.md` v1.6 |
| Monte Carlo (T-15) | Done; illustrative range (73.25% synthetic coverage, D-81): say "if recent habits continue" | `sim/monte_carlo.py` |
| Backend (T-13) | Built; deploy waits for GitHub + Render | `api/`, `render.yaml`, `requirements-api.txt` |
| Database (T-12) | Migration written, never run on a real database | `supabase/` |
| Art (T-22) | **Claude's.** 408 pieces; batch 1, room levels 1–5, tier 1–2 plants, avatar 1 approved; the rest waits for Patrick's review | `tools/asset_generation/`, `assets/isometric/` (read-only for you) |
| Ethics (T-21) | Drafts done; Patrick submits by 31 Oct | `docs/ethics/` |
| App (T-16) | **Not started: your task** | `docs/app_plan.md` |

## 5. Open decisions: do NOT implement until Patrick chooses

| ID | Where | Question |
|---|---|---|
| — | (2026-10-15) | I1, A1–A6, E1–E7 are decided (D-88, D-89); T-16 is now Claude's. Art review (AP1/AP2) is Patrick's |

## 6. Caveats

- The SQL migration has never run on a real Postgres (about 85% confident it runs as written);
  `tests/test_rls.py` checks it live once the project exists.
- Dates: 31 Oct ethics submission, 15 Nov O1, **13 Dec O3 (week-9 rule)**, 27 Dec feature freeze,
  30 Dec pilot, 10 Jan O4, 3 Feb report.
