"""The pre-registered comparator (frozen spec v1.0 §13, Should): the app's Monte Carlo
P(shortfall in the next 3 months), scored on exactly the rows O2 was evaluated on (medium noise,
master seed). **Reported, never part of the criterion**; the O2 result is not touched.

    .venv\\Scripts\\python -m ml.mc_comparator            # all 6,646 rows (see the time estimate it prints)
    .venv\\Scripts\\python -m ml.mc_comparator --rows 200 # a quick sample, for checking only

Design (fixed before looking at any result, D-98)
  rows      the labelled rows of ml/results/medium_seed20261009/oof.parquet (the O2 rows, same order)
  history   that user's months max(1, t-5)..t, mapped to MonthRecords exactly as the Monte Carlo
            coverage audit does (sim/investigate_monte_carlo.py); never a month after t (rule 1).
            The app uses up to 6 past months (D-79), the ML features 3; both look only backwards
  game      GameSnapshot(cash at t, 0, mean essentials + commitments of the last 3 months, level 1):
            it only affects the illustrative room, not the shortfall probability
  forecast  sim.monte_carlo.simulate_future(horizon=3, paths=2,000, the app's default), score =
            shortfall_probability; seed 50,000 + 100 x user_id + t (fixed, reproducible)
  metrics   PR-AUC on the O2 label (band worse OR shortfall) and, because the Monte Carlo models
            only cash, on the shortfall part alone; 1,000-resample user-level bootstrap CIs; paired
            differences against the chosen model (logistic regression) and the best baseline (B0)
Expected (stated before the run): the Monte Carlo can't foresee the band-worsening part (24% of
positives), and its intervals under-cover (73% vs 80%, D-81), so it should rank below the ML model.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from engine.state import MonthRecord
from sim.monte_carlo import FutureProfile, GameSnapshot, simulate_future

from .evaluate import bootstrap, ci, pr_auc

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
DATA = ROOT / CFG["data_dir"] / f"medium_seed{CFG['master_seed']}"
OOF = ROOT / CFG["results_dir"] / f"medium_seed{CFG['master_seed']}" / "oof.parquet"
OUT = ROOT / CFG["results_dir"] / "mc_comparator.json"
HORIZON, PATHS, HISTORY = 3, 2000, 6


def record(r) -> MonthRecord:
    """One generator month as the app's MonthRecord (same mapping as the coverage audit)."""
    return MonthRecord(net_income=r.net_income, debt_payments=r.commitments_total, outstanding_debt=r.outstanding_debt,
                       cash=r.cash, essential_spending=r.spend_essential, total_spending=r.spend_total,
                       family_support=r.family_support, month=int(r.month), bnpl_purchases=r.bnpl_purchases,
                       bnpl_instalments=r.pay_bnpl, education_spending=r.spend_education, other_fees=r.late_fees,
                       event_costs=r.event_shock_cost + r.event_minor_cost)


def score(rows: list, user, t: int) -> float:
    """P(shortfall in months t+1..t+3) from months max(1, t-5)..t only."""
    hist = [record(r) for r in rows[max(0, t - HISTORY):t]]
    assert hist and all(h.month <= t for h in hist)                       # rule 1: nothing after t
    profile = FutureProfile(user.employment_type, int(user.festive_month), bool(user.has_car), bool(user.has_motorbike))
    game = GameSnapshot(hist[-1].cash, 0.0, max(1.0, float(np.mean([h.essential_spending + h.debt_payments
                                                                   for h in hist[-3:]]))), 1)
    return simulate_future(hist, profile, game, seed=50_000 + 100 * int(user.user_id) + t, paths=PATHS,
                           horizon=HORIZON).shortfall_probability


def score_rows(oof: pd.DataFrame, monthly: pd.DataFrame, users: pd.DataFrame) -> np.ndarray:
    by_user = {u: list(g.sort_values("month").itertuples()) for u, g in monthly.groupby("user_id")}
    info = users.set_index("user_id")
    out = np.empty(len(oof))
    for i, (u, t) in enumerate(zip(oof.user_id.to_numpy(), oof.t.to_numpy())):
        user = info.loc[u]
        user = type("U", (), {"user_id": u, **user.to_dict()})
        out[i] = score(by_user[u], user, int(t))
    return out


def evaluate(oof: pd.DataFrame, mc: np.ndarray, B: int, seed: int, level: float) -> dict:
    df = oof.assign(mc=mc)
    res = {"rows": int(len(df)), "users": int(df.user_id.nunique()), "prevalence": float(df.y.mean())}
    for target, col in (("label", "y"), ("shortfall_part", "shortfall_t1_t3")):
        d = df.assign(y=df[col].astype(int))
        cont = ["mc", "lr", "B0"]
        point = {c: pr_auc(d.y, d[c]) for c in cont}
        boot = bootstrap(d, cont, B, seed)
        res[target] = {"prevalence": float(d.y.mean()), "point": point,
                       "ci": {c: ci(boot[:, k], level) for k, c in enumerate(cont)},
                       "mc_minus_lr": [point["mc"] - point["lr"], *ci(boot[:, 0] - boot[:, 1], level)],
                       "mc_minus_b0": [point["mc"] - point["B0"], *ci(boot[:, 0] - boot[:, 2], level)]}
    return res


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=int, help="score only the first N rows (a check, never reported)")
    a = ap.parse_args(argv)
    oof = pd.read_parquet(OOF)
    if a.rows:
        oof = oof.iloc[:a.rows]
    monthly, users = pd.read_parquet(DATA / "monthly.parquet"), pd.read_parquet(DATA / "users.parquet")
    t0 = time.perf_counter()
    first = score_rows(oof.iloc[:20], monthly, users)
    per_row = (time.perf_counter() - t0) / 20
    print(f"about {per_row * len(oof) / 60:.1f} minutes for {len(oof)} rows", flush=True)
    mc = np.concatenate([first, score_rows(oof.iloc[20:], monthly, users)]) if len(oof) > 20 else first[:len(oof)]
    res = evaluate(oof, mc, 100 if a.rows else CFG["bootstrap_resamples"], CFG["master_seed"], CFG["ci_level"])
    res.update(sample_only=bool(a.rows), minutes=round((time.perf_counter() - t0) / 60, 1),
               design="ml/mc_comparator.py docstring (D-98)")
    if not a.rows:
        OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
        oof[["user_id", "t"]].assign(mc=mc).to_parquet(OUT.with_suffix(".parquet"), index=False)
    print(json.dumps({k: res[k] for k in ("label", "shortfall_part")}, indent=1))
    return res


if __name__ == "__main__":
    main()
