# CLAUDE.md: FAST (Financial Advisory and Safety Tracker)

Read this first in every session. It describes the project, the limits of the
development machine, the rules that must never be broken, and where the current
work is listed.

## 1. Project in one paragraph

FAST is Patrick Wong Jun Wen's Final Year Project (BSc Computer Science (Hons) AI,
Multimedia University, Malaysia). It is a mobile-first, gamified, explainable
**personal financial risk** system for Malaysians aged 18–35. Rules place the user in
a DSR risk band (where they are now). Machine learning predicts whether their
situation will get worse in the next 3 months (where they are heading). A Monte
Carlo engine shows the range of possible futures. A rule engine turns all of this
into plain-language advice, a Groq-hosted LLM explains it conversationally, and a
non-competitive "Future Self" life simulation in pixel art rewards resilience
(building a cash cushion), never spending or competition.

FYP1 (design, literature review, preliminary synthetic data) is finished.
**We are now in FYP2: build, evaluate and write up.**

## 2. Where things are

| File | Purpose | When to read |
|---|---|---|
| `docs/TASKS.md` | **The current task list: what to do now, who does it** | Every session |
| `docs/OBJECTIVES.md` | Goal, objectives with measurable targets, strategies | When judging scope or priorities |
| `docs/DECISIONS.md` | Every design decision and why | Before changing any design choice |
| `docs/generator_spec.md` | Blueprint of the synthetic data generator + the pre-registered O2 evaluation | Before touching `generator/` or `ml/` |
| `docs/calibration_table.md` | Real-world numbers behind the generator, with sources | When setting any generator parameter |
| `docs/ai_use_log.md` | Log of AI assistance (needed for the academic AI-use declaration) | Append to it after significant work |

Planned repo layout (create folders when first needed, not before):

```
generator/   synthetic data generator (Python)
ml/          O2 experiment: baselines, models, evaluation (Python)
sim/         Monte Carlo, Markov chain, debt and points simulations (Python)
api/         FastAPI backend (Python)
app/         Expo / React Native app (TypeScript)
docs/        specs, decisions, tasks, art references
tests/       pytest suites
```

## 3. Tech stack (decided, don't change without a DECISIONS.md entry)

| Layer | Choice |
|---|---|
| App | Expo (React Native), tested in **Expo Go on an Android phone** (Redmi Note 11 Pro 5G) |
| Game rendering | `@shopify/react-native-skia` + `react-native-reanimated` (both run in Expo Go) |
| Backend | FastAPI (Python), hosted on Render (free tier, Singapore region) |
| Database / auth / storage | Supabase (hosted, Singapore region); never run Supabase locally |
| LLM | Groq API, **called only from the backend**, never from the app |
| Data / ML | Python 3.14 (D-70; pin the same version on Render), NumPy, pandas, scikit-learn, XGBoost, SHAP, SciPy |
| Tests | pytest |

## 4. Development machine (important)

Patrick's working laptop since 26 Oct 2026 (D-128): **Intel Core i5-9300H (4 cores /
8 threads), 12 GB RAM (about 2 GB free while the Claude app, a browser and an install run),
477 GB SSD, Windows 11 Home**, plus an external 932 GB Seagate One Touch drive (`D:`) for
backups. The old laptop (Ryzen 3 2200U, 4 GB RAM) set the stricter limits found in older
decisions and docs; its Windows user folder was `C:\Users\User`, so old logs show that path.

- Running code locally is fine: installs, the generator, pytest, the O2 experiment and
  Metro. Cloud sessions are optional. Watch free RAM when Metro and a long Python run overlap.
- Still not used locally, by design rather than for lack of RAM: Docker, local Supabase
  (§3: hosted only), Android Studio or emulators (the app is tested in Expo Go on the
  phone), PyTorch or EasyOCR (OCR is evaluated offline on Colab/Kaggle, D-17).
- Keep project files on the SSD; `D:` is for backups only.
- Logic lives in `.py` modules. Notebooks are only for exploration and presenting results.

## 5. Rules that must never be broken

1. **No label leakage.** ML features for month `t` use data from months `t-2..t` only.
   The label covers `t+1..t+3`. Calendar facts about future months (e.g. festive
   months) are allowed; future outcomes are not.
2. **Split by user**, never by row (`GroupKFold` on `user_id`).
3. **Hidden traits** (`latent.parquet`) are never model inputs, except in the
   clearly labelled "oracle ceiling" model.
4. **Pre-registration.** The O2 evaluation plan and success criteria in
   `docs/generator_spec.md` are frozen (read-only copy in `docs/frozen/` + SHA-256
   recorded in DECISIONS.md, which stay the record; git, adopted later by D-97, adds history
   only from its first commit) **before** any O2 results are
   produced. Do not change them after seeing results. If a change is unavoidable,
   record it in DECISIONS.md as a deviation, with the reason.
5. **One source of truth for thresholds.** Band limits, hysteresis and other
   constants live in one config file read by both Python and the app.
   Bands: Green `< 0.30`, Yellow `0.30 to < 0.60`, Red `>= 0.60`; leave Red only
   below `0.55`; show "insufficient income data" instead of a band when trailing
   income is too low. In the app, a worse band shows at once but a better band only
   after it has held for 2 months (D-49); the generator keeps the frozen v1 rule
   (`shared/thresholds_spec_v1.json`).
