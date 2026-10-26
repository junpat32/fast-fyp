"""Financial health score, 0-100 (PROPOSAL, pending Patrick's decision K in DECISIONS.md).

Design: adapted from the Financial Health Network's FinHealth Score, which averages
indicator scores (0-100 each) and reports three tiers: Healthy 80-100, Coping 40-79,
Vulnerable 0-39. FAST uses the four indicators that can be measured from a user's own
records:
  spend      spend less than income   <- savings rate over 3 months
  savings    sufficient liquid savings <- cushion months (target 3)
  debt       manageable debt           <- DSR (same thresholds as the bands)
  bills      pay bills on time         <- shortfalls in the last 3 months
All breakpoints live in shared/thresholds.json ("health_score"), so the app uses the same ones.

Invariants
  H1  each indicator is in [0, 100]; the score is the mean of the available indicators
  H2  with insufficient income the debt indicator is undefined and left out (never guessed)
  H3  the score never uses hidden traits or ML output (it describes the present, not the future)
"""
from __future__ import annotations

from dataclasses import dataclass

from .bands import load_thresholds
from .state import MonthState


def _lin(x, x0, y0, x1, y1):
    """Linear interpolation between (x0, y0) and (x1, y1), clamped to that segment."""
    if x <= x0:
        return y0
    if x >= x1:
        return y1
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


@dataclass
class HealthScore:
    score: float | None
    tier: str | None
    indicators: dict


def health_score(s: MonthState, thresholds: dict | None = None) -> HealthScore:
    h = (thresholds or load_thresholds())["health_score"]
    ind = {}
    if s.savings_rate3 is not None:
        sp = h["spend"]
        r = s.savings_rate3
        ind["spend"] = (_lin(r, 0.0, sp["at_zero"], sp["full_rate"], 100) if r >= 0
                        else _lin(r, sp["zero_score_rate"], 0, 0.0, sp["at_zero"]))
    ind["savings"] = 100 * min(max(s.cushion_months, 0) / h["savings"]["full_months"], 1.0)
    if not s.insufficient_income:
        d = h["debt"]
        ind["debt"] = (100.0 if s.dsr < d["full_below"] else
                       _lin(s.dsr, d["full_below"], 100, d["red_at"], d["at_red"]) if s.dsr < d["red_at"] else
                       _lin(s.dsr, d["red_at"], d["at_red"], d["zero_at"], 0))
    ind["bills"] = h["bills"]["by_shortfalls"][min(s.shortfalls_last3, len(h["bills"]["by_shortfalls"]) - 1)]
    score = sum(ind.values()) / len(ind)
    tiers = h["tiers"]
    tier = "Healthy" if score >= tiers["healthy"] else "Coping" if score >= tiers["coping"] else "Vulnerable"
    return HealthScore(score=round(score, 1), tier=tier, indicators={k: round(v, 1) for k, v in ind.items()})
