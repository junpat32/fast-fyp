"""Expected months to recover: the Markov chain's second role (WP-14b, D-143).

    .venv\\Scripts\\python -m sim.markov_recovery --dev   # debugging (seed 999, 400 users), never reported
    .venv\\Scripts\\python -m sim.markov_recovery         # the one run on the master data

PLAN (committed before the run on the master data; D-132 integrity rules). Exploratory (D-132 N6).

Question  From each band x cushion state, how many months does O2's Markov chain (B2) say recovery
          takes, and do held-out users recover as fast as it says?
Chain     ml.baselines.B2Markov through sim.markov (K1): 9 states, Laplace alpha 1, insufficient-income
          months skipped.
Targets   "Recovered": Green band with at least 1 month of cushion (the reverse of B2's deterioration
          targets, a worse band or under 1 month). "Out of Red": any band but Red.
Data      The master medium-noise data (seed 20261009, 1,000 users x 12 months), checked against the
          frozen spec's SHA-256 and read only.
Part A    Descriptive. The chain fitted on all users. For each start state outside a target: mean months
          (fundamental matrix), median months and P(reached within 3, 6 and 12 months); and how many
          user-months the data has in each state.
Part B    Held-out check of K2. 5-fold GroupKFold by user (rule 2); the chain is fitted on the training
          users only. For every held-out month t in a state outside the target (not an insufficient-
          income month) with t + k <= 12: observed = the target is reached in some month t+1..t+k;
          predicted = the training chain's P(within k); k = 3 and 6. Per start state with at least 30
          held-out start months: mean predicted vs observed share, with a 95% interval for the observed
          share from a user bootstrap (1,000 resamples, seed 20261009). Verdict per state and k:
          "consistent" if the interval contains the mean predicted; otherwise "too fast" (predicted
          above observed) or "too slow". Overall "consistent" only if every eligible state and k is.
Expectation (stated now): a first-order chain forgets how long someone has been in trouble, so it
          may predict recovery too fast from the worst states.
Use       The report gives the months as model-based figures for the synthetic population. Whether the
          app shows them is Patrick's decision; proposed: not shown, because a synthetic population's
          recovery time would read as a fact about real people (rule 12, CR-17).
Not covered  Real people; anything beyond 12 months is the chain's extrapolation; insufficient-income
          months count as not recovered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import GroupKFold

from generator.run import FROZEN_SPEC, generate, sha256
from ml.baselines import state_of
from sim import markov

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
RESULTS = ROOT / "sim" / "results"
KS = (3, 6)
FOLDS, MIN_STARTS, BOOT = 5, 30, 1000
NO_BAND = "INSUFFICIENT_INCOME"


def wide(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (monthly.pivot(index="user_id", columns="month", values="band"),
            monthly.pivot(index="user_id", columns="month", values="cushion_months"))


def states(band_wide: pd.DataFrame, cushion_wide: pd.DataFrame) -> np.ndarray:
    """users x months state matrix; -1 for an insufficient-income month."""
    b, c = band_wide.to_numpy(), cushion_wide.to_numpy(dtype=float)
    out = np.full(b.shape, -1)
    ok = b != NO_BAND
    out[ok] = state_of(b[ok], c[ok])
    return out


def observed(s: np.ndarray, users, target, k: int) -> pd.DataFrame:
    """One row per start month: user, start state, and whether the target was reached within k months."""
    rows, target = [], set(target)
    months = s.shape[1]
    for i, u in enumerate(users):
        for t in range(months - k):                      # t + k <= 12 (0-based: t + k <= months - 1)
            if s[i, t] < 0 or s[i, t] in target:
                continue
            rows.append((u, int(s[i, t]), any(x in target for x in s[i, t + 1:t + k + 1])))
    return pd.DataFrame(rows, columns=["user_id", "state", "reached"])


def part_a(band_w: pd.DataFrame, cush_w: pd.DataFrame) -> dict:
    P = markov.transition_matrix(band_w, cush_w, band_w.index)
    s = states(band_w, cush_w)
    counts = {markov.name(x): int((s == x).sum()) for x in range(markov.N_STATES)}
    return {"user_months": counts, "insufficient_income_months": int((s < 0).sum()),
            "targets": {t: {markov.name(x): v for x, v in markov.recovery(P, members, ks=(3, 6, 12)).items()
                            if x not in members}
                        for t, members in markov.TARGETS.items()}}


def part_b(band_w: pd.DataFrame, cush_w: pd.DataFrame, boot: int = BOOT) -> dict:
    users = band_w.index.to_numpy()
    s = states(band_w, cush_w)
    frames = []
    for train, test in GroupKFold(n_splits=FOLDS).split(users, groups=users):
        P = markov.transition_matrix(band_w, cush_w, users[train])   # training users only (rule 2)
        for t, members in markov.TARGETS.items():
            rec = markov.recovery(P, members, ks=KS)
            for k in KS:
                o = observed(s[test], users[test], members, k)
                o["predicted"] = [rec[x][f"within_{k}"] for x in o.state]
                o["target"], o["k"] = t, k
                frames.append(o)
    df = pd.concat(frames, ignore_index=True)
    rng = np.random.default_rng(SEED)
    pick = rng.integers(0, len(users), size=(boot, len(users)))
    out = {}
    for (t, k, x), g in df.groupby(["target", "k", "state"]):
        per_user = g.groupby("user_id").reached.agg(["sum", "count"]).reindex(users, fill_value=0)
        hits, n = per_user["sum"].to_numpy(dtype=float), per_user["count"].to_numpy(dtype=float)
        shares = hits[pick].sum(axis=1) / np.maximum(n[pick].sum(axis=1), 1)
        lo, hi = np.percentile(shares, [2.5, 97.5])
        pred, obs = float(g.predicted.mean()), float(g.reached.mean())
        eligible = len(g) >= MIN_STARTS
        verdict = ("too few" if not eligible else "consistent" if lo <= pred <= hi
                   else "too fast" if pred > hi else "too slow")
        out.setdefault(t, {}).setdefault(f"k{k}", {})[markov.name(int(x))] = {
            "starts": len(g), "users": int(g.user_id.nunique()), "predicted": round(pred, 4),
            "observed": round(obs, 4), "observed_ci": [round(float(lo), 4), round(float(hi), 4)],
            "verdict": verdict}
    eligible = [c["verdict"] for t in out.values() for kk in t.values() for c in kk.values()
                if c["verdict"] != "too few"]
    return {"cells": out, "overall": "consistent" if all(v == "consistent" for v in eligible) else "not consistent",
            "eligible_cells": len(eligible)}


def load(dev: bool) -> pd.DataFrame:
    if dev:
        gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
        gcfg["n_users"] = CFG["dev"]["n_users"]
        return generate(gcfg, "medium", CFG["dev"]["seed"], with_transactions=False)["monthly"]
    folder = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["spec_sha256"] != sha256(FROZEN_SPEC):
        raise SystemExit("Integrity check failed: the master data was not generated from the frozen spec")
    return pd.read_parquet(folder / "monthly.parquet", columns=["user_id", "month", "band", "cushion_months"])


def fmt_months(v) -> str:
    return "over 120" if v is None else str(v)


def write(res: dict) -> str:
    a, b = res["part_a"], res["part_b"]
    lines = ["# Expected months to recover (Markov chain, D-143)", "",
             "Plan: the docstring of `sim/markov_recovery.py`, committed before this run. Exploratory; synthetic data "
             "only. Raw numbers: `markov_recovery.json`.", "",
             f"## Part A: what the chain says (fitted on all {res['users']:,} users)", ""]
    for t, title in (("recovered", "Months to recover (Green with at least 1 month of cushion)"),
                     ("out_of_red", "Months to leave Red")):
        lines += [f"### {title}", "", "| Start state | User-months in data | Mean months | Median months | "
                  "Within 3 | Within 6 | Within 12 |", "|---|---:|---:|---:|---:|---:|---:|"]
        for st, v in a["targets"][t].items():
            lines.append(f"| {st} | {a['user_months'][st]:,} | {v['mean']:.1f} | {fmt_months(v['median'])} | "
                         f"{v['within_3']:.0%} | {v['within_6']:.0%} | {v['within_12']:.0%} |")
        lines.append("")
    lines += ["## Part B: do held-out users recover as fast as the chain says?", "",
              f"Overall: **{b['overall']}** ({b['eligible_cells']} cells with at least {MIN_STARTS} start months).", ""]
    for t, title in (("recovered", "Recovered"), ("out_of_red", "Out of Red")):
        lines += [f"### {title}", "", "| Start state | Within | Start months (users) | Chain says | Observed (95% CI) "
                  "| Verdict |", "|---|---:|---:|---:|---:|---|"]
        for kk, cells in b["cells"].get(t, {}).items():
            for st, c in cells.items():
                lines.append(f"| {st} | {kk[1:]} months | {c['starts']:,} ({c['users']}) | {c['predicted']:.0%} | "
                             f"{c['observed']:.0%} ({c['observed_ci'][0]:.0%}–{c['observed_ci'][1]:.0%}) | {c['verdict']} |")
        lines.append("")
    return "\n".join(lines)


def run(dev: bool = False) -> dict:
    band_w, cush_w = wide(load(dev))
    return {"dev": dev, "users": int(len(band_w)), "part_a": part_a(band_w, cush_w),
            "part_b": part_b(band_w, cush_w, boot=100 if dev else BOOT)}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", action="store_true")
    args = ap.parse_args(argv)
    res = run(dev=args.dev)
    if not args.dev:
        (RESULTS / "markov_recovery.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        (RESULTS / "MARKOV_RECOVERY.md").write_text(write(res) + "\n", encoding="utf-8")
    print(write(res))
    return res


if __name__ == "__main__":
    main()
