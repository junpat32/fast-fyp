"""Transaction log (spec §10). Generic merchant labels only (no real brand names).

Per user-month:
  income       employees: salary on day 25; gig: 4 weekly payouts; students: allowance on day 1
  spending     each category's amount split into Poisson(rate) transactions (Dirichlet weights);
               discretionary categories are split into cash-paid and BNPL-paid parts
  debt         PTPTN, hire purchase, personal loan, card minimum, BNPL instalments (day 5)
  transfers    family support (day 26)
  life events  one transaction each, in the event's category
The hidden cost is never written (it is unlogged spending by definition, §12).

Invariant T1: per user-month and category, transaction amounts sum to the monthly
amount (up to rounding), so monthly.parquet and transactions.parquet agree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .population import EMP, GIG, STU

YEAR = 2025


def _split(rng, total: np.ndarray, rate: float, alpha: float):
    """Split each positive total into k ~ max(1, Poisson(rate)) parts. Returns (row index, amount)."""
    pos = np.flatnonzero(total > 0.005)
    if pos.size == 0:
        return np.array([], dtype=int), np.array([])
    k = np.maximum(1, rng.poisson(rate, pos.size))
    idx = np.repeat(pos, k)
    w = rng.gamma(alpha, 1.0, idx.size)                    # Dirichlet via normalised gammas
    sums = np.bincount(np.repeat(np.arange(pos.size), k), w)
    share = w / np.repeat(sums, k)
    return idx, total[idx] * share


def _frame(user, month, day, amount, direction, category, merchant, kind):
    return pd.DataFrame({"user_id": user, "month": month, "day": day, "amount": amount,
                         "direction": direction, "category": category, "merchant": merchant, "kind": kind})


def category_amounts(p: dict, r: dict, cfg: dict) -> dict:
    """Monthly spending per HES category (users × months), consumption basis (incl. BNPL-paid)."""
    sp = cfg["spending"]
    ess, disc = sp["essential_shares"], sp["discretionary_shares"]
    ess_core = r["ess"] - r["edu_extra"]
    ess_total_share = sum(ess.values()) - (ess["housing"] - p["housing_share_eff"])
    out = {}
    for c, s in ess.items():
        share = (p["housing_share_eff"] if c == "housing" else s) / ess_total_share
        out[c] = ess_core * share[:, None] if np.ndim(share) else ess_core * share
    out["education"] = out["education"] + r["edu_extra"]
    for c, s in disc.items():
        out[c] = r["disc"] * (s / sum(disc.values()))
    return out


def build_transactions(p: dict, r: dict, cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    tc = cfg["transactions"]
    n, M = r["income"].shape
    uid = p["user_id"]
    frames = []
    cats = category_amounts(p, r, cfg)
    disc_names = set(cfg["spending"]["discretionary_shares"])
    # cash share of discretionary spending (BNPL-paid part is logged separately)
    with np.errstate(divide="ignore", invalid="ignore"):
        cash_share = np.where(r["disc"] > 0, (r["disc"] - r["bnpl_buy"]) / r["disc"], 1.0)

    for m in range(M):
        month = m + 1
        inc = r["income"][:, m]
        # income
        for etype, day, label in ((EMP, 25, "EMPLOYER"), (STU, 1, "ALLOWANCE")):
            sel = (p["etype"] == etype) & (inc > 0)
            frames.append(_frame(uid[sel], month, day, inc[sel], "in", "income",
                                 [f"{label}_{u % 97:03d}" for u in uid[sel]], "income"))
        sel = np.flatnonzero((p["etype"] == GIG) & (inc > 0))
        if sel.size:
            w = rng.gamma(4.0, 1.0, (sel.size, 4))
            parts = inc[sel, None] * w / w.sum(axis=1, keepdims=True)
            frames.append(_frame(np.repeat(uid[sel], 4), month, np.tile([7, 14, 21, 28], sel.size),
                                 parts.ravel(), "in", "income",
                                 [f"GIGPLATFORM_{u % 7:03d}" for u in np.repeat(uid[sel], 4)], "income"))
        # spending by category
        for c, amt in cats.items():
            total = amt[:, m] * (cash_share[:, m] if c in disc_names else 1.0)
            idx, a = _split(rng, total, tc["rates"][c], tc["dirichlet_alpha"])
            frames.append(_frame(uid[idx], month, rng.integers(1, 29, idx.size), a, "out", c,
                                 [f"{c.upper()}_{x:03d}" for x in rng.integers(1, tc["merchants_per_category"] + 1, idx.size)],
                                 "spending"))
        # BNPL-paid discretionary purchases
        idx, a = _split(rng, r["bnpl_buy"][:, m], 2.7, tc["dirichlet_alpha"])
        frames.append(_frame(uid[idx], month, rng.integers(1, 29, idx.size), a, "out", "bnpl_purchase",
                             [f"BNPL_MERCHANT_{x:03d}" for x in rng.integers(1, 41, idx.size)], "bnpl_purchase"))
        # debt payments and transfers
        for col, label in (("ptptn_paid", "PTPTN"), ("car_paid", "HIREPURCHASE_CAR"),
                           ("motorbike_paid", "HIREPURCHASE_MOTORBIKE"), ("pl_paid", "PERSONAL_LOAN"),
                           ("card_min", "CREDIT_CARD"), ("bnpl_due", "BNPL_PROVIDER"),
                           ("late_fee_paid", "BNPL_LATE_FEE")):
            v = r[col][:, m]
            sel = v > 0.005
            frames.append(_frame(uid[sel], month, 5, v[sel], "out", "debt_payment", label, "debt"))
        v = r["family"][:, m]
        sel = v > 0.005
        frames.append(_frame(uid[sel], month, 26, v[sel], "out", "family_transfer", "FAMILY_TRANSFER", "transfer"))

    # life events
    for m, users, eid, cost, cat in r["events"]:
        frames.append(_frame(uid[users], m + 1, rng.integers(1, 29, users.size), cost, "out", cat,
                             f"EVENT_{eid}", "life_event"))

    tx = pd.concat([f for f in frames if len(f)], ignore_index=True)
    tx["amount"] = tx["amount"].round(2)
    tx = tx[tx["amount"] > 0].copy()
    tx["date"] = pd.to_datetime(dict(year=YEAR, month=tx["month"], day=tx["day"]))
    src = tc["source_mix"]
    tx["source"] = rng.choice(list(src), size=len(tx), p=list(src.values()))
    tx = tx.sort_values(["user_id", "date", "kind", "category", "amount"], kind="mergesort").reset_index(drop=True)
    tx.insert(0, "txn_id", np.arange(1, len(tx) + 1))
    return tx[["txn_id", "user_id", "date", "amount", "direction", "category", "merchant", "source", "kind"]]
