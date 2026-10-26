"""The game over HTTP (T-14b, D-76): what GET /v1/game and POST /v1/game/actions do.

Nothing about the game is stored. Each request reads the user's own facts from Supabase AS THE
USER (their token, under Row Level Security; CLAUDE.md rule 8), replays them through
engine/game.py up to today (Malaysia time) and returns the state. An action is checked by
replaying with it first and saved only if the rules allow it; any invalid row that reaches the
database another way is skipped by the replay and listed (C4).

Invariants
  W1  every read and write uses the user's own token; the service-role key is never used
  W2  database rows -> engine inputs is a pure function (game_inputs), tested without a database
  W3  an action is saved only if the replay accepts it today
  W4  points a check-in earned are shown as pending while it can still be edited (48 hours)
Cost: one replay per request, O(days + events): about 11 ms for 3 years on the dev laptop, plus
the six Supabase reads, made in parallel.
Production vs coursework: fine for a study; at scale, cache each user's state and replay only from
the last cached month.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import httpx

from engine.game import (Action, AddAnimal, BuyTree, CardAnswer, CheckIn, ChooseAnimal, DayActivity, Decorate, Dig,
                         GameProfile, GameState, GoalChange, MoveDecoration, Plant, load_game)

from .auth import CurrentUser

MYT = timezone(timedelta(hours=load_game()["day_starts_utc_offset_hours"]))
EDIT_WINDOW = timedelta(hours=load_game()["edit_window_hours"])
NOT_FROM_CHECKINS = ("welcome", "card", "streak")             # awards a check-in edit can't change


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_my() -> date:
    return now_utc().astimezone(MYT).date()


def my_day(ts: str) -> date:
    """A database timestamp (UTC) as a Malaysian calendar day."""
    return datetime.fromisoformat(ts).astimezone(MYT).date()


def _money(x) -> float:
    return 0.0 if x is None else float(x)


@dataclass
class GameFacts:
    """Everything the game needs about one user, as rows from Supabase."""
    profile: dict | None
    checkins: list[dict] = field(default_factory=list)
    days: list[dict] = field(default_factory=list)            # the game_days view
    goal_changes: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    assessments: list[dict] = field(default_factory=list)


def study_clock(profile: dict | None) -> date | None:
    """A user-study persona's simulated today (A4, D-90): its study date. None for everyone else."""
    if profile and profile.get("is_persona") and profile.get("study_date"):
        return date.fromisoformat(profile["study_date"])
    return None


def as_of(f: GameFacts, today: date) -> GameFacts:
    """Only what had happened by `today`: a persona's rows for later months are seeded already, and
    time travel shows them as its study date reaches them."""
    return GameFacts(profile=f.profile,
                     checkins=[c for c in f.checkins if my_day(c["created_at"]) <= today],
                     days=[d for d in f.days if date.fromisoformat(d["day"]) <= today],
                     goal_changes=[c for c in f.goal_changes if my_day(c["created_at"]) <= today],
                     actions=[a for a in f.actions if my_day(a["created_at"]) <= today],
                     assessments=[a for a in f.assessments if date.fromisoformat(a["month"]) <= today])


class GameStore(Protocol):
    def load(self, user: CurrentUser) -> GameFacts: ...
    def update_profile(self, user: CurrentUser, fields: dict) -> None: ...
    def add_action(self, user: CurrentUser, row: dict) -> None: ...
    def load_money(self, user: CurrentUser): ...                  # -> api.money.MoneyFacts
    def add_assessments(self, user: CurrentUser, rows: list[dict]) -> None: ...
    def load_card_answer(self, user: CurrentUser, week: date) -> dict | None: ...    # the week's card answer
    def add_card_answer(self, user: CurrentUser, row: dict) -> None: ...


