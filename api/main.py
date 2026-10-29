"""FAST API (T-13): FastAPI around the risk engine.

    .venv\\Scripts\\python -m uvicorn api.main:app --reload       # local; needs SUPABASE_URL in .env

Endpoints
  GET  /health            public, for Render's health check
  GET  /v1/me             who the token says you are
  GET  /v1/assess         band, health score, forecast with reasons, advice, from the user's own rows (A2)
  POST /v1/assess         the same for months the caller sends (what-if; tests and persona checks)
  GET  /v1/future         the Future Self: six months of possible cushions (A3, D-79, D-81)
  GET  /v1/card           this week's life-event card; POST /v1/card answers it (G-08, D-117)
  GET  /v1/game           points, levels, garden, plants, animals: replayed from the user's own facts
  POST /v1/game/actions   plant, dig, buy the tree, decorate, choose or add an animal (saved if allowed)
  GET  /v1/study          is this a study persona, and its study date (A4, D-90)
  POST /v1/study/time-travel   a persona's study date a month forward or back (personas only)
  POST /v1/assistant      the money helper: a question about the user's own results, answered by
                          Groq from a summary only, numbers checked (T-17, D-92)
A persona's "today" is its study date everywhere, and its rows after that date are hidden.

Every /v1 endpoint: signed in (api/auth.py), rate limited per user (api/limits.py), body
validated with unknown fields rejected (api/models.py). The user is always the token's.
"""
from __future__ import annotations

import dataclasses
import math
import os
from datetime import date

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine.assess import assess
from engine.features import UserProfile
from engine.game import replay
from engine.state import MonthRecord

from . import assistant as a
from . import cards
from . import game as g
from . import money as m
from .auth import CurrentUser, current_user
from .config import Settings, cors_origins, get_settings
from .limits import RateLimiter
from .models import AssessIn, AssistantIn, CardIn, GameActionIn, TimeTravelIn

_DOCS = os.environ.get("FAST_API_DOCS") == "1"       # S-9 (D-93): the endpoint list is public only when asked
app = FastAPI(title="FAST API", version="0.1.0",
              description="Financial Advisory and Safety Tracker: risk band, health score, forecast, advice.",
              docs_url="/docs" if _DOCS else None, redoc_url="/redoc" if _DOCS else None,
              openapi_url="/openapi.json" if _DOCS else None)


def allow_browsers(api: FastAPI, origins: list[str]) -> None:
    """Let the web study build call the API from a browser (D-151): only the listed addresses, only the
    methods and headers the app sends, no cookies; Retry-After stays readable for the 429 message."""
    if origins:
        api.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type"], expose_headers=["Retry-After"],
                           allow_credentials=False, max_age=600)


allow_browsers(app, cors_origins())

_limiter: RateLimiter | None = None


def get_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(settings.rate_limit_per_minute)
    return _limiter


def signed_in(user: CurrentUser = Depends(current_user), limiter: RateLimiter = Depends(get_limiter)) -> CurrentUser:
    wait = limiter.check(user.id)
    if wait is not None:
        raise HTTPException(status_code=429, detail="too many requests",
                            headers={"Retry-After": str(max(1, math.ceil(wait)))})
    return user


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/me")
def me(user: CurrentUser = Depends(signed_in)) -> dict:
    return {"user_id": user.id}


@app.post("/v1/assess")
def assess_month(body: AssessIn, user: CurrentUser = Depends(signed_in)) -> dict:
    """The latest of the months sent (oldest first), assessed without storing anything: a what-if for
    tests and persona checks. The app uses GET /v1/assess, which reads the user's own rows."""
    profile = UserProfile(**body.profile.model_dump())
    records = [MonthRecord(**m.model_dump()) for m in body.months]
    try:
        return assess(profile, records, next_target=body.next_target)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


# ---------------------------------------------------------------- the game (T-14b, D-76)
_stores: dict[tuple[str, str], g.SupabaseStore] = {}


def get_store(settings: Settings = Depends(get_settings)) -> g.GameStore:
    if not settings.anon_key:
        raise HTTPException(status_code=503, detail="game storage is not configured")
    key = (settings.supabase_url, settings.anon_key)
    if key not in _stores:
        _stores[key] = g.SupabaseStore(*key)
    return _stores[key]


def _facts(store: g.GameStore, user: CurrentUser) -> tuple[g.GameFacts, date]:
    """The user's game facts and their today: a persona's study date (A4, D-90), with nothing after
    it; the real Malaysian date for everyone else."""
    try:
        facts = store.load(user)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None
    if facts.profile is None:
        raise HTTPException(status_code=404, detail="finish sign-up first")
    study = g.study_clock(facts.profile)
    return (g.as_of(facts, study), study) if study else (facts, g.today_my())


