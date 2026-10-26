"""Study personas (T-18, A4, D-90): four synthetic users from the O2 dataset, as the app's own rows.

    .venv\\Scripts\\python -m tools.personas.build     # -> data/personas/personas.json, docs/personas.md

Each persona is one user of data/synthetic/medium_seed20261009 (synthetic only, CLAUDE.md rule 12),
turned into exactly the rows the app holds for a real user who logs honestly: a profile (the sign-up
answers), the debts list, every transaction, a monthly check-in, weekly cards, and a few plants
bought with the game's choices. Nothing about a persona is stored that a real user couldn't have.

Timeline: the generator's months 1-12 (calendar 2025) become January-December 2026, the same calendar
months, so festive and semester months stay where they were. The persona signs up on 1 January
2026, logs each transaction on its day and checks in on each month's last day. The study clock
starts on 1 July 2026 (six months of history; June's check-in is the latest) and time travel moves
it a month at a time to 1 January 2027 (the whole year). The API hides every row after the clock.

Invariants
  P1  synthetic only: every number comes from the generator's tables; hidden traits are never used
  P2  the rows have the database's own columns and rules (types, the 24-hour offline check, BNPL as
      purchases plus instalments, card spending on credit), so the seed script inserts them as they are
  P3  the persona notes (docs/personas.md) are computed with the API's own functions (api.money,
      api.game) at each study date, so they show what the app will show
Cost: O(transactions) per persona; a few seconds for all four.
"""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from api import cards
from api import game as g
from api import money as m
from engine.assess import assess
from engine.game import Plant, load_game, replay

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "synthetic" / "medium_seed20261009"
OUT = ROOT / "data" / "personas" / "personas.json"
DOC = ROOT / "docs" / "personas.md"
YEAR = 2026
SIGN_UP = "2025-12-31T16:30:00+00:00"                  # 1 January 2026, 00:30 Malaysia time
STUDY_FIRST, STUDY_LAST = date(2026, 7, 1), date(2027, 1, 1)
CATEGORIES = json.loads((ROOT / "shared" / "categories.json").read_text(encoding="utf-8"))
ESSENTIAL = {c["key"] for c in CATEGORIES["out"] if c["essential"]}      # one list with the app (D-112, rule 5)
DEBT = {"HIREPURCHASE_CAR": ("car", "Car loan", "car_loan", "car_loan"),        # kind, label, category, generator column
        "HIREPURCHASE_MOTORBIKE": ("other", "Motorbike loan", "motorbike_loan", "motorbike_loan"),
        "PTPTN": ("ptptn", "PTPTN", "ptptn", "ptptn"),
        "PERSONAL_LOAN": ("personal", "Personal loan", "personal_loan", "personal_loan"),
        "CREDIT_CARD": ("credit_card", "Credit card", "credit_card", "card"),
        "BNPL_PROVIDER": (None, None, "bnpl_instalment", None)}    # BNPL: the app counts it from the purchases
INCOME = {"EMPLOYER": "salary", "GIGPLATFORM": "gig_income", "ALLOWANCE": "allowance"}
SOURCE_OF = {"manual": "typed", "notification": "pasted", "ocr": "receipt"}
EMAIL = "{key}@personas.fast.test"                     # .test is reserved: these addresses never deliver


@dataclass(frozen=True)
class Persona:
    key: str
    user_id: int           # in the synthetic dataset
    name: str              # a first name for the study script; never stored in the database
    story: str             # one line for the participant (docs/personas.md)
    avatar: int            # the character, as a user picks one at sign-up (D-110, D-124; Patrick may change them)


# Proposed for Patrick's review (T-18 is "Both"): chosen for four different situations the study asks
# about, from users whose year has something to notice when time travel moves on.
PERSONAS = [
    Persona("persona_01", 357, "Aina", "A 21-year-old student living with her parents. Little debt, a few Buy Now Pay "
            "Later plans, and money that often runs out before the allowance comes.", 5),
    Persona("persona_02", 887, "Jason", "A 28-year-old e-hailing driver paying off the car he works with. His income "
            "changes a lot from month to month, and repairs come out of nowhere.", 6),
    Persona("persona_03", 662, "Priya", "A 25-year-old office worker with a car loan and a motorbike loan. Her debt "
            "payments take more than half of her pay.", 4),
    Persona("persona_04", 905, "Daniel", "A 34-year-old employee with a motorbike loan, a credit card and BNPL plans. "
            "Things look fine, until the second half of the year.", 3),
]
CHARACTERS = json.loads((ROOT / "assets" / "isometric" / "characters.json").read_text(encoding="utf-8"))