# ---------------------------------------------------------------- rows -> engine inputs (W2)
def action_from(kind: str, day: date, gx: int | None = None, gy: int | None = None, item: str | None = None,
                spot: str | None = None) -> Action:
    if kind == "plant":
        return Plant(day, (gx, gy), item)
    if kind == "dig":
        return Dig(day, (gx, gy))
    if kind == "buy_tree":
        return BuyTree(day)
    if kind == "decorate":
        return Decorate(day, item, spot)
    if kind == "move_decoration":
        return MoveDecoration(day, item, spot)
    if kind == "choose_animal":
        return ChooseAnimal(day, item)
    if kind == "add_animal":
        return AddAnimal(day, item)
    raise ValueError(f"unknown action: {kind}")


def _profile(p: dict) -> GameProfile:
    snap = p.get("game_employment_type") is not None              # the game's copy of the sign-up situation
    costs = p["game_typical_costs"] if snap else p.get("typical_monthly_costs")
    return GameProfile(
        start=my_day(p["created_at"]),
        employment_type=p["game_employment_type"] if snap else p["employment_type"],
        declared_income=_money(p["declared_income"]),
        onboarding_money=_money(p["onboarding_counted_money"]),
        onboarding_debt=_money(p.get("onboarding_debt")),
        onboarding_other_money=_money(p.get("onboarding_other_money")),
        typical_monthly_costs=None if costs is None else float(costs),
        lives_with_parents=bool(p["game_lives_with_parents"] if snap else p.get("lives_with_parents")),
        savings_goal=None if p.get("savings_goal_monthly") is None else float(p["savings_goal_monthly"]),
        savings_goal_share=None if p.get("savings_goal_share") is None else float(p["savings_goal_share"]))


def _checkin(c: dict, assessed: dict | None) -> CheckIn:
    """Money and debt as at the END of the month (D-77): the balances given at the check-in, minus
    what was logged after the month ended (the database works that out when the check-in is made)."""
    a = assessed or {}
    fc, health = a.get("forecast") or {}, a.get("health") or {}
    cash_at_month_end = max(0.0, _money(c["cash_bank_ewallet"]) - _money(c.get("after_month_net")))
    return CheckIn(
        month=date.fromisoformat(c["month"]), on=my_day(c["created_at"]),
        counted_money=cash_at_month_end + _money(c.get("epf_fleksibel")) + _money(c.get("others_emergency")),
        other_money=_money(c.get("others")),
        total_debt=max(0.0, _money(c["debt_total"]) - _money(c.get("after_month_debt"))),
        bills_on_time=bool(c["bills_paid_on_time"]),
        logged_in=_money(c.get("logged_in")), logged_out=_money(c.get("logged_out")),
        logged_costs=_money(c.get("logged_costs")), logged_debt_paid=_money(c.get("logged_debt_paid")),
        epf_voluntary=_money(c.get("epf_voluntary")),
        epf_compulsory_to_fleksibel=_money(c.get("epf_compulsory_to_fleksibel")),
        net_income=None if c.get("net_income") is None else float(c["net_income"]),
        band=a.get("band", "GREEN"), shortfall=bool(c.get("ran_short")),
        forecast_probability=fc.get("probability"), forecast_base_rate=fc.get("base_rate"),
        health_tier=health.get("tier"))


def game_inputs(f: GameFacts) -> tuple[GameProfile, dict]:
    """The user's rows as engine.game.replay arguments."""
    assessed = {a["month"]: a.get("result") for a in f.assessments}
    days = [date.fromisoformat(d["day"]) for d in f.days]
    return _profile(f.profile), dict(
        days=[DayActivity(day, int(d.get("entries") or 0), bool(d.get("no_spend"))) for day, d in zip(days, f.days)],
        cards=[CardAnswer(day) for day, d in zip(days, f.days) if d.get("card")],
        checkins=[_checkin(c, assessed.get(c["month"])) for c in f.checkins],
        goal_changes=[GoalChange(my_day(g["created_at"]), None if g.get("amount") is None else float(g["amount"]),
                                 None if g.get("share") is None else float(g["share"])) for g in f.goal_changes],
        actions=[action_from(a["kind"], my_day(a["created_at"]), a.get("gx"), a.get("gy"), a.get("item"), a.get("spot"))
                 for a in sorted(f.actions, key=lambda a: a["created_at"])])


