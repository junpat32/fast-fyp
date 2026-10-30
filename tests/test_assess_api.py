"""A2/A3 (D-88): GET /v1/assess builds the user's months from their own rows; GET /v1/future runs the
Monte Carlo on them. Nothing contacts Supabase: the store is faked, and the real store's new calls
are tested against a mock transport."""
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
from engine.assess import assess
from test_api import SETTINGS, USER, FakeJWKS, bearer, token
from test_game_api import checkin_row, day_rows, profile_row

TODAY = date(2026, 6, 10)


def money_profile(**over) -> dict:
    return {**profile_row(), "birth_year": 2000, "family_support": False, "festive_month": 3, "vehicle": "motorcycle",
            **over}


def tx(day: str, amount: float, direction="out", category="food", **flags) -> dict:
    return {"occurred_on": day, "direction": direction, "amount": amount, "category": category,
            "is_essential": flags.pop("essential", direction == "out"), **flags}


def salary_and_rent(k: int) -> list[dict]:
    """Month k of 2026: salary in, RM2,400 of essentials out, as an honest user logs them."""
    return [tx(f"2026-{k:02d}-25", 3000, "in", "salary", essential=False), tx(f"2026-{k:02d}-03", 2400)]


def money_facts(months=5, **over) -> m.MoneyFacts:
    base = dict(profile=money_profile(), transactions=[t for k in range(1, months + 1) for t in salary_and_rent(k)],
                debts=[{"kind": "ptptn", "monthly_payment": 150, "outstanding": 12000, "deducted_from_salary": False,
                        "starts_on": None, "ends_on": None}],
                checkins=[checkin_row(k, debt_total=12000 - 150 * k) for k in range(1, months + 1)])
    return m.MoneyFacts(**{**base, **over})


class FakeStore:
    def __init__(self, money: m.MoneyFacts):
        self.money, self.saved = money, []

    def load_money(self, user):
        assert user.id == USER                                      # only ever the token's user
        return self.money

    def add_assessments(self, user, rows):
        self.saved += rows

    def load(self, user):
        return g.GameFacts(profile=self.money.profile, checkins=self.money.checkins, days=day_rows())

    def add_action(self, user, row):
        raise AssertionError("not used here")


@pytest.fixture
def store():
    return FakeStore(money_facts())


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


# ---------------------------------------------------------------- rows -> records (M1, M2)
def test_one_record_per_month_since_sign_up_with_its_source():
    _, records, months = m.assess_inputs(money_facts(), TODAY)
    assert [x["month"] for x in months] == [f"2026-{k:02d}-01" for k in range(1, 7)]
    assert [x["source"] for x in months] == ["check-in"] * 5 + ["this month so far"]
    jan = records[0]
    assert jan.net_income == 3000 and jan.cash == 300 and jan.outstanding_debt == 11850 and jan.month == 1
    assert jan.debt_payments == 150 and jan.essential_spending == 2400 and jan.total_spending == 2400


def test_this_month_uses_the_declared_income_until_more_is_logged():
    """Early in the month the salary isn't in yet: the band must not jump to 'insufficient income'."""
    _, records, _ = m.assess_inputs(money_facts(), TODAY)
    june = records[-1]
    assert june.net_income == 3000 and june.essential_spending == 2400 - 150   # declared costs less commitments
    assert june.cash == 1500                                                      # May's money, nothing logged yet


def test_a_month_without_a_check_in_is_estimated_from_the_logs():
    f = money_facts(checkins=[checkin_row(k, debt_total=12000 - 150 * k) for k in (1, 2, 4, 5)])
    _, records, months = m.assess_inputs(f, TODAY)
    assert months[2]["source"] == "estimated"
    assert records[2].cash == 600 + 3000 - 2400                                  # February's money + March's net


