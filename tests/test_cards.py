"""The weekly life-event card (G-08, D-117): api/cards.py and GET/POST /v1/card."""
from collections import Counter
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.auth as auth
import api.cards as c
import api.game as g
from api.limits import RateLimiter
from api.main import app, get_limiter, get_settings, get_store
from test_api import SETTINGS, FakeJWKS
from test_game_api import TODAY, FakeStore, facts, headers, profile_row

EMPLOYEE_MOTO = {"employment_type": "employee", "vehicle": "motorcycle"}


def test_the_deck_is_the_generators_own_and_every_card_has_words():
    assert set(c.TEXT["deck"]) <= set(c.DECK)
    for event_id in c.TEXT["deck"]:
        assert c.DECK[event_id]["shock"], f"{event_id}: only shock-size events become cards"
        assert c.TEXT["cards"][event_id]["title"] and c.TEXT["cards"][event_id]["text"]
    assert "L13" not in c.TEXT["deck"]                                   # no funeral card (too close to home)
    assert c.RESPONSES == ("use_savings", "cut_spending", "set_goal", "not_this_week")   # the table's check
    for r in c.RESPONSES:                                                # no wrong answer: every one gets a kind reply
        assert c.TEXT["responses"][r]["label"] and c.TEXT["responses"][r]["after"]
        assert not any(w in c.TEXT["responses"][r]["after"].lower() for w in ("wrong", "should have", "bad"))


def test_only_events_the_user_can_have_weighted_by_frequency_and_the_decks_multipliers():
    moto = dict(c.weights(EMPLOYEE_MOTO))
    assert "L02" in moto and "L04" not in moto                           # a motorbike, no car
    assert moto["L06"] == pytest.approx(0.15)
    gig = dict(c.weights({"employment_type": "gig", "vehicle": "car"}))
    assert gig["L04"] == pytest.approx(0.2 * 1.8) and gig["L06"] == pytest.approx(0.15 * 1.8)
    student = dict(c.weights({"employment_type": "student", "vehicle": "none"}))
    assert student["L08"] == pytest.approx(0.05 * 2.0)
    assert "L16" not in student and "L02" not in student                 # no household appliance, no vehicle


def test_one_card_a_week_the_same_every_time_and_fair_over_many_people():
    week = c.monday(date(2026, 7, 1))
    assert week == date(2026, 6, 29)
    first = c.draw("user-a", week, EMPLOYEE_MOTO)
    assert all(c.draw("user-a", week, EMPLOYEE_MOTO) == first for _ in range(5))       # LC1
    assert c.draw("user-a", c.monday(date(2026, 7, 5)), EMPLOYEE_MOTO) == first      # Sunday: same week
    counts = Counter(c.draw(f"user-{i}", week, EMPLOYEE_MOTO) for i in range(6000))
    total = sum(w for _, w in c.weights(EMPLOYEE_MOTO))
    for event_id, w in c.weights(EMPLOYEE_MOTO):
        assert counts[event_id] / 6000 == pytest.approx(w / total, abs=0.02), event_id


def test_the_real_store_asks_supabase_as_the_user_for_that_week_only():
    import httpx
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"event_id": "L06", "response": "set_goal", "week": "2026-06-29"}])
        return httpx.Response(201)
    store = g.SupabaseStore("https://x.supabase.co", "anon", transport=httpx.MockTransport(handler))
    user = auth.CurrentUser(id="u-1", token="t-1")
    assert store.load_card_answer(user, date(2026, 6, 29))["response"] == "set_goal"
    store.add_card_answer(user, {"event_id": "L06", "response": "use_savings"})
    get, post = seen
    assert get.headers["authorization"] == "Bearer t-1"                  # the user's own token (rule 8)
    assert get.url.params["user_id"] == "eq.u-1" and get.url.params["week"] == "eq.2026-06-29"
    assert post.url.path.endswith("/life_event_answers") and b"week" not in post.content


def test_coverage_in_plain_words():
    assert c.coverage(900, 150, 800) == "covered"
    assert c.coverage(300, 150, 800) == "partly"
    assert c.coverage(100, 150, 800) == "not_yet"
    assert "help" in c.TEXT["coverage"]["not_yet"]                       # what helps, not what's wrong (LC4)
    assert not any("covered" in c.TEXT["coverage"][k].lower() for k in c.TEXT["coverage"])   # the badge says that


class CardStore(FakeStore):
    def __init__(self, f):
        super().__init__(f)
        self.cards = []

    def load_card_answer(self, user, week):
        return next(({"event_id": r["event_id"], "response": r["response"], "week": week.isoformat()}
                     for r in self.cards if r["week"] == week), None)

    def add_card_answer(self, user, row):
        assert set(row) == {"event_id", "response"}                        # the week is the database's
        self.cards.append({**row, "week": c.monday(TODAY)})
        if row["response"] != "not_this_week":                             # as the game_days view does
            self.f.days[-1]["card"] = True


@pytest.fixture
def store():
    f = facts(profile=profile_row(vehicle="motorcycle"))
    for d in f.days:                                                   # no card answered yet, any week
        d["card"] = False
    return CardStore(f)


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


def test_get_card_this_weeks_event_and_its_cost(client):
    r = client.get("/v1/card", headers=headers())
    assert r.status_code == 200
    body = r.json()
    assert body["week"] == c.monday(TODAY).isoformat()
    assert body["event_id"] in c.TEXT["deck"] and body["answer"] is None
    e = c.DECK[body["event_id"]]
    assert (body["cost_low"], body["cost_high"]) == (e["low"], e["high"])
    assert body["coverage"] in ("covered", "partly", "not_yet")
    assert [x["id"] for x in body["responses"]] == list(c.RESPONSES)
    assert body["points"] == 5
    assert client.get("/v1/card", headers=headers()).json()["event_id"] == body["event_id"]    # the same all week


def test_answer_once_a_week_and_the_game_awards_the_card_points(client, store):
    cards_in = lambda game: [a for a in game["ledger"] if a["kind"] == "card"]        # noqa: E731
    before = client.get("/v1/game", headers=headers()).json()
    assert cards_in(before) == []
    r = client.post("/v1/card", headers=headers(), json={"response": "use_savings"})
    assert r.status_code == 200 and r.json()["answer"] == "use_savings"
    assert store.cards[0]["event_id"] == client.get("/v1/card", headers=headers()).json()["event_id"]
    assert client.post("/v1/card", headers=headers(), json={"response": "set_goal"}).status_code == 409
    after = client.get("/v1/game", headers=headers()).json()
    assert [a["points"] for a in cards_in(after)] == [5]                 # the game's fixed card points, once
    assert after["points"] - before["points"] == 5


def test_not_this_week_is_saved_but_earns_nothing_and_a_bad_answer_is_refused(client, store):
    before = client.get("/v1/game", headers=headers()).json()["points"]
    assert client.post("/v1/card", headers=headers(), json={"response": "not_this_week"}).status_code == 200
    assert store.cards[0]["response"] == "not_this_week"
    assert client.get("/v1/game", headers=headers()).json()["points"] == before      # no points, no penalty
    assert client.post("/v1/card", headers=headers(), json={"response": "spend_it"}).status_code == 422
    assert client.post("/v1/card", headers=headers(), json={"response": "use_savings", "event_id": "L18"}).status_code == 422
