"""Settings from environment variables (T-13).

Secrets live only in the environment: Render's dashboard in production, a local `.env` file in
development (ignored by git, CLAUDE.md rule 7). Nothing secret is ever in the repo or the app.

    SUPABASE_URL          https://<project-ref>.supabase.co
    SUPABASE_ANON_KEY     the project's anon (publishable) key: public by design, sent with the
                          user's own token so Row Level Security applies; needed by /v1/game
    SUPABASE_JWT_SECRET   only for projects still on the legacy shared secret (HS256); new
                          projects sign tokens with asymmetric keys published as JWKS, which need
                          no secret here
    RATE_LIMIT_PER_MINUTE requests per signed-in user per minute (default 60)
    GROQ_API_KEY          the assistant's key (T-17); without it POST /v1/assistant answers 503
    GROQ_MODEL            default llama-3.3-70b-versatile (api/assistant.py)
    ASSISTANT_DAILY_LIMIT questions per user per 24 hours (default 30; Groq's free tier is shared)
The service-role key is never read here (CLAUDE.md rule 8: admin scripts only). Secrets are left
out of the settings' repr, so they can't end up in a log.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _load_dotenv(path: Path = ENV_FILE) -> None:
    """Minimal KEY=VALUE reader; real environment variables always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    jwt_secret: str | None = field(default=None, repr=False)
    rate_limit_per_minute: int = 60
    anon_key: str | None = None
    groq_api_key: str | None = field(default=None, repr=False)
    groq_model: str = DEFAULT_GROQ_MODEL
    assistant_daily_limit: int = 30

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    url = os.environ.get("SUPABASE_URL", "").strip()
    if not url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL must be set to https://<project-ref>.supabase.co")
    return Settings(supabase_url=url, jwt_secret=os.environ.get("SUPABASE_JWT_SECRET") or None,
                    rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
                    anon_key=os.environ.get("SUPABASE_ANON_KEY") or None,
                    groq_api_key=os.environ.get("GROQ_API_KEY") or None,
                    groq_model=os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL,
                    assistant_daily_limit=int(os.environ.get("ASSISTANT_DAILY_LIMIT", "30")))
