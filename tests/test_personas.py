"""T-18 / A4 (D-90): the study personas (tools/personas/build.py), their time travel through the API,
and the admin seeding script (tools/personas/seed.py, tested against a mock Supabase)."""
import json
import re
from datetime import date, datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

import api.auth as auth
import api.game as g
import api.money as m
from api.config import get_settings
from api.limits import RateLimiter
from api.main import app, get_limiter, get_store
from engine.game import replay
from test_api import SETTINGS, USER, FakeJWKS, bearer, token
from tools.personas import build as b
from tools.personas import seed

SQL = (b.ROOT / "supabase" / "migrations" / "20261014000000_init.sql").read_text(encoding="utf-8")


def columns(table: str) -> set[str]:
    body = re.search(rf"create table public\.{table} \((.*?)\n\);", SQL, re.S).group(1)
    return {line.split()[0] for line in body.splitlines() if re.match(r"\s+[a-z_]+ ", line)} - {"check", "unique",
                                                                                                  "primary"}


@pytest.fixture(scope="module")
def built():
    import pandas as pd
    users = pd.read_parquet(b.SOURCE / "users.parquet").set_index("user_id")
    monthly = pd.read_parquet(b.SOURCE / "monthly.parquet")
    tx = pd.read_parquet(b.SOURCE / "transactions.parquet", filters=[("user_id", "in", [p.user_id for p in b.PERSONAS])])
    return [b.build_persona(per, users, monthly, tx) for per in b.PERSONAS]


def test_the_file_on_disk_is_up_to_date(built):
    on_disk = json.loads(b.OUT.read_text(encoding="utf-8"))["personas"]
    assert on_disk == json.loads(json.dumps(built)), "stale: run python -m tools.personas.build"


def test_four_different_personas_from_the_synthetic_data(built):
    """P1: synthetic users only; four situations (student, gig, two employees)."""
    assert [p["profile"]["employment_type"] for p in built] == ["student", "gig", "employee", "employee"]
    assert len({p["meta"]["source_user_id"] for p in built}) == 4
    assert all(p["email"].endswith("@personas.fast.test") for p in built)       # reserved domain, never delivers


@pytest.mark.parametrize("table, key", seed.TABLES)
def test_rows_have_the_databases_columns(built, table, key):
    """P2: the seed script inserts the rows as they are (user_id is added there)."""
    cols = columns(table)
    for p in built:
        rows = p[key] if isinstance(p[key], list) else [p[key]]
        for row in rows:
            assert set(row) <= cols - {"user_id", "id"}, set(row) - cols


def test_a_year_on_the_personas_own_dates(built):
    for p in built:
        prof = p["profile"]
        assert prof["is_persona"] and (prof["study_first"], prof["study_last"]) == ("2026-07-01", "2027-01-01")
        assert prof["study_date"] == prof["study_first"] and g.my_day(prof["created_at"]) == date(2026, 1, 1)
        assert [c["month"] for c in p["checkins"]] == [f"2026-{k:02d}-01" for k in range(1, 13)]
        assert all(g.my_day(c["created_at"]) == b._month_end(2026, int(c["month"][5:7])) for c in p["checkins"])
        days = [date.fromisoformat(t["occurred_on"]) for t in p["transactions"]]
        assert min(days) >= date(2026, 1, 1) and max(days) <= date(2026, 12, 31)
        assert all(t["client_logged_at"] == t["created_at"] for t in p["transactions"])         # 24-hour check


def test_bnpl_card_and_debt_entries_follow_the_apps_rules(built):
    for p in built:
        for t in p["transactions"]:
            assert not (t["is_bnpl"] and t["is_debt_payment"])
            assert t["direction"] == "out" or not (t["is_bnpl"] or t["is_debt_payment"] or t["on_credit"])
            if t["is_debt_payment"]:
                assert t["category"] in {"car_loan", "motorbike_loan", "ptptn", "personal_loan", "credit_card",
                                         "bnpl_instalment"}
        if not any(d["kind"] == "credit_card" for d in p["debts"]):
            assert not any(t["on_credit"] for t in p["transactions"])


