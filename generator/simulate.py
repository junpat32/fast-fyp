"""Monthly engine (spec §3). One month at a time, all users at once (numpy arrays of length n).

Order inside each month (matches the spec §3 loop):
  income (+ regimes) -> spending (+ festive, semester, correction) -> BNPL purchases
  -> debt payments -> life events -> hidden cost -> cash update -> deficit to card / shortfall
  -> card pay-in-full and interest -> DSR, DTI, band -> cushion -> behaviour updates

Invariants
  E1  cash never ends a month below 0 (a deficit goes to the card up to its limit, the rest
      is a shortfall and cash floors at 0)
  E2  balances never go below 0; loan payments are min(instalment, balance)
  E3  anything computed for month m uses only months <= m (behaviour updates act on m+1)
  E4  "saved" is observable: it excludes the hidden cost (§9, D-41)
  E5  cfg["alternative"] switches on a structural-robustness world (D-139); absent or empty, the
      code takes exactly the frozen v1 path and draws exactly the same random numbers (verified
      against the master dataset), so O2's data never changes
Cost: O(months × (users + users × events)); about 1,000 × 12 × 21 cheap operations.
"""
from __future__ import annotations

import numpy as np

from .bands import INSUFFICIENT, band_array
from .population import EMP, GIG, STU

DSR_CAP = 9.99   # stored when trailing income is 0 (the band is INSUFFICIENT anyway)


def _lognoise(rng, sigma, n):
    """Mean-1 multiplicative noise: exp(N(-s^2/2, s^2))."""
    sigma = np.broadcast_to(np.asarray(sigma, dtype=float), (n,))
    return np.exp(rng.normal(-sigma ** 2 / 2, sigma))


def _eligible(who: str, p: dict) -> np.ndarray:
    return {"all": np.ones_like(p["has_car"], dtype=bool),
            "car": p["has_car"], "motorbike": p["has_motorbike"],
            "vehicle": p["has_car"] | p["has_motorbike"],
            "student": p["etype"] == STU, "nonstudent": p["etype"] != STU,
            "gig": p["etype"] == GIG}[who]


