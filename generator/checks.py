"""Sanity checks S1-S14 (spec §14, frozen). Judged on the medium-noise, master-seed dataset (D-43).

    python -m generator.checks [--data data/synthetic/medium_seed20261009]

S1-S13 must pass before any modelling; a failure means fixing the generator within the
§16 tested ranges and logging it in generator/TUNING_LOG.md (D-45). S14 is a decision rule:
a failing flag stays an ML feature but is not shown to users; it never triggers generator changes.
Hidden traits (latent.parquet) are read here for auditing only (CLAUDE.md rule 3).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "synthetic" / "medium_seed20261009"
MONEY_EXEMPT = {"user_id", "month"}


def run_checks(data: Path, cfg: dict) -> list[dict]:
    rd = {k: pd.read_parquet(data / f"{k}.parquet")
          for k in ("users", "monthly", "flags", "labels", "latent", "latent_monthly", "transactions")}
    u, mo, fl, lab, lat, latm = (rd[k] for k in ("users", "monthly", "flags", "labels", "latent", "latent_monthly"))
    res = []

    def add(cid, name, value, ok, target, note=""):
        res.append({"id": cid, "check": name, "value": value, "pass": bool(ok), "target": target, "note": note})

    ic = cfg["income"]
    net_factor = 1 - ic["epf_rate"] - ic["socso_eis_rate"]

    # S1: employee median net income by age band (March, excluding jobless months) vs DOSM x net factor
    m3 = mo[mo.month == 3].merge(u[["user_id", "employment_type", "age"]], on="user_id")
    m3 = m3[(m3.employment_type == "employee") & (m3.net_income > 0)]
    worst, detail = 0.0, []
    lo_age = 18
    for max_age, med in ic["employee_median_gross_by_max_age"]:
        g = m3[(m3.age >= lo_age) & (m3.age <= max_age)].net_income
        dev = g.median() / (med * net_factor) - 1
        worst = max(worst, abs(dev))
        detail.append(f"{lo_age}-{max_age}: {dev:+.1%}")
        lo_age = max_age + 1
    add("S1", "Employee median net income by age band vs DOSM", f"max dev {worst:.1%}", worst <= 0.10,
        "within ±10%", "; ".join(detail))

    # S2: category shares in normal months, independent households, no life events
    sp = cfg["spending"]
    shares = {**sp["essential_shares"], **sp["discretionary_shares"]}
    norm = mo.merge(u[["user_id", "festive_month", "employment_type", "lives_with_parents"]], on="user_id")
    norm = norm[(norm.month != norm.festive_month) & ~norm.lives_with_parents
                & ~((norm.employment_type == "student") & norm.month.isin(sp["semester"]["months"]))]
    tot = sum(norm[f"spend_{c}"].sum() for c in shares)
    devs = {c: norm[f"spend_{c}"].sum() / tot - s for c, s in shares.items()}
    worst_c = max(devs, key=lambda c: abs(devs[c]))
    add("S2", "Category shares vs HES 2024 (normal months)", f"max dev {devs[worst_c]*100:+.2f} pts ({worst_c})",
        all(abs(d) <= 0.03 for d in devs.values()), "each within ±3 pts")

    # S3: borrowers in Red at month 12
    m12 = mo[mo.month == 12]
    borrowers = m12[m12.commitments_total > 0]
    red = (borrowers.band == "RED").mean()
    add("S3", "Borrowers in Red at month 12", f"{red:.1%}", 0.05 <= red <= 0.25, "5-25%")

    # S4: starting cushion buckets
    target = [b[0] for b in cfg["cushion_buckets"]]
    edges = [b[1] for b in cfg["cushion_buckets"]] + [np.inf]
    got = np.histogram(lat.start_cushion_months, bins=edges)[0] / len(lat)
    add("S4", "Starting cushion buckets vs Findex", " / ".join(f"{g:.0%}" for g in got),
        np.all(np.abs(got - np.array(target)) <= 0.05), "each within ±5 pts of 13/29/18/40%")

    # S5: DSR vs DTI not identical
    ok_rows = (mo.dsr < 9.99) & (mo.dti < 9.99)
    rr = np.corrcoef(mo.dsr[ok_rows], mo.dti[ok_rows])[0, 1]
    add("S5", "DSR vs DTI correlation", f"r = {rr:.3f}", rr < 0.99, "r < 0.99")

    # S6: each flag fires in 5-30% of scored person-months
    rates = {k: fl[k].dropna().astype(bool).mean() for k in ("impulsivity", "overconfidence", "delayed_correction")}
    add("S6", "Flag firing rates", " / ".join(f"{k} {v:.1%}" for k, v in rates.items()),
        all(0.05 <= v <= 0.30 for v in rates.values()), "each 5-30%")

    # S7: edge cases
    ins = (mo.band == "INSUFFICIENT_INCOME").mean()
    jl = latm.sort_values(["user_id", "month"])
    starts = (jl.jobless & ~jl.groupby("user_id").jobless.shift(fill_value=False)).sum()
    n_emp = (u.employment_type == "employee").sum()
    per100 = 100 * starts / n_emp
    add("S7", "Edge cases", f"insufficient income {ins:.1%}; job losses {per100:.1f} per 100 employees",
        ins >= 0.01 and per100 >= 1, ">= 1% and >= 1 per 100")

    # S8: data hygiene
    money_cols = [c for c in mo.columns if mo[c].dtype == float and c not in MONEY_EXEMPT]
    finite = all(np.isfinite(mo[c]).all() for c in money_cols)
    two_dp = all(np.allclose(mo[c], mo[c].round(2)) for c in money_cols if c not in ("dsr", "dti", "cushion_months"))
    nonneg = all((mo[c] >= 0).all() for c in ("cash", "arrears", "outstanding_debt") + tuple(
        c for c in mo.columns if c.startswith("bal_")))
    tx_ok = np.isfinite(rd["transactions"].amount).all() and (rd["transactions"].amount > 0).all()
    add("S8", "Data hygiene", f"finite {finite}, 2dp {two_dp}, balances>=0 {nonneg}, tx ok {tx_ok}",
        finite and two_dp and nonneg and tx_ok, "all true")

    # S9: positive rate
    y = lab.y.dropna()
    add("S9", "Label positive rate", f"{y.mean():.1%} (n={len(y)}, excluded {lab.y.isna().sum()})",
        0.10 <= y.mean() <= 0.30, "10-30%")

    # S10: BNPL overdue bracket
    bu = mo.merge(u[["user_id", "bnpl_user"]], on="user_id")
    bu = bu[bu.bnpl_user]
    pit = bu[bu.month.isin([3, 6, 9, 12])].bnpl_overdue.mean()
    ever = bu.groupby("user_id").bnpl_overdue.any().mean()
    add("S10", "BNPL overdue brackets BNM 17%", f"quarter-end {pit:.1%}, ever {ever:.1%}", pit <= 0.17 <= ever,
        "17% inside [quarter-end, ever]")

    # S11: BNPL user share
    s11 = u.bnpl_user.mean()
    add("S11", "BNPL user share", f"{s11:.1%}", abs(s11 - 0.32) <= 0.05, "32% ± 5 pts")

    # S12: workers' spending / gross income
    w = u[u.employment_type != "student"].user_id
    spend = mo[mo.user_id.isin(w)].spend_total.sum()
    gross = 12 * lat[lat.user_id.isin(w)].gross_base.sum()
    add("S12", "Workers' spending / gross income", f"{spend / gross:.1%}", 0.55 <= spend / gross <= 0.68,
        "55-68% (DOSM 60.8%)")

    # S13: share who saved over the year
    s13 = (m12.set_index("user_id").cash > u.set_index("user_id").starting_cash).mean()
    add("S13", "Share with more cash at month 12 than at start", f"{s13:.1%}", 0.50 <= s13 <= 0.75,
        "50-75% (Findex 58.8-72.7%)")

    # S14: flag validity (decision rule, not a tuning target)
    f2 = fl.merge(lat[["user_id", "imp", "ovc", "dis"]], on="user_id")
    lifts, s14_ok = [], {}
    for flag, trait, risky_high in (("impulsivity", "imp", True), ("overconfidence", "ovc", True),
                                    ("delayed_correction", "dis", False)):
        g = f2[f2[flag].notna()]
        q1, q3 = g[trait].quantile([0.25, 0.75])
        hi, lo = g[g[trait] >= q3][flag].astype(bool).mean(), g[g[trait] <= q1][flag].astype(bool).mean()
        risky, safe = (hi, lo) if risky_high else (lo, hi)
        lift = risky / safe if safe > 0 else np.inf
        s14_ok[flag] = lift >= 2
        lifts.append(f"{flag} x{lift:.1f}")
    add("S14", "Flag validity lift (decision rule)", " / ".join(lifts), all(s14_ok.values()), ">= x2 each",
        "Flags below x2: " + (", ".join(k for k, v in s14_ok.items() if not v) or "none")
        + " -> ML feature only, not shown to users")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--config", default=str(ROOT / "generator" / "config.yaml"))
    a = ap.parse_args(argv)
    data = Path(a.data)
    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    res = run_checks(data, cfg)
    for x in res:
        print(f"{x['id']:4s} {'PASS' if x['pass'] else 'FAIL'}  {x['check']}: {x['value']}  [{x['target']}]"
              + (f"  ({x['note']})" if x["note"] else ""))
    (data / "checks_report.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    hard_fail = [x["id"] for x in res if not x["pass"] and x["id"] != "S14"]
    print("\nS1-S13:", "ALL PASS" if not hard_fail else f"FAILED {hard_fail}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
