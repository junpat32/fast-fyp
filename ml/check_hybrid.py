"""Hybrid check (Q1-B, D-130): does the forecast improve with the Monte Carlo's shortfall chance as an input?

    .venv\\Scripts\\python -m ml.check_hybrid --dev   # debugging on the development dataset (seed 999), never reported
    .venv\\Scripts\\python -m ml.check_hybrid         # the one real run -> ml/results/HYBRID_CHECK.md

Exploratory, for the app only: decided after O2 and after the Monte Carlo comparator (D-99) were seen,
so it is never pre-registered evidence, and the O2 result is not touched. This design and the adoption
rule were written before any hybrid result was computed.

Design
  rows      the O2 rows (medium noise, master seed; the label y as in O2, its exclusions applied)
  inputs    v1  the 32 forecast inputs (ml/features.py, months t-2..t): the app's forecast_v1
            v3  the same 32 plus one: the logit of the Monte Carlo P(shortfall in t+1..t+3), recomputed
                from months t-2..t only (rule 1; the comparator used up to t-5), 2,000 paths, seed
                50,000 + 100 x user_id + t, the probability clipped to [1/4,000, 1 - 1/4,000] first
  model     logistic regression exactly as forecast_v1 and the FA1 check (D-102): standardised,
            class_weight balanced, C = the medium run's chosen C, no re-tuning; isotonic calibration on
            inner GroupKFold(3) predictions of the training users; outer GroupKFold(5) by user, the same
            folds for v1 and v3 (ml.check_v2.calibrated_oof)
  metrics   PR-AUC with 1,000-resample user-level bootstrap CIs, paired v3 - v1, on the label and on its
            shortfall part; mean predicted vs observed and ECE (5 equal-count bins) per type of work and
            age group; the Monte Carlo alone (3-month history) for reference; the Monte Carlo's time per row

Adoption rule: the app switches from forecast_v1 to the hybrid only if all three hold
  (1) gain         the 95% CI lower bound of PR-AUC(v3) - PR-AUC(v1) is above 0
  (2) calibration  in every type of work and age group: the mean calibrated probability is within
                   2 points of the observed rate, and the ECE is at most 0.015 worse than v1's (D-102)
  (3) speed        the Monte Carlo input takes under 0.5 s per assessment on the development laptop
Otherwise the app keeps forecast_v1 and the report says why.

Expected (stated before the run): a small gain at best. The comparator tied with the model (D-99), and
both lean on the same cushion and cash-flow signals, so their scores are probably highly correlated.
Caveat for any gain: the Monte Carlo draws life events from the same deck the generator used, so on
synthetic data it knows the true shock process; for real users the deck is only an estimate.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from generator.run import FROZEN_SPEC, generate, sha256
from ml.check_v2 import calibrated_oof, ece
from ml.evaluate import bootstrap, ci, pr_auc
from ml.features import FEATURES, build_features
from ml.mc_comparator import record
from sim.monte_carlo import FutureProfile, GameSnapshot, simulate_future

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
RESULTS = ROOT / CFG["results_dir"]
HISTORY, HORIZON, PATHS = 3, 3, 2000
MEAN_GAP, ECE_TOLERANCE, MAX_SECONDS = 0.02, 0.015, 0.5          # the adoption rule (docstring)
V3_FEATURES = list(FEATURES) + ["mc_logit"]


def mc_shortfall(rows: list, user, t: int) -> float:
    """P(shortfall in months t+1..t+3) from months t-2..t only. `rows` are the user's months, month 1 first."""
    hist = [record(r) for r in rows[max(0, t - HISTORY):t]]
    assert hist and all(t - HISTORY < h.month <= t for h in hist)        # rule 1: months t-2..t, nothing after t
    profile = FutureProfile(user.employment_type, int(user.festive_month), bool(user.has_car), bool(user.has_motorbike))
    costs = max(1.0, float(np.mean([h.essential_spending + h.debt_payments for h in hist])))
    game = GameSnapshot(hist[-1].cash, 0.0, costs, 1)                    # affects only the illustrative room
    return simulate_future(hist, profile, game, seed=50_000 + 100 * int(user.user_id) + t, paths=PATHS,
                           horizon=HORIZON).shortfall_probability


def logit_clip(p) -> np.ndarray:
    lo = 1 / (2 * PATHS)
    p = np.clip(np.asarray(p, dtype=float), lo, 1 - lo)
    return np.log(p / (1 - p))


