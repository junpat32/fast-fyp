"""FAST game rules (T-14b): points, streaks, badges, room and garden levels, choices, plant growth.

Everything here follows docs/game_design.md v1.6 (the D-75 package); every number comes from
shared/game.json.

Invariants
  G1  deterministic: the state is a pure function of the user's own history
  G2  points never go down; nothing unlocked is ever taken away (D-11)
  G3  a logged entry earns no points (P1); logging is rewarded for being RIGHT, not for volume: a
      verified month (the logs explain the money) and streak milestones. Padding or hiding entries
      breaks the match, so neither can beat honesty
  G4  money comes from the CHECK-IN, never from logged spending. Counted money (cash, bank,
      e-wallets, EPF Fleksibel, savings marked for emergencies; C6) makes the cushion; other money
      (e.g. investments) counts for saving only. Moving money between any of the user's pockets
      changes nothing
  G5  borrowing is never saving: saving = change in the user's money − new borrowing (C2); in a
      month where debt went up, logged debt payments count as re-borrowed. Paying debt down earns
      the larger debt points, only when total debt reaches a NEW LOW and only as far as the
      payments were logged in a verified month (R5), so borrow-and-repay and fake debts earn nothing
  G6  progress counts straight away in a VERIFIED month; otherwise it waits for the next check-in
      and counts only if the money is still there (C1): room levels, milestones, saving points and
      goal-met garden months. One spike or one lie unlocks nothing. Borrowed cash still held never
      counts toward unlocks (S2)
  G7  the game cushion's monthly costs never fall below the declared typical costs. Until the user's
      logging has been verified (2 of the last 3 months) they also never fall below the
      plausibility floor (option 1) or below what the balances show was spent (S1), so hiding
      costs makes the cushion smaller, not bigger; verified users' own logged costs are used
  G8  the garden opens after 3 check-ins for everyone; it grows with qualifying months: the user met
      their own goal (money set aside + debt paid down) or held 1+ month of cushion (P2). A bad
      month pauses the counter; it never resets
  G9  choices used <= choices earned (1 per 200 points + free choices); every unlock costs 1 choice
  G10 plants grow unless the month is really bad; in a really bad month they droop (after 2 in a row
      they rest calmly) but never lose a stage (C5, D-73, I3)
  G11 time: check-ins only for months since sign-up, from the month's last day to 7 days after it
      (C3, D-77); a check-in's money and debt are as at the END of the month (the server takes
      what was logged after the month ended off the balances given), so its period always matches
      the month's logged entries. Day stamps are the server's arrival day, set before the data
      reaches here
  G12 reward order (R6): a check-in earns the least, logging second, good financial health the most
      (bills on time, saving, paying debt down, keeping a cushion, milestones)
  G13 income for rewards = max(confirmed income, income declared at sign-up), which is locked
      (I1, D-89). It sets the saving and debt tiers, an employee's or student's default goal (a gig
      goal follows the month's income, I2) and, until costs are trusted, what the balances show was
      spent (S1). Hiding income makes the same saving look like a bigger share, a smaller goal and
      smaller costs, so none of it pays. Trade-off: an honest user whose income really falls below
      the sign-up figure sees a smaller game cushion until their logging is trusted (~2 months)

Verified month (option 2, R1): something was logged, the logged money in covers the month's income,
and |change in the user's money − (logged in − logged out)| <= max(RM100, 10% of income), where
    change in money = Δcounted + Δother + voluntary EPF × 90% (the part outside Fleksibel)
                      − compulsory EPF paid into Fleksibel (not the user's effort)
logged out = money that left the user's pockets (spending paid now, debt payments); purchases on
credit or BNPL count when they are paid, and payments deducted from salary are outside it.

Algorithm: replay the history one day at a time (Malaysia time):
    sign-up (day 0): the first money and debt, +20 and a free welcome choice
    for each day d up to `until`:
        logging streak (and its milestone points)
        weekly card points (once per week)
        any check-in made on d: verify, saving, debt, bills, cushion, unlocks, garden, badges
        growing day? planted things grow
        the user's actions on d (plant, dig, tree, decorate, choose/add animal), each validated
    invalid events are skipped and listed in state.rejected (strict=True raises instead)
Cost: O(days + events); three years of use is about 1,100 days, a replay takes milliseconds.

Trace (employee, income RM3,000, declared costs RM2,400; saves RM300 a month, logs honestly):
    check-in  money  points (check-in + verified + saved + bills + kept + milestone)  cushion  garden
    sign-up   0      20 (welcome) + a free choice                                    0.00     closed
    1         300    20 + 40 + 120 + 30 = 210                                        0.11 (*) closed (1 of 3)
    3         900    210                                                             0.38     opens (month 0)
    4         1,200  210 + 50 (0.5 milestone; room 2)                                0.50     qualifying 1 (goal met)
    8         2,400  210 + 40 (1 month kept) + 100 (1 milestone; room 3)             1.00     qualifying 5
    (*) not yet trusted: costs = what the balances show was spent (RM2,700); from month 2, RM2,400
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Union

GAME_CONFIG = Path(__file__).resolve().parents[1] / "shared" / "game.json"
_override: dict | None = None


@lru_cache
def _load_file() -> dict:
    return json.loads(GAME_CONFIG.read_text(encoding="utf-8"))


def load_game() -> dict:
    return _override if _override is not None else _load_file()


@contextmanager
def game_config(cfg: dict):
    """Replay under another set of rules (what-if analysis in sim/points_sim.py only; the app and API
    always use shared/game.json)."""
    global _override
    old, _override = _override, cfg
    try:
        yield
    finally:
        _override = old


class GameRuleError(ValueError):
    """An event the rules don't allow; the app shows the reason as a gentle message."""


