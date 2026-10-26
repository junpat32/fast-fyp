"""T-14b server side (D-76): /v1/game replays the user's own facts; /v1/game/actions saves an action
only if the rules allow it; Supabase is always called as the user. Nothing contacts Supabase: the
store is faked, and the real store is tested against a mock transport."""
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

import api.auth as auth
import api.game as g
from api.config import Settings, get_settings
from api.limits import RateLimiter
from api.main import app, get_limiter, get_store
from engine.game import (CardAnswer, CheckIn, DayActivity, Decorate, GameProfile, Plant, bed_cells, load_game,
                         replay)
from test_api import SETTINGS, USER, FakeJWKS, bearer, token

TODAY = date(2026, 6, 10)


def profile_row(**over) -> dict:
    row = {"user_id": USER, "employment_type": "employee", "lives_with_parents": False, "typical_monthly_costs": 2400,
           "declared_income": 3000, "onboarding_counted_money": 0, "onboarding_other_money": 0, "onboarding_debt": 0,
           "savings_goal_monthly": None, "savings_goal_share": None, "game_employment_type": "employee",
           "game_lives_with_parents": False, "game_typical_costs": 2400, "created_at": "2026-01-01T02:00:00+00:00"}
    return {**row, **over}


def month_end(k: int) -> date:
    return date(2026, k + 1, 1) - timedelta(days=1)


def checkin_row(k: int, **over) -> dict:
    """Month k of 2026: saved RM300 more, logged honestly, checked in on its last day."""
    row = {"month": f"2026-{k:02d}-01", "created_at": f"{month_end(k).isoformat()}T04:00:00+00:00",
           "cash_bank_ewallet": 300 * k, "epf_fleksibel": 0, "others_emergency": 0, "others": 0, "debt_total": 0,
           "bills_paid_on_time": True, "ran_short": False, "logged_in": 3000, "logged_out": 2700,
           "logged_costs": 2400, "logged_debt_paid": 0, "epf_voluntary": 0, "epf_compulsory_to_fleksibel": 0,
           "net_income": 3000, "after_month_net": 0, "after_month_debt": 0}
    return {**row, **over}


def day_rows(start=date(2026, 1, 1), end=TODAY) -> list[dict]:
    out, d = [], start
    while d <= end:
        out.append({"day": d.isoformat(), "entries": 2, "no_spend": False, "card": d.weekday() == 0})
        d += timedelta(days=1)
    return out


def facts(months=5, **over) -> g.GameFacts:
    base = dict(profile=profile_row(), checkins=[checkin_row(k) for k in range(1, months + 1)], days=day_rows())
    return g.GameFacts(**{**base, **over})


class FakeStore:
    def __init__(self, f: g.GameFacts):
        self.f, self.saved, self.assessed = f, [], []

    def load(self, user):
        assert user.id == USER                                      # only ever the token's user
        saved = [{**r, "created_at": f"{TODAY.isoformat()}T03:00:00+00:00"} for r in self.saved]
        return g.GameFacts(**{**self.f.__dict__, "actions": self.f.actions + saved,
                              "assessments": self.f.assessments + self.assessed})

    def add_action(self, user, row):
        self.saved.append(row)

    def load_money(self, user):
        """The same user's money rows (no entries logged here): what /v1/game needs to assess check-ins
        that have no saved assessment yet (S-4)."""
        from api.money import MoneyFacts
        p = {"birth_year": 2000, "family_support": False, "festive_month": None, "vehicle": "none", **self.f.profile}
        return MoneyFacts(profile=p, checkins=self.f.checkins, assessments=self.f.assessments + self.assessed)

    def add_assessments(self, user, rows):
        self.assessed += rows


@pytest.fixture
def store():
    return FakeStore(facts())


@pytest.fixture
def client(monkeypatch, store):
    monkeypatch.setattr(auth, "jwks_client", lambda url: FakeJWKS())
    monkeypatch.setattr(g, "today_my", lambda: TODAY)
    monkeypatch.setattr(g, "now_utc", lambda: datetime(TODAY.year, TODAY.month, TODAY.day, 4, tzinfo=timezone.utc))
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    app.dependency_overrides[get_limiter] = lambda: RateLimiter(1000)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def headers():
    return bearer(token())


