"""Split-conformal adjustment of the Future Self range (phase 5 of the 26 Oct brief, D-142).

The Monte Carlo's P10-P90 cushion range covered 73% of fresh synthetic outcomes instead of 80%,
with most misses below the range (D-81, CR-11). Conformalised quantile regression (Romano, Patterson
and Candes, 2019) moves each end of the range by an offset learnt on held-out users, so that the
adjusted range reaches its target on new users like them. The asymmetric version sets each tail
separately, which suits misses that fall mostly on one side.

Invariants
  C1  Offsets are learnt only on calibration users (seeds 62001-62009) and are fixed in
      sim/monte_carlo_conformal.json before any evaluation user (seeds 63001-63009) is simulated.
  C2  One offset pair per cell (employment type, months ahead 1-6, months of history 3-6). The
      guarantee holds within each cell, so one group's misses cannot hide behind another's.
  C3  Lower offset = the ceil(0.9 (n + 1))-th smallest of (P10 - truth); upper offset = the same
      order statistic of (truth - P90). On new users exchangeable with the calibration users, each
      tail then misses at most 10%, so the range covers at least 80% (finite-sample, not asymptotic).
      An offset can be negative: the range then narrows, because it was too wide.
  C4  The adjusted range keeps P10 <= P50 <= P90 and never goes below 0 (cash never ends a month
      below 0, generator E1). Both clamps only widen the range, so C3 still holds.
  C5  M1 is unchanged: a forecast still reads only the user's own months and profile, plus fixed
      constants. The offsets are constants learnt once from synthetic users, as the life-event deck
      is (CV-05), so they carry the generator's assumptions: nothing here guarantees coverage for
      real people, who are not exchangeable with synthetic ones.

Pseudo-code
  fit:    for each cell, scores_lo = P10 - truth, scores_hi = truth - P90 over its n users
          k = ceil(0.9 (n + 1)); require k <= n; offsets = (k-th smallest scores_lo, k-th smallest scores_hi)
  adjust: lo = max(0, min(P10 - lower, P50)); hi = max(P90 + upper, P50)

Cost: fitting is O(n log n) per cell (a sort); adjusting a six-month range is O(6).

Trace (one cell, n = 9, so k = ceil(0.9 x 10) = 9: the largest score):
  user        1    2    3    4    5    6    7    8    9
  P10-truth  -1.2 -0.9 -0.8 -0.5 -0.4 -0.3 -0.1  0.2  0.6   -> lower offset 0.6
  truth-P90  -2.0 -1.5 -1.1 -1.0 -0.8 -0.7 -0.6 -0.4 -0.3   -> upper offset -0.3 (narrows)
  A range 1.0-3.0 (P50 1.8) becomes 0.4-2.7.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from sim.monte_carlo import MonthRange

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "sim" / "monte_carlo_conformal.json"
TAIL = 0.10                                        # each tail's miss rate; the range aims at 80%
EMPLOYMENT = ("employee", "gig", "student")
HISTORY = (3, 4, 5, 6)                             # the app forecasts from 3 to 6 complete months
HORIZON = 6


def tail_offset(scores, tail: float = TAIL) -> float:
    """The ceil((1 - tail)(n + 1))-th smallest score (C3)."""
    s = np.sort(np.asarray(scores, dtype=float))
    n = len(s)
    k = math.ceil(round((1 - tail) * (n + 1), 9))  # round first: 0.9 x 10 must give 9, not 10
    if not np.isfinite(s).all():
        raise ValueError("scores must be finite")
    if k > n:
        raise ValueError(f"{n} users are too few for a {tail:.0%} tail; need {k}")
    return float(s[k - 1])


def fit_cell(p10, p90, truth, tail: float = TAIL) -> tuple[float, float]:
    """(lower, upper) offsets for one cell's users (C3)."""
    p10, p90, truth = (np.asarray(x, dtype=float) for x in (p10, p90, truth))
    return tail_offset(p10 - truth, tail), tail_offset(truth - p90, tail)


def adjust(p10: float, p50: float, p90: float, lower: float, upper: float) -> tuple[float, float]:
    """The adjusted (low, high) ends of one month's range (C4)."""
    return max(0.0, min(p10 - lower, p50)), max(p90 + upper, p50)


@lru_cache(maxsize=1)
def load_table() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def calibrated_months(months, employment_type: str, n_history: int,
                      table: dict | None = None) -> tuple[MonthRange, ...]:
    """A forecast's six MonthRanges with each month's offsets applied; P50 unchanged."""
    if employment_type not in EMPLOYMENT or n_history not in HISTORY or len(months) != HORIZON:
        raise ValueError("no conformal cell for this forecast")
    cells = (table or load_table())["offsets"][employment_type][str(n_history)]
    out = []
    for m, (lower, upper) in zip(months, cells):
        lo, hi = adjust(m.p10, m.p50, m.p90, lower, upper)
        out.append(MonthRange(m.month, lo, m.p50, hi))
    return tuple(out)