def _day(d) -> date:
    return pd.Timestamp(d).date().replace(year=YEAR)


def _month_end(year: int, month: int) -> date:
    return (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1))


def _utc_noon_my(d: date, hour_my: int = 20) -> str:
    """A Malaysian clock time on day d, as the database's UTC timestamp."""
    return f"{d.isoformat()}T{hour_my - 8:02d}:00:00+00:00"


def _seeded(key: str) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(key.encode()))


def profile_row(u: pd.Series, mo: pd.DataFrame, avatar: int) -> dict:
    first3 = mo[mo.month <= 3]
    declared = float(round(first3.net_income.median(), -1))
    vehicle = {(True, True): "both", (True, False): "car", (False, True): "motorcycle"}.get(
        (bool(u.has_car), bool(u.has_motorbike)), "none")
    costs = float(round((first3.spend_essential + first3.commitments_total).mean(), -1))
    m1 = mo[mo.month == 1].iloc[0]
    kind = u.employment_type
    return {
        "employment_type": kind, "birth_year": YEAR - int(u.age), "lives_with_parents": bool(u.lives_with_parents),
        "family_support": bool(u.family_support), "festive_month": int(u.festive_month), "vehicle": vehicle,
        "typical_monthly_costs": costs, "declared_income": declared,
        "onboarding_counted_money": round(float(u.starting_cash), 2), "onboarding_other_money": 0.0,
        "onboarding_debt": round(float(m1.outstanding_debt + m1.commitments_total), 2),
        "savings_goal_monthly": (30.0 if kind == "student" else float(round(0.10 * declared, -1))) if kind != "gig" else None,
        "savings_goal_share": 0.05 if kind == "gig" else None,
        "game_employment_type": kind, "game_lives_with_parents": bool(u.lives_with_parents), "game_typical_costs": costs,
        # skin tone 1-6 as profiles stores it (characters.json counts from 0)
        "avatar": avatar, "skin_tone": CHARACTERS["avatars"][avatar - 1]["suggested_tone"] + 1, "glasses": False,
        "is_persona": True, "study_date": STUDY_FIRST.isoformat(), "study_first": STUDY_FIRST.isoformat(),
        "study_last": STUDY_LAST.isoformat(), "created_at": SIGN_UP}


def debt_rows(mo: pd.DataFrame, merchants: set) -> list[dict]:
    m1 = mo[mo.month == 1].iloc[0]
    rows = []
    for merchant, (kind, label, _, col) in DEBT.items():
        if kind is None or merchant not in merchants:
            continue
        pay = mo[f"pay_{col}" if col != "card" else "pay_card_min"]
        bal = m1[f"bal_{col}"]
        rows.append({"kind": kind, "label": label, "monthly_payment": round(float(pay[pay > 0].median()), 2),
                     "outstanding": round(float(bal + m1[pay.name]), 2), "deducted_from_salary": False,
                     "starts_on": None, "ends_on": None, "created_at": SIGN_UP})
    return rows