def score_mc(X: pd.DataFrame, monthly: pd.DataFrame, users: pd.DataFrame) -> tuple[np.ndarray, float]:
    """The Monte Carlo input for every row of X, and the seconds it took per row."""
    by_user = {u: list(g.sort_values("month").itertuples()) for u, g in monthly.groupby("user_id")}
    info = users.set_index("user_id")
    out = np.empty(len(X))
    t0 = time.perf_counter()
    for i, (u, t) in enumerate(zip(X.user_id.to_numpy(), X.t.to_numpy())):
        user = type("U", (), {"user_id": u, **info.loc[u].to_dict()})
        out[i] = mc_shortfall(by_user[u], user, int(t))
    return out, (time.perf_counter() - t0) / max(1, len(X))


def group_rows(df: pd.DataFrame, by: str) -> list[dict]:
    rows = []
    for name, g in df.groupby(by):
        y = g.y.to_numpy(dtype=float)
        r = {"group": name, "rows": len(g), "observed": y.mean()}
        for m in ("v1", "v3"):
            p = g[m].to_numpy()
            r[f"{m}_mean"], r[f"{m}_ece"], r[f"{m}_pr_auc"] = p.mean(), ece(p, y), pr_auc(y, p)
        r["pass_mean"] = abs(r["v3_mean"] - r["observed"]) <= MEAN_GAP
        r["pass_ece"] = r["v3_ece"] <= r["v1_ece"] + ECE_TOLERANCE
        rows.append(r)
    return rows


def verdict(delta_ci_low: float, groups: dict, seconds_per_row: float) -> dict:
    v = {"gain": delta_ci_low > 0,
         "calibration": all(r["pass_mean"] and r["pass_ece"] for rows in groups.values() for r in rows),
         "speed": seconds_per_row < MAX_SECONDS}
    v["adopt"] = all(v.values())
    return v


def load(dev: bool) -> dict[str, pd.DataFrame]:
    if dev:
        gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
        gcfg["n_users"] = CFG["dev"]["n_users"]
        return generate(gcfg, "medium", CFG["dev"]["seed"], with_transactions=False)
    folder = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["spec_sha256"] != sha256(FROZEN_SPEC):
        raise SystemExit(f"Integrity check failed: {folder} was not generated from the frozen spec")
    return {k: pd.read_parquet(folder / f"{k}.parquet") for k in ("users", "monthly", "flags", "labels")}


def run(dev: bool = False) -> dict:
    t = load(dev)
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    X = X.merge(t["users"][["user_id", "age_band"]], on="user_id", how="left")
    mc, seconds = score_mc(X, t["monthly"], t["users"])
    X = X.assign(mc_logit=logit_clip(mc))
    C = json.loads((RESULTS / f"medium_seed{SEED}" / "metrics.json").read_text(encoding="utf-8"))["chosen_params"]["lr"]["param"]
    df = X[["user_id", "t", "y", "shortfall_t1_t3", "employment_type", "age_band"]].assign(
        y=X.y.astype(int), mc=mc, v1=calibrated_oof(X, list(FEATURES), C), v3=calibrated_oof(X, V3_FEATURES, C))
    B = CFG["dev"]["bootstrap_resamples"] if dev else CFG["bootstrap_resamples"]
    cont = ["v1", "v3", "mc"]
    res = {"dev": dev, "C": C, "rows": len(df), "users": int(df.user_id.nunique()), "seconds_per_row": seconds,
           "correlation_v1_mc": float(np.corrcoef(df.v1, df.mc)[0, 1])}
    for target, col in (("label", "y"), ("shortfall_part", "shortfall_t1_t3")):
        d = df.assign(y=df[col].astype(int))
        boot = bootstrap(d, cont, B, SEED)
        point = {c: pr_auc(d.y, d[c]) for c in cont}
        res[target] = {"prevalence": float(d.y.mean()), "point": point,
                       "ci": {c: ci(boot[:, k], CFG["ci_level"]) for k, c in enumerate(cont)},
                       "v3_minus_v1": [point["v3"] - point["v1"], *ci(boot[:, 1] - boot[:, 0], CFG["ci_level"])]}
    res["overall"] = {m: {"mean": float(df[m].mean()), "ece": ece(df[m].to_numpy(), df.y.to_numpy(dtype=float))}
                      for m in ("v1", "v3")}
    res["groups"] = {by: group_rows(df, by) for by in ("employment_type", "age_band")}
    res["verdict"] = verdict(res["label"]["v3_minus_v1"][1], res["groups"], seconds)
    if not dev:
        df[["user_id", "t", "mc"]].to_parquet(RESULTS / "hybrid_mc3.parquet", index=False)
    return res


