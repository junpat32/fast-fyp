"""Load the study personas into Supabase (A4, D-90). An ADMIN script: it uses the service-role key,
the one place that key is ever used (CLAUDE.md rule 8). Never run it against anything but the
FAST project, and never commit the key.

    .venv\\Scripts\\python -m tools.personas.seed                         # the four shared persona accounts
    .venv\\Scripts\\python -m tools.personas.seed --reset                 # delete them first, then load again
    .venv\\Scripts\\python -m tools.personas.seed --delete                # delete them only
    .venv\\Scripts\\python -m tools.personas.seed --participant P07       # one participant's own accounts (SR1)
    .venv\\Scripts\\python -m tools.personas.seed --participant P07 --delete   # remove them after the session
    .venv\\Scripts\\python -m tools.personas.seed --delete-all-participants    # end of the study

Needs, in the environment or in .env (never in the repo): SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
and for the shared accounts PERSONA_PASSWORD. Reads data/personas/personas.json
(python -m tools.personas.build).

**Per participant (SR1, D-94).** Each participant gets five accounts made for them alone: a copy of
each persona (`aina.p07@personas.fast.test` ...) and one empty account for the sign-up task
(`new.p07@personas.fast.test`, no rows: the app opens its onboarding). All five share one random,
easy-to-type password, printed once and written to data/sessions/p07.md (data/ is never committed).
Nobody else ever has these logins, two sessions can't disturb each other, and deleting them after
the session ends any later access. The participant code is the only thing about the person in an
email address (P for the main study, T for the pilot; never a name). The persona order comes from
a balanced Latin square (Williams design), so each persona follows each other one equally often.

Order matters: the profile first (it makes the account a persona); transactions before check-ins,
because the database works out each check-in's logged totals from the entries already there
(freeze_logged_sums); the game's actions last. Admin inserts keep the timestamps given, so the
persona's history lands on its own dates (the database's admin path, set_created_at).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "personas" / "personas.json"
SESSIONS = ROOT / "data" / "sessions"                  # git-ignored: the session cards with passwords
BATCH = 500
TABLES = (("profiles", "profile"), ("debts", "debts"), ("transactions", "transactions"),
          ("life_event_answers", "cards"), ("monthly_checkins", "checkins"), ("game_actions", "game_actions"))
DOMAIN = "personas.fast.test"                          # .test is reserved: these addresses never deliver
CODE = re.compile(r"^([pt])0*(\d{1,3})$", re.I)
WILLIAMS = ((0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1))    # balanced order of 4 personas
WORDS = ("kopi", "teh", "roti", "nasi", "mee", "satay", "laksa", "durian", "rambutan", "pisang", "kelapa",
         "sambal", "cendol", "rojak", "kuih", "mangga", "nangka", "betik", "jambu", "limau", "halia", "serai",
         "pandan", "gula", "santan", "tauhu", "kangkung", "petai", "keropok", "teratai", "merak", "harimau",
         "kancil", "tapir", "enggang", "penyu", "pelangi", "bukit", "sungai", "pantai", "awan", "bintang")


def env(name: str) -> str:
    """From the environment, else from .env (a tiny reader: KEY=value lines; no extra dependency)."""
    if os.environ.get(name):
        return os.environ[name]
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip().strip('"').strip("'")
    raise SystemExit(f"{name} is not set (put it in .env, which is never committed)")


class Admin:
    def __init__(self, url: str, service_key: str, transport: httpx.BaseTransport | None = None):
        headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        self.http = httpx.Client(base_url=url.rstrip("/"), headers=headers, timeout=60, transport=transport)

    def users(self) -> list[dict]:
        out, page = [], 1
        while True:
            r = self.http.get("/auth/v1/admin/users", params={"page": page, "per_page": 1000})
            r.raise_for_status()
            batch = r.json().get("users", [])
            out += batch
            if len(batch) < 1000:
                return out
            page += 1

    def find_user(self, email: str) -> str | None:
        return next((u["id"] for u in self.users() if u.get("email") == email), None)

    def delete_user(self, uid: str) -> None:
        self.http.delete(f"/auth/v1/admin/users/{uid}").raise_for_status()     # their rows go too (cascade)

    def create_user(self, email: str, password: str) -> str:
        r = self.http.post("/auth/v1/admin/users", json={"email": email, "password": password, "email_confirm": True})
        r.raise_for_status()
        return r.json()["id"]

    def insert(self, table: str, rows: list[dict]) -> None:
        for i in range(0, len(rows), BATCH):
            r = self.http.post(f"/rest/v1/{table}", json=rows[i:i + BATCH], headers={"Prefer": "return=minimal"})
            r.raise_for_status()

    def select(self, table: str, uid: str) -> list[dict]:
        r = self.http.get(f"/rest/v1/{table}", params={"select": "*", "user_id": f"eq.{uid}"})
        r.raise_for_status()
        return r.json()


def load_persona(admin: Admin, p: dict, password: str, email: str | None = None) -> str:
    uid = admin.create_user(email or p["email"], password)
    for table, key in TABLES:
        rows = p[key] if isinstance(p[key], list) else [p[key]]
        admin.insert(table, [{**row, "user_id": uid} for row in rows])
    return uid


# ---------------------------------------------------------------- one participant's accounts (SR1)
def participant_code(text: str) -> str:
    """'P7', 'p07', 'T1' -> 'p07', 't01'. Anything else (a name, an email) is refused."""
    match = CODE.match(text.strip())
    if not match:
        raise SystemExit(f"{text!r} is not a participant code: use P01-P999 (main study) or T01-T999 (pilot)")
    return f"{match.group(1).lower()}{int(match.group(2)):02d}"


def persona_email(p: dict, code: str) -> str:
    return f"{p['meta']['name'].lower()}.{code}@{DOMAIN}"


def onboarding_email(code: str) -> str:
    return f"new.{code}@{DOMAIN}"


def persona_order(code: str, n: int = 4) -> tuple[int, ...]:
    """Row (number - 1) mod 4 of the Williams square: P01 A-B-D-C, P02 B-C-A-D, P03 C-D-B-A, P04 D-A-C-B."""
    return WILLIAMS[(int(code[1:]) - 1) % len(WILLIAMS)][:n]


def new_password(rng=secrets.SystemRandom()) -> str:
    """Two words and four digits, e.g. 'laksa-merak-4821': easy to type on a phone, about 24 bits of
    randomness, which is plenty for accounts that live for one session (sign-in is rate-limited)."""
    return f"{rng.choice(WORDS)}-{rng.choice(WORDS)}-{rng.randrange(1000, 10000)}"


def session_card(code: str, personas: list[dict], password: str) -> str:
    letters = "ABCD"
    order = persona_order(code, len(personas))
    lines = [f"# Study accounts for {code.upper()}", "",
             "Made by `python -m tools.personas.seed`. **Delete them after the session**: "
             f"`python -m tools.personas.seed --participant {code.upper()} --delete` "
             "(check the sign-up task first: `python -m tools.personas.onboarding --participant "
             f"{code.upper()}`).", "",
             f"Password for all five accounts: **{password}**", "",
             "| Step | Account | Email |", "|---|---|---|",
             f"| Sign-up task (empty account; card: docs/study/onboarding_card.md) | new | `{onboarding_email(code)}` |"]
    for k, i in enumerate(order, 1):
        p = personas[i]
        lines.append(f"| Persona {k} ({letters[i]}) | {p['meta']['name']} | `{persona_email(p, code)}` |")
    lines += ["", f"Persona order on the questionnaire: {'-'.join(letters[i] for i in order)}"]
    return "\n".join(lines) + "\n"


def make_participant(admin: Admin, personas: list[dict], code: str, password: str | None = None) -> str:
    existing = {u.get("email") for u in admin.users()}
    emails = [onboarding_email(code)] + [persona_email(p, code) for p in personas]
    if clash := [e for e in emails if e in existing]:
        raise SystemExit(f"{code.upper()} already has accounts ({clash[0]} ...): delete them first with --delete")
    password = password or new_password()
    admin.create_user(onboarding_email(code), password)               # empty: the app opens its onboarding
    for p in personas:
        load_persona(admin, p, password, persona_email(p, code))
    card = session_card(code, personas, password)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    (SESSIONS / f"{code}.md").write_text(card, encoding="utf-8")
    return card


def delete_participants(admin: Admin, code: str | None = None) -> list[str]:
    """One participant's accounts, or every participant's (code=None). The shared four are kept."""
    pattern = re.compile(rf"^[a-z]+\.{code or '[pt][0-9]{2,3}'}@{re.escape(DOMAIN)}$")
    gone = []
    for u in admin.users():
        if pattern.match(u.get("email") or ""):
            admin.delete_user(u["id"])
            gone.append(u["email"])
    for c in {code} if code else {e.split(".")[1].split("@")[0] for e in gone}:
        (SESSIONS / f"{c}.md").unlink(missing_ok=True)
    return gone


def main(argv=None, admin: Admin | None = None) -> None:
    ap = argparse.ArgumentParser(description="Load the user-study personas (admin only)")
    ap.add_argument("--reset", action="store_true", help="delete existing personas first")
    ap.add_argument("--delete", action="store_true", help="delete the personas (or a participant's accounts) and stop")
    ap.add_argument("--participant", help="make (or with --delete remove) one participant's own accounts, e.g. P07")
    ap.add_argument("--delete-all-participants", action="store_true", help="remove every participant's accounts")
    a = ap.parse_args(argv)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    admin = admin or Admin(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"))
    if a.delete_all_participants or a.participant:
        code = None if a.delete_all_participants else participant_code(a.participant)
        if a.delete or a.delete_all_participants:
            gone = delete_participants(admin, code)
            print(f"deleted {len(gone)} accounts" + "".join(f"\n  {e}" for e in gone))
        else:
            print(make_participant(admin, data["personas"], code))
        return
    for p in data["personas"]:
        existing = admin.find_user(p["email"])
        if existing and (a.reset or a.delete):
            admin.delete_user(existing)
            print(f"deleted {p['key']} ({p['email']})")
        elif existing:
            raise SystemExit(f"{p['email']} already exists: use --reset to load it again")
    if a.delete:
        return
    password = env("PERSONA_PASSWORD")
    for p in data["personas"]:
        load_persona(admin, p, password)
        print(f"loaded {p['key']} {p['meta']['name']}: {len(p['transactions'])} transactions, "
              f"{len(p['checkins'])} check-ins -> {p['email']}")


if __name__ == "__main__":
    main()