def editable_checkin_days(f: GameFacts, now: datetime) -> set[date]:
    """Days of check-ins still inside their 48-hour edit window: what they earned may still change."""
    return {my_day(c["created_at"]) for c in f.checkins if now - datetime.fromisoformat(c["created_at"]) < EDIT_WINDOW}


# ---------------------------------------------------------------- engine state -> JSON
def game_view(st: GameState, today: date, pending_days: set[date] = frozenset()) -> dict:
    """The game as JSON. Points awarded by a check-in that can still be edited are marked pending
    (an edit could lower them), so the app never shows points going down (G2)."""
    def when(e) -> str | None:
        d = getattr(e, "day", None) or getattr(e, "on", None)
        return d.isoformat() if d else None

    def pending(a) -> bool:
        return a.day in pending_days and a.kind not in NOT_FROM_CHECKINS

    return {
        "as_of": today.isoformat(),
        "points": st.points, "points_pending": sum(a.points for a in st.ledger if pending(a)),
        "points_by_tier": st.points_by_tier(),
        "choices": {"earned": st.choices_earned, "used": st.choices_used, "available": st.choices_available},
        "streak": {"current": st.streak, "best": st.best_streak},
        "badges": sorted(st.badges), "milestones": sorted(st.milestones, key=float),
        "room_level": st.room_level,
        "garden": {"open": st.garden_open, "level": st.garden_level, "qualifying_months": st.qualifying_months,
                   "bed_step": st.bed_step, "bed": sorted([list(c) for c in st.bed()]), "plant_tier": st.plant_tier,
                   "animal_slots": st.animal_slots, "animal_slots_used": st.animal_slots_used},
        "plants": [{"cell": list(c), "plant": g.kind, "stage": st.plant_stage(g), "growing_days": g.growing_days}
                   for c, g in sorted(st.plants.items())],
        "seed_box": [g.kind for g in st.seed_box],
        "tree": None if st.tree is None else {"stage": st.tree_stage()},
        "decorations": dict(st.decorations), "animals": dict(st.animals),
        "look": {"mood": st.mood, "plants": st.plant_look, "suggest_akpk": st.suggest_akpk,
                 "coin_jar": st.coin_jar, "savings_plant": st.savings_plant_stage},
        "game_cushion": round(st.game_cushion or 0.0, 2),
        "months": [{"month": m.month.isoformat(), "verified": m.verified, "saving": round(m.saving, 2),
                    "progress": round(m.progress, 2), "goal": round(m.goal, 2), "goal_met": m.goal_met,
                    "cushion": round(m.cushion, 2), "qualifying": m.qualifying} for m in st.months],
        "ledger": [{"day": a.day.isoformat(), "kind": a.kind, "points": a.points, "ref": a.ref, "pending": pending(a)}
                   for a in st.ledger],
        "skipped": [{"what": type(e).__name__, "day": when(e), "why": why} for e, why in st.rejected],
    }