def test_logged_totals_match_what_the_database_would_freeze(built):
    for p in built:
        jan = [t for t in p["transactions"] if t["occurred_on"].startswith("2026-01")]
        c = p["checkins"][0]
        assert c["logged_in"] == round(sum(t["amount"] for t in jan if t["direction"] == "in"), 2)
        assert c["logged_debt_paid"] == round(sum(t["amount"] for t in jan if t["is_debt_payment"]), 2)


def test_persona_game_and_notes_are_what_the_app_shows(built):
    """P3: the garden plan is accepted by the replay; docs/personas.md has the API's own numbers."""
    doc = b.DOC.read_text(encoding="utf-8")
    for p in built:
        prof, inputs = g.game_inputs(b.game_facts(p, b.STUDY_LAST))
        st = replay(prof, b.STUDY_LAST, strict=False, **inputs)
        assert not [e for e, _ in st.rejected if type(e).__name__ == "Plant"]
        assert len(st.plants) == len(p["game_actions"])
        first = b.snapshot(p, b.STUDY_FIRST)
        assert f"| {first['date']} | {first['band']} | {first['dsr']:.2f} |" in doc
        assert sum(x.verified for x in st.months) >= 6                            # mostly logs that add up


def test_time_travel_reveals_only_what_has_happened(built):
    jason = built[1]
    july = b.snapshot(jason, date(2026, 7, 1))
    aug = b.snapshot(jason, date(2026, 8, 1))
    assert july["months"] == 6 and aug["months"] == 7                            # one more check-in seen
    money = m.as_of(m.MoneyFacts(profile=jason["profile"], transactions=jason["transactions"],
                                 checkins=jason["checkins"]), date(2026, 7, 1))
    assert max(t["occurred_on"] for t in money.transactions) <= "2026-07-01"
    assert len(money.checkins) == 6


def test_answer_keys_are_what_the_app_shows_and_up_to_date(built):
    """T-18: the comprehension keys come from the same functions as the screen, on the start date."""
    from tools.personas import answer_key as k
    doc = k.DOC.read_text(encoding="utf-8")
    assert doc == k.render(json.loads(json.dumps(built))), "stale: run python -m tools.personas.answer_key"
    for p in built:
        key, snap = k.key_for(p), b.snapshot(p, b.STUDY_FIRST)
        assert key["B1"].strip('"').upper().replace(" ", "_").startswith(snap["band"].split("_")[0])
        assert key["dsr"] == snap["dsr"] and key["cushion"] == snap["cushion"]
        assert key["B3"] == "straight away"                                       # a worse band shows at once (D-49)
        assert f"| **B1** band |" in doc and p["meta"]["name"] in doc
    assert k.dsr_bucket(0.59) == ("30% to under 60%", True) and k.dsr_bucket(0.19) == ("under 30%", False)
    assert k.cushion_bucket(0.0) == ("less than 1", False) and k.cushion_bucket(3.2) == ("3 or more", False)


# ---------------------------------------------------------------- the API for a persona account
class PersonaStore:
    def __init__(self, p: dict):
        self.p, self.updates = p, []

    def _profile(self):
        return {**self.p["profile"], "user_id": USER}

    def load(self, user):
        return g.GameFacts(profile=self._profile(), checkins=self.p["checkins"],
                           days=b.game_days(self.p["transactions"], self.p["cards"]), actions=self.p["game_actions"])

    def load_money(self, user):
        return m.MoneyFacts(profile=self._profile(), transactions=self.p["transactions"], debts=self.p["debts"],
                            checkins=self.p["checkins"])

    def add_assessments(self, user, rows):
        pass

    def add_action(self, user, row):
        raise AssertionError("not used")

    def load_card_answer(self, user, week):
        return next(({k: c[k] for k in ("event_id", "response", "week")} for c in self.p["cards"]
                     if c["week"] == week.isoformat()), None)

    def update_profile(self, user, fields):
        self.updates.append(fields)
        self.p["profile"] = {**self.p["profile"], **fields}


