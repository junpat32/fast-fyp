"""Phase 5 (26 Oct brief, improvement D): conformal adjustment of the Future Self range (D-142).

    .venv\\Scripts\\python -m sim.recalibrate_monte_carlo --dev        # debugging (seed 999), never reported
    .venv\\Scripts\\python -m sim.recalibrate_monte_carlo --calibrate  # once: writes the offsets table
    .venv\\Scripts\\python -m sim.recalibrate_monte_carlo --evaluate   # once, after the table is committed

PLAN (committed before any run on the calibration or evaluation seeds; D-132 integrity rules).
Exploratory (D-132 N6): the D-80 audit's 73.25% is already known.

Question  Can a split-conformal adjustment (sim/conformal.py) bring the Monte Carlo's P10-P90 cushion
          range to about 80% coverage on new synthetic users, without hiding undercoverage in an
          employment group or a month ahead, and without buying coverage with a needlessly wide range?
Forecast  sim.monte_carlo.simulate_future, unchanged (D-79/D-80 model), 2,000 paths (the app's
          default). Origin: generator month 6, as in D-80. History: the last n complete months, for each
          n = 3, 4, 5, 6 (the app forecasts from 3 to 6). Months ahead h = 1..6. Truth: the user's actual
          cushion at month 6 + h, defined as in the D-80 audit (cash / mean of essentials + commitments
          over the 3 months ending there). Path seeds: SeedSequence([population seed, user, n]).
Data      Generator v1 config, medium noise, no transactions, 1,000 users per population (USERS).
          Calibration: the default world on seeds 62001-62009 (claims register block). The fitted
          offsets go to sim/monte_carlo_conformal.json, which is committed before any evaluation
          population is generated (--evaluate refuses an uncommitted or changed table, and runs once).
          Evaluation: the default world on seeds 63001-63003; the alternative worlds W1, W2, W3
          (ml.structural.world_config, the phase 4 definitions) on seeds 63004, 63005 and 63006.
Method    Asymmetric split conformal per cell (employment type x h x n), each tail at 10% (C1-C4).
Measures  Per cell and pooled, raw and adjusted on the same users: coverage (Wilson 95% interval),
          share below P10, share above P90, mean width, mean interval score (Gneiting and Raftery 2007,
          alpha 0.2: width + 10 x the distance by which the truth falls outside), median P50 error.
Primary   Default world, evaluation seeds, h = 6, n = 6 (the D-80 audit's measure, 73.25% before):
          P1  overall adjusted coverage between 77% and 83%;
          P2  every employment type's adjusted coverage at least 74%;
          P3  each tail (below, above) at most 13%;
          P4  adjusted mean interval score no worse than raw (a wider range must also be a better one).
          Expectation, stated now: within the default world the guarantee makes P1-P3 likely by
          construction, so the informative results are P4 (the cost in width) and the shifted worlds.
Decision  All four hold: the API shows the adjusted range (a new decision, with tests and a claims
          register entry); the app keeps "if recent habits continue" (D-81), never says "validated 80%
          prediction interval", and makes no real-world claim. Any fails: the raw range stays and the
          report says which failed; shrinkage toward a population (which changes M1) is Patrick's
          decision (D-132 N3).
Secondary Reported without pass/fail: every h, n and employment type; W1-W3, where exchangeability
          does not hold (a test of shift, not of the guarantee): "holds" if overall adjusted coverage at
          h = 6, n = 6 is at least 74%, otherwise "degrades"; the asymmetry of misses.
Not covered  The shortfall probability, CFaR and Expected Shortfall (not shown as percentages, D-100);
          origins other than month 6 (the generator year has 12 months, so only July to December is
          forecast); real people (rule 12).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from engine.state import MonthRecord
from generator.run import generate
from ml.structural import world_config
from sim import conformal
from sim.monte_carlo import FutureProfile, GameSnapshot, simulate_future

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "sim" / "results"
CALIBRATION_SEEDS = tuple(range(62001, 62010))
EVALUATION = (("default", 63001), ("default", 63002), ("default", 63003),
              ("W1 stress spending", 63004), ("W2 persistent income shocks", 63005),
              ("W3 correlated expenses", 63006))
USERS = 1000
PATHS = 2000
ORIGIN = 6
DEV_SEED, DEV_USERS, DEV_PATHS = 999, 150, 500
SCORE_ALPHA = 0.2
P1_RANGE, P2_MIN, P3_MAX, SHIFT_MIN = (0.77, 0.83), 0.74, 0.13, 0.74


def records(rows: list) -> list[MonthRecord]:
    """The generator's monthly rows as the app's MonthRecords (the D-80 audit's mapping)."""
    return [MonthRecord(net_income=r.net_income, debt_payments=r.commitments_total,
                        outstanding_debt=r.outstanding_debt, cash=r.cash,
                        essential_spending=r.spend_essential, total_spending=r.spend_total,
                        family_support=r.family_support, month=int(r.month),
                        bnpl_purchases=r.bnpl_purchases, bnpl_instalments=r.pay_bnpl,
                        education_spending=r.spend_education, other_fees=r.late_fees,
                        event_costs=r.event_shock_cost + r.event_minor_cost) for r in rows]


def truth(rows: list, h: int) -> float:
    """The actual cushion h months after the origin (rows sorted by month, month 1 first)."""
    need = np.mean([r.spend_essential + r.commitments_total for r in rows[ORIGIN + h - 3:ORIGIN + h]])
    return float(rows[ORIGIN + h - 1].cash / max(1.0, need))


def collect(world: str, seed: int, n_users: int, paths: int = PATHS) -> pd.DataFrame:
    """One row per user, history length and month ahead: the raw range and the truth."""
    data = generate(world_config(world, n_users), "medium", seed, with_transactions=False)
    grouped = data["monthly"].groupby("user_id")
    out = []
    for u in data["users"].itertuples():
        rows = list(grouped.get_group(u.user_id).sort_values("month").itertuples())
        profile = FutureProfile(u.employment_type, int(u.festive_month), bool(u.has_car), bool(u.has_motorbike))
        actual = [truth(rows, h) for h in range(1, conformal.HORIZON + 1)]
        for n in conformal.HISTORY:
            hist = records(rows[ORIGIN - n:ORIGIN])          # only months before the origin (rule 1)
            game = GameSnapshot(hist[-1].cash, 0, max(1.0, float(np.mean(
                [r.essential_spending + r.debt_payments for r in hist[-3:]]))), 1)
            path_seed = int(np.random.SeedSequence([seed, int(u.user_id), n]).generate_state(1)[0])
            forecast = simulate_future(hist, profile, game, seed=path_seed, paths=paths)
            for h, (m, y) in enumerate(zip(forecast.cushion, actual), start=1):
                out.append((world, seed, int(u.user_id), u.employment_type, n, h, m.p10, m.p50, m.p90, y))
    return pd.DataFrame(out, columns=["world", "seed", "user_id", "employment_type", "n_history", "h",
                                      "p10", "p50", "p90", "truth"])


def fit(df: pd.DataFrame) -> dict:
    """The offsets table: one (lower, upper) pair per employment type, history length and month ahead."""
    offsets, sizes = {}, {}
    for e in conformal.EMPLOYMENT:
        users = df[df.employment_type == e]
        offsets[e] = {}
        sizes[e] = len(users[["seed", "user_id"]].drop_duplicates())
        for n in conformal.HISTORY:
            cells = []
            for h in range(1, conformal.HORIZON + 1):
                c = users[(users.n_history == n) & (users.h == h)]
                cells.append([round(v, 6) for v in conformal.fit_cell(c.p10, c.p90, c.truth)])
            offsets[e][str(n)] = cells
    return {"version": 1, "method": "asymmetric split conformal (CQR), each tail 10%, per employment type,"
                                     " months of history and month ahead (sim/conformal.py, D-142)",
            "tail": conformal.TAIL, "calibration_seeds": sorted({int(s) for s in df.seed}),
            "users_per_type": sizes, "offsets": offsets}


def with_adjusted(df: pd.DataFrame, table: dict) -> pd.DataFrame:
    df = df.copy()
    lo, hi = [], []
    for r in df.itertuples():
        lower, upper = table["offsets"][r.employment_type][str(r.n_history)][r.h - 1]
        a, b = conformal.adjust(r.p10, r.p50, r.p90, lower, upper)
        lo.append(a)
        hi.append(b)
    df["lo"], df["hi"] = lo, hi
    return df


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(centre - half), 4), round(float(centre + half), 4)]