def transaction_rows(tx: pd.DataFrame, mo: pd.DataFrame) -> list[dict]:
    rows = []
    for t in tx.itertuples():
        d = _day(t.date)
        cat, essential, debt_pay, bnpl, unexpected = t.category, False, False, False, False
        if t.kind == "income":
            cat = INCOME[t.merchant.rsplit("_", 1)[0] if t.merchant[-1].isdigit() else t.merchant]
        elif t.kind == "debt":
            if t.merchant == "BNPL_LATE_FEE":
                cat = m.FEES
            else:
                cat, debt_pay = DEBT[t.merchant][2], True
        elif t.kind == "bnpl_purchase":
            cat, bnpl = "shopping", True
        elif t.kind in ("transfer", "life_event"):
            cat = m.FAMILY if t.category == "family_transfer" else t.category
            unexpected = t.kind == "life_event"
        if cat in ESSENTIAL:
            essential = True
        stamp = _utc_noon_my(d)
        rows.append({"occurred_on": d.isoformat(), "direction": t.direction, "amount": round(float(t.amount), 2),
                     "category": cat, "is_essential": essential, "is_bnpl": bnpl, "on_credit": False,
                     "is_debt_payment": debt_pay, "is_own_transfer": False, "is_unexpected": unexpected, "note": None,
                     "source": SOURCE_OF[t.source], "client_logged_at": stamp, "created_at": stamp})
    # spending paid by credit card leaves the bank only when the card is paid (P2): the biggest
    # non-essential purchases of each month, up to what went on the card that month
    for r in mo[mo.card_draw > 0].itertuples():
        month = [x for x in rows if date.fromisoformat(x["occurred_on"]).month == r.month and x["direction"] == "out"
                 and not (x["is_debt_payment"] or x["is_bnpl"] or x["is_essential"] or x["is_unexpected"])]
        left = float(r.card_draw)
        for x in sorted(month, key=lambda x: -x["amount"]):
            if left <= 0:
                break
            x["on_credit"], left = True, left - x["amount"]
    return rows


def checkin_rows(mo: pd.DataFrame, txs: list[dict]) -> list[dict]:
    """On each month's last day at 23:00 (nothing logged yet for the next month), with the month's
    logged totals worked out as the database does (freeze_logged_sums)."""
    rows = []
    for r in mo.itertuples():
        end = _month_end(YEAR, r.month)
        month = [t for t in txs if date.fromisoformat(t["occurred_on"]).month == r.month]
        out = [t for t in month if t["direction"] == "out" and not t["is_own_transfer"]]
        rows.append({
            "month": date(YEAR, r.month, 1).isoformat(), "created_at": _utc_noon_my(end, 23),
            "cash_bank_ewallet": round(float(r.cash), 2), "epf_fleksibel": 0.0, "others_emergency": 0.0, "others": 0.0,
            "epf_retirement": None, "epf_voluntary": 0.0, "epf_compulsory_to_fleksibel": 0.0,
            "debt_total": round(float(r.outstanding_debt), 2), "net_income": round(float(r.net_income), 2),
            "bills_paid_on_time": bool(r.arrears == 0 and r.late_fees == 0), "ran_short": bool(r.shortfall),
            "logged_in": round(sum(t["amount"] for t in month if t["direction"] == "in"), 2),
            "logged_out": round(sum(t["amount"] for t in out if not (t["on_credit"] or t["is_bnpl"])), 2),
            "logged_costs": round(sum(t["amount"] for t in out if t["is_essential"] or t["is_debt_payment"]), 2),
            "logged_debt_paid": round(sum(t["amount"] for t in out if t["is_debt_payment"]), 2),
            "after_month_net": 0.0, "after_month_debt": 0.0})
    return rows


def card_rows(key: str, profile: dict) -> list[dict]:
    """Weekly cards on most Mondays (a persona that engages with the app, as the study assumes). Each
    week's event is the card the server draws for that week (api/cards.py, D-117), so GET /v1/card can
    show the persona's answer: an event outside the deck has no card text."""
    rng = _seeded(key + "cards")
    events = [f"L{k:02d}" for k in range(1, 22)]
    responses = ["use_savings", "cut_spending", "set_goal"]
    rows, d = [], date(YEAR, 1, 5)                     # the first Monday
    while d <= _month_end(YEAR, 12):
        if rng.random() < 0.8:
            rng.choice(events)                         # the pre-deck draw (D-90), kept so the weeks and answers stay
            rows.append({"week": d.isoformat(), "event_id": cards.draw(key, d, profile),
                         "response": str(rng.choice(responses)), "created_at": _utc_noon_my(d)})
        d += timedelta(days=7)
    return rows