def _money_facts(store: g.GameStore, user: CurrentUser) -> tuple[m.MoneyFacts, date]:
    try:
        facts = store.load_money(user)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None
    if facts.profile is None:
        raise HTTPException(status_code=404, detail="finish sign-up first")
    study = g.study_clock(facts.profile)
    return (m.as_of(facts, study), study) if study else (facts, g.today_my())


def _game_facts(store: g.GameStore, user: CurrentUser) -> tuple[g.GameFacts, date]:
    """The game's facts with an assessment for every check-in (S-4, D-93): a month nobody assessed yet
    (the user hadn't opened the Money screen) would otherwise count as Green, so plants wouldn't droop
    in a really bad month (G10), and would droop later, once Money was opened. Missing ones are
    assessed and saved now, each with its own months only (M4); if the save fails they still count."""
    facts, today = _facts(store, user)
    have = {a["month"] for a in facts.assessments}
    if all(c["month"] in have for c in facts.checkins):
        return facts, today
    money, _ = _money_facts(store, user)
    rows = m.missing_assessments(money, today)
    if rows:
        try:
            store.add_assessments(user, rows)
        except httpx.HTTPError:
            pass
    return dataclasses.replace(facts, assessments=facts.assessments + rows), today


def _pending(facts: g.GameFacts) -> set:
    """Check-ins still inside their edit window; a persona's seeded check-ins never are."""
    return set() if g.study_clock(facts.profile) else g.editable_checkin_days(facts, g.now_utc())


def _assessed(facts: m.MoneyFacts, today: date) -> tuple[dict, str, tuple]:
    """The assessment the Money screen shows: up to the latest complete month."""
    profile, records, months = m.assess_inputs(facts, today)
    upto = m.assessed_upto(months)
    return assess(profile, records[:upto]), months[upto - 1]["month"], (profile, records, months)


@app.get("/v1/assess")
def assess_me(user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store)) -> dict:
    """This month so far (and every month since sign-up behind it), from the user's own rows (A2).
    Newly checked-in months' assessments are saved for the game's "really bad month" (M4); if that
    save fails the answer is still returned (it is a cache, and the next request tries again)."""
    facts, today = _money_facts(store, user)
    result, month, (profile, records, months) = _assessed(facts, today)
    rows = m.assessments_to_save(facts, profile, records, months)
    if rows:
        try:
            store.add_assessments(user, rows)
        except httpx.HTTPError:
            pass
    return {**result, "as_of": today.isoformat(), "assessed_month": month, "months": months}


@app.get("/v1/future")
def future(user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store)) -> dict:
    """The Future Self (A3): from the user's complete months and today's game. Labelled "if recent
    habits continue"; never presented as a validated 80% interval (D-81)."""
    facts, today = _money_facts(store, user)
    _, records, months = m.assess_inputs(facts, today)
    game_facts, _ = _game_facts(store, user)
    game_prof, inputs = g.game_inputs(game_facts)
    st = replay(game_prof, today, strict=False, **inputs)
    return {**m.future_view(facts.profile, records, months, st, game_prof, today), "as_of": today.isoformat()}


def _card_answer(store: g.GameStore, user: CurrentUser, today: date) -> dict | None:
    try:
        return store.load_card_answer(user, cards.monday(today))
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None


@app.get("/v1/card")
def card(user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store)) -> dict:
    """This week's life-event card (G-08, D-117): the same event all week, whether the user's money
    now would cover it, and their answer if they gave one."""
    facts, today = _game_facts(store, user)
    prof, inputs = g.game_inputs(facts)
    st = replay(prof, today, strict=False, **inputs)
    return cards.card_view(facts.profile, user.id, today, st.money, _card_answer(store, user, today))


@app.post("/v1/card")
def answer_card(body: CardIn, user: CurrentUser = Depends(signed_in),
                store: g.GameStore = Depends(get_store)) -> dict:
    """Saves the week's answer once (409 after that). The event is the server's own draw, never the
    app's; the card points come through the game's replay (engine/game.py _card)."""
    facts, today = _game_facts(store, user)
    if _card_answer(store, user, today) is not None:
        raise HTTPException(status_code=409, detail="you've already answered this week's card")
    event_id = cards.draw(user.id, cards.monday(today), facts.profile)
    try:
        store.add_card_answer(user, {"event_id": event_id, "response": body.response})
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None
    prof, inputs = g.game_inputs(facts)
    st = replay(prof, today, strict=False, **inputs)
    return cards.card_view(facts.profile, user.id, today, st.money, {"event_id": event_id, "response": body.response})


