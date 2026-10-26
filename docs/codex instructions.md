# Codex instructions (FAST, FYP2)

Written 2026-10-26 by Claude Code for Codex. **Read this whole file before any task**, then `CLAUDE.md` (the
project's binding rules: they apply to you exactly as to Claude; wherever it says "Claude", read "the AI agent"),
then `docs/TASKS.md`, then your task in `docs/codex tasks.md`. Do **only** the task you were given.

## 1. The project in four lines

FAST is Patrick Wong Jun Wen's Final Year Project (BSc Computer Science (Hons) AI, Multimedia University): a
gamified, explainable personal-financial-risk app for young Malaysians. Python backend and research code
(`engine/`, `api/`, `ml/`, `generator/`, `sim/`), an Expo / React Native app (`app/`), synthetic data only.
**Patrick decides; Claude reviews your work before it is merged.** Decisions are recorded in `docs/DECISIONS.md`.

## 2. Hard rules (break one and the work is thrown away)

| Rule | Details |
|---|---|
| **No art, ever** | Never edit, add, delete, regenerate or "fix" anything in `tools/asset_generation/`, `assets/isometric/`, `assets/app/`, `tools/asset_generation/previews/` or `docs/assets/`, and don't run the asset build. No image generation of any kind (D-83). If you think art is needed, write it in your hand-back |
| **Research records are frozen** | Never edit `docs/frozen/`, `ml/results/O2_REPORT.md`, anything under `data/`, or `ml/artifacts/`. Never rerun or change the O2 experiment, the generator's default behaviour, or any analysis in `ml/` or `sim/` unless your task says so. No new experiments: they need a plan written and committed **before** the run (D-132), which is Claude's job |
| **CLAUDE.md §5, rules 1–12** | Especially: no label leakage; synthetic data only; secrets never in the repo or the app bundle (`EXPO_PUBLIC_*` is public); Groq only from the backend and only with summaries; redaction of sensitive text; money as NUMERIC; one source for thresholds (`shared/thresholds.json`) |
| **Never read or print `.env`** | Never paste keys or passwords anywhere. If a task needs a key, stop and say so |
| **Human-only work** | User-facing wording is a **draft** for Patrick (review "W2" in `docs/advice_wording_review.md`): flag it, don't decide it. `[DECISION]` items, art approval and the FYP report text are Patrick's. Never touch `docs/reports/` |
| **Stay inside your task** | Change only the files your task lists under "may change". Anything else you notice goes in your hand-back, not in the code |

## 3. How to work

1. **Git:** create a branch `codex/<task-id>` from `main` (e.g. `codex/cx-1`). Never commit to `main`, never
   push, never rewrite history (no rebase, amend or reset of existing commits). Small commits with clear messages;
   end each message with `Co-Authored-By: Codex <noreply@openai.com>`.
2. **Environment** (Windows 11, PowerShell 5.1; Python 3.14.8 in `.venv`; Node v24):
   - Python tests: `.venv\Scripts\python -m pytest -q` (baseline 2026-10-26: **2,663 passed, 4 skipped**; the 4
     are live Supabase tests). Set `PYTHONUTF8=1` if you pipe output (the console code page can't print "−").
   - App tests (only if your task touches `app/`): in `app/`, `npm test` (150 passing) and `npm run typecheck`.
3. **Style:** match the surrounding code. Python modules start with a docstring that states their invariants;
   tests read as sentences (`test_a_reply_that_promises_an_outcome_is_retried`). Docs use short, plain sentences
   and tables (the house style in `docs/`).
4. **Tests are the definition of done.** Every behaviour you add gets a test; never weaken or skip an existing
   test to make yours pass. The full suite must pass before you hand back.
5. **When unsure, stop.** Write the question in your hand-back rather than guessing. A half-finished task with a
   clear question is better than a guessed one.

## 4. Hand-back (when the task is done, or when you stop)

Add a section under your task in `docs/codex tasks.md`, headed `Hand-back (Codex, <date>)`:

- **Status:** done / partly done / stopped (why).
- **Branch and commits:** the branch name and each commit's short hash and message.
- **Files changed:** each file, one line on what changed.
- **Tests run:** the exact commands and their final counts (Python, and the app's if you touched it).
- **Not done, and questions:** anything left, anything you were unsure of, anything you noticed outside the task.
- **Proposed decision text:** if your work changes a behaviour, a short paragraph Claude can turn into a
  `docs/DECISIONS.md` entry. **Do not edit `docs/DECISIONS.md` yourself.**

Also append one row to the main table of `docs/ai_use_log.md` (Tool column: **Codex**): the date, the task ID,
what you produced, "Claude reviews; Patrick approves", and the files.

## 5. Where things are

| Need | File |
|---|---|
| Binding rules | `CLAUDE.md` |
| Tasks and who does what | `docs/TASKS.md`; your task: `docs/codex tasks.md` |
| Why things are the way they are | `docs/DECISIONS.md` (search the D- number a file mentions) |
| What results may be claimed | `docs/claims_register.md` |
| The money helper (Groq assistant) | `api/assistant.py`, `tests/test_assistant.py`, `tools/assistant_eval/` |
| The risk engine | `engine/` (`engine/README.md`) |
| The app | `app/` (`docs/app_plan.md`) |