@pytest.fixture
def persona_client(monkeypatch, built):
    store = PersonaStore(json.loads(json.dumps(built[1])))
    monkeypatch.setattr(auth, "jwks_client", lambda url: FakeJWKS())
    monkeypatch.setattr(g, "today_my", lambda: date(2026, 12, 20))               # the real clock: ignored
    monkeypatch.setattr(g, "now_utc", lambda: datetime(2026, 12, 20, 4, tzinfo=timezone.utc))
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    app.dependency_overrides[get_limiter] = lambda: RateLimiter(1000)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app), store
    app.dependency_overrides.clear()


def test_a_persona_lives_on_its_study_date(persona_client):
    client, _ = persona_client
    game = client.get("/v1/game", headers=bearer(token())).json()
    assert game["as_of"] == "2026-07-01" and len(game["months"]) == 6 and game["points_pending"] == 0
    a = client.get("/v1/assess", headers=bearer(token())).json()
    assert a["as_of"] == "2026-07-01" and a["assessed_month"] == "2026-06-01"
    assert client.get("/v1/study", headers=bearer(token())).json() == {
        "persona": True, "study_date": "2026-07-01", "first": "2026-07-01", "last": "2027-01-01"}


def test_time_travel_moves_a_month_and_stays_in_range(persona_client):
    client, store = persona_client
    r = client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "next"})
    assert r.status_code == 200 and r.json()["study_date"] == "2026-08-01"
    assert client.get("/v1/game", headers=bearer(token())).json()["as_of"] == "2026-08-01"
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "last"}).json()["study_date"] \
        == "2027-01-01"
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "next"}).json()["study_date"] \
        == "2027-01-01"                                                           # clamped
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "first"}).json()["study_date"] \
        == "2026-07-01"
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "previous"}).json()["study_date"] \
        == "2026-07-01"
    assert store.updates[0] == {"study_date": "2026-08-01"}
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "back"}).status_code == 422


def test_the_card_shows_the_personas_own_answers_on_every_study_date(persona_client):
    """D-119: on each study date GET /v1/card shows the persona's answer for that week when it gave one,
    with that week's own event (from the deck: an event outside it has no card text), else the week's draw."""
    client, store = persona_client
    weeks = {c["week"]: c for c in store.p["cards"]}
    seen = 0
    for _ in b.study_dates():
        r = client.get("/v1/card", headers=bearer(token()))
        assert r.status_code == 200
        card, mine = r.json(), weeks.get(r.json()["week"])
        assert card["answer"] == (mine and mine["response"])
        assert not mine or card["event_id"] == mine["event_id"]
        seen += mine is not None
        client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "next"})
    assert seen                                                                   # the answered case happens


def test_persona_characters_are_valid_profile_values(built):
    """D-124/D-125: avatar and skin tone 1-6 as the table checks them (characters.json counts tones from 0)."""
    for p in built:
        prof = p["profile"]
        assert 1 <= prof["avatar"] <= 6 and 1 <= prof["skin_tone"] <= 6 and prof["glasses"] is False
        assert prof["skin_tone"] == b.CHARACTERS["avatars"][prof["avatar"] - 1]["suggested_tone"] + 1


def test_persona_cards_come_from_the_deck(built):
    from api import cards
    for p in built:
        allowed = {e for e, _ in cards.weights(p["profile"])}
        assert len(p["cards"]) > 30 and {c["event_id"] for c in p["cards"]} <= allowed
        assert {c["response"] for c in p["cards"]} <= set(cards.RESPONSES) - {"not_this_week"}


def test_only_personas_can_time_travel(persona_client):
    client, store = persona_client
    store.p["profile"] = {**store.p["profile"], "is_persona": False, "study_date": None, "study_first": None,
                          "study_last": None}
    assert client.post("/v1/study/time-travel", headers=bearer(token()), json={"step": "next"}).status_code == 403
    assert client.get("/v1/study", headers=bearer(token())).json() == {"persona": False}
    assert client.get("/v1/game", headers=bearer(token())).json()["as_of"] == "2026-12-20"   # the real clock
    assert not store.updates