@app.get("/v1/game")
def game(user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store)) -> dict:
    """The user's whole game, replayed from their own facts up to today (Malaysia time; a persona's
    study date)."""
    facts, today = _game_facts(store, user)
    prof, inputs = g.game_inputs(facts)
    return g.game_view(replay(prof, today, strict=False, **inputs), today, _pending(facts))


@app.post("/v1/game/actions")
def game_action(body: GameActionIn, user: CurrentUser = Depends(signed_in),
                store: g.GameStore = Depends(get_store)) -> dict:
    """Checks the action by replaying with it today; saves it only if the rules allow it (W3).
    409 with a gentle reason otherwise (e.g. "no choice available yet")."""
    facts, today = _game_facts(store, user)
    prof, inputs = g.game_inputs(facts)
    new = g.action_from(body.kind, today, *(body.cell or (None, None)), body.item, body.spot)
    st = replay(prof, today, strict=False, **{**inputs, "actions": inputs["actions"] + [new]})
    why = next((reason for event, reason in st.rejected if event is new), None)
    if why is not None:
        raise HTTPException(status_code=409, detail=why)
    try:
        store.add_action(user, body.row())                          # the database dates it (a persona: study date)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None
    return g.game_view(st, today, _pending(facts))


# ---------------------------------------------------------------- the user study (A4, D-90)
def _study_state(profile: dict) -> dict:
    if not g.study_clock(profile):
        return {"persona": False}
    return {"persona": True, "study_date": profile["study_date"], "first": profile["study_first"],
            "last": profile["study_last"]}


@app.get("/v1/study")
def study(user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store)) -> dict:
    """Whether this account is a study persona, and its study date (the app shows the time-travel
    control only for personas)."""
    facts, _ = _facts(store, user)
    return _study_state(facts.profile)


def _shift_month(d: date, k: int) -> date:
    y, mo = divmod(d.year * 12 + d.month - 1 + k, 12)
    return date(y, mo + 1, 1)


@app.post("/v1/study/time-travel")
def time_travel(body: TimeTravelIn, user: CurrentUser = Depends(signed_in),
                store: g.GameStore = Depends(get_store)) -> dict:
    """Moves a persona's study date a month at a time (or to the start or end of its range). Only a
    persona account can; everyone else gets 403. The database checks the range again."""
    facts, today = _facts(store, user)
    state = _study_state(facts.profile)
    if not state["persona"]:
        raise HTTPException(status_code=403, detail="time travel is only for study personas")
    first, last = date.fromisoformat(state["first"]), date.fromisoformat(state["last"])
    target = {"first": first, "last": last, "next": _shift_month(today, 1),
              "previous": _shift_month(today, -1)}[body.step]
    target = min(max(target, first), last)
    try:
        store.update_profile(user, {"study_date": target.isoformat()})
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="storage unavailable, try again shortly") from None
    return {**state, "study_date": target.isoformat()}


# ---------------------------------------------------------------- the money helper (T-17, D-92)
_llms: dict[tuple[str, str], a.GroqClient] = {}
_daily: RateLimiter | None = None


def get_llm(settings: Settings = Depends(get_settings)) -> a.ChatModel:
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="the assistant is not configured")
    key = (settings.groq_api_key, settings.groq_model)
    if key not in _llms:
        _llms[key] = a.GroqClient(*key)
    return _llms[key]


def get_daily_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _daily
    if _daily is None:
        _daily = RateLimiter(settings.assistant_daily_limit, window=24 * 3600)
    return _daily


@app.post("/v1/assistant")
def assistant(body: AssistantIn, user: CurrentUser = Depends(signed_in), store: g.GameStore = Depends(get_store),
              llm: a.ChatModel = Depends(get_llm), daily: RateLimiter = Depends(get_daily_limiter)) -> dict:
    """A question about the user's own results (a persona's: as of its study date). Groq sees only the
    summary in `shared_with_assistant` and the redacted question (rule 10); neither is stored. Every
    answer is FAST's own words or passed the number check (api/assistant.py AS2)."""
    wait = daily.check(user.id)
    if wait is not None:
        raise HTTPException(status_code=429, detail="that's all the questions for today; try again tomorrow",
                            headers={"Retry-After": str(max(1, math.ceil(wait)))})
    facts, today = _money_facts(store, user)
    result, month, (profile, _, _) = _assessed(facts, today)
    ctx = a.build_context(result, profile.employment_type, month)
    reply = a.answer(body.question, ctx, llm)
    return {**reply.public(), "as_of": today.isoformat(), "assessed_month": month,
            "shared_with_assistant": ctx if reply.sent else None}
