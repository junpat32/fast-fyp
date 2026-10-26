"""Supabase sign-in check (T-13). The user ID comes ONLY from a verified token.

Invariants
  A1  every protected endpoint needs `Authorization: Bearer <access token>` from Supabase Auth
  A2  the token's signature, expiry, audience ("authenticated") and issuer (this project) are all
      checked; the user ID is its `sub` claim, never anything the request body says
  A3  the algorithm is taken from the key, not trusted from the token: asymmetric tokens are
      checked only against this project's published keys (JWKS), HS256 only against the legacy
      secret, and only if one is configured. This blocks the "algorithm confusion" attack, where a
      forged HS256 token is signed with the public key as if it were a shared secret
  A4  failures say little (401 + WWW-Authenticate), so they don't help an attacker
The token is kept so the backend can query Supabase *as this user*, under Row Level Security
(CLAUDE.md rule 8); the service-role key is never used here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings

ASYMMETRIC = ("ES256", "RS256")          # Supabase JWT signing keys (JWKS)
AUDIENCE = "authenticated"
LEEWAY_SECONDS = 30                      # small clock skew between phone, Supabase and Render


@dataclass(frozen=True)
class CurrentUser:
    id: str                              # auth.users.id, from the verified token's `sub`
    token: str                           # forwarded to Supabase so RLS applies


_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def jwks_client(url: str) -> jwt.PyJWKClient:
    """One cached client per project: keys are fetched once and reused for an hour."""
    if url not in _jwks_clients:
        _jwks_clients[url] = jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)
    return _jwks_clients[url]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def verify_token(token: str, settings: Settings) -> CurrentUser:
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError:
        raise _unauthorized("malformed token") from None
    if alg in ASYMMETRIC:
        try:
            key = jwks_client(settings.jwks_url).get_signing_key_from_jwt(token).key
        except jwt.PyJWTError:
            raise _unauthorized("unknown signing key") from None
    elif alg == "HS256" and settings.jwt_secret:
        key = settings.jwt_secret
    else:
        raise _unauthorized("unsupported token")
    try:
        claims = jwt.decode(token, key, algorithms=[alg], audience=AUDIENCE, issuer=settings.issuer,
                            leeway=LEEWAY_SECONDS, options={"require": ["exp", "sub", "aud", "iss"]})
    except jwt.ExpiredSignatureError:
        raise _unauthorized("token expired") from None
    except jwt.PyJWTError:
        raise _unauthorized("invalid token") from None
    if claims.get("role") != "authenticated":
        raise _unauthorized("not a signed-in user")
    try:
        user_id = str(uuid.UUID(str(claims["sub"])))
    except ValueError:
        raise _unauthorized("invalid token") from None
    return CurrentUser(id=user_id, token=token)


def current_user(request: Request, settings: Settings = Depends(get_settings)) -> CurrentUser:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("missing bearer token")
    return verify_token(token.strip(), settings)