# ---------------------------------------------------------------- the admin seeding script
def test_seed_creates_accounts_and_loads_rows_in_order(built, monkeypatch, tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["Authorization"] == "Bearer service-key" and req.headers["apikey"] == "service-key"
        calls.append((req.method, req.url.path, json.loads(req.content) if req.content else None))
        if req.method == "GET":
            return httpx.Response(200, json={"users": []})
        if req.url.path == "/auth/v1/admin/users":
            return httpx.Response(200, json={"id": f"uid-{len(calls)}"})
        return httpx.Response(201)

    data = tmp_path / "personas.json"
    data.write_text(json.dumps({"personas": built[:1]}), encoding="utf-8")
    monkeypatch.setattr(seed, "DATA", data)
    monkeypatch.setenv("PERSONA_PASSWORD", "study-only")
    seed.main([], admin=seed.Admin("https://x.supabase.co", "service-key", transport=httpx.MockTransport(handler)))
    posts = [(path, body) for method, path, body in calls if method == "POST"]
    assert posts[0][0] == "/auth/v1/admin/users" and posts[0][1]["email_confirm"] is True
    tables = [path.rsplit("/", 1)[1] for path, _ in posts[1:]]
    assert tables.index("profiles") == 0 and tables.index("transactions") < tables.index("monthly_checkins")
    assert tables[-1] == "game_actions"
    uid = {row["user_id"] for _, body in posts[1:] for row in body}
    assert len(uid) == 1 and all(len(body) <= seed.BATCH for _, body in posts[1:])
    assert sum(len(body) for path, body in posts if path.endswith("/transactions")) == len(built[0]["transactions"])


class FakeAuth:
    """A mock Supabase admin API that keeps its users, for the per-participant accounts (SR1)."""

    def __init__(self):
        self.users, self.rows = {}, []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/auth/v1/admin/users" and req.method == "GET":
            return httpx.Response(200, json={"users": [{"id": k, "email": v} for k, v in self.users.items()]})
        if path == "/auth/v1/admin/users" and req.method == "POST":
            body = json.loads(req.content)
            uid = f"uid-{len(self.users) + 1}"
            self.users[uid] = body["email"]
            self.password = body["password"]
            return httpx.Response(200, json={"id": uid})
        if req.method == "DELETE":
            self.users.pop(path.rsplit("/", 1)[1])
            return httpx.Response(200)
        self.rows += json.loads(req.content)
        return httpx.Response(201)


def test_each_participant_gets_their_own_five_accounts(built, monkeypatch, tmp_path):
    fake = FakeAuth()
    data = tmp_path / "personas.json"
    data.write_text(json.dumps({"personas": built}), encoding="utf-8")
    monkeypatch.setattr(seed, "DATA", data)
    monkeypatch.setattr(seed, "SESSIONS", tmp_path / "sessions")
    admin = seed.Admin("https://x.supabase.co", "k", transport=httpx.MockTransport(fake))
    seed.main(["--participant", "P7"], admin=admin)
    assert sorted(fake.users.values()) == sorted(["new.p07@personas.fast.test", "aina.p07@personas.fast.test",
                                                  "jason.p07@personas.fast.test", "priya.p07@personas.fast.test",
                                                  "daniel.p07@personas.fast.test"])
    card = (tmp_path / "sessions" / "p07.md").read_text(encoding="utf-8")
    assert fake.password in card and "Persona order on the questionnaire: C-D-B-A" in card     # row 3 (P07)
    assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", fake.password) and len(fake.password) >= 10
    assert not any(r["user_id"] == next(k for k, v in fake.users.items() if v.startswith("new."))
                   for r in fake.rows)                                    # the sign-up account is empty
    with pytest.raises(SystemExit, match="already has accounts"):
        seed.main(["--participant", "p07"], admin=admin)
    seed.main(["--participant", "P08"], admin=admin)
    seed.main(["--participant", "P07", "--delete"], admin=admin)
    assert all(".p08@" in e for e in fake.users.values()) and len(fake.users) == 5
    assert not (tmp_path / "sessions" / "p07.md").exists()
    seed.main(["--delete-all-participants"], admin=admin)
    assert fake.users == {}


def test_participant_codes_and_the_balanced_order():
    assert [seed.participant_code(c) for c in ("P7", "p07", "T1", "P120")] == ["p07", "p07", "t01", "p120"]
    for bad in ("Patrick", "p", "a@b.com", "P1234"):
        with pytest.raises(SystemExit):
            seed.participant_code(bad)
    rows = [seed.persona_order(f"p{n:02d}") for n in range(1, 5)]
    assert all(sorted(r) == [0, 1, 2, 3] for r in rows)
    pairs = {(r[i], r[i + 1]) for r in rows for i in range(3)}
    assert len(pairs) == 12                                             # every persona follows every other once
    assert seed.persona_order("p05") == rows[0]


def test_sign_up_card_and_its_check():
    from tools.personas import onboarding as ob
    assert ob.DOC.read_text(encoding="utf-8") == ob.render()            # the card on disk is up to date
    profile = {**ob.EXPECTED_PROFILE, "declared_income": "2800.00", "created_at": "2026-12-30T03:06:00+00:00"}
    debts = [{"kind": "bnpl", "outstanding": 360, "monthly_payment": 120, "deducted_from_salary": False},
             {"kind": "ptptn", "outstanding": 14500, "monthly_payment": 150, "deducted_from_salary": False}]
    r = ob.check(profile, debts, "2026-12-30T03:00:00+00:00")
    assert r["accuracy"] == 1 and r["minutes"] == 6.0 and r["finished"]
    wrong = ob.check({**profile, "declared_income": 28000}, debts[:1])
    assert wrong["correct"] == wrong["total"] - 4                     # income typo + the missing PTPTN's 3 fields
    assert ob.check(None, [])["finished"] is False
    for label, _ in ob.CARD:
        assert label                                                   # every line has a label
    assert not any(word in " ".join(v for _, v in ob.CARD).lower() for word in ("maybank", "atome", "shopee"))


def test_seed_refuses_to_load_twice_unless_reset(built, monkeypatch, tmp_path):
    deleted = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "GET":
            return httpx.Response(200, json={"users": [{"id": "old", "email": built[0]["email"]}]})
        if req.method == "DELETE":
            deleted.append(req.url.path)
        return httpx.Response(200, json={"id": "new"})

    data = tmp_path / "personas.json"
    data.write_text(json.dumps({"personas": built[:1]}), encoding="utf-8")
    monkeypatch.setattr(seed, "DATA", data)
    admin = seed.Admin("https://x.supabase.co", "k", transport=httpx.MockTransport(handler))
    with pytest.raises(SystemExit, match="already exists"):
        seed.main([], admin=admin)
    seed.main(["--delete"], admin=admin)
    assert deleted == ["/auth/v1/admin/users/old"]


def test_expert_review_form_is_up_to_date_and_covers_every_advice_text():
    """D-101: the form shows the app's current wording; regenerate it after any change (W2)."""
    from tools.personas import expert_form as ef
    personas = json.loads(b.OUT.read_text(encoding="utf-8"))["personas"]
    text = ef.render(personas)
    assert ef.DOC.read_text(encoding="utf-8") == text
    assert len(re.findall(r"^\| C\d+ \|", text, re.M)) == len(ef.advice_rows()) and "Y / N" in text
    assert all(f"**A{i}." in text for i in range(1, len(personas) + 1))


def test_b12_answer_key_is_one_of_the_questionnaire_options():
    """B12 (D-135) is scored against a fixed key: it must be printed, word for word, as an option."""
    from tools.personas import answer_key as k
    questionnaire = (b.ROOT / "docs" / "ethics" / "04_questionnaire.md").read_text(encoding="utf-8")
    assert f"☐ {k.B12}" in questionnaire
