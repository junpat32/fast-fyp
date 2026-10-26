"""Features X(u,t) of spec §11 (frozen), from observable files only, months t-2..t.

Invariants
  X1  a feature for month t reads monthly/flags rows with month <= t only (tested);
      the one exception is the calendar group, which uses known future dates (allowed by §11)
  X2  no column from latent*.parquet is ever read here (CLAUDE.md rule 3)
  X3  rows are (user, t) for t = 3..9; rows excluded by the label rule are dropped
Encoding choices (implementation): flags that are not yet scorable count as "not fired";
the calendar group is two binaries (festive / semester start in t+1..t+3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEMESTER_MONTHS = (3, 8, 11)          # spec §5, C-26
AGE_BANDS = ("18-19", "20-24", "25-29", "30-35")
TYPES = ("employee", "gig", "student")
BANDS = ("GREEN", "YELLOW", "RED")

FEATURES = (["inc_median3", "inc_cv3"] + [f"type_{t}" for t in TYPES] + [f"age_{a}" for a in AGE_BANDS]
            + ["essential_share3", "disc_cv3", "overrun_count3", "savings_rate3"]
            + ["dsr_t", "dti_t"] + [f"band_{b}" for b in BANDS]
            + ["bnpl_active", "bnpl_new3", "has_personal_loan"]
            + ["lives_with_parents", "family_support"]
            + ["cushion_t", "cash_slope3", "shortfall_last3"]
            + ["flag_impulsivity", "flag_overconfidence", "flag_delayed_correction"]
            + ["shock_count3", "festive_next3", "semester_next3"])


def _wide(df: pd.DataFrame, col: str, users: np.ndarray, months: int) -> np.ndarray:
    w = df.pivot(index="user_id", columns="month", values=col).reindex(index=users, columns=range(1, months + 1))
    return w.to_numpy(dtype=float, na_value=np.nan)


def _cv(a: np.ndarray) -> np.ndarray:
    mean = a.mean(axis=1)
    sd = a.std(axis=1, ddof=1)
    return np.where(mean > 0, sd / np.where(mean > 0, mean, 1), 0.0)


def build_features(monthly: pd.DataFrame, users: pd.DataFrame, flags: pd.DataFrame,
                   labels: pd.DataFrame | None = None, ts=range(3, 10)) -> pd.DataFrame:
    users = users.sort_values("user_id")
    uid = users.user_id.to_numpy()
    M = int(monthly.month.max())
    W = {c: _wide(monthly, c, uid, M) for c in (
        "net_income", "spend_essential", "spend_total", "spend_discretionary", "saved", "dsr", "dti",
        "bnpl_new_purchases", "bal_personal_loan", "cushion_months", "cash", "shock_count")}
    W["overrun"] = _wide(monthly.assign(overrun=monthly.overrun.astype("Float64")), "overrun", uid, M)
    W["shortfall"] = _wide(monthly.assign(shortfall=monthly.shortfall.astype(float)), "shortfall", uid, M)
    band = monthly.pivot(index="user_id", columns="month", values="band").reindex(index=uid, columns=range(1, M + 1))
    F = {k: _wide(flags.assign(**{k: flags[k].astype("Float64")}), k, uid, M)
         for k in ("impulsivity", "overconfidence", "delayed_correction")}

    rows = []
    for t in ts:
        i = t - 1
        w = slice(i - 2, i + 1)
        inc = W["net_income"][:, w]
        x = {"user_id": uid, "t": t,
             "inc_median3": np.median(inc, axis=1), "inc_cv3": _cv(inc)}
        for typ in TYPES:
            x[f"type_{typ}"] = (users.employment_type.to_numpy() == typ).astype(float)
        for a in AGE_BANDS:
            x[f"age_{a}"] = (users.age_band.to_numpy() == a).astype(float)
        tot = W["spend_total"][:, w].sum(axis=1)
        x["essential_share3"] = np.where(tot > 0, W["spend_essential"][:, w].sum(axis=1) / np.where(tot > 0, tot, 1), 0.0)
        x["disc_cv3"] = _cv(W["spend_discretionary"][:, w])
        x["overrun_count3"] = np.nansum(W["overrun"][:, w], axis=1)
        x["savings_rate3"] = W["saved"][:, w].sum(axis=1) / np.maximum(inc.sum(axis=1), 1.0)
        x["dsr_t"], x["dti_t"] = W["dsr"][:, i], W["dti"][:, i]
        for b in BANDS:
            x[f"band_{b}"] = (band[t].to_numpy() == b).astype(float)
        x["bnpl_active"] = W["bnpl_new_purchases"][:, i - 1] + W["bnpl_new_purchases"][:, i]   # 3-instalment plans still owing after t
        x["bnpl_new3"] = W["bnpl_new_purchases"][:, w].sum(axis=1)
        x["has_personal_loan"] = (W["bal_personal_loan"][:, i] > 0).astype(float)
        x["lives_with_parents"] = users.lives_with_parents.to_numpy().astype(float)
        x["family_support"] = users.family_support.to_numpy().astype(float)
        x["cushion_t"] = W["cushion_months"][:, i]
        x["cash_slope3"] = (W["cash"][:, i] - W["cash"][:, i - 2]) / 2       # OLS slope over 3 equally spaced months
        x["shortfall_last3"] = (W["shortfall"][:, w].sum(axis=1) > 0).astype(float)
        for k in F:
            x[f"flag_{k}"] = np.nan_to_num(F[k][:, i], nan=0.0)
        x["shock_count3"] = W["shock_count"][:, w].sum(axis=1)
        nxt = {t + 1, t + 2, t + 3}
        x["festive_next3"] = users.festive_month.isin(nxt).to_numpy().astype(float)
        x["semester_next3"] = ((users.employment_type.to_numpy() == "student")
                               & bool(nxt & set(SEMESTER_MONTHS))).astype(float)
        x["employment_type"] = users.employment_type.to_numpy()
        x["band_t"] = band[t].to_numpy()
        rows.append(pd.DataFrame(x))
    X = pd.concat(rows, ignore_index=True)
    X = X.astype({f: float for f in FEATURES})
    if labels is not None:
        lab = labels[labels.exclusion_reason == ""][["user_id", "t", "y", "worsened", "shortfall_t1_t3"]]
        X = X.merge(lab, on=["user_id", "t"], how="inner")
        X["y"] = X["y"].astype(int)
    return X.sort_values(["user_id", "t"]).reset_index(drop=True)


def check_no_lookahead(monthly: pd.DataFrame, users: pd.DataFrame, flags: pd.DataFrame) -> bool:
    """Invariant X1 (spec §11 'feature-timestamp unit test' and §13 leakage alarm):
    features for month t are identical whether or not months after t exist."""
    for t in range(3, 10):
        full = build_features(monthly, users, flags, ts=[t])
        cut = build_features(monthly[monthly.month <= t], users, flags[flags.month <= t], ts=[t])
        a, b = full[FEATURES].to_numpy(), cut[FEATURES].to_numpy()
        if not (np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(np.nan_to_num(a), np.nan_to_num(b))):
            return False
    return True