# ---------------------------------------------------------------- inputs
@dataclass(frozen=True)
class GameProfile:
    start: date                              # sign-up day: also the first check-in
    employment_type: str                     # employee / gig / student
    declared_income: float                   # net monthly income declared at sign-up
    onboarding_money: float                  # counted money at sign-up (C6)
    onboarding_debt: float = 0.0             # everything owed at sign-up
    onboarding_other_money: float = 0.0      # money not marked for emergencies (e.g. investments)
    typical_monthly_costs: float | None = None
    lives_with_parents: bool = False
    savings_goal: float | None = None        # RM a month (employees, students); None -> suggested
    savings_goal_share: float | None = None  # share of each month's income (gig); None -> suggested


@dataclass(frozen=True)
class DayActivity:
    day: date                                # server arrival day (C3)
    entries: int = 0
    no_spend: bool = False


@dataclass(frozen=True)
class CheckIn:
    month: date                              # first day of the month being checked in
    on: date                                 # server day it arrived
    counted_money: float                     # at month end: cash + bank + e-wallets + EPF Fleksibel + emergency savings
    total_debt: float                        # at month end: everything owed
    bills_on_time: bool
    other_money: float = 0.0                 # money not marked for emergencies (e.g. investments)
    logged_in: float = 0.0                   # money in logged that month
    logged_out: float = 0.0                  # money out of the user's pockets logged that month
    logged_costs: float = 0.0                # essentials + debt payments logged (for the cushion)
    logged_debt_paid: float = 0.0            # debt payments logged, incl. those deducted from salary
    epf_voluntary: float = 0.0               # voluntary EPF contributions that month (self top-up, i-Saraan)
    epf_compulsory_to_fleksibel: float = 0.0  # compulsory contributions credited to Fleksibel
    net_income: float | None = None          # confirmed at the check-in; None -> declared income
    band: str = "GREEN"
    shortfall: bool = False
    forecast_probability: float | None = None
    forecast_base_rate: float | None = None
    health_tier: str | None = None


@dataclass(frozen=True)
class CardAnswer:
    day: date
    skipped: bool = False


@dataclass(frozen=True)
class GoalChange:
    day: date                                # takes effect from the next month
    amount: float | None = None
    share: float | None = None


@dataclass(frozen=True)
class Plant:
    day: date
    cell: tuple[int, int]
    plant: str


@dataclass(frozen=True)
class Dig:
    day: date
    cell: tuple[int, int]