def measures(lo, hi, med, y) -> dict:
    lo, hi, med, y = (np.asarray(x, dtype=float) for x in (lo, hi, med, y))
    below, above = y < lo, y > hi
    covered = int((~below & ~above).sum())
    score = (hi - lo) + (2 / SCORE_ALPHA) * ((lo - y) * below + (y - hi) * above)
    return {"n": len(y), "coverage": round(covered / len(y), 4), "coverage_ci": wilson(covered, len(y)),
            "below": round(float(below.mean()), 4), "above": round(float(above.mean()), 4),
            "mean_width": round(float(np.mean(hi - lo)), 4), "interval_score": round(float(score.mean()), 4),
            "median_p50_error": round(float(np.median(med - y)), 4)}


def summarise(df: pd.DataFrame) -> dict:
    """Raw and adjusted measures per (employment type or all) x history length x month ahead."""
    out = {}
    for (n, h), cell in df.groupby(["n_history", "h"]):
        for group, g in [("all", cell)] + list(cell.groupby("employment_type")):
            out[f"{group}_n{n}_h{h}"] = {"raw": measures(g.p10, g.p90, g.p50, g.truth),
                                         "adjusted": measures(g.lo, g.hi, g.p50, g.truth)}
    return out


def primary(s: dict) -> dict:
    a = {k: s[f"{k}_n6_h6"]["adjusted"] for k in ("all",) + conformal.EMPLOYMENT}
    raw = s["all_n6_h6"]["raw"]
    checks = {"P1": P1_RANGE[0] <= a["all"]["coverage"] <= P1_RANGE[1],
              "P2": all(a[e]["coverage"] >= P2_MIN for e in conformal.EMPLOYMENT),
              "P3": a["all"]["below"] <= P3_MAX and a["all"]["above"] <= P3_MAX,
              "P4": a["all"]["interval_score"] <= raw["interval_score"]}
    return {"checks": checks, "all_hold": all(checks.values())}


