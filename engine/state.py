"""A user's financial state per month, from their own records (spec §6, §8; same definitions as
the generator, so the app and the O2 experiment agree).

Invariants
  S1  month i uses records 0..i only (no look-ahead)
  S2  income for DSR/DTI/band is the median of the last 3 months' net income (D-05)
  S3  DSR = monthly debt payments / median income; DTI = outstanding debt / (12 x median income)
      (CLAUDE.md rule 6: DSR is not DTI)
  S4  the raw band uses engine.bands with hysteresis from the previous month's raw band
  S5  the SHOWN band (D-49): a worse or equal band is shown at once; a better band only after
      K consecutive months that are all better than the shown band, and then the worst of
      those K months (the level they all confirm). Entering or leaving INSUFFICIENT is shown at once.
Cost: O(months); each month looks at a window of at most 3 records.

Trace (K = 2)   raw:   R  Y  G  G  Y
                shown: R  R  Y  G  Y
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .bands import INSUFFICIENT, NAMES, band, load_thresholds

DSR_CAP = 9.99   # stored when median income is 0; the band is INSUFFICIENT anyway


@dataclass
class MonthRecord:
    net_income: float            # income received this month (after EPF/SOCSO for employees)
    debt_payments: float         # instalments due: loans, card minimum, BNPL instalments
    outstanding_debt: float      # everything still owed at month end
    cash: float                  # cash / savings at month end
    essential_spending: float    # housing, food at home, transport, bills, health, education
    total_spending: float = 0.0  # everything bought this month, including BNPL-paid purchases
    family_support: float = 0.0
    shortfall: bool = False      # ran out of cash or missed a payment this month
    month: int | None = None     # calendar month 1-12 (festive / semester rules, forecast calendar features)
    bnpl_purchases: float = 0.0  # part of total_spending paid with BNPL (its cost arrives as instalments)
    bnpl_new_count: int = 0      # new BNPL purchases this month
    bnpl_instalments: float = 0.0  # BNPL instalments due this month (already inside debt_payments)
    personal_loan_balance: float = 0.0
    event_costs: float = 0.0     # expenses the user marked as unexpected (all sizes)
    shock_count: int = 0         # unexpected expenses of RM300 or more
    other_fees: float = 0.0      # e.g. late fees
    savings_target: float | None = None   # the user's savings goal for this month
    education_spending: float = 0.0  # subset of essentials; calendar uplift for students


def saved_amount(r: MonthRecord) -> float:
    """Observable saving (spec §9, D-41): income minus cash-paid spending, debt payments, family
    support, unexpected costs and fees. BNPL purchases count through their instalments only."""
    return (r.net_income - (r.total_spending - r.bnpl_purchases) - r.debt_payments - r.family_support
            - r.event_costs - r.other_fees)


@dataclass
class MonthState:
    index: int
    month: int | None
    income_median3: float
    dsr: float
    dti: float
    band: int                    # the band shown to the user (with improvement confirmation, D-49)
    band_name: str
    raw_band: int                # this month's band from the thresholds alone
    cushion_months: float
    savings_rate3: float | None
    shortfalls_last3: int
    insufficient_income: bool


def compute_states(records: list[MonthRecord], thresholds: dict | None = None) -> list[MonthState]:
    t = thresholds or load_thresholds()
    w_len, k = t["income_window_months"], t.get("improvement_confirm_months", 1)
    states, prev_raw, shown_prev, raws = [], None, None, []
    for i, r in enumerate(records):
        win = records[max(0, i - w_len + 1):i + 1]
        med = median(x.net_income for x in win)
        dsr = r.debt_payments / med if med > 0 else DSR_CAP
        dti = r.outstanding_debt / (12 * med) if med > 0 else DSR_CAP
        raw = band(min(dsr, DSR_CAP), med, prev_raw, t)
        raws.append(raw)
        if shown_prev is None or INSUFFICIENT in (raw, shown_prev) or raw >= shown_prev:
            b = raw                                       # C1, C3: shown at once
        else:                                             # C2: an improvement must hold k months
            run = 0
            for x in reversed(raws):                      # consecutive recent months better than shown
                if x == INSUFFICIENT or x >= shown_prev:
                    break
                run += 1
            b = max(raws[-k:]) if run >= k else shown_prev
        need = sum(x.essential_spending + x.debt_payments for x in win) / len(win)
        cushion = r.cash / max(need, 1.0)
        inc = sum(x.net_income for x in win)
        saved = sum(saved_amount(x) for x in win)
        rate = saved / inc if inc > 0 and any(x.total_spending for x in win) else None
        states.append(MonthState(index=i, month=r.month, income_median3=med, dsr=dsr, dti=dti, band=b,
                                 band_name=NAMES[b], raw_band=raw, cushion_months=cushion, savings_rate3=rate,
                                 shortfalls_last3=sum(x.shortfall for x in win),
                                 insufficient_income=(b == INSUFFICIENT)))
        prev_raw, shown_prev = raw, b
    return states