@dataclass(frozen=True)
class BuyTree:
    day: date


@dataclass(frozen=True)
class Decorate:
    day: date
    item: str
    spot: str


@dataclass(frozen=True)
class MoveDecoration:
    day: date
    item: str
    spot: str


@dataclass(frozen=True)
class ChooseAnimal:
    day: date
    kind: str


@dataclass(frozen=True)
class AddAnimal:
    day: date
    kind: str


Action = Union[Plant, Dig, BuyTree, Decorate, MoveDecoration, ChooseAnimal, AddAnimal]


# ---------------------------------------------------------------- state
@dataclass
class Growing:
    kind: str
    growing_days: int = 0


@dataclass
class Award:
    day: date
    kind: str            # one of the kinds in game.json reward_tiers
    points: int
    ref: str = ""


@dataclass
class Pending:
    """An unverified month's progress, waiting for the next check-in to confirm it (G6)."""
    ref: str
    wealth: float
    saving_kind: str
    saving_points: int
    goal_met: bool


@dataclass
class MonthResult:
    month: date
    verified: bool
    saving: float                            # set aside minus new borrowing
    progress: float                          # set aside + debt paid down (the goal measure)
    goal: float
    goal_met: bool
    cushion: float
    qualifying: bool


@dataclass
class GameState:
    money: float                             # counted money at the last check-in
    other: float                             # other money at the last check-in
    debt: float
    lowest_debt: float                       # lowest debt confirmed by a verified month
    borrowed_cash: float = 0.0               # borrowed money still held (never unlocks anything, S2)
    pending: Pending | None = None
    points: int = 0
    ledger: list[Award] = field(default_factory=list)
    months: list[MonthResult] = field(default_factory=list)
    rejected: list[tuple[object, str]] = field(default_factory=list)
    streak: int = 0
    best_streak: int = 0
    free_choices: int = 0
    badges: set[str] = field(default_factory=set)
    milestones: set[str] = field(default_factory=set)
    best_cushion: float = 0.0
    game_cushion: float | None = None
    prev_cushion: float | None = None
    room_level: int = 1
    check_ins: int = 0
    garden_opened_on: date | None = None
    qualifying_months: int = 0
    saved_months: int = 0
    saved_in_a_row: int = 0
    really_bad_in_a_row: int = 0
    last_checkin: CheckIn | None = None
    choices_used: int = 0
    plants: dict[tuple[int, int], Growing] = field(default_factory=dict)
    seed_box: list[Growing] = field(default_factory=list)
    tree: Growing | None = None
    decorations: dict[str, str] = field(default_factory=dict)
    animals: dict[str, int] = field(default_factory=dict)
    animal_slots_used: int = 0
    _logged_costs: list[float] = field(default_factory=list)   # verified months only
    _outflows: list[float] = field(default_factory=list)       # income − saving, from the balances
    _verified: list[bool] = field(default_factory=list)
    _carded_weeks: set[date] = field(default_factory=set)
    _rest_used: dict[date, int] = field(default_factory=dict)
    _streak_rewards: set[str] = field(default_factory=set)
    _checkin_months: set[date] = field(default_factory=set)
    _goal_changes: list[GoalChange] = field(default_factory=list)

    # ---- derived views
    def points_by_tier(self) -> dict[str, int]:
        """Points earned per reward tier (G12): checkin, learning, logging, health."""
        tiers = {k: v for k, v in load_game()["reward_tiers"].items() if not k.startswith("_") and k != "order"}
        out = {t: 0 for t in tiers}
        for a in self.ledger:
            out[next(t for t, kinds in tiers.items() if a.kind in kinds)] += a.points
        return out

    @property
    def choices_earned(self) -> int:
        return self.points // load_game()["choices"]["points_per_choice"] + self.free_choices

    @property
    def choices_available(self) -> int:
        return self.choices_earned - self.choices_used

    @property
    def garden_open(self) -> bool:
        return self.garden_opened_on is not None

    @property
    def garden_level(self) -> int:
        if not self.garden_open:
            return 0
        at = load_game()["garden"]["level_at_qualifying_months"]
        return max(int(lv) for lv, m in at.items() if self.qualifying_months >= m)

    @property
    def bed_step(self) -> int:
        g = load_game()["garden"]
        g4 = g["level_at_qualifying_months"]["4"]
        return max(0, min(self.qualifying_months - g4, len(g["bed_growth_after_g4"]))) if self.garden_level == 4 else 0

    @property
    def plant_tier(self) -> int:
        if not self.garden_open:
            return 0
        at = load_game()["garden"]["plant_tier_at_qualifying_months"]
        return max(int(t) for t, m in at.items() if self.qualifying_months >= m)

    @property
    def animal_slots(self) -> int:
        if not self.garden_open:
            return 0
        return sum(self.qualifying_months >= m for m in load_game()["garden"]["animal_slots_at_qualifying_months"])

    @property
    def really_bad(self) -> bool:
        return self.last_checkin is not None and is_really_bad(self.last_checkin)

    @property
    def plant_look(self) -> str:
        """normal / droop / rest (after 2 really bad months in a row: calm, I3)."""
        if not self.really_bad:
            return "normal"
        return "rest" if self.really_bad_in_a_row >= load_game()["really_bad"]["rest_after_months"] else "droop"

    @property
    def suggest_akpk(self) -> bool:
        return self.plant_look == "rest"

    @property
    def mood(self) -> str:
        if self.really_bad:
            return "concerned_hopeful"
        tier = self.last_checkin.health_tier if self.last_checkin else None
        return {"Healthy": "relaxed", "Coping": "calm", "Vulnerable": "focused"}.get(tier, "calm")

    @property
    def coin_jar(self) -> int:
        c = self.game_cushion or 0.0
        return sum(c >= t for t in load_game()["coin_jar_fills_at_cushion"])

    @property
    def savings_plant_stage(self) -> int:
        return sum(self.saved_months >= t for t in load_game()["savings_plant_stages_at_saved_months"])

    @property
    def costs_trusted(self) -> bool:
        v = load_game()["verification"]
        return sum(self._verified[-v["out_of_last_check_ins"]:]) >= v["trust_own_costs_after_verified"]

    def plant_stage(self, g: Growing) -> str:
        cfg = load_game()["growth"]
        if g.growing_days >= cfg["full_after_growing_days"]:
            return "full"
        return "young" if g.growing_days >= cfg["young_after_growing_days"] else "seedling"

    def tree_stage(self) -> int | None:
        if self.tree is None:
            return None
        cfg = load_game()["growth"]
        return min(cfg["tree_stages"] - 1, self.tree.growing_days // cfg["tree_stage_growing_days"])

    def bed(self) -> set[tuple[int, int]]:
        return bed_cells(self.garden_level, self.bed_step)


def is_really_bad(ci: CheckIn) -> bool:
    cfg = load_game()["really_bad"]
    if ci.band != cfg["band"]:
        return False
    high = (ci.forecast_probability is not None and ci.forecast_base_rate
            and ci.forecast_probability >= cfg["forecast_ratio"] * ci.forecast_base_rate)
    return bool(ci.shortfall or high)


# ---------------------------------------------------------------- garden geometry (shared with the art)
def bed_size(level: int, step: int = 0) -> tuple[int, int]:
    g = load_game()["garden"]
    if level < 1:
        return 0, 0
    k = min(step, len(g["bed_growth_after_g4"])) if level == 4 else 0
    return tuple(g["bed_growth_after_g4"][k - 1]) if k >= 1 else tuple(g["bed_size"][str(level)])


def bed_cells(level: int, step: int = 0) -> set[tuple[int, int]]:
    w, d = bed_size(level, step)
    x0, y0 = load_game()["garden"]["bed_back_cell"]
    return {(x0 + i, y0 + j) for i in range(w) for j in range(d)}


# ---------------------------------------------------------------- helpers
def _award(st: GameState, day: date, kind: str, points: int, ref: str = "") -> None:
    if points > 0:                                                   # G2: never negative
        st.points += points
        st.ledger.append(Award(day, kind, points, ref))


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_end(m: date) -> date:
    return (m.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _tiers(rate: float, low_rate: float, low: int, high_rate: float, high: int) -> tuple[int, str]:
    if rate >= high_rate:
        return high, "10"
    return (low, "5") if rate >= low_rate else (0, "")


def _protected_costs(st: GameState, prof: GameProfile, income: float) -> float:
    """The game cushion's monthly costs (G7)."""
    gc = load_game()["game_cushion"]
    declared = (prof.typical_monthly_costs if prof.typical_monthly_costs is not None
                else gc["floor_share_of_income_if_undeclared"] * income)
    own = sum(st._logged_costs) / len(st._logged_costs) if st._logged_costs else 0.0
    if st.costs_trusted:
        return max(own, declared, 1.0)                               # verified logging: own costs count
    plausible = gc["plausible_cost_floor"][prof.employment_type]["with_parents" if prof.lives_with_parents else "own"]
    seen = sum(st._outflows) / len(st._outflows) if st._outflows else 0.0
    return max(own, declared, plausible, seen, 1.0)                  # option 1 + S1


def protected_monthly_costs(st: GameState, prof: GameProfile) -> float:
    """The game cushion's monthly costs as of the latest check-in (the Future Self's room projection)."""
    ci = st.last_checkin
    income = ci.net_income if ci is not None and ci.net_income is not None else prof.declared_income
    return _protected_costs(st, prof, income)


def _goal(st: GameState, prof: GameProfile, month: date, income: float) -> float:
    gl = load_game()["goals"]
    amount, share = prof.savings_goal, prof.savings_goal_share
    for c in st._goal_changes:                                       # a change applies from the next month
        if (c.day.replace(day=1) + timedelta(days=32)).replace(day=1) <= month:
            amount, share = c.amount, c.share
    suggested = gl["suggested"][prof.employment_type]
    if prof.employment_type in gl["percent_of_month_income_for"]:    # I2: gig goals follow the month's income
        target = (share if share is not None else suggested["share"]) * income
    elif amount is not None:
        target = amount
    else:
        target = suggested.get("rm", suggested.get("share", 0) * income)
    return max(target, gl["min_share_of_income"] * income, gl["min_rm"])


# ---------------------------------------------------------------- steps of the replay
def _sign_up(st: GameState, prof: GameProfile) -> None:
    w = load_game()["welcome"]
    _award(st, prof.start, "welcome", w["checkin_points"], "sign-up")
    st.free_choices += w["free_choices"]
    st.game_cushion = st.prev_cushion = prof.onboarding_money / _protected_costs(st, prof, prof.declared_income)


def _saved(st: GameState, day: date, kind: str, points: int, ref: str) -> None:
    """A month's saving counts (now if verified, or confirmed a month later)."""
    _award(st, day, kind, points, ref)
    st.saved_months += 1
    st.saved_in_a_row += 1
    if st.saved_in_a_row >= load_game()["badges"]["steady_saver_months_in_a_row"]:
        st.badges.add("steady_saver")


def _resolve_pending(st: GameState, day: date, wealth: float, tol: float) -> None:
    """Last month's unverified progress counts if the money is still there (G6)."""
    p, st.pending = st.pending, None
    if p is None:
        return
    if wealth < p.wealth - tol:
        st.saved_in_a_row = 0
        return
    if p.saving_points:
        _saved(st, day, p.saving_kind, p.saving_points, p.ref)
    if p.goal_met:
        st.qualifying_months += 1


def _log_day(st: GameState, act: DayActivity | None, d: date) -> None:
    cfg = load_game()["streak"]
    if act and (act.entries > 0 or act.no_spend):
        st.streak += 1
    elif st.streak and st._rest_used.get(_monday(d), 0) < cfg["rest_days_per_week"]:
        st._rest_used[_monday(d)] = st._rest_used.get(_monday(d), 0) + 1
    else:
        st.streak = 0
    st.best_streak = max(st.best_streak, st.streak)
    for days, pts in cfg["milestone_points"].items():                # R2: points, once each
        if st.streak >= int(days) and days not in st._streak_rewards:
            st._streak_rewards.add(days)
            _award(st, d, "streak", pts, days)
    if st.streak >= load_game()["badges"]["honest_tracker_streak_days"]:
        st.badges.add("honest_tracker")


def _card(st: GameState, c: CardAnswer) -> None:
    week = _monday(c.day)
    if not c.skipped and week not in st._carded_weeks:
        st._carded_weeks.add(week)
        _award(st, c.day, "card", load_game()["points"]["card_answered"], week.isoformat())


def _check_in(st: GameState, prof: GameProfile, ci: CheckIn) -> None:
    cfg = load_game()
    p, v, gc = cfg["points"], cfg["verification"], cfg["game_cushion"]
    if ci.month in st._checkin_months:
        raise GameRuleError(f"already checked in for {ci.month:%B %Y}")
    if ci.month < prof.start.replace(day=1):                         # G11: nothing before sign-up
        raise GameRuleError("no check-ins for months before you joined")
    if not (_month_end(ci.month) <= ci.on <= _month_end(ci.month) + timedelta(days=cfg["checkin_grace_days"])):
        raise GameRuleError("a month can be checked in from its last day until a week after it")
    st._checkin_months.add(ci.month)
    ref = ci.month.isoformat()
    income = ci.net_income if ci.net_income is not None else prof.declared_income
    tol = max(v["tolerance_rm"], v["tolerance_income_share"] * income)
    # change in the user's own money (G4): transfers between pockets net to zero
    wealth = ci.counted_money + ci.other_money
    d_wealth = (wealth - st.money - st.other
                + ci.epf_voluntary * (1 - cfg["epf"]["fleksibel_share"]) - ci.epf_compulsory_to_fleksibel)
    d_debt = ci.total_debt - st.debt
    new_borrowing = d_debt + ci.logged_debt_paid if d_debt > 0 else 0.0   # what was paid off was re-borrowed
    # option 2 (R1): does the logging explain the month?
    verified = (ci.logged_in + ci.logged_out > 0 and ci.logged_in >= income - tol
                and abs(d_wealth - (ci.logged_in - ci.logged_out)) <= tol)
    st._verified.append(verified)
    _award(st, ci.on, "checkin", p["checkin"], ref)
    if verified:
        _award(st, ci.on, "verified", p["verified"], ref)
    _resolve_pending(st, ci.on, wealth, tol)
    # saving (G5): money set aside minus new borrowing; tier shares use the larger of the confirmed
    # and the declared income (G13, I1), so reporting less income can't lift a tier
    saving = d_wealth - new_borrowing
    tier_income = max(income, prof.declared_income)
    rate = saving / tier_income if tier_income > 0 else 0.0
    saving_points, tier = _tiers(rate, p["saved_low_rate"], p["saved_low"], p["saved_high_rate"], p["saved_high"])
    if not saving_points:
        st.saved_in_a_row = 0
    elif verified:
        _saved(st, ci.on, f"saved_{tier}", saving_points, ref)
    # debt paid down to a NEW LOW, as far as logged payments in a verified month show (G5, R5)
    if verified and ci.total_debt < st.lowest_debt:
        drop = min(st.lowest_debt - ci.total_debt, ci.logged_debt_paid)
        st.lowest_debt = ci.total_debt
        pts, debt_tier = _tiers(drop / tier_income if tier_income > 0 else 0.0,
                                p["debt_low_rate"], p["debt_low"], p["debt_high_rate"], p["debt_high"])
        _award(st, ci.on, f"debt_{debt_tier}", pts, ref)
    if ci.bills_on_time:
        _award(st, ci.on, "bills", p["bills_on_time"], ref)
    # borrowed cash still held never unlocks anything (S2)
    st.borrowed_cash = max(0.0, st.borrowed_cash + min(new_borrowing, max(0.0, d_wealth)) - max(0.0, -d_debt))
    # game cushion (G7, S1)
    window = gc["logged_cost_window_months"]
    st._outflows = (st._outflows + [tier_income - saving])[-window:]     # G13: spent = income − saving
    if verified:
        st._logged_costs = (st._logged_costs + [ci.logged_costs])[-window:]
    costs = _protected_costs(st, prof, income)
    st.game_cushion = ci.counted_money / costs
    unlock_cushion = max(0.0, ci.counted_money - st.borrowed_cash) / costs
    # unlocks (G6): verified now, or held since the last check-in
    confirmed = unlock_cushion if verified else min(unlock_cushion, st.prev_cushion or 0.0)
    st.prev_cushion = unlock_cushion
    kept = [(float(m), pts) for m, pts in p["cushion_kept"].items() if confirmed >= float(m)]
    if kept:                                                         # R4: keeping a cushion is health
        m, pts = max(kept)
        _award(st, ci.on, f"cushion_{m:g}", pts, ref)
    for m, pts in sorted(p["milestones"].items(), key=lambda kv: float(kv[0])):
        if confirmed >= float(m) and m not in st.milestones:
            st.milestones.add(m)
            _award(st, ci.on, "milestone", pts, m)
    st.best_cushion = max(st.best_cushion, confirmed)
    st.room_level = max([1] + [int(lv) for lv, c in cfg["room_level_at_cushion"].items() if st.best_cushion >= c])
    if st.best_cushion >= cfg["badges"]["cushion_builder_months"]:
        st.badges.add("cushion_builder")
    # garden (G8): opens after 3 check-ins; grows with goal met or 1+ month held
    progress = d_wealth - max(d_debt, -ci.logged_debt_paid)          # debt paid down counts as far as logged
    gig_goal = prof.employment_type in cfg["goals"]["percent_of_month_income_for"]   # I2: follows the month
    goal = _goal(st, prof, ci.month, income if gig_goal else tier_income)
    goal_met = progress >= goal
    st.check_ins += 1
    qualifying = pending_goal = False
    if not st.garden_open and st.check_ins >= cfg["garden"]["opens_after_check_ins"]:
        st.garden_opened_on = ci.on
    elif st.garden_open:
        if confirmed >= cfg["garden"]["qualifying_cushion_months"] or (goal_met and verified):
            st.qualifying_months += 1
            qualifying = True
        else:
            pending_goal = goal_met
    if not verified and (saving_points or pending_goal):          # waits for the next check-in (G6)
        st.pending = Pending(ref, wealth, f"saved_{tier}", saving_points, pending_goal)
    # really bad months in a row (I3)
    st.really_bad_in_a_row = st.really_bad_in_a_row + 1 if is_really_bad(ci) else 0
    st.months.append(MonthResult(ci.month, verified, saving, progress, goal, goal_met, st.game_cushion, qualifying))
    st.money, st.other, st.debt = ci.counted_money, ci.other_money, ci.total_debt
    st.last_checkin = ci


def _grow(st: GameState) -> None:
    """One day passes: planted things grow unless the latest month is really bad (G10)."""
    if st.really_bad:
        return
    for g in st.plants.values():
        g.growing_days += 1
    if st.tree is not None:
        st.tree.growing_days += 1


def _spend_choice(st: GameState) -> None:
    if st.choices_available < 1:                                     # G9
        raise GameRuleError("no choice available yet: every 200 points gives one")
    st.choices_used += 1


def _apply(st: GameState, a: Action) -> None:
    cfg = load_game()
    g = cfg["garden"]
    if isinstance(a, Plant):
        if not st.garden_open:
            raise GameRuleError("the garden isn't open yet")
        if a.cell not in st.bed():
            raise GameRuleError("plants go in the flower bed")
        if a.cell in st.plants:
            raise GameRuleError("something is already growing there")
        if a.plant not in g["plants"]:
            raise GameRuleError(f"unknown plant: {a.plant}")
        if g["plants"][a.plant] > st.plant_tier:
            raise GameRuleError("that plant unlocks with more months of keeping your buffer")
        from_box = next((s for s in st.seed_box if s.kind == a.plant), None)
        if from_box is not None:
            st.seed_box.remove(from_box)
            st.plants[a.cell] = from_box
        else:
            _spend_choice(st)
            st.plants[a.cell] = Growing(a.plant)
    elif isinstance(a, Dig):
        if a.cell not in st.plants:
            raise GameRuleError("nothing planted there")
        st.seed_box.append(st.plants.pop(a.cell))
    elif isinstance(a, BuyTree):
        if st.garden_level < g["tree_from_garden_level"]:
            raise GameRuleError("the tree needs the bigger garden (G4)")
        if st.tree is not None:
            raise GameRuleError("the garden already has its tree")
        _spend_choice(st)
        st.tree = Growing("tree")
    elif isinstance(a, Decorate):
        room, garden = cfg["decorations"]["room"], cfg["decorations"]["garden"]
        if a.item not in room + garden:
            raise GameRuleError(f"unknown decoration: {a.item}")
        if a.item in garden and not st.garden_open:
            raise GameRuleError("the garden isn't open yet")
        if a.item in st.decorations:
            raise GameRuleError("you already have that one")
        if a.spot in st.decorations.values():
            raise GameRuleError("that spot is taken")
        _spend_choice(st)
        st.decorations[a.item] = a.spot
    elif isinstance(a, MoveDecoration):
        if a.item not in st.decorations:
            raise GameRuleError("you don't have that decoration")
        if a.spot in st.decorations.values() and st.decorations[a.item] != a.spot:
            raise GameRuleError("that spot is taken")
        st.decorations[a.item] = a.spot
    elif isinstance(a, ChooseAnimal):
        if a.kind not in g["animals"]:
            raise GameRuleError(f"unknown animal: {a.kind}")
        if st.animal_slots_used >= st.animal_slots:
            raise GameRuleError("no animal slot open yet")
        if a.kind in st.animals:
            raise GameRuleError("you already have that animal; add another with a choice")
        st.animals[a.kind] = 1
        st.animal_slots_used += 1
    elif isinstance(a, AddAnimal):
        if a.kind not in st.animals:
            raise GameRuleError("choose this animal at an animal slot first")
        if st.animals[a.kind] >= g["max_animals_per_type"]:
            raise GameRuleError(f"at most {g['max_animals_per_type']} of each animal")
        _spend_choice(st)
        st.animals[a.kind] += 1
    else:
        raise TypeError(f"not an action: {a!r}")


def replay(profile: GameProfile, until: date, days: list[DayActivity] = (), checkins: list[CheckIn] = (),
           cards: list[CardAnswer] = (), actions: list[Action] = (), goal_changes: list[GoalChange] = (),
           strict: bool = True, observe=None) -> GameState:
    """The user's game state at the end of `until`, from their whole history (G1). With
    strict=False, events the rules reject are skipped and listed in state.rejected, so a bad row
    in the database can never break a user's game (C4). `observe(day, state)`, if given, is called
    at the end of every day (the simulation takes month-end snapshots with it)."""
    def guard(fn, event):
        try:
            fn()
        except GameRuleError as e:
            if strict:
                raise
            st.rejected.append((event, str(e)))

    by_day: dict[date, DayActivity] = {}
    for a in days:
        if a.day in by_day:
            raise ValueError(f"two activity records for {a.day}")
        by_day[a.day] = a
    events: dict[date, list] = {}
    for c in cards:
        events.setdefault(c.day, []).append(c)
    for ci in sorted(checkins, key=lambda c: (c.on, c.month)):      # catching up: oldest month first
        events.setdefault(ci.on, []).append(ci)
    acts: dict[date, list[Action]] = {}
    for a in actions:
        acts.setdefault(a.day, []).append(a)
    changes = sorted(goal_changes, key=lambda c: c.day)
    st = GameState(money=profile.onboarding_money, other=profile.onboarding_other_money,
                   debt=profile.onboarding_debt, lowest_debt=profile.onboarding_debt)
    _sign_up(st, profile)
    d = profile.start
    while d <= until:
        st._goal_changes = [c for c in changes if c.day <= d]
        _log_day(st, by_day.get(d), d)
        for e in events.get(d, []):
            if isinstance(e, CardAnswer):
                _card(st, e)
            else:
                guard(lambda e=e: _check_in(st, profile, e), e)
        _grow(st)
        for a in acts.get(d, []):
            guard(lambda a=a: _apply(st, a), a)
        if observe is not None:
            observe(d, st)
        d += timedelta(days=1)
    return st
