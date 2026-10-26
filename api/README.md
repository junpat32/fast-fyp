# FAST backend (T-13)

FastAPI around the risk engine (`engine.assess`). The app never talks to Groq or holds secrets;
it talks to Supabase (with the user's own token, under Row Level Security) and to this API.

```bash
.venv\Scripts\python -m uvicorn api.main:app --reload
.venv\Scripts\python -m pytest tests/test_api.py -q
```

Local runs need a `.env` (copy `.env.example`; never commit it) with at least `SUPABASE_URL`.

| Endpoint | Auth | What it does |
|---|---|---|
| `GET /health` | public | Render's health check |
| `GET /v1/me` | signed in | the user ID from the token |
| `POST /v1/assess` | signed in | band, health score, forecast with reasons, advice for the latest month of the months sent |
| `GET /v1/game` | signed in | the whole game (points by tier, ledger, choices, room and garden levels, plants, animals, decorations, moods, months), replayed from the user's own facts up to today, Malaysia time (D-76); points from a check-in still open to edits are marked `pending` (D-78) |
| `POST /v1/game/actions` | signed in | plant, dig, buy the tree, decorate, move a decoration, choose or add an animal: saved only if a replay with it succeeds; otherwise 409 with a gentle reason |

## Security model

| Rule | How |
|---|---|
| Signed in | `Authorization: Bearer <Supabase access token>`; signature, expiry, audience `authenticated`, issuer = this project, role `authenticated` all checked (`auth.py`) |
| User from the token only | the user ID is the token's `sub`; request bodies reject unknown fields, so a `user_id` can't be smuggled in (`models.py`) |
| No algorithm confusion | asymmetric tokens (ES256/RS256) only against the project's JWKS; HS256 only against the legacy secret, only if configured |
| Validation | every field typed and bounded: money ≥ 0, months 1–12, 1–36 months per request, unknown fields → 422 |
| Rate limit | per user, sliding window, default 60 requests/minute → 429 with `Retry-After` (`limits.py`) |
| Secrets | only in the environment (Render dashboard / local `.env`); the service-role key is never used here |
| Supabase as the user | the game reads and writes with the anon key + the user's own token, so Row Level Security decides what is visible (`game.py`, W1) |
| No forgeable game state | points and levels are never stored; they are replayed from facts on each request, so there is nothing to write (D-76) |

## Deploy (Render, Singapore, free)

`render.yaml` is a Render Blueprint. Render deploys from GitHub, so this waits until the project is
in a repository (D-36). Set `SUPABASE_URL` in Render's dashboard. Python is pinned to 3.14.8
(D-70); the service installs only `requirements-api.txt`.

**Production vs coursework:** the free tier sleeps after about 15 minutes idle (the first request
then takes ~30–60 s): open the app a minute before each user-study session. The rate limiter is
in memory, right for one instance; several instances would need a shared store (e.g. Redis).

**Production vs coursework:** `/v1/game` replays the user's whole history on every request (about
11 ms for 3 years locally; slower on the free tier's shared CPU), after six Supabase reads made in
parallel. Fine for the study; at scale, cache
each user's state and replay only from the last cached month.

## Next (T-16)

`/v1/assess` is stateless for now (months in the body). Once the app writes real months, the API
builds them from Supabase with the user's own token and caches results in `assessments`, which
`/v1/game` already reads for each month's band, forecast and health tier. Time-travel for the
user study (persona accounts, a chosen "today") comes with T-18.
