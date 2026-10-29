"""The risk assessment and the Future Self from the user's own rows (A2, A3, D-88): what
GET /v1/assess and GET /v1/future do.

The app no longer sends months: each request reads the user's rows from Supabase AS THE USER (their
token, under Row Level Security; W1 in api/game.py) and builds one engine.state.MonthRecord per month,
from the sign-up month to this month:
  a checked-in month   money and debt as at its end (the balances given, minus what was logged after
                       the month ended, D-77), its confirmed income, its logged spending
  a month without one  estimated: the previous month's money plus what was logged in, minus what
                       was paid out; debt plus new credit and BNPL, minus logged repayments
  this month           the same estimate so far, with the declared income until more is logged;
                       assessed only until the first month is complete (assessed_upto)
Committed debt payments come from the debts list (loans, cards, BNPL plans) plus a third of each
BNPL purchase logged in the last 3 months (3 instalments, spec §9). Income for the DSR is the
take-home pay plus loan payments deducted from salary: the take-home already had them removed,
and DSR divides every commitment by income before them (CLAUDE.md rule 6).

Invariants
  M1  rows -> records is a pure function (assess_inputs), tested without a database
  M2  month m's record uses rows dated in month m (and the months before it) only: no look-ahead (S1)
  M3  every read and write uses the user's own token (the same store as the game)
  M4  a checked-in month's assessment is saved once and then kept, so the game's "really bad month"
      (D-73) can't change after the fact; months still open are never saved
Cost: O(rows + months); one assess() per newly checked-in month.
Production vs coursework: the debts list stores current payments only, so past months reuse them.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from engine.assess import assess
from engine.features import UserProfile
from engine.game import GameState, protected_monthly_costs
from engine.state import MonthRecord
from sim.conformal import calibrated_months
from sim.monte_carlo import FutureProfile, GameSnapshot, simulate_future

from .game import my_day

FAMILY, EDUCATION, FEES = "family", "education", "fees"      # category keys the app uses (docs/app_plan.md)
SHOCK_RM = 300.0                                             # an unexpected expense this big is a shock (engine)
FUTURE_LABEL = "if recent habits continue"                   # D-81: an illustrative range, not a prediction


def _money(x) -> float:
    return 0.0 if x is None else float(x)


@dataclass
class MoneyFacts:
    """Everything the assessment needs about one user, as rows from Supabase."""
    profile: dict | None
    transactions: list[dict] = field(default_factory=list)
    debts: list[dict] = field(default_factory=list)
    checkins: list[dict] = field(default_factory=list)
    goal_changes: list[dict] = field(default_factory=list)
    assessments: list[dict] = field(default_factory=list)


def as_of(f: MoneyFacts, today: date) -> MoneyFacts:
    """Only what had happened by `today` (a persona's study date; see api.game.as_of)."""
    return MoneyFacts(profile=f.profile, debts=f.debts,
                      transactions=[t for t in f.transactions if date.fromisoformat(t["occurred_on"]) <= today],
                      checkins=[c for c in f.checkins if my_day(c["created_at"]) <= today],
                      goal_changes=[c for c in f.goal_changes if my_day(c["created_at"]) <= today],
                      assessments=[a for a in f.assessments if date.fromisoformat(a["month"]) <= today])


def _next_month(m: date) -> date:
    return (m + timedelta(days=32)).replace(day=1)


def _month_end(m: date) -> date:
    return _next_month(m) - timedelta(days=1)


def _months_back(m: date, k: int) -> date:
    for _ in range(k):
        m = (m - timedelta(days=1)).replace(day=1)
    return m


def _active(d: dict, m: date) -> bool:
    starts = d.get("starts_on") and date.fromisoformat(d["starts_on"])
    ends = d.get("ends_on") and date.fromisoformat(d["ends_on"])
    return (not starts or starts <= _month_end(m)) and (not ends or ends >= m)


def _goal(f: MoneyFacts, m: date, income: float) -> float | None:
    """The user's savings goal for month m: the latest change made before the month, else sign-up's."""
    p = f.profile
    amount = None if p.get("savings_goal_monthly") is None else float(p["savings_goal_monthly"])
    share = None if p.get("savings_goal_share") is None else float(p["savings_goal_share"])
    for g in sorted(f.goal_changes, key=lambda g: g["created_at"]):
        if _next_month(my_day(g["created_at"]).replace(day=1)) <= m:
            amount = None if g.get("amount") is None else float(g["amount"])
            share = None if g.get("share") is None else float(g["share"])
    if share is not None and p["employment_type"] == "gig":
        return share * income
    return amount if amount is not None else (share * income if share is not None else None)


def assess_inputs(f: MoneyFacts, today: date) -> tuple[UserProfile, list[MonthRecord], list[dict]]:
    """The user's rows as engine.assess arguments, plus where each month's numbers came from."""
    p = f.profile
    first, current = my_day(p["created_at"]).replace(day=1), today.replace(day=1)
    by_month: dict[date, list[dict]] = defaultdict(list)
    for t in f.transactions:
        by_month[date.fromisoformat(t["occurred_on"]).replace(day=1)].append(t)
    checkins = {date.fromisoformat(c["month"]): c for c in f.checkins}
    declared = _money(p["declared_income"])
    typical = p.get("typical_monthly_costs")
    cash, owed = _money(p["onboarding_counted_money"]), _money(p.get("onboarding_debt"))
    bnpl_bought: dict[date, float] = {}
    records, months = [], []
    m = first
    while m <= current:
        txs = by_month.get(m, [])
        outs = [t for t in txs if t["direction"] == "out" and not t.get("is_own_transfer")]
        logged_in = sum(_money(t["amount"]) for t in txs if t["direction"] == "in" and not t.get("is_own_transfer"))
        purchases = [t for t in outs if not t.get("is_debt_payment")]
        bnpl = [t for t in purchases if t.get("is_bnpl")]
        bnpl_bought[m] = sum(_money(t["amount"]) for t in bnpl)
        instalments = sum(bnpl_bought.get(_months_back(m, k), 0.0) for k in range(3)) / 3
        active = [d for d in f.debts if _active(d, m)]
        committed = sum(_money(d["monthly_payment"]) for d in active)
        deducted = sum(_money(d["monthly_payment"]) for d in active if d.get("deducted_from_salary"))
        repaid = sum(_money(t["amount"]) for t in outs if t.get("is_debt_payment"))
        c = checkins.get(m)
        if c is not None:
            income = _money(c["net_income"]) if c.get("net_income") is not None else (logged_in or declared)
            cash = (max(0.0, _money(c["cash_bank_ewallet"]) - _money(c.get("after_month_net")))
                    + _money(c.get("epf_fleksibel")) + _money(c.get("others_emergency")))
            owed = max(0.0, _money(c["debt_total"]) - _money(c.get("after_month_debt")))
            source, shortfall = "check-in", bool(c.get("ran_short"))
        else:
            income = max(declared, logged_in) if m == current else (logged_in or declared)
            paid_now = sum(_money(t["amount"]) for t in outs if not (t.get("on_credit") or t.get("is_bnpl")))
            cash = max(0.0, cash + logged_in - paid_now)
            owed = max(0.0, owed + sum(_money(t["amount"]) for t in purchases if t.get("on_credit") or t.get("is_bnpl"))
                       - repaid)
            source, shortfall = ("this month so far" if m == current else "estimated"), False
        essentials = sum(_money(t["amount"]) for t in purchases if t.get("is_essential"))
        if typical is not None and (essentials == 0 or m == current):      # nothing (or not all) logged yet
            essentials = max(essentials, float(typical) - committed, 0.0)
        education = min(sum(_money(t["amount"]) for t in purchases if t["category"] == EDUCATION), essentials)
        unexpected = [_money(t["amount"]) for t in outs if t.get("is_unexpected")]
        records.append(MonthRecord(
            net_income=income + deducted, debt_payments=committed + instalments, outstanding_debt=owed, cash=cash,
            essential_spending=essentials, total_spending=sum(_money(t["amount"]) for t in purchases),
            family_support=sum(_money(t["amount"]) for t in outs if t["category"] == FAMILY), shortfall=shortfall,
            month=m.month, bnpl_purchases=bnpl_bought[m], bnpl_new_count=len(bnpl), bnpl_instalments=instalments,
            personal_loan_balance=sum(_money(d["outstanding"]) for d in active if d["kind"] == "personal"),
            event_costs=sum(unexpected), shock_count=sum(x >= SHOCK_RM for x in unexpected),
            other_fees=sum(_money(t["amount"]) for t in outs if t["category"] == FEES),
            savings_target=_goal(f, m, income), education_spending=education))
        months.append({"month": m.isoformat(), "source": source})
        m = _next_month(m)
    profile = UserProfile(employment_type=p["employment_type"], age=today.year - int(p["birth_year"]),
                          lives_with_parents=bool(p.get("lives_with_parents")),
                          family_support=bool(p.get("family_support")), festive_month=p.get("festive_month"))
    return profile, records, months


def assessed_upto(months: list[dict]) -> int:
    """How many records to assess: up to the latest COMPLETE month. This month so far is only a few
    days of spending, which made features like "how much spending jumped around" look extreme
    (D-90); it is assessed only while there is no complete month yet (a new user's first weeks, when
    the band from the declared income and the debts list is what there is)."""
    return len(months) - 1 if len(months) > 1 and months[-1]["source"] == "this month so far" else len(months)


def assessments_to_save(f: MoneyFacts, profile: UserProfile, records: list[MonthRecord],
                        months: list[dict]) -> list[dict]:
    """M4: rows for checked-in months that have no saved assessment yet (each assessed with its own
    months only, so a month's result never uses later ones)."""
    saved = {a["month"] for a in f.assessments}
    rows = []
    for i, m in enumerate(months):
        if m["source"] == "check-in" and m["month"] not in saved:
            result = assess(profile, records[:i + 1])
            version = (result.get("forecast") or {}).get("version") or "rules-only"
            rows.append({"month": m["month"], "model_version": version, "result": result})
    return rows


def missing_assessments(f: MoneyFacts, today: date) -> list[dict]:
    """The rows assessments_to_save would add as of `today`: what the game needs for every check-in
    (S-4, D-93; also used by the persona builder, so its notes match the app)."""
    profile, records, months = assess_inputs(f, today)
    return assessments_to_save(f, profile, records, months)


def forecast_seed(done: list[MonthRecord], fp: FutureProfile, snap: GameSnapshot, today: date) -> int:
    """The Monte Carlo's seed (D-150): from the forecast's own inputs and the month, never the account.
    The same complete months give the same range all month (until one of them is corrected), and two
    accounts with the same history, such as each participant's copy of a persona (D-94), see the same
    screens, which the sample data and the answer keys assume."""
    facts = {"month": f"{today:%Y-%m}", "profile": asdict(fp), "game": asdict(snap), "months": [asdict(r) for r in done]}
    return int.from_bytes(hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).digest()[:4], "big")