def game_days(txs: list[dict], cards: list[dict]) -> list[dict]:
    """What the database's game_days view gives: entries per day (by when the phone saved them) and cards."""
    days: dict[str, dict] = {}
    for t in txs:
        day = g.my_day(t["client_logged_at"]).isoformat()
        days.setdefault(day, {"day": day, "entries": 0, "no_spend": False, "card": False})["entries"] += 1
    for c in cards:
        day = g.my_day(c["created_at"]).isoformat()
        days.setdefault(day, {"day": day, "entries": 0, "no_spend": False, "card": False})["card"] = True
    return [days[k] for k in sorted(days)]


_ASSESSED: dict[str, list[dict]] = {}


def assessments(p: dict) -> list[dict]:
    """Every check-in's assessment, as GET /v1/game saves them (S-4, D-93); each month uses its own
    months only, so one computation serves every study date."""
    if p["key"] not in _ASSESSED:
        money = m.MoneyFacts(profile=p["profile"], transactions=p["transactions"], debts=p["debts"],
                             checkins=p["checkins"])
        _ASSESSED[p["key"]] = m.missing_assessments(money, STUDY_LAST)
    return _ASSESSED[p["key"]]


def game_facts(p: dict, until: date | None = None) -> g.GameFacts:
    f = g.GameFacts(profile=p["profile"], checkins=p["checkins"], days=game_days(p["transactions"], p["cards"]),
                    actions=p.get("game_actions", []), assessments=assessments(p))
    return g.as_of(f, until) if until else f


def plan_garden(p: dict) -> list[dict]:
    """A few plants bought with the persona's own choices: after each check-in once the garden is
    open, one plant in the next empty bed cell, kept only if the replay accepts it."""
    plants_by_tier = {}
    for name, tier in load_game()["garden"]["plants"].items():
        plants_by_tier.setdefault(tier, []).append(name)
    actions: list[dict] = []
    for k in range(3, 13):
        day = _month_end(YEAR, k) + timedelta(days=1)
        p["game_actions"] = actions
        prof, inputs = g.game_inputs(game_facts(p, day))
        st = replay(prof, day, strict=False, **inputs)
        empty = sorted(set(st.bed()) - set(st.plants))
        if not (st.garden_open and st.choices_available and empty):
            continue
        options = [n for t in range(1, st.plant_tier + 1) for n in plants_by_tier.get(t, [])]
        item = options[len(actions) % len(options)]
        row = {"kind": "plant", "gx": empty[0][0], "gy": empty[0][1], "item": item, "spot": None,
               "created_at": _utc_noon_my(day, 12)}
        new = Plant(day, empty[0], item)
        test = replay(prof, day, strict=False, **{**inputs, "actions": inputs["actions"] + [new]})
        if not any(e is new for e, _ in test.rejected):
            actions.append(row)
    return actions


def build_persona(per: Persona, users: pd.DataFrame, monthly: pd.DataFrame, tx: pd.DataFrame) -> dict:
    u = users.loc[per.user_id]
    mo = monthly[monthly.user_id == per.user_id].sort_values("month")
    ut = tx[tx.user_id == per.user_id].sort_values(["date", "txn_id"])
    txs = transaction_rows(ut, mo)
    p = {"key": per.key, "email": EMAIL.format(key=per.key), "meta": {"name": per.name, "story": per.story,
                                                                     "source_user_id": per.user_id},
         "profile": profile_row(u, mo, per.avatar), "debts": debt_rows(mo, set(ut[ut.kind == "debt"].merchant)),
         "transactions": txs, "checkins": checkin_rows(mo, txs)}
    p["cards"] = card_rows(per.key, p["profile"])
    p["game_actions"] = plan_garden(p)
    return p


