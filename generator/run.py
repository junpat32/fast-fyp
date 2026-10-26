"""Generate one synthetic dataset.

    python -m generator.run --config generator/config.yaml --noise medium --seed 20261009

Outputs (spec §10) go to data/synthetic/<noise>_seed<seed>/ unless --out is given.
Invariants: G1 same config + seed -> byte-identical files (no timestamps anywhere);
G2 hidden traits only in latent*.parquet; G3 money at 2 dp, no NaN/inf in money columns;
G4 every parameter comes from config.yaml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .bands import NAMES
from .flags import compute_flags
from .labels import build_labels
from .population import TYPE_NAMES, build_population
from .simulate import simulate
from .transactions import build_transactions, category_amounts

ROOT = Path(__file__).resolve().parents[1]
FROZEN_SPEC = ROOT / "docs" / "frozen" / "generator_spec_v1.0.md"
SPEC_VERSION = "1.0"
STREAMS = ["population", "income", "spending", "bnpl", "shocks", "hidden", "behaviour", "transactions"]
AGE_BANDS = [(19, "18-19"), (24, "20-24"), (29, "25-29"), (35, "30-35")]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_rngs(seed: int) -> dict:
    """One independent stream per component, so extra draws in one part never shift another."""
    return {k: np.random.default_rng(s) for k, s in zip(STREAMS, np.random.SeedSequence(seed).spawn(len(STREAMS)))}


def generate(cfg: dict, noise: str, seed: int, with_transactions: bool = True) -> dict[str, pd.DataFrame]:
    rngs = make_rngs(seed)
    p = build_population(cfg, rngs["population"])
    r = simulate(p, cfg, noise, rngs)
    n, M = r["income"].shape
    uid = p["user_id"]
    users_long, months_long = np.repeat(uid, M), np.tile(np.arange(1, M + 1), n)

    def age_band(a):
        return next(lbl for lim, lbl in AGE_BANDS if a <= lim)

    users = pd.DataFrame({
        "user_id": uid, "age": p["age"], "age_band": [age_band(a) for a in p["age"]],
        "employment_type": [TYPE_NAMES[e] for e in p["etype"]], "festive_month": p["festive_month"],
        "has_car": p["has_car"], "has_motorbike": p["has_motorbike"],
        "lives_with_parents": p["lives_with_parents"], "family_support": p["family_amount"] > 0,
        "has_ptptn": p["ptptn_pay"] > 0, "has_car_loan": p["car_loan_pay"] > 0,
        "has_motorbike_loan": p["motorbike_loan_pay"] > 0, "has_personal_loan": p["pl_pay"] > 0,
        "has_credit_card": p["card"], "credit_limit": p["card_limit"].round(2),
        "bnpl_user": p["bnpl_user"], "starting_cash": p["cash0"].round(2),
    })

    cats = category_amounts(p, r, cfg)
    money = {"net_income": r["income"], **{f"spend_{c}": v for c, v in cats.items()},
             "spend_essential": r["ess"], "spend_discretionary": r["disc"], "spend_total": r["spend_total"],
             "bnpl_purchases": r["bnpl_buy"], "cash_spending": r["cash_spend"],
             "pay_ptptn": r["ptptn_paid"], "pay_car_loan": r["car_paid"], "pay_motorbike_loan": r["motorbike_paid"],
             "pay_personal_loan": r["pl_paid"], "pay_card_min": r["card_min"], "pay_bnpl": r["bnpl_due"],
             "commitments_total": r["commitments"], "family_support": r["family"],
             "event_shock_cost": r["shock_cost"], "event_minor_cost": r["minor_cost"],
             "late_fees": r["late_fee_paid"], "cash": r["cash"],
             "bal_ptptn": r["bal_ptptn"], "bal_car_loan": r["bal_car"], "bal_motorbike_loan": r["bal_motorbike"],
             "bal_personal_loan": r["bal_pl"], "bal_card": r["card_bal"], "bal_bnpl": r["bnpl_outstanding"],
             "arrears": r["arrears"], "outstanding_debt": r["outstanding"], "card_draw": r["card_draw"],
             "budget": r["budget"], "savings_target": r["target"], "saved": r["saved"]}
    monthly = pd.DataFrame({"user_id": users_long, "month": months_long})
    for k, v in money.items():
        monthly[k] = np.round(v.reshape(-1), 2)
    monthly["budget"] = monthly["budget"].astype("Float64").where(~np.isnan(r["budget"].reshape(-1)), pd.NA)
    for k, v in (("dsr", r["dsr"]), ("dti", r["dti"]), ("cushion_months", r["cushion"])):
        monthly[k] = np.round(v.reshape(-1), 4)
    monthly["goal_achievement"] = pd.array(np.round(r["achieved"].reshape(-1), 4), dtype="Float64")
    sr = r["savings_rate"].reshape(-1)
    monthly["savings_rate"] = pd.array(np.where(np.isnan(sr), np.nan, np.round(sr, 4)), dtype="Float64")
    monthly["band"] = [NAMES[b] for b in r["band"].reshape(-1)]
    monthly["overrun"] = pd.array(np.where(np.isnan(r["overrun"].reshape(-1)), pd.NA,
                                           r["overrun"].reshape(-1) == 1), dtype="boolean")
    monthly["shortfall"] = r["shortfall"].reshape(-1).astype(bool)
    monthly["bnpl_overdue"] = r["bnpl_overdue"].reshape(-1).astype(bool)
    monthly["bnpl_new_purchases"] = r["bnpl_count"].reshape(-1).astype(int)
    monthly["shock_count"] = r["shock_count"].reshape(-1).astype(int)

    fl = compute_flags(r, p["festive_month"], cfg["flags"])
    flags = pd.DataFrame({"user_id": users_long, "month": months_long})
    for k, v in fl.items():
        x = v.reshape(-1)
        flags[k] = pd.array(np.where(np.isnan(x), pd.NA, x == 1), dtype="boolean")

    labels = build_labels(uid, r["band"], r["shortfall"].astype(bool))
    labels["band_t"] = [NAMES[b] for b in labels["band_t"]]
    labels["band_t3"] = [NAMES[b] for b in labels["band_t3"]]

    latent = pd.DataFrame({"user_id": uid, "imp": p["imp"], "dis": p["dis"], "ovc": p["ovc"],
                           "sigma_inc": p["sigma_inc"], "consumption_ratio": p["consumption_ratio"],
                           "gross_base": p["gross"].round(2), "net_base": p["net_base"].round(2),
                           "start_cushion_months": p["start_cushion_months"]})
    latent_monthly = pd.DataFrame({"user_id": users_long, "month": months_long,
                                   "hidden_cost": np.round(r["hidden"].reshape(-1), 2),
                                   "jobless": r["jobless"].reshape(-1).astype(bool),
                                   "slow_month": r["slow_month"].reshape(-1).astype(bool),
                                   "pay_rise": r["pay_rise"].reshape(-1).astype(bool),
                                   "correction_active": r["correction_active"].reshape(-1).astype(bool)})
    out = {"users": users, "monthly": monthly, "flags": flags, "labels": labels,
           "latent": latent, "latent_monthly": latent_monthly}
    if with_transactions:   # the transaction stream is drawn last, so skipping it changes nothing else
        out["transactions"] = build_transactions(p, r, cfg, rngs["transactions"])
    return out


def write(tables: dict, out: Path, cfg_path: Path, noise: str, seed: int, n_users: int) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
    meta = {"spec_version": SPEC_VERSION,
            "spec_sha256": sha256(FROZEN_SPEC) if FROZEN_SPEC.exists() else None,
            "config_sha256": sha256(cfg_path), "seed": seed, "noise": noise, "n_users": n_users,
            "rows": {k: int(len(v)) for k, v in tables.items()},
            "observable_files": ["users", "monthly", "transactions", "flags", "labels"],
            "hidden_files": ["latent", "latent_monthly"]}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description="FAST synthetic data generator (spec v1.0)")
    ap.add_argument("--config", default=str(ROOT / "generator" / "config.yaml"))
    ap.add_argument("--noise", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--n-users", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    cfg_path = Path(a.config)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    seed = a.seed if a.seed is not None else cfg["seed"]
    if a.n_users:
        cfg["n_users"] = a.n_users
    out = Path(a.out) if a.out else ROOT / "data" / "synthetic" / f"{a.noise}_seed{seed}"
    meta = write(generate(cfg, a.noise, seed), out, cfg_path, a.noise, seed, cfg["n_users"])
    print(f"wrote {out}  rows: {meta['rows']}")


if __name__ == "__main__":
    main()