def future_view(profile: dict, records: list[MonthRecord], months: list[dict], st: GameState,
                game_profile, today: date) -> dict:
    """The Future Self: six months of possible cushions from the user's complete months (D-79, D-81),
    each month's P10-P90 adjusted by the conformal offsets for the user's cell (D-142); P50 unchanged."""
    done = [r for r, m in zip(records, months) if m["source"] != "this month so far"][-6:]
    if len(done) < 3:
        return {"available": False, "reason": "the Future Self needs 3 complete months", "label": FUTURE_LABEL}
    vehicle = profile.get("vehicle") or "none"
    fp = FutureProfile(employment_type=profile["employment_type"], festive_month=profile.get("festive_month"),
                       has_car=vehicle in ("car", "both"), has_motorbike=vehicle in ("motorcycle", "both"))
    snap = GameSnapshot(counted_money=st.money, borrowed_cash=st.borrowed_cash,
                        protected_monthly_costs=protected_monthly_costs(st, game_profile),
                        current_room_level=st.room_level)
    r = simulate_future(done, fp, snap, seed=forecast_seed(done, fp, snap, today))
    months = calibrated_months(r.cushion, fp.employment_type, len(done))
    return {"available": True, "label": FUTURE_LABEL, "based_on_months": len(done),
            "months": [{"month": x.month, "p10": round(x.p10, 2), "p50": round(x.p50, 2), "p90": round(x.p90, 2)}
                       for x in months],
            "shortfall_probability": round(r.shortfall_probability, 3),
            "cash_flow_at_risk": round(r.cash_flow_at_risk, 2), "expected_shortfall": round(r.expected_shortfall, 2),
            "median_path_room_level": r.median_path_room_level,
            "median_path_final_cushion": round(r.median_path_final_cushion, 2)}