# ---------------------------------------------------------------- what the app will show (P3)
def study_dates() -> list[date]:
    out, d = [], STUDY_FIRST
    while d <= STUDY_LAST:
        out.append(d)
        d = date(d.year + d.month // 12, d.month % 12 + 1, 1)
    return out


def snapshot(p: dict, today: date) -> dict:
    money = m.as_of(m.MoneyFacts(profile=p["profile"], transactions=p["transactions"], debts=p["debts"],
                                 checkins=p["checkins"]), today)
    profile, records, months = m.assess_inputs(money, today)
    a = assess(profile, records[:m.assessed_upto(months)])                # as GET /v1/assess does
    prof, inputs = g.game_inputs(game_facts(p, today))
    st = replay(prof, today, strict=False, **inputs)
    fc = a.get("forecast") or {}
    return {"date": today.isoformat(), "band": a["band"], "dsr": a["dsr"], "cushion": a["cushion_months"],
            "health": (a.get("health") or {}).get("score"), "tier": (a.get("health") or {}).get("tier"),
            "forecast": fc.get("probability"),
            "reasons": [f"{r['label']} ({r['direction']})" for r in (fc.get("reasons") or [])][:2],
            "advice": [x["rule"] for x in (a.get("advice") or [])][:2],
            "points": st.points, "room": st.room_level, "garden": st.garden_level if st.garden_open else None,
            "plants": len(st.plants), "verified": sum(1 for x in st.months if x.verified), "months": len(st.months)}


def write_doc(personas: list[dict], snaps: dict) -> str:
    lines = ["# Study personas (T-18, D-90)", "",
             "Four synthetic users from the O2 dataset (`data/synthetic/medium_seed20261009`), built by "
             "`tools/personas/build.py` into the app's own rows and loaded by `tools/personas/seed.py`. "
             "**Synthetic only** (rule 12); the names are for the study script and are never stored. "
             "**Proposed for Patrick's review.**", "",
             "Timeline: January-December 2026. The study clock starts on **1 July 2026** (six months behind it) "
             "and time travel moves it a month at a time to 1 January 2027. Every number below is what the app "
             "shows at that study date (computed with the API's own functions).", ""]
    for p in personas:
        meta, prof = p["meta"], p["profile"]
        lines += [f"## {meta['name']} ({p['key']}, synthetic user {meta['source_user_id']})", "", meta["story"], "",
                  f"Sign-up: {prof['employment_type']}, born {prof['birth_year']}, "
                  f"{'lives with parents' if prof['lives_with_parents'] else 'lives on their own'}, vehicle: "
                  f"{prof['vehicle']}, declared income RM{prof['declared_income']:,.0f}, typical costs "
                  f"RM{prof['typical_monthly_costs']:,.0f}, debts: "
                  f"{', '.join(d['label'] for d in p['debts']) or 'none'}. Login: `{p['email']}`.", "",
                  "| Study date | Band | DSR | Cushion (months) | Health | Forecast risk | Main reasons | Points | "
                  "Room | Garden | Plants | Verified months |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for s in snaps[p["key"]]:
            fc = "-" if s["forecast"] is None else f"{s['forecast']:.0%}"
            lines.append(f"| {s['date']} | {s['band']} | {s['dsr']:.2f} | {s['cushion']:.1f} | "
                         f"{s['health']} ({s['tier']}) | {fc} | {'; '.join(map(str, s['reasons'])) or '-'} | "
                         f"{s['points']} | {s['room']} | {s['garden'] or 'closed'} | {s['plants']} | "
                         f"{s['verified']} of {s['months']} |")
        lines.append("")
    text = "\n".join(lines) + "\n"
    DOC.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    users = pd.read_parquet(SOURCE / "users.parquet").set_index("user_id")
    monthly = pd.read_parquet(SOURCE / "monthly.parquet")
    ids = [p.user_id for p in PERSONAS]
    tx = pd.read_parquet(SOURCE / "transactions.parquet", filters=[("user_id", "in", ids)])
    personas = [build_persona(per, users, monthly, tx) for per in PERSONAS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"note": "SYNTHETIC user-study personas (D-90); built by tools/personas/build.py",
                               "study_first": STUDY_FIRST.isoformat(), "study_last": STUDY_LAST.isoformat(),
                               "personas": personas}, indent=1), encoding="utf-8")
    snaps = {p["key"]: [snapshot(p, d) for d in study_dates()] for p in personas}
    write_doc(personas, snaps)
    for p in personas:
        print(f"{p['key']} {p['meta']['name']}: {len(p['transactions'])} transactions, {len(p['debts'])} debts, "
              f"{len(p['game_actions'])} plants; at {STUDY_FIRST}: {snaps[p['key']][0]}")
    print(f"-> {OUT}\n-> {DOC}")


if __name__ == "__main__":
    main()
