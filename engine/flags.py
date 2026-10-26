"""Behavioural proxy flags (spec §9, D-41): canonical implementation, used by the generator
(re-exported in generator/flags.py) and by the app engine. Observable data only; never hidden traits.

compute_flags returns float arrays (users x months): 1.0 fired, 0.0 not fired, NaN = not scorable
(not enough history). Month index m is 0-based (calendar month m + 1).

Invariants
  F1  the flag at month m reads only months <= m, except overconfidence's "next target",
      which is set from data up to m (generator) or by the user at the start of m + 1 (app;
      default: the goal is kept), so there is no look-ahead into outcomes
  F2  inputs are observable only: spending, budget, saved, savings rate, band, cushion
"""
from __future__ import annotations

import warnings

import numpy as np

from .bands import RED


def compute_flags(r: dict, festive_month: np.ndarray, fcfg: dict) -> dict:
    disc, budget, overrun = r["disc"], r["budget"], r["overrun"]
    n, M = disc.shape
    T = r["target"].shape[1]          # may be M + 1 in the app (next month's goal already known)
    imp = np.full((n, M), np.nan)
    ovc = np.full((n, M), np.nan)
    dc = np.full((n, M), np.nan)
    cal = np.arange(1, M + 1)

    for m in range(2, M):
        w = slice(m - 2, m + 1)
        # ---- impulsivity: CV of discretionary (festive month excluded) and >= 2 overruns ----
        if not np.isnan(budget[:, w]).any():
            d = np.where(festive_month[:, None] == cal[w][None, :], np.nan, disc[:, w])
            cnt = (~np.isnan(d)).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.nanmean(d, axis=1)
                sd = np.nanstd(d, axis=1, ddof=1)
                cv = np.where((cnt >= 2) & (mean > 0), sd / mean, 0.0)
            over = np.nansum(overrun[:, w], axis=1)
            imp[:, m] = ((cv > fcfg["impulsivity_cv"]) & (over >= fcfg["impulsivity_overruns"])).astype(float)

        # ---- overconfidence: < 60% of goal for 3 months and next goal cut by < 20% ----
        if m >= 3 and m + 1 < T:
            low = (r["achieved"][:, w] < fcfg["overconfidence_achievement"]).all(axis=1)
            kept = r["target"][:, m + 1] > fcfg["overconfidence_target_keep"] * r["target"][:, m]
            ovc[:, m] = (low & kept).astype(float)

        # ---- delayed correction: under pressure 2 months, no smoothed correction ----
        press = ((r["band"][:, m - 1:m + 1] == RED) | (r["cushion"][:, m - 1:m + 1] < 1)).all(axis=1)
        prior = slice(max(0, m - 4), m - 1)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)   # all-NaN savings rate (zero income) -> NaN, handled below
            cut = disc[:, m - 1:m + 1].mean(axis=1) <= fcfg["dc_cut"] * np.median(disc[:, prior], axis=1)
            now_rate = np.nanmean(r["savings_rate"][:, m - 1:m + 1], axis=1)
            prior_rate = np.nanmean(r["savings_rate"][:, prior], axis=1)
        save_up = np.nan_to_num(now_rate - prior_rate, nan=-np.inf) >= fcfg["dc_rate_rise"]
        dc[:, m] = (press & ~(cut | save_up)).astype(float)

    return {"impulsivity": imp, "overconfidence": ovc, "delayed_correction": dc}
