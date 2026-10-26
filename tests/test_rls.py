"""T-12 / O3, LIVE: one user can never read or change another user's data (Row Level Security).

Runs against the hosted Supabase project once it exists, and is skipped until then. Setup (Patrick):
  1. create the project (Singapore) and run supabase/migrations/20261014000000_init.sql in the SQL editor
  2. Authentication -> Users -> "Add user" twice: two TEST users (made-up emails, synthetic data only)
  3. put in .env (never committed):  SUPABASE_URL, SUPABASE_ANON_KEY, RLS_TEST_A_EMAIL,
     RLS_TEST_A_PASSWORD, RLS_TEST_B_EMAIL, RLS_TEST_B_PASSWORD
The anon (publishable) key is public by design; only RLS stands between users, which is what this
proves. The service-role key is not used.
"""
import os
import uuid

import pytest

from api.config import _load_dotenv

_load_dotenv()
NEEDED = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "RLS_TEST_A_EMAIL", "RLS_TEST_A_PASSWORD",
          "RLS_TEST_B_EMAIL", "RLS_TEST_B_PASSWORD"]
pytestmark = pytest.mark.skipif(any(not os.environ.get(k) for k in NEEDED),
                                reason="live Supabase project not configured yet (see module docstring)")


@pytest.fixture(scope="module")
def http():
    import httpx
    url, anon = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_ANON_KEY"]

    def sign_in(who):
        r = httpx.post(f"{url}/auth/v1/token?grant_type=password", headers={"apikey": anon},
                       json={"email": os.environ[f"RLS_TEST_{who}_EMAIL"],
                             "password": os.environ[f"RLS_TEST_{who}_PASSWORD"]}, timeout=20)
        r.raise_for_status()
        body = r.json()
        return body["access_token"], body["user"]["id"]

    users = {who: sign_in(who) for who in ("A", "B")}

    def call(who, method, path, **kw):
        token = users[who][0]
        headers = {"apikey": anon, "Authorization": f"Bearer {token}", "Prefer": "return=representation"}
        return httpx.request(method, f"{url}/rest/v1/{path}", headers=headers, timeout=20, **kw)

    return call, {who: uid for who, (_, uid) in users.items()}


def test_another_users_rows_are_invisible_and_untouchable(http):
    call, ids = http
    row = {"occurred_on": "2026-10-01", "direction": "out", "amount": "12.50", "category": "food",
           "note": f"rls-test {uuid.uuid4()}"}
    created = call("A", "POST", "transactions", json=row)
    assert created.status_code == 201, created.text
    tx = created.json()[0]
    assert tx["user_id"] == ids["A"]                                    # set from the token, not the body
    try:
        # B reads: 0 of A's rows
        assert call("B", "GET", f"transactions?id=eq.{tx['id']}&select=id").json() == []
        assert all(r["user_id"] == ids["B"] for r in call("B", "GET", "transactions?select=user_id").json())
        # B changes or deletes: nothing happens
        assert call("B", "PATCH", f"transactions?id=eq.{tx['id']}", json={"amount": "999"}).json() == []
        assert call("B", "DELETE", f"transactions?id=eq.{tx['id']}").json() == []
        # B writes a row in A's name: refused
        assert call("B", "POST", "transactions", json={**row, "user_id": ids["A"]}).status_code >= 400
        # A's row is unchanged
        assert call("A", "GET", f"transactions?id=eq.{tx['id']}&select=amount").json() == [{"amount": 12.5}]
    finally:
        call("A", "DELETE", f"transactions?id=eq.{tx['id']}")


def test_users_cannot_award_themselves_points(http):
    """D-76: points and levels are never stored (the API replays them), so there is no table to write."""
    call, ids = http
    for table in ("points_ledger", "game_state"):
        r = call("A", "POST", table, json={"user_id": ids["A"], "points": 1000})
        assert r.status_code >= 400, table


def test_security_review_rules_hold_live(http):
    """D-93: a saved assessment can't be changed or removed (S-3); the profile can't be deleted on its
    own (S-1); the persona clock says nothing about another account (S-5). The test users have no
    profile, so the profile check only proves DELETE is not allowed to touch anything."""
    call, ids = http
    month = "2020-01-01"                                                # far outside any real data
    made = call("A", "POST", "assessments", json={"month": month, "model_version": "rls-test", "result": {}})
    assert made.status_code in (201, 409), made.text
    assert call("A", "PATCH", f"assessments?month=eq.{month}", json={"result": {"band": "GREEN"}}).json() == []
    assert call("A", "DELETE", f"assessments?month=eq.{month}").json() == []
    assert call("A", "GET", f"assessments?month=eq.{month}&select=result").json() == [{"result": {}}]
    assert call("A", "DELETE", f"profiles?user_id=eq.{ids['A']}").json() == []
    clock = call("A", "POST", "rpc/study_now", json={"uid": ids["B"]})
    assert clock.status_code == 200                                     # the real clock, whoever B is


def test_game_actions_only_in_your_own_name(http):
    call, ids = http
    row = {"kind": "buy_tree"}
    assert call("B", "POST", "game_actions", json={**row, "user_id": ids["A"]}).status_code >= 400
    assert call("B", "GET", f"game_actions?user_id=eq.{ids['A']}&select=id").json() == []
    assert call("B", "GET", f"game_days?user_id=eq.{ids['A']}&select=day").json() == []   # the view obeys RLS
