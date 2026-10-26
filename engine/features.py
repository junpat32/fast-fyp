"""Forecast features for ONE user, from their own months (serving side of spec §11).

Must reproduce ml/features.py exactly on the same data: the forecast model was trained and
evaluated (O2) with those definitions. tests/test_equivalence.py checks this on synthetic users.

Invariants
  X1  features for month index i read records 0..i only (calendar features use known dates)
  X2  bands and DSR use the FROZEN spec-v1 per-month rule (shared/thresholds_spec_v1.json),
      i.e. the rule the model was trained on, not the app's display rule (D-49)
  X3  feature order equals ml.features.FEATURES (tested)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .bands import NAMES, load_thresholds
from .flags import compute_flags
from .state import MonthRecord, compute_states, saved_amount

FEATURES = (["inc_median3", "inc_cv3", "type_employee", "type_gig", "type_student",
             "age_18-19", "age_20-24", "age_25-29", "age_30-35",
             "essential_share3", "disc_cv3", "overrun_count3", "savings_rate3",
             "dsr_t", "dti_t", "band_GREEN", "band_YELLOW", "band_RED",
             "bnpl_active", "bnpl_new3", "has_personal_loan", "lives_with_parents", "family_support",
             "cushion_t", "cash_slope3", "shortfall_last3",
             "flag_impulsivity", "flag_overconfidence", "flag_delayed_correction",
             "shock_count3", "festive_next3", "semester_next3"])
AGE_BANDS = [(19, "18-19"), (24, "20-24"), (29, "25-29"), (35, "30-35")]
LABELS = {   # plain-language names, shared by the app's reasons and the O2 report
    "inc_median3": "typical monthly income (last 3 months)", "inc_cv3": "how much income varied",
    "type_employee": "is an employee", "type_gig": "is a gig worker", "type_student": "is a student",
    "age_18-19": "aged 18-19", "age_20-24": "aged 20-24", "age_25-29": "aged 25-29", "age_30-35": "aged 30-35",
    "essential_share3": "share of spending on essentials", "disc_cv3": "how much non-essential spending jumped around",
    "overrun_count3": "months spending above 95% of your usual level (last 3)",
    "savings_rate3": "savings rate (last 3 months)",
    "dsr_t": "debt payments / income (DSR)", "dti_t": "total debt / yearly income (DTI)",
    "band_GREEN": "currently Green", "band_YELLOW": "currently Yellow", "band_RED": "currently Red",
    "bnpl_active": "active BNPL plans", "bnpl_new3": "new BNPL purchases (last 3 months)",
    "has_personal_loan": "has a personal loan", "lives_with_parents": "lives with parents",
    "family_support": "sends money to family", "cushion_t": "months of expenses saved (cushion)",
    "cash_slope3": "cash trend (last 3 months)", "shortfall_last3": "ran out of cash recently",
    "flag_impulsivity": "impulsive-spending flag", "flag_overconfidence": "overconfidence flag",
    "flag_delayed_correction": "delayed-correction flag", "shock_count3": "unexpected costs (last 3 months)",
    "festive_next3": "festive month coming up", "semester_next3": "semester start coming up",
}
SPEC_V1 = load_thresholds(Path(__file__).resolve().parents[1] / "shared" / "thresholds_spec_v1.json")
FLAGS_CFG = load_thresholds()["flags"]


@dataclass
class UserProfile:
    employment_type: str               # "employee" | "gig" | "student" (onboarding)
    age: int
    lives_with_parents: bool = False   # asked at onboarding (D-42)
    family_support: bool = False       # sends money to family regularly (D-42)
    festive_month: int | None = None   # the festival the user celebrates (calendar month)
    semester_months: tuple = (3, 8, 11)


def _cv(a: np.ndarray) -> float:
    m = a.mean()
    return float(a.std(ddof=1) / m) if m > 0 else 0.0


def flag_arrays(records: list[MonthRecord], profile: UserProfile, fcfg: dict, next_target="keep") -> dict:
    """Inputs for engine.flags.compute_flags for one user (arrays of shape 1 x months).
    next_target: the goal for the month after the last record; "keep" (default: the user's goal
    stays unless changed), a number, or None (unknown)."""
    M = len(records)
    total = np.array([r.total_spending for r in records], float)
    ess = np.array([r.essential_spending for r in records], float)
    inc = np.array([r.net_income for r in records], float)
    saved = np.array([saved_amount(r) for r in records], float)
    budget = np.array([fcfg["budget_factor"] * np.median(total[max(0, i - 3):i]) if i > 0 else np.nan
                       for i in range(M)])
    overrun = np.where(np.isnan(budget), np.nan, (total > budget).astype(float))
    target = [np.nan if r.savings_target is None else float(r.savings_target) for r in records]
    if next_target == "keep":
        target.append(target[-1])
    elif next_target is not None:
        target.append(float(next_target))
    target = np.array(target)
    with np.errstate(divide="ignore", invalid="ignore"):
        achieved = np.where(target[:M] > 0, saved / target[:M], np.nan)
        rate = np.where(inc > 0, saved / inc, np.nan)
    states = compute_states(records, SPEC_V1)
    return {"disc": (total - ess)[None, :], "budget": budget[None, :], "overrun": overrun[None, :],
            "achieved": achieved[None, :], "target": target[None, :],
            "band": np.array([s.raw_band for s in states])[None, :],
            "cushion": np.array([s.cushion_months for s in states])[None, :],
            "savings_rate": rate[None, :]}


def user_flags(records, profile: UserProfile, fcfg: dict, next_target="keep") -> dict:
    fm = np.array([profile.festive_month if profile.festive_month is not None else 0])
    f = compute_flags(flag_arrays(records, profile, fcfg, next_target), fm, fcfg)
    return {k: v[0] for k, v in f.items()}


def features_at(profile: UserProfile, records: list[MonthRecord], i: int, flags: dict) -> dict:
    """Feature dict for month index i (needs i >= 2). flags: output of user_flags."""
    if i < 2:
        raise ValueError("forecast features need at least 3 months of records")
    w = records[i - 2:i + 1]
    states = compute_states(records[:i + 1], SPEC_V1)
    s = states[-1]
    inc = np.array([r.net_income for r in w], float)
    total = np.array([r.total_spending for r in w], float)
    ess = np.array([r.essential_spending for r in w], float)
    allrec = records[:i + 1]
    tot_all = np.array([r.total_spending for r in allrec], float)
    over = 0.0
    for j in range(i - 2, i + 1):
        if j > 0 and tot_all[j] > FLAGS_CFG["budget_factor"] * np.median(tot_all[max(0, j - 3):j]):
            over += 1
    age_band = next(lbl for lim, lbl in AGE_BANDS if profile.age <= lim)
    t = records[i].month
    nxt = {((t + k - 1) % 12) + 1 for k in (1, 2, 3)} if t else set()
    x = {
        "inc_median3": float(np.median(inc)), "inc_cv3": _cv(inc),
        **{f"type_{k}": float(profile.employment_type == k) for k in ("employee", "gig", "student")},
        **{f"age_{a}": float(age_band == a) for _, a in AGE_BANDS},
        "essential_share3": float(ess.sum() / total.sum()) if total.sum() > 0 else 0.0,
        "disc_cv3": _cv(total - ess), "overrun_count3": over,
        "savings_rate3": float(sum(saved_amount(r) for r in w) / max(inc.sum(), 1.0)),
        "dsr_t": s.dsr, "dti_t": s.dti,
        **{f"band_{b}": float(NAMES[s.raw_band] == b) for b in ("GREEN", "YELLOW", "RED")},
        "bnpl_active": float(records[i - 1].bnpl_new_count + records[i].bnpl_new_count),
        "bnpl_new3": float(sum(r.bnpl_new_count for r in w)),
        "has_personal_loan": float(records[i].personal_loan_balance > 0),
        "lives_with_parents": float(profile.lives_with_parents), "family_support": float(profile.family_support),
        "cushion_t": s.cushion_months, "cash_slope3": (records[i].cash - records[i - 2].cash) / 2,
        "shortfall_last3": float(any(r.shortfall for r in w)),
        **{f"flag_{k}": float(np.nan_to_num(flags[k][i], nan=0.0))
           for k in ("impulsivity", "overconfidence", "delayed_correction")},
        "shock_count3": float(sum(r.shock_count for r in w)),
        "festive_next3": float(profile.festive_month in nxt) if profile.festive_month else 0.0,
        "semester_next3": float(profile.employment_type == "student" and bool(nxt & set(profile.semester_months))),
    }
    return {k: x[k] for k in FEATURES}
