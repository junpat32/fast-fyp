"""Throwaway prototype of generator_spec.md v0.4 for a market-realism check.

NOT the generator (T-05). Simplified: no transactions, no copula between traits,
no overconfidence flag. Pure Python (numpy not installed). Usage:
    python proto_sim.py <variant> [n_users] [seed]
variant: current | fixed
"""
import math
import random
import statistics as st
import sys

VARIANT = sys.argv[1] if len(sys.argv) > 1 else "fixed"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 20261009
C_LO = float(sys.argv[4]) if len(sys.argv) > 4 else .70
C_HI = float(sys.argv[5]) if len(sys.argv) > 5 else .95
FIX = VARIANT == "fixed"
R = random.Random(SEED)

AGE_MEDIAN = [(19, 1700), (24, 1900), (29, 2600), (35, 3200)]  # C-01
NET_FACTOR = 1 - 0.11 - 0.007                                     # C-07, C-08
FESTIVE_W = {1: .192, 3: .652, 10: .063, 12: .093} if FIX else {1: .25, 3: .25, 10: .25, 12: .25}
SEMESTER = {3, 8, 11}
# (id, who, lo, hi, freq/yr, shock?)
DECK = [("L01", "moto", 80, 300, 1.0, 0), ("L02", "moto", 400, 1200, .2, 1),
        ("L03", "car", 250, 700, .5, 1), ("L04", "car", 800, 2500, .2, 1),
        ("L05", "veh", 150, 300, .3, 0), ("L06", "all", 150, 800, .15, 1),
        ("L07", "all", 600, 2000, .05, 1), ("L08", "all", 1500, 3000, .05, 1),
        ("L09", "all", 40, 150, 1.0, 0), ("L10", "all", 100, 600, .2, 1),
        ("L11", "all", 300, 2000, .05, 1), ("L12", "all", 300, 1500, .15, 1),
        ("L13", "all", 200, 800, .1, 1), ("L14", "all", 100, 500, .5, 0),
        ("L15", "nonstu", 800, 2500, .05, 1), ("L16", "nonstu", 300, 1500, .1, 1),
        ("L17", "nonstu", 100, 300, .2, 0), ("L18", "all", 200, 3000, .03, 1),
        ("L19", "stu", 300, 1200, .1, 1), ("L20", "stu", 100, 400, .3, 0),
        ("L21", "gig", 80, 400, .3, 0)]
GIG_X = {"L01", "L02", "L03", "L04", "L06", "L07"}