def simulate(p: dict, cfg: dict, noise: str, rngs: dict) -> dict:
    n, M = len(p["user_id"]), cfg["months"]
    nl = cfg["noise_levels"][noise]
    scale, hshare = nl["scale"], nl["hidden_cost_share"]
    ic, sp, cc, bc = cfg["income"], cfg["spending"], cfg["debt"]["credit_card"], cfg["debt"]["bnpl"]
    beh, sh = cfg["behaviour"], cfg["shocks"]
    alt = cfg.get("alternative") or {}                     # E5: empty = the frozen v1 world
    ri, rs, rb, rk, rh, rv = (rngs[k] for k in ("income", "spending", "bnpl", "shocks", "hidden", "behaviour"))

    is_emp, is_gig, is_stu = p["etype"] == EMP, p["etype"] == GIG, p["etype"] == STU
    rec = {k: np.zeros((n, M)) for k in (
        "income", "ess", "disc", "edu_extra", "bnpl_buy", "cash_spend", "spend_total",
        "ptptn_paid", "car_paid", "motorbike_paid", "pl_paid", "card_min", "bnpl_due", "commitments",
        "family", "shock_cost", "minor_cost", "shock_count", "hidden", "late_fee_paid", "cash",
        "card_bal", "card_draw", "arrears", "outstanding", "dsr", "dti", "cushion",
        "saved", "savings_rate", "target", "achieved", "budget", "overrun",
        "shortfall", "bnpl_overdue", "jobless", "slow_month", "pay_rise", "correction_active",
        "bnpl_count", "bnpl_outstanding", "bal_ptptn", "bal_car", "bal_motorbike", "bal_pl")}
    rec["band"] = np.zeros((n, M), dtype=np.int8)
    events = []   # (month, user_idx array, event_id, cost array, category) for transactions.py

    base_inc = p["net_base"].copy()
    jobless_left = np.zeros(n, dtype=int)
    cash = p["cash0"].copy()
    card_bal, missed = p["card_bal"].copy(), p["card_missed"].copy()
    bal = {"ptptn": p["ptptn_bal"].copy(), "car": p["car_loan_bal"].copy(),
           "motorbike": p["motorbike_loan_bal"].copy(), "pl": p["pl_bal"].copy()}
    pay = {"ptptn": p["ptptn_pay"], "car": p["car_loan_pay"], "motorbike": p["motorbike_loan_pay"], "pl": p["pl_pay"]}
    arrears = np.zeros(n)
    inst = np.zeros((n, M + bc["instalments"]))
    corr_left, kappa = np.zeros(n, dtype=int), np.zeros(n)
    prev_band, prev_shock = None, np.zeros(n, dtype=bool)
    prev_shock2, prev_slow = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)      # used only by E5 worlds
    late_fee = np.zeros(n)
    ach_prev, target_prev = np.full(n, np.nan), np.full(n, np.nan)
    deck = sh["deck"]
    jl = ic["job_loss"]

    for m in range(M):
        cal = m + 1

        # ---- income and world-only regimes (§4) ----
        inc = base_inc * _lognoise(ri, p["sigma_inc"] * scale, n)
        was = jobless_left > 0
        jobless_left = np.where(was, jobless_left - 1, jobless_left)
        p_loss = np.where(p["age"] <= jl["young_max_age"], jl["p_young"], jl["p_older"])
        new = is_emp & ~was & (ri.random(n) < p_loss)
        spells = jl["spell_months"]
        bucket = ri.choice(len(spells), size=n, p=[s[0] for s in spells])
        lo = np.array([s[1] for s in spells])[bucket]
        hi = np.array([s[2] for s in spells])[bucket]
        duration = ri.integers(lo, hi + 1)
        jobless_left = np.where(new, duration - 1, jobless_left)
        jobless = is_emp & (was | new)
        inc = np.where(jobless, 0.0, inc)
        if alt.get("scar") and m > 0:      # W2: back at work after a spell, on lower pay for the rest of the year
            back = is_emp & ~jobless & (rec["jobless"][:, m - 1] > 0)
            base_inc = np.where(back, base_inc * (1 - alt["scar"]), base_inc)
            inc = np.where(back, inc * (1 - alt["scar"]), inc)
        rise = is_emp & ~jobless & (ri.random(n) < ic["pay_rise"]["p"])
        base_inc = np.where(rise, base_inc * (1 + ri.uniform(*ic["pay_rise"]["pct"], n)), base_inc)
        p_slow = ic["gig_slow"]["p"]
        if alt.get("slow_persist"):        # W2: a slow gig month makes the next one likelier to be slow
            p_slow = np.where(prev_slow, alt["slow_persist"], p_slow)
        slow = is_gig & (ri.random(n) < p_slow)
        prev_slow = slow
        inc = np.where(slow, inc * ri.uniform(*ic["gig_slow"]["factor"], n), inc)

        # ---- spending (§5) ----
        festive = np.where(p["festive_month"] == cal, rs.uniform(*sp["festive"]["multiplier"], n), 1.0)
        sem = is_stu & (cal in sp["semester"]["months"])
        sem_mult = np.where(sem, sp["semester"]["multiplier"], 1.0)
        corr_active = corr_left > 0
        corr_factor = np.where(corr_active, 1 - kappa, 1.0)
        corr_left = np.maximum(corr_left - 1, 0)
        edu_extra = np.where(sem, p["edu_base"] * (sp["semester"]["multiplier"] - 1), 0.0)
        ess = p["ess_base"] * _lognoise(rs, sp["essential_sigma_log"] * scale, n) + edu_extra
        dsig = (sp["discretionary_sigma_log"]["base"] + sp["discretionary_sigma_log"]["per_imp"] * p["imp"]) * scale
        disc = p["disc_base"] * _lognoise(rs, dsig, n) * festive * sem_mult * corr_factor

        # ---- BNPL purchases: a payment method for part of discretionary spending (§6) ----
        counts = np.where(p["bnpl_user"], rb.poisson(bc["purchases_per_month"], n), 0)
        amounts = np.clip(bc["amount_median"] * np.exp(rb.normal(0, bc["amount_sigma_log"], counts.sum())),
                          *bc["amount_clip"])
        buy = np.minimum(np.bincount(np.repeat(np.arange(n), counts), amounts, minlength=n), disc)
        inst[:, m:m + bc["instalments"]] += (buy / bc["instalments"])[:, None]
        bnpl_due = inst[:, m].copy()

        # ---- debt payments (§6) ----
        paid = {}
        for k in bal:
            paid[k] = np.minimum(pay[k], bal[k])
            bal[k] -= paid[k]
        card_min = np.where(card_bal > 0, np.minimum(card_bal, np.maximum(cc["min_payment_rate"] * card_bal,
                                                                          cc["min_payment_floor"])), 0.0)
        card_bal = card_bal - card_min
        commitments = sum(paid.values()) + card_min + bnpl_due

        # ---- life events (§7) ----
        shock_cost, minor_cost = np.zeros(n), np.zeros(n)
        shock_count, any_shock = np.zeros(n), np.zeros(n, dtype=bool)
        cluster = np.where(prev_shock, sh["clustering"], 1.0)
        if alt.get("cluster"):             # W3: stronger, longer clustering; more events for unsteady incomes
            cluster = np.where(prev_shock | prev_shock2, alt["cluster"], 1.0) * np.where(
                p["sigma_inc"] > np.median(p["sigma_inc"]), alt.get("volatile_events", 1.0), 1.0)
        for eid, who, lo, hi, freq, is_shock, cat in deck:
            mult = np.where(is_gig & (eid in sh["gig_events"]), sh["gig_multiplier"], 1.0)
            if eid == "L08":
                mult = mult * np.where(is_stu, sh["student_laptop_multiplier"], 1.0)
            prob = np.minimum(1.0, sh["k"] * freq / 12 * mult * cluster)
            hit = _eligible(who, p) & (rk.random(n) < prob)
            cost = np.where(hit, rk.uniform(lo, hi, n), 0.0)
            if hit.any():
                events.append((m, np.flatnonzero(hit), eid, cost[hit], cat))
            if is_shock:
                shock_cost += cost
                shock_count += hit
                any_shock |= hit
            else:
                minor_cost += cost
        events_cost = shock_cost + minor_cost

        # ---- hidden cost (§12, unobserved) and cash update (§8) ----
        hidden = hshare * np.maximum(inc, 0) * np.exp(rh.normal(0, cfg["hidden_cost_sigma_log"], n))
        family = p["family_amount"]
        cash_spend = ess + disc - buy
        saved = inc - cash_spend - commitments - family - events_cost - late_fee      # E4
        cash = cash + saved - hidden
        late_fee_paid, late_fee = late_fee, np.zeros(n)

        # ---- deficit: card up to its limit, the rest is a shortfall (§8, D-33) ----
        room = np.maximum(p["card_limit"] - card_bal, 0)
        draw = np.where(p["card"] & (cash < 0), np.minimum(-cash, room), 0.0)
        card_bal, cash = card_bal + draw, cash + draw
        short = cash < -0.005
        arrears += np.where(short, np.minimum(-cash, commitments), 0.0)
        cash = np.where(short, 0.0, cash)                                              # E1
        overdue = short & (bnpl_due > 0)
        late_fee = np.where(overdue, rb.uniform(*bc["late_fee"], n), 0.0)
        missed += (short & (card_min > 0)).astype(int)

        # ---- card: pay in full with probability dis, otherwise interest (C-15, C-16) ----
        full = p["card"] & (card_bal > 0) & (rv.random(n) < p["dis"]) & (cash >= card_bal)
        cash = np.where(full, cash - card_bal, cash)
        card_bal = np.where(full, 0.0, card_bal)
        apr = np.where(missed == 0, cc["apr"]["prompt"], np.where(missed <= 2, cc["apr"]["mostly"], cc["apr"]["poor"]))
        card_bal = card_bal * (1 + apr / 12)

        # ---- DSR, DTI, band (§6) ----
        rec["income"][:, m] = inc
        med3 = np.median(rec["income"][:, max(0, m - 2):m + 1], axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            dsr = np.where(med3 > 0, commitments / med3, DSR_CAP)
        outstanding = sum(bal.values()) + card_bal + inst[:, m + 1:].sum(axis=1) + arrears
        with np.errstate(divide="ignore", invalid="ignore"):
            dti = np.where(med3 > 0, outstanding / (12 * med3), DSR_CAP)
        band = band_array(np.minimum(dsr, DSR_CAP), med3, prev_band)

        # ---- cushion (§8) ----
        rec["ess"][:, m], rec["commitments"][:, m] = ess, commitments
        need = (rec["ess"][:, max(0, m - 2):m + 1] + rec["commitments"][:, max(0, m - 2):m + 1]).mean(axis=1)
        cushion = cash / np.maximum(need, 1.0)

        # ---- savings target and achievement (§9, D-41) ----
        if m == 0:
            target = np.full(n, float(beh["target_floor"]))
        else:
            target = np.maximum(beh["target_floor"],
                                (1 + p["ovc"]) * rec["saved"][:, max(0, m - 3):m].mean(axis=1))
            # goal stickiness = ovc (§9); the §16 sensitivity run scales it (0.5, 0 = off; default 1.0)
            keep = (ach_prev < 1) & (rv.random(n) < beh.get("goal_stickiness_scale", 1.0) * p["ovc"]) & (target < target_prev)
            target = np.where(keep, target_prev, target)
        achieved = saved / target
        ach_prev, target_prev = achieved, target

        # ---- budget and overrun (§5, D-41): previous 3 months of total spending ----
        spend_total = ess + disc
        rec["spend_total"][:, m] = spend_total
        budget = (sp["budget_factor"] * np.median(rec["spend_total"][:, max(0, m - 3):m], axis=1)
                  if m > 0 else np.full(n, np.nan))
        overrun = np.where(np.isnan(budget), np.nan, spend_total > budget)

        # ---- behaviour update for the NEXT months (§9; E3) ----
        valid = (band != INSUFFICIENT) if prev_band is None else (band != INSUFFICIENT) & (prev_band != INSUFFICIENT)
        worsened = valid & (band > prev_band) if prev_band is not None else np.zeros(n, dtype=bool)
        if alt.get("stress_spending"):     # W1: under pressure, impulsive users spend MORE instead of cutting back
            trigger = (worsened | (cushion < 1)) & (rv.random(n) < p["imp"])
            kappa = np.where(trigger, -rv.uniform(*beh["correction_kappa"], n), kappa)
        else:
            trigger = (worsened | (cushion < 1)) & (rv.random(n) < p["dis"])
            kappa = np.where(trigger, rv.uniform(*beh["correction_kappa"], n), kappa)
        corr_left = np.where(trigger, beh["correction_months"], corr_left)
        prev_band, prev_shock2, prev_shock = band, prev_shock, any_shock

        # ---- record ----
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = np.where(inc > 0, saved / inc, np.nan)
        for k, v in (("disc", disc), ("edu_extra", edu_extra), ("bnpl_buy", buy), ("cash_spend", cash_spend),
                     ("ptptn_paid", paid["ptptn"]), ("car_paid", paid["car"]),
                     ("motorbike_paid", paid["motorbike"]), ("pl_paid", paid["pl"]), ("card_min", card_min),
                     ("bnpl_due", bnpl_due), ("family", family), ("shock_cost", shock_cost),
                     ("minor_cost", minor_cost), ("shock_count", shock_count), ("hidden", hidden),
                     ("late_fee_paid", late_fee_paid), ("cash", cash), ("card_bal", card_bal),
                     ("card_draw", draw), ("arrears", arrears), ("outstanding", outstanding),
                     ("dsr", dsr), ("dti", dti), ("cushion", cushion), ("saved", saved),
                     ("savings_rate", rate), ("target", target), ("achieved", achieved), ("budget", budget),
                     ("overrun", overrun), ("shortfall", short), ("bnpl_overdue", overdue),
                     ("jobless", jobless), ("slow_month", slow), ("pay_rise", rise),
                     ("correction_active", corr_active), ("bnpl_count", counts),
                     ("bnpl_outstanding", inst[:, m + 1:].sum(axis=1)), ("bal_ptptn", bal["ptptn"]),
                     ("bal_car", bal["car"]), ("bal_motorbike", bal["motorbike"]), ("bal_pl", bal["pl"])):
            rec[k][:, m] = v
        rec["band"][:, m] = band

    rec["events"] = events
    return rec