def write(res: dict) -> str:
    v, lab, sf, o = res["verdict"], res["label"], res["shortfall_part"], res["overall"]
    yes = lambda b: "yes" if b else "**no**"                                            # noqa: E731
    head = ("**ADOPT the hybrid** (all three conditions hold)" if v["adopt"]
            else "**KEEP forecast_v1** (at least one condition fails)")
    L = ["# Hybrid check: the forecast with the Monte Carlo as an input (D-130)", "",
         ("**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**\n" if res["dev"] else "") +
         "Exploratory, for the app only (the O2 result is unchanged). Design and adoption rule written before any "
         "result: `ml/check_hybrid.py` docstring. Logistic regression, C = "
         f"{res['C']}; {res['rows']:,} rows from {res['users']:,} users.", "",
         f"## Verdict: {head}", "",
         "| Condition | Result | Holds |", "|---|---|---|",
         f"| (1) Gain: CI lower bound of v3 − v1 above 0 | {lab['v3_minus_v1'][0]:+.3f} "
         f"[{lab['v3_minus_v1'][1]:+.3f}, {lab['v3_minus_v1'][2]:+.3f}] | {yes(v['gain'])} |",
         f"| (2) Calibration in every type of work and age group | see the tables below | {yes(v['calibration'])} |",
         f"| (3) Speed: under {MAX_SECONDS} s per assessment | {res['seconds_per_row'] * 1000:.0f} ms | {yes(v['speed'])} |", "",
         "## PR-AUC (95% user-level bootstrap CI)", "",
         f"| Model | O2 label (prevalence {lab['prevalence']:.1%}) | Shortfall part only ({sf['prevalence']:.1%}) |",
         "|---|---|---|"]
    for c, name in (("v1", "v1: forecast_v1 (32 inputs)"), ("v3", "v3: hybrid (33 inputs)"),
                    ("mc", "Monte Carlo alone (months t−2..t)")):
        L.append(f"| {name} | {lab['point'][c]:.3f} [{lab['ci'][c][0]:.3f}, {lab['ci'][c][1]:.3f}] | "
                 f"{sf['point'][c]:.3f} [{sf['ci'][c][0]:.3f}, {sf['ci'][c][1]:.3f}] |")
    L += ["", f"v3 − v1 on the shortfall part: {sf['v3_minus_v1'][0]:+.3f} [{sf['v3_minus_v1'][1]:+.3f}, "
          f"{sf['v3_minus_v1'][2]:+.3f}]. Correlation of v1's calibrated chance with the Monte Carlo's: "
          f"{res['correlation_v1_mc']:.2f}. Mean predicted: v1 {o['v1']['mean']:.1%}, v3 {o['v3']['mean']:.1%}; "
          f"ECE: v1 {o['v1']['ece']:.3f}, v3 {o['v3']['ece']:.3f}.", ""]
    for by, title in (("employment_type", "Type of work"), ("age_band", "Age group")):
        L += [f"## {title}", "", "| Group | Rows | Observed | v1 mean | v3 mean | v1 ECE | v3 ECE | v1 PR-AUC | "
              "v3 PR-AUC | Passes |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in res["groups"][by]:
            ok = "yes" if r["pass_mean"] and r["pass_ece"] else ("NO (mean)" if not r["pass_mean"] else "NO (ECE)")
            L.append(f"| {r['group']} | {r['rows']} | {r['observed']:.1%} | {r['v1_mean']:.1%} | {r['v3_mean']:.1%} | "
                     f"{r['v1_ece']:.3f} | {r['v3_ece']:.3f} | {r['v1_pr_auc']:.3f} | {r['v3_pr_auc']:.3f} | {ok} |")
        L.append("")
    L += ["Caveat (stated before the run): the Monte Carlo draws life events from the same deck the generator used, "
          "so on synthetic data it knows the true shock process; for real users the deck is only an estimate.", ""]
    text = "\n".join(L)
    out = (RESULTS / "dev" if res["dev"] else RESULTS) / "HYBRID_CHECK.md"
    out.write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", action="store_true", help="debug on the development dataset (never reported)")
    a = ap.parse_args(argv)
    res = run(dev=a.dev)
    print(write(res))
    return res


if __name__ == "__main__":
    main()