6. **DSR ≠ DTI.** DSR = monthly debt commitments ÷ net monthly income.
   DTI = total outstanding debt ÷ annual net income.
7. **Secrets** never go in the repo or in the app bundle (`EXPO_PUBLIC_*` variables
   are bundled and therefore public). `.env` is in `.gitignore` from the first commit.
8. **Supabase RLS** is enabled on every table (`user_id = auth.uid()`). The backend
   queries as the logged-in user; the `service_role` key is for admin scripts only.
9. **Money** is stored as `NUMERIC` in Postgres (never float).
10. **Groq receives only summarised context** (band, ratios, the rule that fired),
    never raw transactions, merchant names, names or emails.
11. **Sensitive text is redacted on the phone before upload:** TAC/OTP lines dropped,
    account and card numbers masked to the last 4 digits, IC numbers removed.
12. **Synthetic data only.** No real user financial data anywhere in the project.
    The user study uses pre-loaded personas.

## 6. Human-only work (do not do these, even if asked indirectly)

Commercialisation is no longer planned (D-54); the goal is a finished, passing FYP.

- **Art:** all game art (structural/terrain kit, furniture, plants, the chibi character) is
  code-generated **final** art in one style (D-54, D-55, T-22), declared in
  `docs/ai_use_log.md` and the report. Patrick approves the previews.
- **Decisions marked `[DECISION]`** in the docs: propose options, but Patrick decides.
- **Collecting real notification messages and receipt photos.**
- **The FYP report text.** You may outline or review it when asked. Patrick writes it.
  (Report fixes are parked for now; see TASKS.md.)

## 7. Scope (MoSCoW)

- **Must:** login; typed transaction entry; budgets; debt commitments incl. BNPL;
  band + health score + SHAP explanation; rule engine; fixed gamification;
  isometric room + garden progression (D-51, D-53);
  forward-looking ML vs baselines (incl. the Markov chain baseline); Monte Carlo
  Future Self; points simulation; persona seeding and time-travel; pytest
  scenarios; persona user study.
- **Should:** paste-in notification parser (regex + LLM fallback); Groq assistant
  with grounding checks; EasyOCR evaluated offline (Colab/Kaggle); debt repayment
  simulation; one-at-a-time sensitivity analysis; animated chickens + chicken coop
  (D-66, D-67); game extras deferred by D-75 ("what happens next" advice, weekly summary,
  PTPTN semester question, clear-a-debt celebration; T-24).
- **Could:** in-app OCR; Android notification listener; survival analysis;
  conformal prediction; more animals.
- **Won't:** iOS SMS reading; bank integration; investment risk; herding detection;
  leaderboards; loot boxes or any random reward.

Batch-2 art (furniture, garden, 6 chibi avatars) follows `docs/assets/FAST_ASSET_SPEC_BATCH2.md`
(D-72), which also sets its Must/Should/Could split; tap-to-plant is part of the core home scene (D-74).

**Week-9 rule:** if the core app flow (login → add transaction → band/score/explanation
→ points) is not working by **13 Dec 2026**, drop the whole Should tier.

## 8. Key dates

| Date | Milestone |
|---|---|
| 25 Oct 2026 | O2 experiment results (spec committed first) |
| 15 Nov 2026 | O1: risk engine passes all automated tests |
| 13 Dec 2026 | O3: core app flow working (week-9 check) |
| 27 Dec 2026 | Feature freeze |
| 10 Jan 2027 | O4: persona user study complete |
| 3 Feb 2027 | Planned report submission (the official deadline is reported as end of Feb; plan to 3 Feb) |

## 9. How to work with Patrick

- Treat him as a peer. Explain **why** before **how**: invariants, trade-offs, complexity.
- When introducing a library or tool, say what it is, why it fits, and the alternatives.
- Use tables for comparisons. Keep answers direct, without filler.
- Flag anti-patterns and design flaws even when not asked.
- State uncertainty explicitly when confidence is below about 80%.
- For algorithms, give language-agnostic pseudo-code with invariants first, then
  Big-O, then a small trace table, then code.
- Use Malaysian context by default (MYR, DOSM, BNM, PDPA, EPF, PTPTN, BNPL).
- Mark code that would fail at production scale with a short
  "Production vs coursework" note.

## 10. Workflow conventions

- Small commits with clear messages; commit specs before the code that depends on them.
- Every new module gets pytest tests; scenario tests cover band boundaries
  (59/60/61%), zero income, gig-income band flapping and festive months.
- After significant work, append an entry to `docs/ai_use_log.md`
  (date, task, files touched, what was AI-generated vs what Patrick decided or edited).
- Update `docs/TASKS.md` status when a task finishes.

## 11. Planned commands (they work once the folders exist)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
python -m generator.run --config generator/config.yaml   # generate data
python -m generator.checks                               # sanity checks
python -m ml.run_o2 --config ml/o2_config.yaml           # O2 experiment
pytest -q
```