def table_is_committed(path: Path = conformal.TABLE) -> bool:
    """True when the table is tracked by git and identical to its last commit (C1)."""
    rel = path.relative_to(ROOT).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True)
    changed = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=ROOT, capture_output=True, text=True)
    return tracked.returncode == 0 and changed.stdout.strip() == ""


def calibrate(dev: bool = False) -> dict:
    if not dev and conformal.TABLE.exists():
        raise SystemExit("the offsets table already exists; calibration runs once (C1)")
    seeds = (DEV_SEED,) if dev else CALIBRATION_SEEDS
    n_users, paths = (DEV_USERS, DEV_PATHS) if dev else (USERS, PATHS)
    df = pd.concat([collect("default", s, n_users, paths) for s in seeds], ignore_index=True)
    table = fit(df)
    if not dev:
        conformal.TABLE.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
        cal = summarise(with_adjusted(df, table))
        (RESULTS / "monte_carlo_conformal_calibration.json").write_text(
            json.dumps({"table": table, "in_sample": cal}, indent=2) + "\n", encoding="utf-8")
    return table


def evaluate(dev: bool = False, table: dict | None = None) -> dict:
    out_path = RESULTS / "monte_carlo_conformal_eval.json"
    if not dev:
        if not table_is_committed():
            raise SystemExit("commit sim/monte_carlo_conformal.json before evaluating (C1)")
        if out_path.exists():
            raise SystemExit("the evaluation seeds have been used; it runs once")
        table = conformal.load_table()
    plan = [("default", DEV_SEED), ("W1 stress spending", DEV_SEED)] if dev else EVALUATION
    n_users, paths = (DEV_USERS, DEV_PATHS) if dev else (USERS, PATHS)
    frames = [with_adjusted(collect(w, s, n_users, paths), table) for w, s in plan]
    df = pd.concat(frames, ignore_index=True)
    worlds = {}
    for w, g in df.groupby("world", sort=False):
        worlds[w] = summarise(g)
    res = {"table_sha256": hashlib.sha256(conformal.TABLE.read_bytes()).hexdigest() if not dev else None,
           "users_per_population": n_users, "paths": paths, "evaluation": [list(x) for x in plan],
           "primary": primary(worlds["default"]), "worlds": worlds,
           "shift": {w: ("holds" if s["all_n6_h6"]["adjusted"]["coverage"] >= SHIFT_MIN else "degrades")
                     for w, s in worlds.items() if w != "default"}}
    if not dev:
        out_path.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return res


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dev", action="store_true")
    mode.add_argument("--calibrate", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    args = ap.parse_args(argv)
    if args.dev:
        table = calibrate(dev=True)
        res = evaluate(dev=True, table=table)
    elif args.calibrate:
        res = calibrate()
    else:
        res = evaluate()
    print(json.dumps(res.get("primary", res.get("users_per_type")), indent=2))
    return res


if __name__ == "__main__":
    main()
