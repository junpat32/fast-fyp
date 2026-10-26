"""The weekly life-event card (game_design §10, G-08; D-117).

    GET  /v1/card    this week's card: the event, its usual cost, whether the user's money would cover it
    POST /v1/card    the answer: use_savings, cut_spending, set_goal or not_this_week

Invariants
  LC1  one card a week, the same on every device and every request: drawn from (user, Monday) with a
       hash, not a random generator, so a replay or a second phone always sees the same event
  LC2  only events the user can have (a motorbike repair needs a motorbike; a resit, a student),
       weighted by the event's yearly frequency and the deck's own multipliers (gig workers wear out
       vehicles and phones faster; students break laptops more often): generator/config.yaml shocks,
       the same numbers the synthetic data uses
  LC3  hypothetical: answering never changes money; the reward is the game's fixed card points, once
       a week (engine/game.py _card); "Not this week" earns nothing and costs nothing
  LC4  no alarming words: covered, partly covered, or "not covered yet" with what helps (engine/cards.yaml)
Cost: O(deck) per request.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

import yaml

from engine.game import load_game

ROOT = Path(__file__).resolve().parents[1]
_SHOCKS = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))["shocks"]
DECK = {row[0]: {"who": row[1], "low": row[2], "high": row[3], "freq": row[4], "shock": row[5]} for row in _SHOCKS["deck"]}
TEXT = yaml.safe_load((ROOT / "engine" / "cards.yaml").read_text(encoding="utf-8"))
RESPONSES = tuple(TEXT["responses"])                     # the database's allowed answers, in order


def monday(day: date) -> date:
    """The card's week (the database's set_card_week: date_trunc('week', ...))."""
    return day - timedelta(days=day.weekday())


def _can_have(who: str, profile: dict) -> bool:
    vehicle = profile.get("vehicle") or "none"
    student = profile.get("employment_type") == "student"
    return {"all": True, "motorbike": vehicle in ("motorcycle", "both"), "car": vehicle in ("car", "both"),
            "vehicle": vehicle != "none", "student": student, "nonstudent": not student}[who]


def weights(profile: dict) -> list[tuple[str, float]]:
    """The card events this user can have, with their weights (LC2), in the deck's order."""
    gig = profile.get("employment_type") == "gig"
    student = profile.get("employment_type") == "student"
    out = []
    for event_id in TEXT["deck"]:
        e = DECK[event_id]
        if not e["shock"] or not _can_have(e["who"], profile):
            continue
        w = e["freq"]
        if gig and event_id in _SHOCKS["gig_events"]:
            w *= _SHOCKS["gig_multiplier"]
        if student and event_id == "L08":
            w *= _SHOCKS["student_laptop_multiplier"]
        out.append((event_id, w))
    return out


def draw(user_id: str, week: date, profile: dict) -> str:
    """This week's event for this user (LC1): a point in [0, 1) from a hash of (user, week), then the
    event whose share of the total weight contains it."""
    options = weights(profile)
    total = sum(w for _, w in options)
    u = int.from_bytes(hashlib.sha256(f"{user_id}:card:{week.isoformat()}".encode()).digest()[:8], "big") / 2 ** 64
    acc = 0.0
    for event_id, w in options:
        acc += w / total
        if u < acc:
            return event_id
    return options[-1][0]


def coverage(money: float, low: float, high: float) -> str:
    """Would the money the user has now pay for it (LC4)?"""
    if money >= high:
        return "covered"
    return "partly" if money >= low else "not_yet"


def card_view(profile: dict, user_id: str, today: date, money: float, answer: dict | None) -> dict:
    week = monday(today)
    event_id = answer["event_id"] if answer else draw(user_id, week, profile)
    e, words = DECK[event_id], TEXT["cards"][event_id]
    cover = coverage(money, e["low"], e["high"])
    return {
        "week": week.isoformat(), "event_id": event_id, "title": words["title"], "text": words["text"],
        "cost_low": e["low"], "cost_high": e["high"], "coverage": cover, "coverage_text": TEXT["coverage"][cover],
        "responses": [{"id": r, "label": TEXT["responses"][r]["label"], "after": TEXT["responses"][r]["after"]}
                      for r in RESPONSES],
        "points": load_game()["points"]["card_answered"],
        "answer": answer["response"] if answer else None,
    }
