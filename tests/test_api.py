"""T-13: the API rejects missing or invalid tokens, takes the user only from the token, validates
bodies, rate-limits per user, and returns the engine's assessment. Tokens are made here with a
test key pair; nothing contacts Supabase."""
import base64
import copy
import hashlib
import hmac
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import api.auth as auth
from api.config import Settings, get_settings
from api.limits import RateLimiter
from api.main import app, get_limiter

URL = "https://testproject.supabase.co"
SETTINGS = Settings(supabase_url=URL, jwt_secret=None, rate_limit_per_minute=5)
KEY = ec.generate_private_key(ec.SECP256R1())          # this project's signing key (ES256)
OTHER = ec.generate_private_key(ec.SECP256R1())        # someone else's key
USER = str(uuid.uuid4())


class FakeJWKS:
    """Stands in for the project's published keys (/auth/v1/.well-known/jwks.json)."""
    def get_signing_key_from_jwt(self, token):
        if jwt.get_unverified_header(token).get("kid") != "k1":
            raise jwt.PyJWKClientError("no matching key")
        return type("K", (), {"key": KEY.public_key()})()


def token(sub=USER, key=KEY, alg="ES256", kid="k1", **over):
    claims = {"sub": sub, "aud": "authenticated", "iss": f"{URL}/auth/v1", "role": "authenticated",
              "exp": int(time.time()) + 600, **over}
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": kid} if kid else None)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "jwks_client", lambda url: FakeJWKS())
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    limiter = RateLimiter(SETTINGS.rate_limit_per_minute)
    app.dependency_overrides[get_limiter] = lambda: limiter
    yield TestClient(app)
    app.dependency_overrides.clear()


def bearer(t):
    return {"Authorization": f"Bearer {t}"}


BODY = {"profile": {"employment_type": "employee", "age": 29, "festive_month": 1},
        "months": [{"net_income": 3600, "debt_payments": 600, "outstanding_debt": 20000, "cash": 7000 + 300 * k,
                    "essential_spending": 1500, "total_spending": 2400, "month": 4 + k, "savings_target": 300}
                   for k in range(4)]}


@pytest.mark.parametrize("typed", [URL, f"{URL}/", f"{URL}/rest/v1/", f" {URL}/rest/v1 ", f"{URL}/auth/v1"])
def test_the_supabase_address_is_its_base_however_it_was_copied(typed):
    """D-147: the dashboard's Data API page shows the address with /rest/v1/ on the end."""
    from api.config import base_url
    assert base_url(typed) == URL


def test_cors_origins_are_explicit_https_addresses():
    """D-151: the web study build's address only; none by default; never a wildcard."""
    from api.config import cors_origins
    assert cors_origins("") == []
    assert cors_origins(" https://fast-web.onrender.com/ , http://localhost:8090 ") == [
        "https://fast-web.onrender.com", "http://localhost:8090"]
    for bad in ("*", "http://fast-web.onrender.com", "https://*.onrender.com", "ftp://x.test"):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            cors_origins(bad)


def test_only_the_listed_browser_address_may_call_the_api():
    from fastapi import FastAPI
    from api.main import allow_browsers
    api = FastAPI()

    @api.get("/v1/ping")
    def ping():
        return {"ok": True}
    allow_browsers(api, ["https://fast-web.onrender.com"])
    c = TestClient(api)
    ask = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    ok = c.options("/v1/ping", headers={"Origin": "https://fast-web.onrender.com", **ask})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "https://fast-web.onrender.com"
    assert "access-control-allow-credentials" not in ok.headers
    other = c.options("/v1/ping", headers={"Origin": "https://evil.test", **ask})
    assert "access-control-allow-origin" not in other.headers
    assert c.get("/v1/ping", headers={"Origin": "https://fast-web.onrender.com"}).headers[
        "access-control-expose-headers"] == "Retry-After"


def test_no_listed_address_means_no_browser_access():
    from fastapi import FastAPI
    from api.main import allow_browsers
    api = FastAPI()
    allow_browsers(api, [])
    assert not any("CORS" in str(m.cls) for m in api.user_middleware)


# ---- sign-in
def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_valid_token_gives_the_tokens_user(client):
    r = client.get("/v1/me", headers=bearer(token()))
    assert r.status_code == 200 and r.json() == {"user_id": USER}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer"}, {"Authorization": "Basic abc"},
                                     {"Authorization": "Bearer not-a-jwt"}])
def test_missing_or_malformed_token_is_rejected(client, headers):
    r = client.get("/v1/me", headers=headers)
    assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("bad", [
    {"exp": int(time.time()) - 3600},                    # expired
    {"aud": "anon"},                                      # wrong audience
    {"iss": "https://evil.supabase.co/auth/v1"},          # another project
    {"role": "anon"},                                     # not a signed-in user
    {"sub": "not-a-uuid"},
], ids=["expired", "audience", "issuer", "role", "subject"])
def test_wrong_claims_are_rejected(client, bad):
    assert client.get("/v1/me", headers=bearer(token(**bad))).status_code == 401