# ---- S-4 (D-93): every check-in has an assessment before the replay
def test_game_assesses_check_ins_nobody_assessed_yet_once(client, store):
    assert client.get("/v1/game", headers=headers()).status_code == 200
    assert [r["month"] for r in store.assessed] == [f"2026-{k:02d}-01" for k in range(1, 6)]
    assert all(r["result"]["band"] in ("GREEN", "YELLOW", "RED") for r in store.assessed)
    client.get("/v1/game", headers=headers())
    assert len(store.assessed) == 5                                    # saved once (M4)


def test_api_docs_are_not_published_by_default(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


# ---- rows -> engine inputs (W2)
def test_rows_become_engine_inputs():
    f = g.GameFacts(
        profile=profile_row(created_at="2026-01-31T17:00:00+00:00", employment_type="employee",
                            game_employment_type="student", game_lives_with_parents=True, game_typical_costs=None),
        checkins=[checkin_row(2, cash_bank_ewallet=100, epf_fleksibel=50, others_emergency=25, others=4000,
                              ran_short=True, created_at="2026-02-27T16:30:00+00:00")],
        days=[{"day": "2026-02-02", "entries": 3, "no_spend": False, "card": True},
              {"day": "2026-02-03", "entries": 0, "no_spend": True, "card": False}],
        goal_changes=[{"created_at": "2026-02-10T20:00:00+00:00", "amount": 50, "share": None}],
        actions=[{"kind": "decorate", "item": "rug_green", "spot": "room:rug", "created_at": "2026-02-05T01:00:00+00:00"},
                 {"kind": "plant", "gx": 6, "gy": 8, "item": "serai", "created_at": "2026-02-04T01:00:00+00:00"}],
        assessments=[{"month": "2026-02-01", "result": {"band": "RED", "health": {"tier": "Vulnerable"},
                                                        "forecast": {"probability": 0.3, "base_rate": 0.12}}}])
    prof, inp = g.game_inputs(f)
    assert prof.start == date(2026, 2, 1)                              # 01:00 in Malaysia
    assert (prof.employment_type, prof.lives_with_parents, prof.typical_monthly_costs) == ("student", True, None)
    ci = inp["checkins"][0]
    assert ci.on == date(2026, 2, 28) and ci.counted_money == 175 and ci.other_money == 4000
    assert (ci.band, ci.shortfall, ci.forecast_probability, ci.forecast_base_rate, ci.health_tier) == \
        ("RED", True, 0.3, 0.12, "Vulnerable")
    assert inp["days"] == [DayActivity(date(2026, 2, 2), 3, False), DayActivity(date(2026, 2, 3), 0, True)]
    assert inp["cards"] == [CardAnswer(date(2026, 2, 2))]
    assert inp["goal_changes"][0].day == date(2026, 2, 11) and inp["goal_changes"][0].amount == 50
    assert inp["actions"] == [Plant(date(2026, 2, 4), (6, 8), "serai"), Decorate(date(2026, 2, 5), "rug_green", "room:rug")]


def test_check_ins_use_money_and_debt_at_the_end_of_the_month():
    """D-77: checked in on 5 Feb with February's RM3,000 salary already in the bank and RM400 spent,
    a RM250 PTPTN payment made and a RM600 BNPL phone bought since 31 Jan: the game sees 31 Jan."""
    late = checkin_row(1, created_at="2026-02-05T04:00:00+00:00", cash_bank_ewallet=300 + 3000 - 400 - 250,
                       debt_total=10000 - 250 + 600, after_month_net=3000 - 400 - 250, after_month_debt=600 - 250)
    _, inp = g.game_inputs(g.GameFacts(profile=profile_row(), checkins=[late]))
    ci = inp["checkins"][0]
    assert ci.on == date(2026, 2, 5) and ci.counted_money == 300 and ci.total_debt == 10000
    on_time = g.game_inputs(g.GameFacts(profile=profile_row(), checkins=[checkin_row(1, debt_total=10000)]))[1]
    assert (on_time["checkins"][0].counted_money, on_time["checkins"][0].total_debt) == (300, 10000)


def test_profile_without_the_games_copy_uses_the_current_situation():
    prof, _ = g.game_inputs(g.GameFacts(profile=profile_row(game_employment_type=None, game_lives_with_parents=None,
                                                            game_typical_costs=None, employment_type="gig")))
    assert prof.employment_type == "gig" and prof.typical_monthly_costs == 2400


# ---- GET /v1/game
def test_game_is_the_replay_of_the_users_facts(client):
    r = client.get("/v1/game", headers=headers())
    assert r.status_code == 200
    out = r.json()
    prof = GameProfile(date(2026, 1, 1), "employee", 3000.0, 0.0, typical_monthly_costs=2400.0)
    days = [DayActivity(date.fromisoformat(d["day"]), 2) for d in day_rows()]
    cards = [CardAnswer(x.day) for x in days if x.day.weekday() == 0]
    cis = [CheckIn(date(2026, k, 1), month_end(k), 300.0 * k, 0.0, True, logged_in=3000, logged_out=2700,
                   logged_costs=2400, net_income=3000.0) for k in range(1, 6)]
    direct = replay(prof, TODAY, days=days, checkins=cis, cards=cards)
    assert out["points"] == direct.points and out["as_of"] == "2026-06-10"
    assert out["garden"]["open"] and out["garden"]["qualifying_months"] == 2 and out["garden"]["level"] == 2
    assert out["points_by_tier"] == direct.points_by_tier()
    assert out["choices"]["available"] == direct.choices_available and out["skipped"] == []
    assert [m["verified"] for m in out["months"]] == [True] * 5


def test_points_from_a_check_in_still_open_to_edits_are_pending(client, store, monkeypatch):
    """W4: May's check-in (31 May, 04:00 UTC) can be edited until 2 June 04:00 UTC: its points show
    as pending until then, so an edit that lowers them never looks like points going down."""
    store.f = facts(months=5)
    monkeypatch.setattr(g, "now_utc", lambda: datetime(2026, 6, 1, 4, tzinfo=timezone.utc))
    out = client.get("/v1/game", headers=headers()).json()
    pending = [a for a in out["ledger"] if a["pending"]]
    assert pending and {a["day"] for a in pending} == {"2026-05-31"}
    assert {a["kind"] for a in pending} >= {"checkin", "verified", "bills"}
    assert out["points_pending"] == sum(a["points"] for a in pending)
    monkeypatch.setattr(g, "now_utc", lambda: datetime(2026, 6, 2, 4, 1, tzinfo=timezone.utc))
    assert client.get("/v1/game", headers=headers()).json()["points_pending"] == 0


def test_game_needs_sign_in_and_a_profile(client, store):
    assert client.get("/v1/game").status_code == 401
    store.f = g.GameFacts(profile=None)
    assert client.get("/v1/game", headers=headers()).status_code == 404


def test_bad_rows_already_in_the_database_are_skipped_not_fatal(client, store):
    """C4: a plant saved before the garden opened (e.g. written straight to Supabase) is ignored."""
    early = {"kind": "plant", "gx": 6, "gy": 8, "item": "serai", "created_at": "2026-01-05T03:00:00+00:00"}
    store.f.actions = [early]
    out = client.get("/v1/game", headers=headers()).json()
    assert out["plants"] == [] and out["skipped"] == [{"what": "Plant", "day": "2026-01-05",
                                                        "why": "the garden isn't open yet"}]


# ---- POST /v1/game/actions (W3)
def test_an_allowed_action_is_saved_and_shown(client, store):
    cell = sorted(bed_cells(2))[0]
    r = client.post("/v1/game/actions", headers=headers(), json={"kind": "plant", "cell": list(cell), "item": "serai"})
    assert r.status_code == 200
    assert store.saved == [{"kind": "plant", "gx": cell[0], "gy": cell[1], "item": "serai", "spot": None}]
    assert r.json()["plants"][0]["plant"] == "serai" and r.json()["choices"]["used"] == 1
    assert client.get("/v1/game", headers=headers()).json()["plants"][0]["cell"] == list(cell)   # replayed from the row


@pytest.mark.parametrize("months, body, why", [
    (2, {"kind": "plant", "cell": [6, 8], "item": "serai"}, "isn't open"),               # only 2 check-ins
    (5, {"kind": "plant", "cell": [6, 8], "item": "orchid"}, "unlocks"),                 # tier 3 needs 12 months
    (5, {"kind": "plant", "cell": [0, 0], "item": "serai"}, "flower bed"),
    (5, {"kind": "choose_animal", "item": "dog"}, "unknown animal"),
    (5, {"kind": "buy_tree"}, "G4"),
], ids=["closed", "tier", "not-bed", "unknown", "tree"])
def test_a_disallowed_action_is_refused_and_not_saved(client, store, months, body, why):
    store.f = facts(months=months)
    r = client.post("/v1/game/actions", headers=headers(), json=body)
    assert r.status_code == 409 and why in r.json()["detail"] and store.saved == []


def test_no_choices_left_is_refused(client, store):
    available = client.get("/v1/game", headers=headers()).json()["choices"]["available"]
    items = (load_game()["decorations"]["room"] + load_game()["decorations"]["garden"])[:available]
    for i, item in enumerate(items):
        assert client.post("/v1/game/actions", headers=headers(),
                           json={"kind": "decorate", "item": item, "spot": f"spot:{i}"}).status_code == 200
    r = client.post("/v1/game/actions", headers=headers(), json={"kind": "plant", "cell": [6, 8], "item": "serai"})
    assert r.status_code == 409 and "no choice" in r.json()["detail"] and len(store.saved) == available


@pytest.mark.parametrize("body", [
    {"kind": "plant", "cell": [6, 8], "item": "serai", "user_id": USER},                 # can't name a user
    {"kind": "plant", "item": "serai"},                                                    # no cell
    {"kind": "dig", "cell": [6, 8], "item": "serai"},                                      # extra field
    {"kind": "plant", "cell": [6, 8], "item": "Bunga Raya"},
    {"kind": "decorate", "item": "bench'; drop table x;--", "spot": "a"},
    {"kind": "plant", "cell": [999, 8], "item": "serai"},
    {"kind": "teleport"},
], ids=["user_id", "no-cell", "extra", "item-case", "item-injection", "cell-range", "kind"])
def test_action_shapes_are_validated(client, store, body):
    assert client.post("/v1/game/actions", headers=headers(), json=body).status_code == 422
    assert store.saved == []


# ---- storage
def test_storage_trouble_is_a_503(client, store):
    def down(user):
        raise httpx.ConnectError("no route")
    store.load = down
    assert client.get("/v1/game", headers=headers()).status_code == 503
    app.dependency_overrides.pop(get_store)                                # the real one, with no anon key set
    assert client.get("/v1/game", headers=headers()).status_code == 503


def test_supabase_store_reads_and_writes_as_the_user(monkeypatch):
    """W1: anon key + the user's own token on every call (RLS decides), user filter, paging,
    and a written row that names no user."""
    monkeypatch.setattr(g.SupabaseStore, "PAGE", 5)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        table = request.url.path.rsplit("/", 1)[-1]
        if request.method == "POST":
            return httpx.Response(201)
        if table == "profiles":
            return httpx.Response(200, json=[profile_row()])
        if table == "game_days":
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json=day_rows()[offset:offset + (5 if offset == 0 else 2)])
        return httpx.Response(200, json=[])

    s = g.SupabaseStore("https://testproject.supabase.co", "anon-test", transport=httpx.MockTransport(handler))
    user = auth.CurrentUser(id=USER, token="user-token")
    f = s.load(user)
    s.add_action(user, {"kind": "buy_tree", "gx": None, "gy": None, "item": None, "spot": None})
    assert f.profile["user_id"] == USER and len(f.days) == 7
    assert {c.url.path.rsplit("/", 1)[-1] for c in calls if c.method == "GET"} == {t for t, _ in s.TABLES}
    assert [int(c.url.params["offset"]) for c in calls if c.url.path.endswith("/game_days")] == [0, 5]
    for c in calls:
        assert c.headers["apikey"] == "anon-test" and c.headers["authorization"] == "Bearer user-token"
        assert c.url.path.startswith("/rest/v1/")
        if c.method == "GET":
            assert c.url.params["user_id"] == f"eq.{USER}"
    post = calls[-1]
    assert post.url.path == "/rest/v1/game_actions" and post.headers["prefer"] == "return=minimal"
    assert b"user_id" not in post.content


def test_settings_read_the_anon_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test")
    get_settings.cache_clear()
    try:
        assert get_settings().anon_key == "anon-test"
    finally:
        get_settings.cache_clear()
    assert Settings(supabase_url="https://x.supabase.co").anon_key is None