def test_bnpl_is_paid_in_three_instalments_and_counts_as_a_commitment():
    f = money_facts(transactions=money_facts().transactions + [tx("2026-03-10", 600, category="shopping",
                                                                   essential=False, is_bnpl=True)])
    _, records, _ = m.assess_inputs(f, TODAY)
    mar, apr, may, jun = records[2], records[3], records[4], records[5]
    assert mar.bnpl_purchases == 600 and mar.bnpl_new_count == 1
    assert [x.bnpl_instalments for x in (mar, apr, may, jun)] == [200, 200, 200, 0]
    assert mar.debt_payments == 150 + 200


def test_salary_deductions_count_as_income_before_commitments():
    """DSR divides every commitment by income before it; take-home already had a salary deduction removed."""
    debts = [{"kind": "ptptn", "monthly_payment": 150, "outstanding": 12000, "deducted_from_salary": True}]
    _, records, _ = m.assess_inputs(money_facts(debts=debts), TODAY)
    assert records[0].net_income == 3000 + 150 and records[0].debt_payments == 150


def test_unexpected_costs_family_support_and_goals():
    f = money_facts(transactions=money_facts().transactions + [
        tx("2026-02-14", 450, category="repair", essential=False, is_unexpected=True),
        tx("2026-02-20", 80, category="clinic", is_unexpected=True),
        tx("2026-02-28", 200, category=m.FAMILY, essential=False)],
        profile=money_profile(savings_goal_monthly=300),
        goal_changes=[{"created_at": "2026-03-05T02:00:00+00:00", "amount": 500, "share": None}])
    _, records, _ = m.assess_inputs(f, TODAY)
    feb, mar, apr = records[1], records[2], records[3]
    assert feb.event_costs == 530 and feb.shock_count == 1 and feb.family_support == 200
    assert (feb.savings_target, mar.savings_target, apr.savings_target) == (300, 300, 500)   # from the next month


def test_no_look_ahead():
    """M2: adding a later month's rows never changes an earlier month's record."""
    _, early, _ = m.assess_inputs(money_facts(months=3), date(2026, 3, 31))
    _, later, _ = m.assess_inputs(money_facts(months=5), TODAY)
    assert early[:3] == later[:3]


# ---------------------------------------------------------------- GET /v1/assess
def test_get_assess_reads_the_users_rows_and_saves_new_months(client, store):
    r = client.get("/v1/assess", headers=bearer(token()))
    assert r.status_code == 200
    body = r.json()
    assert body["band"] in ("GREEN", "YELLOW", "RED") and body["as_of"] == TODAY.isoformat()
    assert [x["source"] for x in body["months"]][-1] == "this month so far"
    assert [row["month"] for row in store.saved] == [f"2026-{k:02d}-01" for k in range(1, 6)]   # checked-in months
    profile, records, _ = m.assess_inputs(store.money, TODAY)
    assert store.saved[0]["result"] == assess(profile, records[:1])                         # its own months only


def test_saved_assessments_are_kept(client, store):
    """M4: a month already saved is never assessed again (the game's really-bad month can't change)."""
    store.money.assessments = [{"month": f"2026-{k:02d}-01", "result": {}} for k in range(1, 5)]
    client.get("/v1/assess", headers=bearer(token()))
    assert [row["month"] for row in store.saved] == ["2026-05-01"]


def test_get_assess_needs_sign_up_and_a_token(client, store):
    store.money = m.MoneyFacts(profile=None)
    assert client.get("/v1/assess", headers=bearer(token())).status_code == 404
    assert client.get("/v1/assess").status_code == 401


def test_assess_says_what_the_band_counts_as_debt_payments(client):
    """D-152: the month's debt payments (the DSR's numerator) and the BNPL instalments inside them."""
    body = client.get("/v1/assess", headers=bearer(token())).json()
    assert body["debt_payments"] >= body["bnpl_instalments"] >= 0
    from engine.state import MonthRecord
    record = MonthRecord(net_income=2800, debt_payments=480.556, outstanding_debt=0, cash=0, essential_spending=1500,
                         bnpl_instalments=120.0)
    assert m.debt_parts(record) == {"debt_payments": 480.56, "bnpl_instalments": 120.0}


