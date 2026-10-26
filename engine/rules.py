"""Rule engine: turns the financial state into plain-language advice (T-11).

Each rule is (id, priority, condition, values). Lower priority number = more urgent.
The result is a ranked list of advice items with the rule id, so the API can pass the id and
numbers (never raw transactions) to the Groq assistant (CLAUDE.md rule 10).

Invariants
  A1  only flags listed in shared/thresholds.json "user_facing_flags" can produce advice (S14, D-41)
  A2  a festive month never triggers the spending-swings advice (D-09)
  A3  advice never recommends a financial product or an investment (D-15); wording in advice.yaml
  A4  deterministic: same inputs -> same advice in the same order
  A5  the band limits, goals and income floor in the texts come from shared/thresholds.json
      (rule 5), never typed into advice.yaml
  A6  the advice explains the band actually shown: Red below the Red line (held by hysteresis,
      or waiting for an improvement to hold) and a pending improvement get their own words (D-92)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .bands import GREEN, INSUFFICIENT, RED, YELLOW, load_thresholds
from .health import health_score
from .state import MonthState

_ADVICE = yaml.safe_load((Path(__file__).with_name("advice.yaml")).read_text(encoding="utf-8"))
FESTIVE_MONTHS_2025 = {1, 3, 10, 12}      # C-24; replaced by the user's own festival in the app


@dataclass
class Context:
    state: MonthState
    debt_payments: float = 0.0
    essentials_and_debts: float = 0.0       # average monthly essentials + debt payments (for cushion goals)
    cash: float = 0.0
    bnpl_plans: int = 0
    bnpl_monthly: float = 0.0
    flags: dict = field(default_factory=dict)   # e.g. {"impulsivity": True}
    festive_month: bool = False
    forecast_risk: float | None = None          # calibrated ML probability (D-44), if available
    forecast_in_red: bool = False               # the model's band is Red: the forecast is only about running short (W3)


@dataclass
class Advice:
    rule: str
    priority: int
    title: str
    text: str
    values: dict
    short: str = ""        # the one-line, action-first version shown first in the app (D-108)


def _rm(x: float) -> str:
    return f"RM{x:,.0f}"


def _months(n: float) -> str:
    return f"{n:g} month" + ("" if n == 1 else "s")


BAND_WORDS = {GREEN: "Green", YELLOW: "Yellow", RED: "Red"}


def limits(t: dict) -> dict:
    """The thresholds the advice texts quote (A5)."""
    d, a = t["dsr"], t["advice"]
    return {"red_pct": f"{d['red_at_or_above']:.0%}", "leave_red_pct": f"{d['leave_red_below']:.0%}",
            "green_pct": f"{d['green_below']:.0%}", "confirm_months": t["improvement_confirm_months"],
            "min_income": _rm(t["insufficient_income_below_rm"]), "window": t["income_window_months"],
            "first_goal": _months(a["cushion_first_goal_months"]), "next_goal": _months(a["cushion_next_goal_months"])}


def advise(ctx: Context, thresholds: dict | None = None) -> list[Advice]:
    t = thresholds or load_thresholds()
    a, s = t["advice"], ctx.state
    need = max(ctx.essentials_and_debts, 1.0)
    fixed = limits(t)
    rules = []

    def add(rule, prio, variant="text", **values):
        txt = _ADVICE[rule]
        short = txt.get(variant.replace("text", "short", 1), txt["short"])        # a variant's own short, if any
        rules.append(Advice(rule, prio, txt["title"].format(**fixed), txt[variant].format(**fixed, **values), values,
                            short.format(**fixed, **values)))

    improving = not s.insufficient_income and s.raw_band != INSUFFICIENT and s.raw_band < s.band   # A6, D-49
    if s.insufficient_income:
        add("R01_insufficient_income", 1)
    if s.shortfalls_last3 > 0:
        add("R02_recent_shortfall", 1, shortfalls=s.shortfalls_last3, debt_payments=_rm(ctx.debt_payments))
    if not s.insufficient_income and s.band == RED:
        variant = ("text" if s.dsr >= t["dsr"]["red_at_or_above"] else
                   "text_improving" if improving else "text_held")                         # A6
        add("R03_red_band", 2, variant, dsr_pct=f"{s.dsr:.0%}")
    elif not s.insufficient_income and s.band == YELLOW and s.dsr >= a["near_red_dsr"]:
        add("R04_near_red", 3, dsr_pct=f"{s.dsr:.0%}")
    if improving and s.band == YELLOW:                     # Red's own text covers a pending way out of Red
        add("R13_band_improving", 4, dsr_pct=f"{s.dsr:.0%}", new_band=BAND_WORDS[s.raw_band])
    if s.savings_rate3 is not None and s.savings_rate3 < 0:
        add("R11_spending_more_than_income", 2, overspend_pct=f"{-s.savings_rate3:.0%}")
    if s.cushion_months < a["cushion_first_goal_months"]:
        add("R05_build_first_cushion", 2, cushion_months=f"{max(s.cushion_months, 0):.1f}",
            gap_to_first=_rm(max(a["cushion_first_goal_months"] * need - ctx.cash, 0)))
    elif s.cushion_months < a["cushion_next_goal_months"]:
        add("R06_next_cushion_goal", 4, cushion_months=f"{s.cushion_months:.1f}",
            gap_to_next=_rm(max(a["cushion_next_goal_months"] * need - ctx.cash, 0)))
    if ctx.bnpl_plans >= a["bnpl_plans_warn"]:
        add("R07_bnpl_load", 3, bnpl_plans=ctx.bnpl_plans, bnpl_monthly=_rm(ctx.bnpl_monthly))
    shown = set(t["user_facing_flags"])
    if ctx.festive_month:
        add("R09_festive_month", 5)
    elif ctx.flags.get("impulsivity") and "impulsivity" in shown:
        add("R08_spending_swings", 3)
    if ctx.forecast_risk is not None and ctx.forecast_risk >= a["forecast_elevated"]:
        add("R10_forecast_elevated", 3, "text_red" if ctx.forecast_in_red else "text",
            risk_pct=f"{ctx.forecast_risk:.0%}")
    hs = health_score(s, t)
    if not rules and hs.tier == "Healthy":
        add("R12_doing_well", 9, cushion_months=f"{s.cushion_months:.1f}")
    return sorted(rules, key=lambda r: (r.priority, r.rule))
