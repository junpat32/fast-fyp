"""Structural robustness (26 Oct brief B, trimmed; D-139): does the synthetic world reproduce real relationships
it was not tuned to, and does the frozen forecast still work when people behave differently?

    .venv\\Scripts\\python -m ml.structural --dev   # debugging (small worlds, seed 999), never reported
    .venv\\Scripts\\python -m ml.structural         # the one run -> ml/results/STRUCTURAL.md

**Exploratory** (D-132 N6); this plan and its reading rules were committed before the first full run. Nothing is
tuned and the generator's default output is unchanged (spec v1 path, simulate.py E5; checked against the master data).

Part A, pattern checks on the master data (data only, no model). Each pattern is a direction reported in published
work that the generator was **not** calibrated to; it compares the bottom and top group, per user over the year:
  P1  essentials' share of spending falls as income rises (Engel; DOSM HES 2024 Table 3.15, used only to classify)
  P2  the cushion at month 12 rises with income (Findex 2025 reports resilience by income group; verify)
  P3  running short at least once in the year falls with income (Lusardi, Schneider & Tufano, 2011)
  P4  running short rises with income volatility, observed CV of monthly income (Farrell & Greig, 2016; US data)
  P5  BNPL users run short more often than non-users (BNM FSR reporting on BNPL users; low confidence, verify)
  groups: income quintiles (P1-P3; mean monthly net income), volatility terciles (P4), BNPL users vs not (P5)
  reading rule: "reproduced" if the 95% user-bootstrap interval of the difference (expected direction positive)
  lies above 0; "opposite" if it lies below 0; otherwise "unclear". A failure is reported, never tuned.

Part B, alternative-mechanism worlds (fresh seed 61001 for every world, so differences come from the mechanism;
the default world also on seed 61002, to show seed-to-seed variation); 1,000 users, medium noise
  default  the frozen v1 generator
  W1       stress spending: under pressure (band worse or cushion < 1), users raise non-essential spending by
           10-25% for 3 months with probability = their impulsivity, instead of cutting it with probability =
           their discipline
  W2       persistent income shocks: job-loss spells 2-3 months (30%), 4-8 (50%), 9-12 (20%); back at work on
           15% lower pay; a slow gig month makes the next one slow with probability 0.5
  W3       correlated expenses: a shock in either of the last 2 months triples event chances; people with
           above-median income volatility have 1.5x the event chances
  scored   the frozen app model (forecast_v1, never retrained; calibrated probability), a frozen B0 (base
           rates per band and cushion bucket from the master O2 rows) and cushion months (ranking only)
  measures label rate and its shortfall share; PR-AUC, ROC-AUC, Brier, mean predicted - observed, calibration
           slope; model - frozen B0 PR-AUC with a 95% user-bootstrap interval
  reading rule: "holds" if the model - B0 interval lies above 0; "degrades" if ROC-AUC is more than 0.03 below the
           default world's (same seed; ROC-AUC, because PR-AUC moves with the label rate, which these worlds
           change), or mean predicted - observed is beyond +-0.02, or the slope is outside 0.8-1.2; "breaks" if
           the model - B0 interval lies below 0. (Rule set after the development run showed the PR-AUC flaw and
           before any full run.)
Synthetic-to-synthetic transfer: this is a stress test, never real-world validation.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score

from engine.forecast import FEATURES, _load
from generator.run import FROZEN_SPEC, generate, sha256
from ml.baselines import cushion_bucket
from ml.features import build_features
from ml.secondary import boot_weights, calibration_slope, ci

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
GEN = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
RESULTS = ROOT / CFG["results_dir"]
WORLD_SEEDS = (61001, 61002)                    # claims_register.md seed block 61001-61049
DEV_SEED, DEV_USERS = 999, 300
B_DEV = 100
WORLDS = {
    "default": {},
    "W1 stress spending": {"alternative": {"stress_spending": True}},
    "W2 persistent income shocks": {"alternative": {"scar": 0.15, "slow_persist": 0.5},
                                    "spell_months": [[0.30, 2, 3], [0.50, 4, 8], [0.20, 9, 12]]},
    "W3 correlated expenses": {"alternative": {"cluster": 3.0, "volatile_events": 1.5}},
}
PATTERNS = {
    "P1": ("Essentials' share of spending falls as income rises", "DOSM HES 2024 Table 3.15 (Engel's law; D-28)"),
    "P2": ("The cushion at month 12 rises with income", "Findex 2025, resilience by income group (verify)"),
    "P3": ("Running short at least once falls with income", "Lusardi, Schneider & Tufano (2011)"),
    "P4": ("Running short rises with income volatility", "Farrell & Greig (2016), JPMorgan Chase Institute (US)"),
    "P5": ("BNPL users run short more often than non-users", "BNM Financial Stability Review on BNPL (low confidence; verify)"),
}


def world_config(name: str, n_users: int | None = None) -> dict:
    cfg = copy.deepcopy(GEN)
    spec = WORLDS[name]
    if "alternative" in spec:
        cfg["alternative"] = dict(spec["alternative"])
    if "spell_months" in spec:
        cfg["income"]["job_loss"]["spell_months"] = spec["spell_months"]
    if n_users:
        cfg["n_users"] = n_users
    return cfg


# ---------------------------------------------------------------- part A
def per_user(t: dict) -> pd.DataFrame:
    m = t["monthly"].sort_values(["user_id", "month"])
    g = m.groupby("user_id")
    df = pd.DataFrame({"income": g.net_income.mean(), "ess_share": g.spend_essential.sum() / g.spend_total.sum(),
                       "cushion12": g.cushion_months.last(), "any_short": g.shortfall.max().astype(float),
                       "inc_cv": g.net_income.std(ddof=1) / g.net_income.mean().replace(0, np.nan)})
    u = t["users"].set_index("user_id")
    df["bnpl_user"] = u.bnpl_user.astype(bool)
    df["inc_q"] = pd.qcut(df.income.rank(method="first"), 5, labels=False) + 1
    df["vol_t"] = pd.qcut(df.inc_cv.fillna(0).rank(method="first"), 3, labels=False) + 1
    return df.reset_index()


def pattern_stats(df: pd.DataFrame) -> dict:
    """The expected-direction difference for each pattern (positive = as published)."""
    q = df.groupby("inc_q")
    v = df.groupby("vol_t")
    b = df.groupby("bnpl_user").any_short.mean()
    return {"P1": q.ess_share.mean()[1] - q.ess_share.mean()[5],
            "P2": q.cushion12.mean()[5] - q.cushion12.mean()[1],
            "P3": q.any_short.mean()[1] - q.any_short.mean()[5],
            "P4": v.any_short.mean()[3] - v.any_short.mean()[1],
            "P5": b.get(True, np.nan) - b.get(False, np.nan)}


def patterns(t: dict, B: int) -> dict:
    df = per_user(t)
    point = pattern_stats(df)
    rng = np.random.default_rng(SEED)
    boots = {k: [] for k in point}
    for _ in range(B):
        s = df.iloc[rng.integers(0, len(df), len(df))]
        s = s.assign(inc_q=pd.qcut(s.income.rank(method="first"), 5, labels=False) + 1,
                     vol_t=pd.qcut(s.inc_cv.fillna(0).rank(method="first"), 3, labels=False) + 1)
        for k, val in pattern_stats(s).items():
            boots[k].append(val)
    out = {}
    for k in point:
        lo, hi = ci(np.array(boots[k]))
        out[k] = {"claim": PATTERNS[k][0], "source": PATTERNS[k][1], "difference": float(point[k]), "ci": [lo, hi],
                  "reading": "reproduced" if lo > 0 else "opposite" if hi < 0 else "unclear"}
    groups = {"by_income_quintile": df.groupby("inc_q")[["income", "ess_share", "cushion12", "any_short"]].mean().reset_index().to_dict("records"),
              "by_volatility_tercile": df.groupby("vol_t")[["inc_cv", "any_short"]].mean().reset_index().to_dict("records"),
              "by_bnpl": df.groupby("bnpl_user")[["any_short", "cushion12"]].mean().reset_index().to_dict("records")}
    return {"patterns": out, "groups": groups}


# ---------------------------------------------------------------- part B
def frozen_b0(t_master: dict) -> dict:
    X = build_features(t_master["monthly"], t_master["users"], t_master["flags"], t_master["labels"])
    key = X.band_t + "|" + pd.Series(cushion_bucket(X.cushion_t), index=X.index).astype(str)
    return {"rates": X.y.astype(float).groupby(key).mean().to_dict(), "prior": float(X.y.astype(float).mean())}


def score_world(t: dict, b0: dict, B: int, seed: int) -> dict:
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"]).reset_index(drop=True)
    art = _load()
    M = X[list(FEATURES)].to_numpy(dtype=float)
    p = art["calibrator"].predict(art["model"].predict_proba(M)[:, 1])
    key = X.band_t + "|" + pd.Series(cushion_bucket(X.cushion_t)).astype(str)
    s_b0 = key.map(b0["rates"]).fillna(b0["prior"]).to_numpy()
    s_cush = -X.cushion_t.to_numpy()
    y = X.y.astype(int).to_numpy()
    shortfall_share = float(X.shortfall_t1_t3[y == 1].mean()) if y.sum() else float("nan")
    res = {"rows": len(X), "users": int(X.user_id.nunique()), "label_rate": float(y.mean()), "shortfall_share_of_positives": shortfall_share,
           "model": {"pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p)),
                     "brier": float(np.mean((p - y) ** 2)), "citl": float(p.mean() - y.mean()), "slope": calibration_slope(p, y)},
           "b0_pr_auc": float(average_precision_score(y, s_b0)), "cushion_pr_auc": float(average_precision_score(y, s_cush))}
    d, pr = [], []
    for w in boot_weights(X.user_id.to_numpy(), B, seed):
        keep = w > 0
        a = average_precision_score(y[keep], p[keep], sample_weight=w[keep])
        pr.append(a)
        d.append(a - average_precision_score(y[keep], s_b0[keep], sample_weight=w[keep]))
    res["model"]["pr_auc_ci"] = ci(np.array(pr))
    res["model_minus_b0"] = [res["model"]["pr_auc"] - res["b0_pr_auc"], *ci(np.array(d))]
    return res


def reading(world: dict, default: dict) -> str:
    lo, hi = world["model_minus_b0"][1:]
    if hi < 0:
        return "breaks"
    worse = (world["model"]["roc_auc"] < default["model"]["roc_auc"] - 0.03 or abs(world["model"]["citl"]) > 0.02
             or not 0.8 <= world["model"]["slope"] <= 1.2)
    return ("holds, but degrades" if worse else "holds") if lo > 0 else ("unclear, degrades" if worse else "unclear")


def worlds(dev: bool, b0: dict, B: int) -> dict:
    out = {}
    seeds = (DEV_SEED,) if dev else WORLD_SEEDS
    for name in WORLDS:
        for seed in (seeds if name == "default" else seeds[:1]):
            t = generate(world_config(name, DEV_USERS if dev else None), "medium", seed, with_transactions=False)
            out[f"{name} (seed {seed})"] = score_world(t, b0, B, seed)
    first = seeds[0]
    base = out[f"default (seed {first})"]
    for k, v in out.items():
        v["reading"] = "reference" if k.startswith("default") else reading(v, base)
    return out


# ---------------------------------------------------------------- run and report
def run(dev: bool = False) -> dict:
    folder = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["spec_sha256"] != sha256(FROZEN_SPEC):
        raise SystemExit("Integrity check failed: the master data was not generated from the frozen spec")
    t_master = {k: pd.read_parquet(folder / f"{k}.parquet") for k in ("users", "monthly", "flags", "labels")}
    B = B_DEV if dev else CFG["bootstrap_resamples"]
    if dev:
        t_pat = generate({**copy.deepcopy(GEN), "n_users": DEV_USERS}, "medium", DEV_SEED, with_transactions=False)
    else:
        t_pat = t_master
    res = {"dev": dev, "patterns": patterns(t_pat, B), "worlds": worlds(dev, frozen_b0(t_master), B)}
    (RESULTS / ("dev" if dev else "") / "structural.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


def write(res: dict) -> str:
    pa, wd = res["patterns"], res["worlds"]
    L = ["# Structural robustness: real patterns and alternative worlds (D-139)", ""]
    if res["dev"]:
        L += ["**DEVELOPMENT RUN (small worlds, seed 999): for debugging only, never reported.**", ""]
    L += ["**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/structural.py` docstring). "
          "Nothing was tuned; the generator's default output is unchanged. Synthetic-to-synthetic: a stress test, not "
          "real-world validation.", "",
          "## Part A: does the synthetic world reproduce published relationships it wasn't tuned to?", "",
          "| ID | Published direction | Source | Difference in that direction (95% CI) | Reading |", "|---|---|---|---|---|"]
    for k, r in pa["patterns"].items():
        L.append(f"| {k} | {r['claim']} | {r['source']} | {r['difference']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] | {r['reading']} |")
    L += ["", "By income quintile (1 = lowest): mean monthly net income, essentials' share, cushion at month 12, share running short:", "",
          "| Quintile | Income (RM) | Essentials' share | Cushion (months) | Ran short |", "|---|---|---|---|---|"]
    for r in pa["groups"]["by_income_quintile"]:
        L.append(f"| {int(r['inc_q'])} | {r['income']:,.0f} | {r['ess_share']:.1%} | {r['cushion12']:.2f} | {r['any_short']:.1%} |")
    L += ["", "By income volatility (tercile of the observed CV): " + "; ".join(
        f"{int(r['vol_t'])}: CV {r['inc_cv']:.2f}, ran short {r['any_short']:.1%}" for r in pa["groups"]["by_volatility_tercile"])
          + ". BNPL: " + "; ".join(f"{'users' if r['bnpl_user'] else 'non-users'} ran short {r['any_short']:.1%}"
                                    for r in pa["groups"]["by_bnpl"]) + ".", "",
          "## Part B: the frozen app model in alternative worlds", "",
          "| World | Label rate (shortfall share) | Model PR-AUC (95% CI) | ROC-AUC | Mean pred. − observed | Slope | Frozen B0 | Cushion months | Model − B0 (95% CI) | Reading |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k, w in wd.items():
        m, d = w["model"], w["model_minus_b0"]
        L.append(f"| {k} | {w['label_rate']:.1%} ({w['shortfall_share_of_positives']:.0%}) | {m['pr_auc']:.3f} [{m['pr_auc_ci'][0]:.3f}, "
                 f"{m['pr_auc_ci'][1]:.3f}] | {m['roc_auc']:.3f} | {m['citl']:+.3f} | {m['slope']:.2f} | {w['b0_pr_auc']:.3f} | "
                 f"{w['cushion_pr_auc']:.3f} | {d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}] | {w['reading']} |")
    text = "\n".join(L) + "\n"
    (RESULTS / ("dev" if res["dev"] else "") / "STRUCTURAL.md").write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", action="store_true", help="debug on small worlds (never reported)")
    res = run(dev=ap.parse_args(argv).dev)
    print(write(res))
    return res


if __name__ == "__main__":
    main()