def poisson(lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= R.random()
        if p <= L:
            return k
        k += 1


def ln_noise(sigma):
    return math.exp(R.gauss(-sigma * sigma / 2, sigma)) if sigma > 0 else 1.0


def band_of(dsr, inc3, prev):
    if inc3 < 300:
        return "I"
    b = "G" if dsr < .30 else ("Y" if dsr < .60 else "R")
    if prev == "R" and .55 <= dsr < .60:
        b = "R"
    return b


RANK = {"G": 0, "Y": 1, "R": 2}


def make_user():
    u = {}
    r = R.random()
    u["type"] = "emp" if r < .70 else ("gig" if r < .85 else "stu")
    u["age"] = R.randint(18, 23) if u["type"] == "stu" else R.randint(18, 35)
    u["imp"], u["dis"] = R.betavariate(2, 5), R.betavariate(5, 2)
    a = u["age"]
    if u["type"] == "emp":
        med = next(m for lim, m in AGE_MEDIAN if a <= lim)
        gross = med * math.exp(R.gauss(0, .35))
        if FIX:
            gross = max(gross, 1700)                      # minimum wage 2025
        u["gross"], u["net"] = gross, gross * NET_FACTOR
        u["sig"] = R.uniform(.03, .08)
    elif u["type"] == "gig":
        u["net"] = 2500 * math.exp(R.gauss(0, .70 if FIX else .35))
        u["gross"] = u["net"]
        u["sig"] = R.uniform(.15, .35)
    else:
        u["net"] = u["gross"] = R.uniform(500, 1200)
        u["sig"] = R.uniform(.20, .40)
    # vehicles (D-35)
    if u["type"] == "emp":
        u["car"], u["moto"] = R.random() < .90, R.random() < .75
    elif u["type"] == "gig":
        u["moto"] = R.random() < .55
        u["car"] = not u["moto"]
    else:
        r = R.random()
        u["car"], u["moto"] = r < .32, .32 <= r < .45
    loan_p = .5
    if FIX and (u["type"] == "stu"):
        loan_p = 0.0
    elif FIX and a < 21:
        loan_p = .1
    fixed = 0.0
    if u["car"] and R.random() < loan_p:
        fixed += R.uniform(400, 900)
    if u["moto"] and R.random() < loan_p:
        fixed += R.uniform(150, 400)
    worker = u["type"] != "stu"
    if worker and a >= 23 and R.random() < .45:
        fixed += R.uniform(100, 300)                       # PTPTN
    if worker and a >= 21 and R.random() < .07:
        fixed += R.uniform(200, 800)                       # personal loan
    u["fixed"] = fixed
    u["family"] = R.uniform(100, 500) if worker and R.random() < .17 else 0.0
    u["parents"] = R.random() < (.6 if a <= 24 else .3)
    u["bnpl"] = R.random() < min(.9, .32 * u["imp"] / .29)
    u["card_ok"] = worker and a >= 21 and u["gross"] >= 2000
    u["festive"] = R.choices(list(FESTIVE_W), weights=list(FESTIVE_W.values()))[0]
    return u


def assign_cards(users):
    workers = [u for u in users if u["type"] != "stu"]
    elig = [u for u in workers if u["card_ok"]]
    need = int(.15 * len(workers))
    holders = set(id(u) for u in R.sample(elig, min(need, len(elig))))
    for u in users:
        u["card"] = id(u) in holders
        u["limit"] = 2 * u["gross"] if u["card"] else 0
        u["bal"] = 0.0 if (not u["card"] or R.random() < u["dis"]) else R.uniform(.1, .6) * u["limit"]


def simulate(u):
    c = min(1.05, max(.60, R.uniform(C_LO, C_HI) + .1 * (u["imp"] - .29) - .1 * (u["dis"] - .71)))
    base = u["net"] - u["fixed"] - u["family"] if FIX else u["net"]
    S = max(0.0, c * base)
    housing = .240 * S * (.4 if u["parents"] else 1.0)
    ess_base = .594 * S - .240 * S + housing
    disc_base = .406 * S
    card_min0 = max(.05 * u["bal"], 50) if u["bal"] > 0 else 0
    r = R.random()
    months = R.uniform(0, .5) if r < .13 else R.uniform(.5, 1.5) if r < .42 else R.uniform(1.5, 2.5) if r < .60 else R.uniform(2.5, 6)
    cash = months * (ess_base + u["fixed"] + card_min0)
    rec = dict(income=[], dsr=[], band=[], short=[], cash=[cash], spend=[], comm=[], disc=[], overdue=0, cushion=[])
    plans, unemployed, correction, late_fee, prev_band, prev_shock = [], 0, 1.0, 0.0, None, False
    job_p = (.03 if u["age"] <= 30 else .015) if FIX else .01
    raise_p, raise_r = (1 / 12, (.03, .07)) if FIX else (.02, (.03, .10))
    base_inc = u["net"]
    for m in range(1, 13):
        inc = base_inc * ln_noise(u["sig"])
        if u["type"] == "emp":
            if unemployed > 0:
                inc, unemployed = 0.0, unemployed - 1
            elif R.random() < job_p:
                unemployed = R.randint(1, 3) - 1
                inc = 0.0
            elif R.random() < raise_p:
                base_inc *= 1 + R.uniform(*raise_r)
        elif u["type"] == "gig" and R.random() < .08:
            inc *= R.uniform(.5, .8)
        mult = R.uniform(1.2, 1.4) if m == u["festive"] else 1.0
        if u["type"] == "stu" and m in SEMESTER:
            mult *= 1.15
        ess = ess_base * ln_noise(.05)
        disc = disc_base * ln_noise(.10 + .40 * u["imp"]) * mult * correction
        bnpl_buy = 0.0
        if u["bnpl"]:
            for _ in range(poisson(2.7)):
                bnpl_buy += min(2000, max(10, 60 * math.exp(R.gauss(0, .9))))
            bnpl_buy = min(bnpl_buy, disc)
            if bnpl_buy > 0:
                plans.append([3, bnpl_buy / 3])
        bnpl_due = sum(p[1] for p in plans)
        for p in plans:
            p[0] -= 1
        plans = [p for p in plans if p[0] > 0]
        card_min = min(u["bal"], max(.05 * u["bal"], 50)) if u["bal"] > 0 else 0.0
        u["bal"] -= card_min
        comm = u["fixed"] + card_min + bnpl_due
        shocks, any_shock = 0.0, False
        for eid, who, lo, hi, f, is_shock in DECK:
            ok = (who == "all" or (who == "moto" and u["moto"]) or (who == "car" and u["car"])
                  or (who == "veh" and (u["car"] or u["moto"])) or (who == "stu" and u["type"] == "stu")
                  or (who == "nonstu" and u["type"] != "stu") or (who == "gig" and u["type"] == "gig"))
            if not ok:
                continue
            p = f / 12 * (1.8 if u["type"] == "gig" and eid in GIG_X else 1) \
                * (2 if u["type"] == "stu" and eid == "L08" else 1) * (1.5 if prev_shock else 1)
            if R.random() < min(1, p):
                shocks += R.uniform(lo, hi)
                any_shock |= bool(is_shock)
        hidden = .03 * max(inc, 0) * math.exp(R.gauss(0, .5))
        cash += inc - ess - (disc - bnpl_buy) - comm - u["family"] - shocks - hidden - late_fee
        late_fee, short = 0.0, 0
        if cash < 0 and u["card"]:
            draw = min(-cash, u["limit"] - u["bal"])
            u["bal"] += draw
            cash += draw
        od_now = 0
        if cash < -0.005:
            short, cash = 1, 0.0
            if bnpl_due > 0:
                rec["overdue"] = 1
                od_now = 1
                late_fee = R.uniform(10, 30)
        rec.setdefault("od", []).append(od_now)
        if u["bal"] > 0:
            if R.random() < u["dis"] and cash > u["bal"]:
                cash -= u["bal"]
                u["bal"] = 0.0
            else:
                u["bal"] *= 1 + .17 / 12
        rec["income"].append(inc)
        inc3 = st.median(rec["income"][-3:])
        dsr = comm / inc3 if inc3 > 0 else 9.9
        b = band_of(dsr, inc3, prev_band)
        cushion = cash / max(1.0, ess + comm)
        worsened = prev_band in RANK and b in RANK and RANK[b] > RANK[prev_band]
        correction = (1 - R.uniform(.10, .25)) if ((worsened or cushion < 1) and R.random() < u["dis"]) else 1.0
        prev_band, prev_shock = b, any_shock
        for k, v in (("dsr", dsr), ("band", b), ("short", short), ("cash", cash), ("spend", ess + disc),
                     ("comm", comm), ("disc", disc), ("cushion", cushion)):
            rec[k].append(v)
    return rec


def main():
    users = [make_user() for _ in range(N)]
    assign_cards(users)
    recs = [simulate(u) for u in users]
    rows, comp = [], {"band": 0, "short": 0, "both": 0}
    for u, r in zip(users, recs):
        for t in range(3, 10):
            bt, b3 = r["band"][t - 1], r["band"][t + 2]
            if "I" in (bt, b3):
                continue
            wb = RANK[b3] > RANK[bt]
            sh = any(r["short"][t:t + 3])
            y = wb or sh
            rows.append((u["type"], y))
            if y:
                comp["both" if wb and sh else "band" if wb else "short"] += 1
    pos = sum(y for _, y in rows) / len(rows)
    borrowers = [(u, r) for u, r in zip(users, recs) if r["comm"][-1] > 0]
    red12 = sum(r["band"][-1] == "R" for _, r in borrowers) / len(borrowers)
    dsr_b = [r["dsr"][-1] for _, r in borrowers if r["dsr"][-1] < 9]
    um = [(u, r, m) for u, r in zip(users, recs) for m in range(12)]
    short_um = sum(r["short"][m] for _, r, m in um) / len(um)
    ever_short = sum(any(r["short"]) for r in recs) / N
    ins = sum(r["band"][m] == "I" for _, r, m in um) / len(um)
    bnpl_users = [r for u, r in zip(users, recs) if u["bnpl"]]
    overdue = sum(r["overdue"] for r in bnpl_users) / max(1, len(bnpl_users))
    workers = [(u, r) for u, r in zip(users, recs) if u["type"] != "stu"]
    spend_ratio = sum(sum(r["spend"]) for u, r in workers) / sum(12 * u["gross"] for u, r in workers)
    saved = sum(r["cash"][-1] > r["cash"][0] for r in recs) / N
    cush12 = [r["cushion"][-1] for r in recs]
    buckets = [sum(lo <= c < hi for c in cush12) / N for lo, hi in ((-1, .5), (.5, 1.5), (1.5, 2.5), (2.5, 1e9))]
    emp = [u for u in users if u["type"] == "emp"]
    print(f"variant={VARIANT} users={N} seed={SEED} c=U({C_LO},{C_HI})")
    cush6 = [r["cushion"][5] for r in recs]
    print("cushion buckets m6                   : " + " / ".join(
        f"{sum(lo <= c < hi for c in cush6)/N:.0%}" for lo, hi in ((-1, .5), (.5, 1.5), (1.5, 2.5), (2.5, 1e9))))
    print(f"positive rate (S9 10-30%)           : {pos:.1%}   rows={len(rows)}")
    tot = sum(comp.values())
    print(f"  positives: band-only {comp['band']/tot:.0%} | shortfall-only {comp['short']/tot:.0%} | both {comp['both']/tot:.0%}")
    for typ in ("emp", "gig", "stu"):
        ys = [y for t, y in rows if t == typ]
        print(f"  positive rate {typ:4s}                 : {sum(ys)/len(ys):.1%}")
    print(f"Red share of borrowers m12 (S3 5-25%): {red12:.1%}")
    print(f"median DSR of borrowers m12          : {st.median(dsr_b):.1%}  (BNM median incl. mortgages 33%)")
    print(f"shortfall per user-month             : {short_um:.1%}; users with >=1 shortfall: {ever_short:.1%}")
    print(f"insufficient-income user-months (S7) : {ins:.1%}")
    print(f"BNPL users {len(bnpl_users)/N:.1%} (S11 32%), ever overdue in 12 months: {overdue:.1%}")
    pit = [st.mean(r["od"][2::3]) for r in bnpl_users]   # quarter-end months 3, 6, 9, 12
    print(f"BNPL overdue at quarter-ends (point-in-time, BNM Q4 2022 = 17%): {st.mean(pit):.1%}")
    print(f"worker spending / gross income       : {spend_ratio:.1%}  (HES/HIES 2024 households: 60.8%)")
    print(f"users with cash m12 > m0 ('saved')   : {saved:.1%}  (Findex saved any: 15-24 72.7%, 25+ 58.8%)")
    print("cushion buckets m12 (<.5/.5-1.5/1.5-2.5/>=2.5): " + " / ".join(f"{b:.0%}" for b in buckets) + "  (m1 target 13/29/18/40)")
    print(f"employee gross <RM2,000              : {sum(u['gross'] < 2000 for u in emp)/len(emp):.1%}  (DOSM all ages 27.4%)")
    print(f"card holders among workers           : {sum(u['card'] for u in users)/sum(u['type']!='stu' for u in users):.1%}")


if __name__ == "__main__":
    main()