def test_signed_by_another_key_or_unknown_kid_is_rejected(client):
    assert client.get("/v1/me", headers=bearer(token(key=OTHER))).status_code == 401
    assert client.get("/v1/me", headers=bearer(token(kid="k9"))).status_code == 401


def test_algorithm_confusion_and_none_are_rejected(client):
    """A3: an HS256 token signed with the PUBLIC key as the secret, and an unsigned token."""
    pem = KEY.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    claims = {"sub": USER, "aud": "authenticated", "iss": f"{URL}/auth/v1", "role": "authenticated",
              "exp": int(time.time()) + 600}
    forged = _hs256_with(pem, claims)
    unsigned = jwt.encode(claims, None, algorithm="none")
    for t in (forged, unsigned):
        assert client.get("/v1/me", headers=bearer(t)).status_code == 401


def _hs256_with(secret: bytes, claims: dict) -> str:
    """HS256 by hand (PyJWT itself refuses to use a PEM public key as an HMAC secret)."""
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=")  # noqa: E731
    signing_input = enc({"alg": "HS256", "typ": "JWT"}) + b"." + enc(claims)
    sig = base64.urlsafe_b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest()).rstrip(b"=")
    return (signing_input + b"." + sig).decode()


def test_legacy_hs256_secret_works_only_when_configured(client):
    secret = "legacy-test-secret-at-least-32-characters-long"
    t = token(key=secret, alg="HS256", kid=None)
    assert client.get("/v1/me", headers=bearer(t)).status_code == 401           # no secret configured
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_url=URL, jwt_secret=secret)
    assert client.get("/v1/me", headers=bearer(t)).json() == {"user_id": USER}


# ---- the user comes from the token only; bodies are validated
def test_body_cannot_name_a_user(client):
    r = client.post("/v1/assess", headers=bearer(token()), json={**BODY, "user_id": str(uuid.uuid4())})
    assert r.status_code == 422


@pytest.mark.parametrize("patch", [
    lambda b: b["months"][0].update(net_income=-5),       # negative money
    lambda b: b["months"][0].update(month=13),
    lambda b: b["profile"].update(employment_type="ceo"),
    lambda b: b.update(months=[]),
    lambda b: b.update(months=b["months"] * 10),           # 40 months > 36
    lambda b: b["months"][0].update(merchant="Shopee"),     # raw transaction detail not accepted
], ids=["negative", "month13", "employment", "no-months", "too-many", "unknown-field"])
def test_invalid_bodies_are_rejected(client, patch):
    b = copy.deepcopy(BODY)
    patch(b)
    assert client.post("/v1/assess", headers=bearer(token()), json=b).status_code == 422


def test_assess_returns_the_engine_result(client):
    r = client.post("/v1/assess", headers=bearer(token()), json=BODY)
    assert r.status_code == 200
    out = r.json()
    assert out["band"] in {"GREEN", "YELLOW", "RED", "INSUFFICIENT_INCOME"}
    assert 0 <= out["health"]["score"] <= 100 and out["forecast"]["version"] == "forecast_v1"
    from engine.assess import assess
    from engine.features import UserProfile
    from engine.state import MonthRecord
    direct = assess(UserProfile(**BODY["profile"]), [MonthRecord(**m) for m in BODY["months"]])
    assert out == json.loads(json.dumps(direct))


def test_assess_needs_sign_in(client):
    assert client.post("/v1/assess", json=BODY).status_code == 401


# ---- rate limit
def test_rate_limit_per_user(client):
    for _ in range(SETTINGS.rate_limit_per_minute):
        assert client.get("/v1/me", headers=bearer(token())).status_code == 200
    r = client.get("/v1/me", headers=bearer(token()))
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    assert client.get("/v1/me", headers=bearer(token(sub=str(uuid.uuid4())))).status_code == 200   # others unaffected


def test_deployed_requirements_match_the_tested_lock():
    """D-70: Render installs requirements-api.txt; every pin there is the version tested locally."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]

    def pins(name):
        lines = (root / name).read_text(encoding="utf-8").splitlines()
        return dict(line.split("==") for line in lines if "==" in line and not line.startswith("#"))
    api, lock = pins("requirements-api.txt"), {k.lower(): v for k, v in pins("requirements-lock.txt").items()}
    assert "httpx" in api
    for package, version in api.items():
        assert lock.get(package.lower()) == version, package


def test_rate_window_slides():
    now = [0.0]
    rl = RateLimiter(2, window=60, clock=lambda: now[0])
    assert rl.check("u") is None and rl.check("u") is None and rl.check("u") == pytest.approx(60)
    now[0] = 59.9
    assert rl.check("u") is not None
    now[0] = 60.0
    assert rl.check("u") is None