# ---------------------------------------------------------------- GET /v1/future
def test_future_self_from_complete_months(client):
    r = client.get("/v1/future", headers=bearer(token()))
    assert r.status_code == 200
    body = r.json()
    assert body["available"] and body["label"] == "if recent habits continue" and body["based_on_months"] == 5
    assert len(body["months"]) == 6 and all(x["p10"] <= x["p50"] <= x["p90"] for x in body["months"])
    assert 0 <= body["shortfall_probability"] <= 1 and 1 <= body["median_path_room_level"] <= 5
    assert client.get("/v1/future", headers=bearer(token())).json() == body                # steady all month


def test_future_self_shows_the_conformal_range_for_the_users_cell(client, monkeypatch):
    seen = {}
    real = m.calibrated_months

    def spy(months, employment_type, n_history, table=None):
        seen.update(raw=months, cell=(employment_type, n_history))
        return real(months, employment_type, n_history, table)
    monkeypatch.setattr(m, "calibrated_months", spy)
    body = client.get("/v1/future", headers=bearer(token())).json()
    assert seen["cell"][1] == body["based_on_months"] == 5                       # D-142: the user's own cell
    adjusted = real(seen["raw"], *seen["cell"])
    assert [(x["p10"], x["p50"], x["p90"]) for x in body["months"]] == [
        (round(a.p10, 2), round(r.p50, 2), round(a.p90, 2)) for a, r in zip(adjusted, seen["raw"])]


def test_the_forecast_seed_comes_from_the_facts_not_the_account():
    """D-150: the same history gives the same range all month and for every copy of a persona (D-94)."""
    from dataclasses import replace
    from sim.monte_carlo import FutureProfile, GameSnapshot
    from engine.state import MonthRecord
    done = [MonthRecord(net_income=2800, debt_payments=300, outstanding_debt=9000, cash=1200 + 100 * i,
                        essential_spending=1500, total_spending=2100, month=4 + i) for i in range(3)]
    fp, snap = FutureProfile("employee", 3), GameSnapshot(1500, 0, 1800, 1)
    seed = m.forecast_seed(done, fp, snap, date(2026, 7, 2))
    assert seed == m.forecast_seed(list(done), fp, snap, date(2026, 7, 30))                  # steady all month
    assert seed != m.forecast_seed(done, fp, snap, date(2026, 8, 1))                         # a new month
    assert seed != m.forecast_seed(done[:2] + [replace(done[2], cash=1401)], fp, snap, date(2026, 7, 2))
    assert seed != m.forecast_seed(done, replace(fp, has_car=True), snap, date(2026, 7, 2))
    assert 0 <= seed < 2 ** 32


def test_future_self_needs_three_complete_months(client, store):
    store.money = money_facts(months=2, profile=money_profile(created_at="2026-04-01T02:00:00+00:00"),
                              checkins=[checkin_row(k) for k in (4, 5)],
                              transactions=[t for k in (4, 5) for t in salary_and_rent(k)])
    body = client.get("/v1/future", headers=bearer(token())).json()
    assert body["available"] is False and "3 complete months" in body["reason"]


# ---------------------------------------------------------------- the real store's new calls
def test_store_reads_six_tables_as_the_user_and_saves_without_overwriting():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        assert req.headers["Authorization"] == "Bearer the-users-token"
        if req.method == "POST":
            assert req.url.path.endswith("/assessments") and req.url.params["on_conflict"] == "user_id,month"
            assert "ignore-duplicates" in req.headers["Prefer"]
            return httpx.Response(201)
        table = req.url.path.rsplit("/", 1)[1]
        return httpx.Response(200, json=[money_profile()] if table == "profiles" else [])

    store = g.SupabaseStore("https://x.supabase.co", "anon", transport=httpx.MockTransport(handler))
    user = auth.CurrentUser(id=USER, token="the-users-token")
    f = store.load_money(user)
    assert f.profile["birth_year"] == 2000
    assert {r.url.path.rsplit("/", 1)[1] for r in seen} == {t for t, _ in g.SupabaseStore.MONEY_TABLES}
    assert all(r.url.params["user_id"] == f"eq.{USER}" for r in seen)
    store.add_assessments(user, [{"month": "2026-01-01", "model_version": "v1", "result": {}}])
