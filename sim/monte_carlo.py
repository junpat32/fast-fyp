"""Six-month, one-user Future Self simulation (D-79).

Invariants
  M1  Only the user's completed MonthRecords and stated profile enter a forecast.
      Generator hidden traits, later months and other users never enter it.
  M2  BNPL purchases are paid through three instalments, not again as cash spending.
      Past event costs are not part of routine spending; future events are drawn anew.
  M3  Each path records an unmet-outgoings shortfall before cash is floored at zero.
      Its cumulative net cash flow stays signed for CFaR and Expected Shortfall.
  M4  Financial cushion uses rolling essentials plus commitments. Projected room
      uses the separate protected game cushion and never loses an unlocked level.

Pseudo-code
  validate history, profile and current game snapshot
  take up to the last six complete months; remove known festive/semester uplifts
  draw one persistent Student-t estimate error per path for routine net cash flow
  for each future month:
      sample one historical month per path (income and spending stay paired)
      use employee median plus modest monthly noise, otherwise sampled income
      apply known calendar uplift to discretionary/education costs
      schedule three BNPL instalments; draw eligible independent deck events
      update signed net flow, cash and rolling essential-cost denominator
      record a shortfall when net cash is negative or essentials cannot be met
  report per-month cushion quantiles and horizon-wide tail statistics
  choose the terminal path nearest P50 for the illustrative room

Cost: O(H * P * (W + E)) time, O(H * P + E) space; H=6, P=2,000,
W<=6 history months, E=21 life events. All draws operate on NumPy path arrays.

Trace (no shocks; RM, essential+debt cost RM800, protected cost RM1,000):
  month  start cash  income  cash costs  end cash  shortfall  cushion
  0      --          --      --          500       --         0.625
  1      500         900     800         600       no         0.750
  2      600         0       800         0         yes        0.000

Production vs coursework: the last 3-6 months cannot reveal job loss or a new
income regime. This deliberately simple model may under-cover true outcomes;
the synthetic calibration audit reports that limitation without tuning to it.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import t as student_t

from engine.state import MonthRecord
from engine.game import load_game

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FutureProfile:
    employment_type: str
    festive_month: int | None = None
    has_car: bool = False
    has_motorbike: bool = False
    semester_months: tuple[int, ...] = (3, 8, 11)


@dataclass(frozen=True)
class GameSnapshot:
    counted_money: float
    borrowed_cash: float
    protected_monthly_costs: float
    current_room_level: int


@dataclass(frozen=True)
class MonthRange:
    month: int
    p10: float
    p50: float
    p90: float


@dataclass(frozen=True)
class FutureResult:
    cushion: tuple[MonthRange, ...]
    shortfall_probability: float
    cash_flow_at_risk: float
    expected_shortfall: float
    median_path_room_level: int
    median_path_final_cushion: float


@dataclass(frozen=True)
class DebtPlan:
    """Debt table's kind/outstanding/monthly_payment plus its APR (debts.annual_rate).

    The rate is optional in the debts table (D-144). The user supplies it or the
    comparison is not made; the engine never guesses a rate. The app's port is
    app/src/lib/debt-plan.ts, kept equal by tools/app_fixtures.py.
    """
    kind: str
    outstanding: float
    monthly_payment: float
    annual_rate: float


@dataclass(frozen=True)
class DebtComparison:
    avalanche_months: int | None
    snowball_months: int | None
    avalanche_interest: float
    snowball_interest: float


@lru_cache(maxsize=1)
def _deck() -> dict:
    # The generator's deck mirrors docs/life_events.md; no second set of event constants.
    with (ROOT / "generator" / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["shocks"]


def _eligible(who: str, p: FutureProfile) -> bool:
    return {"all": True, "car": p.has_car, "motorbike": p.has_motorbike,
            "vehicle": p.has_car or p.has_motorbike,
            "student": p.employment_type == "student",
            "nonstudent": p.employment_type != "student",
            "gig": p.employment_type == "gig"}[who]


def simulate_future(records: list[MonthRecord], profile: FutureProfile, game: GameSnapshot,
                    *, seed: int, paths: int = 2000, horizon: int = 6) -> FutureResult:
    if len(records) < 3 or paths < 2 or horizon < 1:
        raise ValueError("Need >=3 complete months, >=2 paths and a positive horizon")
    if profile.employment_type not in {"employee", "gig", "student"}:
        raise ValueError("Unknown employment type")
    if profile.festive_month is not None and not 1 <= profile.festive_month <= 12:
        raise ValueError("Invalid festive month")
    if records[-1].month is None or not 1 <= records[-1].month <= 12:
        raise ValueError("The last record needs a calendar month")
    if game.protected_monthly_costs <= 0 or game.current_room_level not in range(1, 6):
        raise ValueError("Invalid current game snapshot")
    hist = records[-6:]
    fields = np.asarray([[r.net_income, r.essential_spending, r.total_spending,
                          r.bnpl_purchases, r.debt_payments, r.family_support,
                          r.event_costs, r.other_fees, r.cash,
                          r.bnpl_instalments, r.education_spending]
                         for r in hist], dtype=float)
    if not np.isfinite(fields).all() or (fields < 0).any():
        raise ValueError("History must contain finite nonnegative amounts")
    if any(r.month is None or not 1 <= r.month <= 12 for r in hist):
        raise ValueError("Each sampled month needs a calendar month")
    if any(r.education_spending > r.essential_spending or
           r.bnpl_instalments > r.debt_payments for r in hist):
        raise ValueError("Education and BNPL components cannot exceed their totals")
    if not np.isfinite([game.counted_money, game.borrowed_cash,
                        game.protected_monthly_costs]).all() or min(game.counted_money,
                                                                       game.borrowed_cash) < 0:
        raise ValueError("Invalid game money")

    rng = np.random.default_rng(seed)
    deck = _deck()
    income = fields[:, 0]
    essential = fields[:, 1].copy()
    education = fields[:, 10].copy()
    discretionary = np.maximum(0.0, fields[:, 2] - fields[:, 1])
    # The deck's festive/semester uplift is removed from observed ordinary costs.
    for j, r in enumerate(hist):
        if profile.festive_month == r.month:
            discretionary[j] /= 1.3
        if profile.employment_type == "student" and r.month in profile.semester_months:
            discretionary[j] /= 1.15
            essential[j] -= education[j] * (1 - 1 / 1.15)
            education[j] /= 1.15
    bnpl_share = np.divide(fields[:, 3], np.maximum(fields[:, 2], 1),
                           out=np.zeros(len(hist)), where=fields[:, 2] > 0)
    debt_due = float(np.median(fields[:, 4] - fields[:, 9]))
    family_due = float(np.median(fields[:, 5]))
    fees = float(np.median(fields[:, 7]))
    ordinary_net = (income - essential - discretionary + fields[:, 3]
                    - (fields[:, 4] - fields[:, 9]) - family_due - fees - fields[:, 9])
    scale = float(np.std(ordinary_net, ddof=1) / np.sqrt(len(hist)))
    estimate_error = student_t.rvs(df=len(hist)-1, size=paths,
                                   random_state=rng) * scale
    recent_buy = [float(hist[-2].bnpl_purchases), float(hist[-1].bnpl_purchases)]
    cash = np.full(paths, fields[-1, 8])
    counted = np.full(paths, game.counted_money)
    cum_net = np.zeros(paths)
    ever_short = np.zeros(paths, dtype=bool)
    need_history = [np.full(paths, float(r.essential_spending + r.debt_payments))
                    for r in hist[-2:]]
    cushions = np.empty((horizon, paths))

    for step in range(horizon):
        month = (records[-1].month + step) % 12 + 1
        idx = rng.integers(0, len(hist), size=paths)
        if profile.employment_type == "employee":
            salary = float(np.median(income[-3:]))
            inc = np.maximum(0.0, rng.normal(salary, salary * 0.05, paths))
        else:
            inc = income[idx]
        ess = essential[idx].copy()
        disc = discretionary[idx].copy()
        if month == profile.festive_month:
            disc *= rng.uniform(1.2, 1.4, paths)
        if profile.employment_type == "student" and month in profile.semester_months:
            ess += education[idx] * 0.15
            disc *= 1.15
        new_buy = np.minimum(disc, bnpl_share[idx] * (ess + disc))
        cash_spend = ess + disc - new_buy
        bnpl_due = (recent_buy[-2] + recent_buy[-1] + new_buy) / 3
        recent_buy.append(new_buy)
        recent_buy = recent_buy[-2:]
        event_cost = np.zeros(paths)
        for eid, who, lo, hi, freq, _is_shock, _cat in deck["deck"]:
            if not _eligible(who, profile):
                continue
            mult = deck["gig_multiplier"] if profile.employment_type == "gig" and eid in deck["gig_events"] else 1.0
            if profile.employment_type == "student" and eid == "L08":
                mult *= deck["student_laptop_multiplier"]
            hit = rng.random(paths) < min(1.0, deck["k"] * freq * mult / 12)
            event_cost += np.where(hit, rng.uniform(lo, hi, paths), 0.0)
        net = inc - cash_spend - debt_due - bnpl_due - family_due - fees - event_cost + estimate_error
        available = cash + inc
        ever_short |= (available < ess + debt_due + bnpl_due + family_due) | (cash + net < 0)
        cum_net += net
        next_cash = np.maximum(0.0, cash + net)
        counted = np.maximum(0.0, counted + next_cash - cash)
        cash = next_cash
        need_history.append(ess + debt_due + bnpl_due)
        need_history = need_history[-3:]
        cushions[step] = cash / np.maximum(1.0, np.mean(need_history, axis=0))

    q = np.percentile(cushions, [10, 50, 90], axis=1)
    months = tuple(MonthRange((records[-1].month + i) % 12 + 1,
                              float(q[0, i]), float(q[1, i]), float(q[2, i]))
                   for i in range(horizon))
    tail = np.percentile(cum_net, 5)
    worst_count = max(1, int(np.ceil(paths * 0.05)))
    expected = float(np.mean(np.partition(cum_net, worst_count - 1)[:worst_count]))
    median_idx = int(np.argmin(np.abs(cushions[-1] - q[1, -1])))
    game_cushion = max(0.0, counted[median_idx] - game.borrowed_cash) / game.protected_monthly_costs
    thresholds = load_game()["room_level_at_cushion"]
    level = max([game.current_room_level] +
                [int(level) for level, threshold in thresholds.items() if game_cushion >= threshold])
    return FutureResult(months, float(np.mean(ever_short)), float(tail), expected,
                        level, float(cushions[-1, median_idx]))


def compare_debt_plans(debts: list[DebtPlan], extra_monthly: float,
                       *, max_months: int = 360) -> DebtComparison:
    """Apply committed minimums, then the available extra to highest APR or lowest balance.

    Freed minimums roll into the same fixed monthly budget. APR is an explicit
    caller-supplied assumption because the database has no interest-rate column.
    Returns None for payoff months if the budget cannot clear debt in max_months.
    """
    if not debts or extra_monthly < 0 or max_months < 1 or any(
        not np.isfinite([d.outstanding, d.monthly_payment, d.annual_rate]).all()
        or min(d.outstanding, d.monthly_payment, d.annual_rate) < 0 for d in debts
    ):
        raise ValueError("Valid debts, nonnegative extra and positive horizon required")
    budget = sum(d.monthly_payment for d in debts) + extra_monthly

    def run(method: str) -> tuple[int | None, float]:
        balances = [d.outstanding for d in debts]
        interest_total = 0.0
        for month in range(1, max_months + 1):
            if all(x <= 0.005 for x in balances):
                return month - 1, interest_total
            interest = [balances[i] * d.annual_rate / 12 for i, d in enumerate(debts)]
            interest_total += sum(interest)
            balances = [balances[i] + interest[i] for i in range(len(debts))]
            left = budget
            for i, d in enumerate(debts):
                paid = min(left, balances[i], d.monthly_payment)
                balances[i] -= paid
                left -= paid
            order = sorted(range(len(debts)),
                           key=lambda i: (-debts[i].annual_rate, balances[i], i)
                           if method == "avalanche" else (balances[i], -debts[i].annual_rate, i))
            for i in order:
                paid = min(left, balances[i])
                balances[i] -= paid
                left -= paid
            if all(x <= 0.005 for x in balances):
                return month, interest_total
        return None, interest_total

    a_months, a_interest = run("avalanche")
    s_months, s_interest = run("snowball")
    return DebtComparison(a_months, s_months, a_interest, s_interest)
