"""Static attributes of each synthetic user (spec §3a, §4, §5, §6, §8).

Everything here is drawn once per user, before month 1. Hidden traits (imp, dis, ovc)
are returned too, but run.py writes them only to latent.parquet (invariant G2).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

EMP, GIG, STU = 0, 1, 2
TYPE_NAMES = {EMP: "employee", GIG: "gig", STU: "student"}

# Implementation choice not fixed by the spec (see generator/README.md):
# spending never falls below this share of net income, even when debts exceed income.
SPENDING_FLOOR_SHARE = 0.30


def _u(rng, lohi, n):
    return rng.uniform(lohi[0], lohi[1], n)


def beta_mean(ab):
    return ab[0] / (ab[0] + ab[1])


def sample_traits(rng, n, tcfg):
    """Gaussian copula: correlated normals -> uniforms -> Beta marginals (§3a)."""
    corr = np.eye(3)
    corr[0, 1] = corr[1, 0] = tcfg["rho_imp_dis"]
    corr[0, 2] = corr[2, 0] = tcfg["rho_imp_ovc"]
    z = rng.standard_normal((n, 3)) @ np.linalg.cholesky(corr).T
    u = stats.norm.cdf(z)
    return (stats.beta.ppf(u[:, 0], *tcfg["imp_beta"]),
            stats.beta.ppf(u[:, 1], *tcfg["dis_beta"]),
            stats.beta.ppf(u[:, 2], *tcfg["ovc_beta"]))


def build_population(cfg: dict, rng: np.random.Generator) -> dict:
    n = cfg["n_users"]
    p = {"user_id": np.arange(1, n + 1)}

    mix = cfg["population"]["employment_mix"]
    p["etype"] = rng.choice([EMP, GIG, STU], size=n, p=[mix["employee"], mix["gig"], mix["student"]])
    worker = p["etype"] != STU
    wa, sa = cfg["population"]["worker_age"], cfg["population"]["student_age"]
    p["age"] = np.where(worker, rng.integers(wa[0], wa[1] + 1, n), rng.integers(sa[0], sa[1] + 1, n))
    p["imp"], p["dis"], p["ovc"] = sample_traits(rng, n, cfg["traits"])

    # ---- income (§4) ----
    ic = cfg["income"]
    median = np.zeros(n)
    for max_age, med in reversed(ic["employee_median_gross_by_max_age"]):
        median = np.where(p["age"] <= max_age, med, median)
    emp_gross = np.maximum(median * np.exp(rng.normal(0, ic["employee_sigma_log"], n)), ic["min_wage"])
    gig_net = ic["gig_median"] * np.exp(rng.normal(0, ic["gig_sigma_log"], n))
    stu_inc = _u(rng, ic["student_range"], n)
    p["gross"] = np.select([p["etype"] == EMP, p["etype"] == GIG], [emp_gross, gig_net], stu_inc)
    net_factor = 1 - ic["epf_rate"] - ic["socso_eis_rate"]
    p["net_base"] = np.where(p["etype"] == EMP, p["gross"] * net_factor, p["gross"])
    s = ic["sigma_inc"]
    p["sigma_inc"] = np.select([p["etype"] == EMP, p["etype"] == GIG],
                               [_u(rng, s["employee"], n), _u(rng, s["gig"], n)], _u(rng, s["student"], n))

    # ---- vehicles (D-35, D-40) ----
    vc = cfg["debt"]["vehicles"]
    r = rng.random(n)
    p["has_car"] = np.select([p["etype"] == EMP, p["etype"] == GIG],
                             [rng.random(n) < vc["employee"]["car"], r >= vc["gig_motorbike_share"]],
                             r < vc["student"]["car"])
    p["has_motorbike"] = np.select(
        [p["etype"] == EMP, p["etype"] == GIG],
        [rng.random(n) < vc["employee"]["motorbike"], r < vc["gig_motorbike_share"]],
        (r >= vc["student"]["car"]) & (r < vc["student"]["car"] + vc["student"]["motorbike"]))

    vl = cfg["debt"]["vehicle_loan"]
    p_loan = np.where(p["etype"] == STU, vl["student"], np.where(p["age"] < 21, vl["p_under_21"], vl["p"]))
    for kind in ("car", "motorbike"):
        has_loan = p[f"has_{kind}"] & (rng.random(n) < p_loan)
        pay = np.where(has_loan, _u(rng, vl[f"{kind}_payment"], n), 0.0)
        tenure = vl[f"{kind}_tenure_months"]
        remaining = rng.integers(12, tenure + 1, n)
        p[f"{kind}_loan_pay"] = pay
        p[f"{kind}_loan_bal"] = pay * remaining

    # ---- PTPTN (C-14, D-38): workers only ----
    pc = cfg["debt"]["ptptn"]
    has_pt = worker & (p["age"] >= pc["min_age"]) & (rng.random(n) < pc["p"])
    loan = _u(rng, pc["loan"], n)
    tenure = np.where(loan > pc["big_loan_threshold"], pc["tenure_months_big"], pc["tenure_months_small"])
    total = loan * (1 + pc["ujrah_rate"] * tenure / 12)
    pay = total / tenure
    paid_months = np.minimum(12 * (p["age"] - pc["min_age"]), tenure - 1)
    p["ptptn_pay"] = np.where(has_pt, pay, 0.0)
    p["ptptn_bal"] = np.where(has_pt, total - pay * paid_months, 0.0)

    # ---- personal loan (C-32) ----
    pl = cfg["debt"]["personal_loan"]
    has_pl = worker & (p["age"] >= pl["min_age"]) & (rng.random(n) < pl["p"])
    pay = np.where(has_pl, _u(rng, pl["payment"], n), 0.0)
    p["pl_pay"] = pay
    p["pl_bal"] = pay * rng.integers(12, pl["tenure_months"] + 1, n)

    # ---- household (C-33, C-34) ----
    fs = cfg["debt"]["family_support"]
    p["family_amount"] = np.where(worker & (rng.random(n) < fs["p"]), _u(rng, fs["amount"], n), 0.0)
    lp = cfg["spending"]["living_with_parents"]
    p["lives_with_parents"] = rng.random(n) < np.where(p["age"] <= 24, lp["p_18_24"], lp["p_25_35"])

    # ---- BNPL users (C-12) ----
    bc = cfg["debt"]["bnpl"]
    imp_mean = beta_mean(cfg["traits"]["imp_beta"])
    p["bnpl_user"] = rng.random(n) < np.clip(bc["user_share"] * p["imp"] / imp_mean, 0, bc["max_p"])

    # ---- credit cards (C-27, C-28, C-30; D-32, D-33, D-38) ----
    cc = cfg["debt"]["credit_card"]
    eligible = worker & (p["age"] >= cc["min_age"]) & (p["gross"] >= cc["min_gross"])
    need = int(round(cc["share_of_workers"] * worker.sum()))
    idx = np.flatnonzero(eligible)
    holders = rng.choice(idx, size=min(need, idx.size), replace=False) if idx.size else idx
    p["card"] = np.zeros(n, dtype=bool)
    p["card"][holders] = True
    # 2 x gross income (BNM's cap up to RM3,000 a month); the §16 sensitivity run tries 3 x above it
    # (`limit_multiple_high` above `high_income_gross`; both absent by default, so nothing changes)
    multiple = np.where(p["gross"] > cc.get("high_income_gross", np.inf),
                        cc.get("limit_multiple_high", cc["limit_multiple"]), cc["limit_multiple"])
    p["card_limit"] = np.where(p["card"], multiple * p["gross"], 0.0)
    full_start = rng.random(n) < p["dis"]
    p["card_bal"] = np.where(p["card"] & ~full_start, _u(rng, cc["start_balance_share"], n) * p["card_limit"], 0.0)
    p["card_missed"] = np.where(p["card"] & ~full_start, 1, 0)   # 0 -> 15% tier, 1-2 -> 17%

    # ---- calendar (C-24, C-35) ----
    fw = cfg["spending"]["festive"]["weights"]
    months, w = zip(*sorted((int(k), v) for k, v in fw.items()))
    p["festive_month"] = rng.choice(months, size=n, p=np.array(w) / sum(w))

    # ---- spending base (§5, D-40) ----
    sp = cfg["spending"]
    shift = sp["trait_shift"]
    c = _u(rng, sp["consumption_ratio"], n) + shift * (p["imp"] - imp_mean) \
        - shift * (p["dis"] - beta_mean(cfg["traits"]["dis_beta"]))
    p["consumption_ratio"] = np.clip(c, *sp["ratio_clip"])
    card_min0 = np.where(p["card_bal"] > 0, np.maximum(cc["min_payment_rate"] * p["card_bal"],
                                                       cc["min_payment_floor"]), 0.0)
    p["fixed_pay"] = p["ptptn_pay"] + p["car_loan_pay"] + p["motorbike_loan_pay"] + p["pl_pay"]
    disposable = p["net_base"] - p["fixed_pay"] - card_min0 - p["family_amount"]
    total = p["consumption_ratio"] * np.maximum(disposable, SPENDING_FLOOR_SHARE * p["net_base"])
    ess, disc = sp["essential_shares"], sp["discretionary_shares"]
    housing_cut = np.where(p["lives_with_parents"], ess["housing"] * (1 - sp["living_with_parents"]["housing_factor"]), 0.0)
    p["ess_base"] = total * (sum(ess.values()) - housing_cut)
    p["disc_base"] = total * sum(disc.values())
    p["edu_base"] = total * ess["education"]
    p["housing_share_eff"] = ess["housing"] - housing_cut   # housing share of total, after living with parents

    # ---- starting cash (C-21, D-31) ----
    buckets = cfg["cushion_buckets"]
    b = rng.choice(len(buckets), size=n, p=[x[0] for x in buckets])
    lo = np.array([x[1] for x in buckets])[b]
    hi = np.array([x[2] for x in buckets])[b]
    p["start_cushion_months"] = rng.uniform(lo, hi)
    p["cash0"] = p["start_cushion_months"] * (p["ess_base"] + p["fixed_pay"] + card_min0)
    return p
