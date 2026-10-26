"""Points simulation (T-14b, game_design.md §13): can any way of gaming the app beat being honest?

One synthetic person's TRUE life (income, essentials, wants, a PTPTN loan, real balances) is
generated once; each strategy is a different way of reporting that same life to the app. Every
strategy is replayed through engine.game (the D-75 rules) and compared with honest reporting
month by month.

    .venv\\Scripts\\python -m sim.points_sim         # writes sim/results/points_sim.md

Check-ins carry money and debt as at the END of the month (D-77: the server takes what was logged
after the month ended off the balances given), so a check-in's day doesn't change what it reports.
Snapshots are taken 7 days after each month end, when every month's check-in is in.

Strategies (the person's real finances are identical in all of them):
  honest          logs everything, checks in on the last day of each month with the true balances
  forgetful       honest, but forgets 8% of their spending (not a cheat: measures false alarms)
  late_checker    honest, but checks in 5 days after each month ends (not a cheat: D-77 check)
  padder          logs 40 entries a day: 37 made-up RM1 purchases on top of the real ones
  hider           hides impulse purchases
  cost_hider      declares RM900 typical costs (true about RM2,200) and never logs essentials
  borrower        borrows RM2,000 before every odd-month check-in, repays it the month after
  debt_liar       declares a RM40,000 debt (true RM12,000) and reports it falling RM2,000 a month
  debt_liar_logs  the same, and logs made-up RM1,750 loan payments to back it up
  spike_liar      reports RM10,000 more in the bank in month 6
  fleksibel_mover moves RM1,000 from EPF Fleksibel to the bank every 3 months
  backdater       skips months 4-6, then tries to check them in late (and one before sign-up)
  stale           stops checking in after month 8
The known limit, a lie told every month (no app can catch it without bank data):
  section_liar    moves RM300 a month from ASB to the bank but reports ASB unchanged (a small
                  lie inside the verification tolerance)
  balance_liar    reports RM1,000 more in the bank, every month
  month_shifter   logs a made-up RM1,000 purchase dated just after each month ends, so the
                  server's month-end balance comes out RM1,000 higher (the same lie through D-77)
  income_hider    leaves RM1,100 of salary and RM1,100 of spending out of the logs and confirms
                  RM1,900 income, so the same saving looks like a bigger share of income
and comparisons: a non-saver, a rough patch, a student and a gig worker.

Synthetic data only (CLAUDE.md rule 12); every life is seeded, so results are reproducible.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from engine.game import CardAnswer, CheckIn, DayActivity, GameProfile, game_config, load_game, replay

START = date(2026, 1, 1)
MONTHS = 24
RESULTS = Path(__file__).resolve().parent / "results"
ASB = 5000.0                            # investments not marked for emergencies (other money)


def month_start(k: int) -> date:
    return date(2026 + (k - 1) // 12, (k - 1) % 12 + 1, 1)


def month_end(k: int) -> date:
    return month_start(k + 1) - timedelta(days=1)


@dataclass(frozen=True)
class Month:
    k: int
    income: float
    essentials: float
    wants: float
    impulse: float                      # part of wants
    debt_paid: float
    extra_out: float                    # a one-off cost (car repair)
    money: float                        # true counted money at month end
    debt: float                         # true debt at month end
    band: str = "GREEN"
    shortfall: bool = False

    @property
    def out(self) -> float:
        return self.essentials + self.wants + self.debt_paid + self.extra_out


@dataclass(frozen=True)
class Life:
    kind: str
    with_parents: bool
    declared_income: float
    money0: float
    debt0: float
    days: tuple[tuple[date, int, int, int], ...]     # day, purchases, impulse, essentials
    months: tuple[Month, ...]


LIVES = {   # kind, with parents, income (mean, sd), essentials, wants, debt (start, payment, interest)
    "employee": ("employee", False, (3000, 0), 1950, 550, (12000, 250, 10)),
    "non_saver": ("employee", False, (3000, 0), 1950, 800, (12000, 250, 10)),
    "student": ("student", True, (800, 0), 300, 440, (0, 0, 0)),
    "gig": ("gig", False, (2400, 400), 1500, 750, (0, 0, 0)),
}


def make_life(seed: int = 7, who: str = "employee", rough_patch: bool = False) -> Life:
    kind, parents, (inc, inc_sd), ess, wants, (debt, pay, interest) = LIVES[who]
    rng = np.random.default_rng(seed)
    days, d = [], START
    while d <= month_end(MONTHS):
        n = int(rng.poisson(2.2))
        imp = int(n > 0 and rng.random() < 0.15)
        days.append((d, n, imp, int(rng.binomial(n - imp, 0.6)) if n > imp else 0))
        d += timedelta(days=1)
    months, money = [], 1000.0
    for k in range(1, MONTHS + 1):
        income = max(0.0, inc + float(rng.normal(0, inc_sd))) if inc_sd else float(inc)
        e = ess + float(rng.normal(0, 60 if ess > 1000 else 20))
        w = max(0.0, wants + float(rng.normal(0, 90 if wants > 500 else 30)))
        imp = min(w, max(0.0, float(rng.normal(0.3 * w, 40))))
        paid = min(pay, debt + interest) if debt > 0 else 0.0
        extra, band, short = 0.0, "GREEN", False
        if rough_patch and k == 10:
            extra = 1800.0                                         # car repair
        if rough_patch and k == 14:
            income, band, short = income - 1500, "RED", True       # lost overtime: a really bad month
        debt = max(0.0, debt + interest - paid)
        money = money + income - e - w - paid - extra
        months.append(Month(k, round(income, 2), round(e, 2), round(w, 2), round(imp, 2), paid, extra,
                            round(money, 2), round(debt, 2), band, short))
    return Life(kind, parents, float(inc), 1000.0, float(LIVES[who][5][0]), tuple(days), tuple(months))


def profile(life: Life, **kw) -> GameProfile:
    costs = float(np.mean([m.essentials + m.debt_paid for m in life.months]))
    base = dict(start=START, employment_type=life.kind, declared_income=life.declared_income,
                onboarding_money=life.money0, onboarding_debt=life.debt0, onboarding_other_money=ASB,
                typical_monthly_costs=round(costs, -1), lives_with_parents=life.with_parents)
    return GameProfile(**{**base, **kw})


def honest_checkin(m: Month) -> CheckIn:
    return CheckIn(month=month_start(m.k), on=month_end(m.k), counted_money=m.money, total_debt=m.debt,
                   other_money=ASB, bills_on_time=True, logged_in=m.income, logged_out=m.out,
                   logged_costs=m.essentials + m.debt_paid, logged_debt_paid=m.debt_paid, net_income=m.income,
                   band=m.band, shortfall=m.shortfall)


def strategy_inputs(name: str, life: Life, forget: float = 0.08) -> dict:
    """How each strategy reports the same true life to the app."""
    ms = life.months
    honest = [honest_checkin(m) for m in ms]
    days = [DayActivity(d, n, n == 0) for d, n, _, _ in life.days]
    cards = [CardAnswer(d) for d, *_ in life.days if d.weekday() == 0]
    out = dict(profile=profile(life), days=days, checkins=honest, cards=cards)
    if name in ("honest", "fleksibel_mover"):       # one total of counted money: moving inside it changes nothing
        return out
    if name == "forgetful":
        out["checkins"] = [replace(c, logged_out=c.logged_out - forget * (m.essentials + m.wants))
                           for c, m in zip(honest, ms)]
    elif name == "padder":
        out["days"] = [DayActivity(d, 40) for d, *_ in life.days]
        out["checkins"] = [replace(c, logged_out=c.logged_out + 37 * month_end(m.k).day) for c, m in zip(honest, ms)]
    elif name == "hider":
        out["days"] = [DayActivity(d, n - i, n - i == 0) for d, n, i, _ in life.days]
        out["checkins"] = [replace(c, logged_out=c.logged_out - m.impulse) for c, m in zip(honest, ms)]
    elif name == "cost_hider":
        out["profile"] = profile(life, typical_monthly_costs=900.0)
        out["days"] = [DayActivity(d, n - e, n - e == 0) for d, n, _, e in life.days]
        out["checkins"] = [replace(c, logged_out=c.logged_out - m.essentials, logged_costs=m.debt_paid)
                           for c, m in zip(honest, ms)]
    elif name == "borrower":
        out["checkins"] = [replace(c, counted_money=c.counted_money + 2000, total_debt=c.total_debt + 2000,
                                   logged_in=c.logged_in + 2000) if m.k % 2 else
                           replace(c, logged_out=c.logged_out + 2000, logged_debt_paid=c.logged_debt_paid + 2000)
                           if m.k > 1 else c for c, m in zip(honest, ms)]
    elif name in ("debt_liar", "debt_liar_logs"):
        out["profile"] = profile(life, onboarding_debt=40000.0)
        fake = 1750.0 if name == "debt_liar_logs" else 0.0
        out["checkins"] = [replace(c, total_debt=max(m.debt, 40000.0 - 2000 * m.k), logged_out=c.logged_out + fake,
                                   logged_debt_paid=c.logged_debt_paid + fake) for c, m in zip(honest, ms)]
    elif name == "spike_liar":
        out["checkins"] = [replace(c, counted_money=c.counted_money + 10000) if m.k == 6 else c
                           for c, m in zip(honest, ms)]
    elif name == "backdater":
        late = month_end(7)
        out["checkins"] = ([c for c, m in zip(honest, ms) if m.k not in (4, 5, 6)]
                           + [replace(honest[k - 1], on=late) for k in (4, 5, 6)]
                           + [replace(honest[0], month=date(2025, 12, 1), on=month_start(1) + timedelta(days=2))])
    elif name == "stale":
        out["checkins"] = honest[:8]
    elif name == "late_checker":
        out["checkins"] = [replace(c, on=c.on + timedelta(days=5)) for c in honest]
    elif name == "section_liar":
        moved = [min(300.0 * m.k, ASB) for m in ms]
        out["checkins"] = [replace(c, counted_money=c.counted_money + mv) for c, mv in zip(honest, moved)]
    elif name == "balance_liar":
        out["checkins"] = [replace(c, counted_money=c.counted_money + 1000) for c in honest]
    elif name == "month_shifter":
        # the fake purchase is dated the 2nd of the next month and logged before the check-in on the
        # 5th: the server's month-end balance comes out RM1,000 higher, and next month's own entries
        # include the fake purchase
        out["checkins"] = [replace(c, on=c.on + timedelta(days=5), counted_money=c.counted_money + 1000,
                                   logged_out=c.logged_out + (1000 if m.k > 1 else 0)) for c, m in zip(honest, ms)]
    elif name == "income_hider":
        # salary and spending (wants) left out alike: RM1,100, at most 37% of the month's income (the
        # employee's share), so the lie stays possible for a student or a gig worker
        out["checkins"] = [replace(c, logged_in=c.logged_in - h, logged_out=c.logged_out - h, net_income=c.net_income - h)
                           for c in honest for h in [min(1100.0, 0.37 * c.net_income)]]
    else:
        raise ValueError(name)
    return out


CHEATS = ["padder", "hider", "cost_hider", "borrower", "debt_liar", "debt_liar_logs", "spike_liar",
          "fleksibel_mover", "backdater", "stale"]
KNOWN_LIMITS = ["section_liar", "balance_liar", "month_shifter", "income_hider"]
STRATEGIES = ["honest", "forgetful", "late_checker"] + CHEATS + KNOWN_LIMITS
STOPPED_BY = {
    "honest": "-",
    "forgetful": "tolerance: max(RM100, 10% of income)",
    "late_checker": "- (money and debt as at month end, D-77)",
    "padder": "no points per entry (P1); made-up spending breaks the match (R1)",
    "hider": "saving comes from balances, not logs (G4)",
    "cost_hider": "costs at least what the balances show was spent, until verified (S1)",
    "borrower": "borrowing isn't saving (C2); borrowed cash unlocks nothing (S2)",
    "debt_liar": "debt points only as far as logged payments (R5)",
    "debt_liar_logs": "made-up payments break the match, so no debt points (R1, R5)",
    "spike_liar": "unverified progress waits a month and the money was gone (C1, G6)",
    "fleksibel_mover": "counted money is one total (C6)",
    "backdater": "check-in window and sign-up date (C3)",
    "stale": "no check-in, no progress",
    "section_liar": "not stopped: a small lie inside the tolerance (known limit)",
    "balance_liar": "not stopped: verification checks changes, not how much there is (known limit)",
    "month_shifter": "the fake entries break every month's match, so it loses points; levels early (known limit)",
    "income_hider": "tiers use the larger of confirmed and declared income (I1, G13); a little gets through in a gig "
                    "worker's above-average months (known limit)",
}


@dataclass(frozen=True)
class Snapshot:
    k: int
    points: int
    tiers: dict
    room_level: int
    garden_open: bool
    qualifying_months: int
    verified_months: int
    rejected: int


SNAPSHOT_AFTER_MONTH_END = timedelta(days=7)          # every month's check-in window has closed


def run(name: str, life: Life, **kw) -> list[Snapshot]:
    """Monthly snapshots of one strategy (one replay, observed 7 days after each month end)."""
    inputs = strategy_inputs(name, life, **kw)
    prof = inputs.pop("profile")
    ends = {month_end(k) + SNAPSHOT_AFTER_MONTH_END: k for k in range(1, MONTHS + 1)}
    out = []

    def snap(d, st):
        if d in ends:
            out.append(Snapshot(ends[d], st.points, st.points_by_tier(), st.room_level, st.garden_open,
                                st.qualifying_months, sum(m.verified for m in st.months), len(st.rejected)))

    replay(prof, month_end(MONTHS) + SNAPSHOT_AFTER_MONTH_END, strict=False, observe=snap, **inputs)
    return out


def tolerance_tradeoff(life: Life, shares=(0.10, 0.07, 0.05)) -> list[str]:
    """What-if: a tighter verification tolerance catches the RM300-a-month lie but flags more
    honest users who forget to log some spending."""
    lines = ["| Tolerance (share of income) | section_liar vs honest at 24 | Forgets 8%: verified months | "
             "Forgets 12%: verified months |", "|---|---|---|---|"]
    for share in shares:
        cfg = copy.deepcopy(load_game())
        cfg["verification"]["tolerance_income_share"] = share
        with game_config(cfg):
            h, sl = run("honest", life), run("section_liar", life)
            f8 = run("forgetful", life)
            f12 = run("forgetful", life, forget=0.12)
        lines.append(f"| {share:.0%} | {sl[-1].points - h[-1].points:+d} | {f8[-1].verified_months} / 24 | "
                     f"{f12[-1].verified_months} / 24 |")
    return lines


def first(snaps: list[Snapshot], cond) -> int | None:
    return next((s.k for s in snaps if cond(s)), None)


def months_ahead(snaps: list[Snapshot], honest: list[Snapshot]) -> int:
    return sum(s.points > h.points for s, h in zip(snaps, honest))


def report() -> str:
    life = make_life()
    runs = {s: run(s, life) for s in STRATEGIES}
    h = runs["honest"]
    lines = ["# Points simulation (T-14b, D-75 to D-77 rules)", "",
             "One synthetic employee (RM3,000 take-home, about RM2,200 essentials + PTPTN, a RM12,000 PTPTN",
             f"loan, RM5,000 in ASB, saving about RM250 a month) reported to the app in {len(STRATEGIES)} ways over "
             "24 months. Every strategy lives the same true life; only what it tells the app differs. Snapshots "
             "are 7 days after each month end, when every check-in window has closed.", "",
             "| Strategy | Points at 6 / 12 / 24 months | Check-in / learning / logging / health at 24 | "
             "Verified months | Room level 2 / 3 reached (month) | Garden months at 24 | Months ahead of honest | "
             "What stops it |",
             "|---|---|---|---|---|---|---|---|"]
    for s, snaps in runs.items():
        t = snaps[-1].tiers
        pts = " / ".join(str(snaps[m - 1].points) for m in (6, 12, 24))
        lv = " / ".join(str(first(snaps, lambda x, n=n: x.room_level >= n)) for n in (2, 3))
        lines.append(f"| {s} | {pts} | {t['checkin']} / {t['learning']} / {t['logging']} / {t['health']} | "
                     f"{snaps[-1].verified_months} | {lv} | {snaps[-1].qualifying_months} | {months_ahead(snaps, h)} | "
                     f"{STOPPED_BY[s]} |")
    gap = max(x.points - y.points for s in CHEATS for x, y in zip(runs[s], h))
    ties = [s for s in CHEATS if runs[s][-1].points == h[-1].points]
    never_earlier = all(x.room_level <= y.room_level and x.qualifying_months <= y.qualifying_months
                        for s in CHEATS for x, y in zip(runs[s], h))
    sl, bl, ms = runs["section_liar"], runs["balance_liar"], runs["month_shifter"]
    gig = make_life(who="gig")
    gig_hider = run("income_hider", gig)[-1].points - run("honest", gig)[-1].points
    lv3 = {s: first(runs[s], lambda x: x.room_level >= 3) for s in ("honest", "balance_liar", "month_shifter")}
    same = all(x.points == y.points and x.room_level == y.room_level for x, y in zip(runs["late_checker"], h))
    lines += ["", f"**Cheats:** the best any cheat does against honest in any month is {gap:+d} points "
              f"({', '.join(ties)} only tie, because what they change doesn't matter to the rules); "
              f"no cheat reaches a room level or a garden month earlier than honest ({'yes' if never_earlier else 'NO'}).",
              f"The backdater's {runs['backdater'][-1].rejected} late or pre-sign-up check-ins were all rejected.",
              "",
              f"**Checking in late changes nothing** (D-77): the late checker earned exactly what honest earned in "
              f"every month ({'yes' if same else 'NO'}).",
              "",
              "**Known limit: a lie told every month.** Verification checks how money *changes*; it can't see a lie "
              "about how much there *is* while the lie stays the same:",
              f"- section_liar (a small lie inside the tolerance): {sl[-1].points - h[-1].points:+d} points over 24 "
              "months, saving points only (the money it moved to the bank is real, so its cushion is real).",
              f"- balance_liar (RM1,000 more than it has, every month): unverified only in month 1, then verified; "
              f"{bl[-1].points - h[-1].points:+d} points, room level 3 in month {lv3['balance_liar']} "
              f"(honest: {lv3['honest']}). Claiming the same extra at sign-up would cost it nothing at all.",
              f"- month_shifter (the same lie through made-up entries dated after month end): never verified, so "
              f"{ms[-1].points - h[-1].points:+d} points, but room level 3 in month {lv3['month_shifter']}.",
              f"- income_hider (leaves equal amounts of salary and spending out, confirms a lower income): "
              f"{runs['income_hider'][-1].verified_months} months verified; {runs['income_hider'][-1].points - h[-1].points:+d} "
              "points (it was +2,580 before I1, D-89: the same saving and debt payments were bigger shares of a smaller "
              "income). The tiers now use the larger of the confirmed income and the income declared at sign-up, "
              f"so the lie no longer pays for a steady salary. A gig worker can still gain a little "
              f"({gig_hider:+d} points over 24 months): in months above the declared average, hiding income lowers the "
              "tier's denominator to the declared level. Levels are never affected, and in the real app a lower "
              "income also raises the debt-service ratio and can worsen the band.",
              "Only outside evidence can catch these: balances in pasted bank notifications (the parser, a Should) "
              "or bank integration (a Won't). With no leaderboards, such a user only fools themselves.",
              "",
              f"**False alarms:** the forgetful but honest user (8% of spending never logged) had "
              f"{runs['forgetful'][-1].verified_months} of 24 months verified.", "",
              "**Tolerance trade-off** (what-if; shared/game.json keeps 10%). A tighter tolerance only shrinks the "
              "lie that gets through; it never removes it, and it flags more honest users:", ""]
    lines += tolerance_tradeoff(life) + [""]
    # who earns what
    lines += ["## Reward order and fairness across people", "",
              "| Person (honest) | Check-in / learning / logging / health points at 24 | Garden months at 24 | "
              "Room level at 24 |",
              "|---|---|---|---|"]
    for who in ("employee", "student", "gig", "non_saver"):
        snaps = run("honest", make_life(who=who))
        t = snaps[-1].tiers
        lines.append(f"| {who} | {t['checkin']} / {t['learning']} / {t['logging']} / {t['health']} | "
                     f"{snaps[-1].qualifying_months} | {snaps[-1].room_level} |")
    rough = run("honest", make_life(rough_patch=True))
    mono = all(b.qualifying_months >= a.qualifying_months and b.room_level >= a.room_level and b.points >= a.points
               for a, b in zip(rough, rough[1:]))
    lines += ["", f"**Rough patch** (RM1,800 car repair in month 10, a really bad Red month in 14): points, room level "
              f"and garden months never go down ({'yes' if mono else 'NO'}); {rough[-1].qualifying_months} garden months "
              f"at 24 vs {h[-1].qualifying_months} without it.", ""]
    return "\n".join(lines)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    text = report()
    (RESULTS / "points_sim.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