# ---------------------------------------------------------------- Supabase, as the user (W1)
class SupabaseStore:
    """Reads and writes through Supabase's REST API with the anon key + the user's own token, so
    Row Level Security decides what is visible (rule 8). Pages through long tables."""
    PAGE = 1000                                                    # Supabase's default row limit

    def __init__(self, url: str, anon_key: str, transport: httpx.BaseTransport | None = None):
        self._anon = anon_key
        self._http = httpx.Client(base_url=f"{url.rstrip('/')}/rest/v1", timeout=20, transport=transport)

    def _headers(self, user: CurrentUser) -> dict:
        return {"apikey": self._anon, "Authorization": f"Bearer {user.token}"}

    def _select(self, user: CurrentUser, table: str, order: str) -> list[dict]:
        rows, offset = [], 0
        while True:
            r = self._http.get(f"/{table}", headers=self._headers(user), params={
                "select": "*", "user_id": f"eq.{user.id}", "order": order, "limit": self.PAGE, "offset": offset})
            r.raise_for_status()
            page = r.json()
            rows += page
            if len(page) < self.PAGE:
                return rows
            offset += self.PAGE

    TABLES = (("profiles", "user_id"), ("monthly_checkins", "month"), ("game_days", "day"),
              ("goal_changes", "created_at"), ("game_actions", "created_at"), ("assessments", "month"))

    def load(self, user: CurrentUser) -> GameFacts:
        """The six reads run at the same time (one round trip instead of six on the free tier)."""
        with ThreadPoolExecutor(max_workers=len(self.TABLES)) as pool:
            jobs = {table: pool.submit(self._select, user, table, order) for table, order in self.TABLES}
            rows = {table: job.result() for table, job in jobs.items()}
        if not rows["profiles"]:
            return GameFacts(profile=None)
        return GameFacts(profile=rows["profiles"][0], checkins=rows["monthly_checkins"], days=rows["game_days"],
                         goal_changes=rows["goal_changes"], actions=rows["game_actions"],
                         assessments=rows["assessments"])

    def add_action(self, user: CurrentUser, row: dict) -> None:
        r = self._http.post("/game_actions", headers={**self._headers(user), "Prefer": "return=minimal"}, json=row)
        r.raise_for_status()

    def update_profile(self, user: CurrentUser, fields: dict) -> None:
        """Changes the user's own profile row (time travel moves a persona's study date; the
        database lets only a persona do that, within its range)."""
        r = self._http.patch("/profiles", headers={**self._headers(user), "Prefer": "return=minimal"},
                             params={"user_id": f"eq.{user.id}"}, json=fields)
        r.raise_for_status()

    MONEY_TABLES = (("profiles", "user_id"), ("transactions", "occurred_on"), ("debts", "created_at"),
                    ("monthly_checkins", "month"), ("goal_changes", "created_at"), ("assessments", "month"))

    def load_money(self, user: CurrentUser):
        """The assessment's six reads, in parallel (A2)."""
        from .money import MoneyFacts
        with ThreadPoolExecutor(max_workers=len(self.MONEY_TABLES)) as pool:
            jobs = {table: pool.submit(self._select, user, table, order) for table, order in self.MONEY_TABLES}
            rows = {table: job.result() for table, job in jobs.items()}
        if not rows["profiles"]:
            return MoneyFacts(profile=None)
        return MoneyFacts(profile=rows["profiles"][0], transactions=rows["transactions"], debts=rows["debts"],
                          checkins=rows["monthly_checkins"], goal_changes=rows["goal_changes"],
                          assessments=rows["assessments"])

    def load_card_answer(self, user: CurrentUser, week: date) -> dict | None:
        """This week's answer to the life-event card, if any (D-117; one per week, the table's unique key)."""
        r = self._http.get("/life_event_answers", headers=self._headers(user), params={
            "select": "event_id,response,week", "user_id": f"eq.{user.id}", "week": f"eq.{week.isoformat()}"})
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    def add_card_answer(self, user: CurrentUser, row: dict) -> None:
        """The database dates it to the user's week (set_card_week: a persona's study date)."""
        r = self._http.post("/life_event_answers", headers={**self._headers(user), "Prefer": "return=minimal"}, json=row)
        r.raise_for_status()

    def add_assessments(self, user: CurrentUser, rows: list[dict]) -> None:
        """Saves checked-in months' assessments; one already saved is kept (M4: ignore duplicates)."""
        r = self._http.post("/assessments", headers={**self._headers(user),
                                                     "Prefer": "resolution=ignore-duplicates,return=minimal"},
                            params={"on_conflict": "user_id,month"}, json=rows)
        r.raise_for_status()
