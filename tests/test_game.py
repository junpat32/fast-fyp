"""T-14b: the game rules (engine/game.py) against docs/game_design.md v1.6 and shared/game.json (D-75)."""
from datetime import date, timedelta

import pytest

from engine.game import (AddAnimal, BuyTree, CardAnswer, CheckIn, ChooseAnimal, DayActivity, Decorate, Dig,
                         GameProfile, GameRuleError, GoalChange, MoveDecoration, Plant, bed_cells, load_game, replay)

START = date(2026, 1, 1)
INCOME = 3000.0
PROFILE = GameProfile(start=START, employment_type="employee", declared_income=INCOME, onboarding_money=0.0,
                      typical_monthly_costs=2400.0)


def month(k: int) -> date:
    """First day of the k-th month of the user's life (k = 1 is January 2026)."""
    return date(2026 + (k - 1) // 12, (k - 1) % 12 + 1, 1)


def end_of(k: int) -> date:
    return month(k + 1) - timedelta(days=1)


def check(k: int, money: float, **kw) -> CheckIn:
    """A check-in on the month's last day; unverified unless the logging is given."""
    defaults = dict(total_debt=0.0, bills_on_time=True, logged_costs=2400.0)
    return CheckIn(month=month(k), on=end_of(k), counted_money=money, **{**defaults, **kw})


def honest(k: int, money: float, prev: float, **kw) -> CheckIn:
    """Logs the salary (and any extra money in) and everything that left, so the month adds up."""
    logged_in = kw.pop("logged_in", INCOME)
    return check(k, money, **{"logged_in": logged_in, "logged_out": logged_in - (money - prev), **kw})


def saver(months: int, per_month=300.0, start=0.0, **kw) -> list[CheckIn]:
    """Saves RM300 (10%) a month and logs honestly."""
    return [honest(k, start + per_month * k, start + per_month * (k - 1), **kw) for k in range(1, months + 1)]


def every_day(until: date, entries=3) -> list[DayActivity]:
    days, d = [], START
    while d <= until:
        days.append(DayActivity(d, entries=entries))
        d += timedelta(days=1)
    return days


def kinds(st, k=None) -> list[str]:
    return [a.kind for a in st.ledger if k is None or a.ref == month(k).isoformat()]


# ---- points (§3) and the reward order (G12, R6)
def test_a_good_month_check_in_verified_saving_bills():
    st = replay(PROFILE, end_of(1), checkins=saver(1))
    assert kinds(st, 1) == ["checkin", "verified", "saved_10", "bills"] and st.points == 20 + 210


@pytest.mark.parametrize("saved, kind", [(300, "saved_10"), (150, "saved_5"), (100, None)])
def test_saving_tiers(saved, kind):
    st = replay(PROFILE, end_of(1), checkins=[honest(1, saved, 0)])
    assert [x for x in kinds(st, 1) if x.startswith("saved")] == ([kind] if kind else [])


def test_tiers_use_the_larger_of_confirmed_and_declared_income():
    """G13 (I1, D-89): RM150 saved is 5% of the declared RM3,000. Confirming only RM1,500 (and logging
    to match) would make it 10%, but the tier stays at 5%. A real rise counts in full."""
    hidden = honest(1, 150, 0, logged_in=1500.0, net_income=1500.0)
    assert [x for x in kinds(replay(PROFILE, end_of(1), checkins=[hidden]), 1) if x.startswith("saved")] == ["saved_5"]
    rise = honest(1, 400, 0, logged_in=4000.0, net_income=4000.0)                     # 10% of RM4,000
    assert [x for x in kinds(replay(PROFILE, end_of(1), checkins=[rise]), 1) if x.startswith("saved")] == ["saved_10"]


def test_welcome_points_and_choice():
    st = replay(PROFILE, START)
    assert st.points == 20 and st.choices_earned == 1 and kinds(st) == ["welcome"]


def test_logged_entries_earn_nothing_so_padding_ties_at_best():
    """G3 (P1): 40 entries a day earn exactly what 1 entry a day earns: the streak points."""
    one = replay(PROFILE, START + timedelta(days=40), days=every_day(START + timedelta(days=40), entries=1))
    forty = replay(PROFILE, START + timedelta(days=40), days=every_day(START + timedelta(days=40), entries=40))
    assert one.points == forty.points == 20 + 20 + 40
    assert kinds(forty) == ["welcome", "streak", "streak"]


def test_streak_milestones_are_points_once_each():
    """R2: days 7, 30, 100 give +20, +40, +60 once; only the welcome choice is free."""
    end = START + timedelta(days=120)
    st = replay(PROFILE, end, days=every_day(end, entries=1))
    assert [(a.ref, a.points) for a in st.ledger if a.kind == "streak"] == [("7", 20), ("30", 40), ("100", 60)]
    assert st.free_choices == 1


def test_cards_once_a_week_and_skipping_costs_nothing():
    monday = date(2026, 1, 5)
    st = replay(PROFILE, monday + timedelta(days=13), cards=[
        CardAnswer(monday), CardAnswer(monday + timedelta(days=2)), CardAnswer(monday + timedelta(days=7), skipped=True)])
    assert st.points == 20 + 5


def test_points_never_negative_even_in_a_terrible_month():
    st = replay(PROFILE, end_of(3), checkins=[check(1, 900), check(2, 0, bills_on_time=False, band="RED", shortfall=True)])
    assert all(a.points > 0 for a in st.ledger) and st.points >= 0


def test_reward_order_in_the_config():
    """R6: the most a month can give: check-in < logging < good financial health, and keeping a
    built cushion (with bills on time) beats a verified month, so healthy users earn most."""
    cfg = load_game()
    p, streak = cfg["points"], cfg["streak"]["milestone_points"]
    window = max(sum(v for e, v in streak.items() if int(d) - 30 <= int(e) <= int(d)) for d in streak)
    checkin = p["checkin"]
    logging_routine, logging_max = p["verified"], p["verified"] + window
    learning_max = 5 * p["card_answered"]
    health_max = p["bills_on_time"] + p["saved_high"] + p["debt_high"] + max(p["cushion_kept"].values())
    assert checkin < logging_routine and learning_max < logging_routine
    assert logging_max < health_max
    assert p["bills_on_time"] + min(p["cushion_kept"].values()) > logging_routine
    assert p["debt_high"] > p["saved_high"] and p["debt_low"] > p["saved_low"]          # debt payoff counts more
    assert cfg["reward_tiers"]["order"] == ["checkin", "logging", "health"]


def test_reward_order_over_an_honest_year():
    end = end_of(12)
    cards = [CardAnswer(d.day) for d in every_day(end) if d.day.weekday() == 0]
    st = replay(PROFILE, end, days=every_day(end, entries=2), checkins=saver(12), cards=cards)
    t = st.points_by_tier()
    assert t["checkin"] < t["logging"] < t["health"]
    assert t["learning"] < t["logging"]


def test_keeping_a_cushion_is_rewarded_every_month():
    """R4: someone with 3 months' cushion who saves nothing more still earns most from health."""
    rich = GameProfile(START, "employee", INCOME, onboarding_money=7200.0, typical_monthly_costs=2400.0)
    st = replay(rich, end_of(2), checkins=[honest(1, 7200, 7200), honest(2, 7200, 7200)])
    month2 = [a for a in st.ledger if a.ref == month(2).isoformat()]
    assert [(a.kind, a.points) for a in month2] == [("checkin", 20), ("verified", 40), ("bills", 30), ("cushion_3", 80)]


# ---- verification (option 2, R1)
def test_verified_when_the_logging_explains_the_month():
    assert replay(PROFILE, end_of(1), checkins=saver(1)).months[0].verified


@pytest.mark.parametrize("kw, why", [
    (dict(), "logged nothing"),
    (dict(logged_in=1500.0, logged_out=1200.0), "salary not logged"),
    (dict(logged_in=3000.0, logged_out=3500.0), "padded with made-up spending"),
    (dict(logged_in=3000.0, logged_out=1900.0), "spending hidden"),
])
def test_not_verified(kw, why):
    st = replay(PROFILE, end_of(1), checkins=[check(1, 300, **kw)])
    assert not st.months[0].verified, why
    assert "verified" not in kinds(st)


def test_small_differences_are_tolerated():
    """Unlogged cash up to max(RM100, 10% of income) still counts as adding up."""
    st = replay(PROFILE, end_of(1), checkins=[check(1, 300, logged_in=3000.0, logged_out=2950.0)])
    assert st.months[0].verified


# ---- money sections (C6, G4)
def test_moving_money_between_pockets_is_not_saving():
    p = GameProfile(START, "employee", INCOME, onboarding_money=1000.0, onboarding_other_money=5000.0,
                    typical_monthly_costs=2400.0)
    st = replay(p, end_of(1), checkins=[check(1, 2000, other_money=4000.0, logged_in=3000.0, logged_out=3000.0)])
    assert st.months[0].saving == 0 and st.months[0].verified
    assert not [x for x in kinds(st) if x.startswith("saved")]


def test_voluntary_epf_is_saving_and_compulsory_epf_is_not():
    """RM300 voluntary EPF: 10% lands in Fleksibel (counted money), 90% in the other accounts."""
    st = replay(PROFILE, end_of(1), checkins=[check(1, 30, epf_voluntary=300.0, logged_in=3000.0, logged_out=2700.0)])
    assert st.months[0].saving == pytest.approx(300) and "saved_10" in kinds(st) and st.months[0].verified
    st = replay(PROFILE, end_of(1), checkins=[check(1, 90, epf_compulsory_to_fleksibel=90.0,
                                                    logged_in=3000.0, logged_out=3000.0)])
    assert st.months[0].saving == pytest.approx(0)


# ---- borrowing and debt (C2, R5)
DEBTOR = GameProfile(START, "employee", INCOME, onboarding_money=0.0, onboarding_debt=10000.0, typical_monthly_costs=2400.0)


def test_borrowing_is_never_saving():
    st = replay(DEBTOR, end_of(1), checkins=[check(1, 1000, total_debt=11000.0, logged_in=4000.0, logged_out=3000.0)])
    assert st.months[0].verified and st.months[0].saving == 0
    assert not [x for x in kinds(st) if x.startswith(("saved", "debt"))]


def test_paying_debt_down_earns_more_than_saving_the_same():
    st = replay(DEBTOR, end_of(1), checkins=[check(1, 0, total_debt=9700.0, logged_in=3000.0, logged_out=3000.0,
                                                   logged_debt_paid=300.0)])
    assert kinds(st, 1) == ["checkin", "verified", "debt_10", "bills"]
    assert st.months[0].progress == pytest.approx(300)                    # counts toward the garden goal


def test_borrow_and_repay_earns_nothing():
    ci = [check(1, 1000, total_debt=11000.0, logged_in=4000.0, logged_out=3000.0),
          check(2, 0, total_debt=10000.0, logged_in=3000.0, logged_out=4000.0, logged_debt_paid=1000.0)]
    st = replay(DEBTOR, end_of(2), checkins=ci)
    assert not [x for x in kinds(st) if x.startswith(("saved", "debt"))]


def test_debt_points_only_as_far_as_logged_payments_show():
    """R5: a fake drop (or a fake debt declared at sign-up) earns only what was really paid."""
    fake = check(1, 0, total_debt=5000.0, logged_in=3000.0, logged_out=3000.0, logged_debt_paid=100.0)
    st = replay(DEBTOR, end_of(1), checkins=[fake])
    assert "debt_10" not in kinds(st) and "debt_5" not in kinds(st)         # RM100 is 3.3% of income
    unproven = check(1, 0, total_debt=9700.0)                              # unverified month
    st = replay(DEBTOR, end_of(2), checkins=[unproven, check(2, 0, total_debt=9400.0, logged_in=3000.0,
                                                              logged_out=3000.0, logged_debt_paid=300.0)])
    assert [x for x in kinds(st) if x.startswith("debt")] == ["debt_10"]     # month 2 only
    assert st.lowest_debt == 9400


def test_no_new_low_no_debt_points():
    ci = [check(1, 0, total_debt=9700.0, logged_in=3000.0, logged_out=3000.0, logged_debt_paid=300.0),
          check(2, 0, total_debt=9900.0, logged_in=3200.0, logged_out=3200.0),          # took a small BNPL
          check(3, 0, total_debt=9800.0, logged_in=3000.0, logged_out=3000.0, logged_debt_paid=100.0)]
    st = replay(DEBTOR, end_of(3), checkins=ci)
    assert [a.ref for a in st.ledger if a.kind.startswith("debt")] == [month(1).isoformat()]


# ---- game cushion and levels (§7, §7a, G6, G7)
def test_plausibility_floor_until_the_users_own_costs_are_trusted():
    low = GameProfile(START, "employee", 1000.0, onboarding_money=0.0, typical_monthly_costs=300.0)
    st = replay(low, end_of(1), checkins=[check(1, 910, logged_costs=0.0, net_income=1000.0)])
    assert st.game_cushion == pytest.approx(1.0)                           # employee living alone: RM910
    # G13: with RM3,000 declared, a RM1,000 month counts as RM3,000 for "what was spent" until trusted
    declared_more = GameProfile(START, "employee", INCOME, onboarding_money=0.0, typical_monthly_costs=300.0)
    st = replay(declared_more, end_of(1), checkins=[check(1, 910, logged_costs=0.0, net_income=1000.0)])
    assert st.game_cushion == pytest.approx(910 / (INCOME - 910))
    trusted = [honest(1, 300, 0, logged_costs=300.0), honest(2, 600, 300, logged_costs=300.0)]
    st = replay(low, end_of(2), checkins=trusted)
    assert st.costs_trusted and st.game_cushion == pytest.approx(2.0)      # own verified costs used
    with_parents = GameProfile(START, "student", 300.0, onboarding_money=0.0, typical_monthly_costs=100.0,
                               lives_with_parents=True)
    st = replay(with_parents, end_of(1), checkins=[check(1, 220, logged_costs=0.0, net_income=300.0)])
    assert st.game_cushion == pytest.approx(1.0)


def test_hiding_costs_makes_the_cushion_smaller_not_bigger():
    """S1: until logging is verified, costs are at least what the balances show was spent."""
    under = GameProfile(START, "employee", INCOME, onboarding_money=0.0, typical_monthly_costs=900.0)
    hider = [check(k, 250 * k, logged_costs=250.0, logged_in=INCOME, logged_out=1000.0) for k in range(1, 4)]
    st = replay(under, end_of(3), checkins=hider)
    assert not st.costs_trusted and st.game_cushion == pytest.approx(750 / 2750)
    honest_st = replay(PROFILE, end_of(3), checkins=saver(3, per_month=250.0, logged_costs=2250.0))
    assert honest_st.game_cushion > st.game_cushion


def test_borrowed_cash_never_unlocks_levels():
    """S2: RM7,200 borrowed and kept in the bank is real money, but it unlocks nothing."""
    loan = check(1, 7200, total_debt=7200.0, logged_in=10200.0, logged_out=3000.0)
    st = replay(PROFILE, end_of(2), checkins=[loan, honest(2, 7200, 7200, total_debt=7200.0)])
    assert st.months[0].verified and st.game_cushion == pytest.approx(3.0)
    assert st.room_level == 1 and not st.milestones
    repaid = honest(3, 300, 7200, total_debt=0.0, logged_in=3000.0, logged_out=9900.0, logged_debt_paid=7200.0)
    st = replay(PROFILE, end_of(3), checkins=[loan, honest(2, 7200, 7200, total_debt=7200.0), repaid])
    assert st.borrowed_cash == 0 and st.room_level == 1


def test_unverified_saving_waits_for_the_next_check_in():
    """G6: unverified saving points count a month later if the money is still there."""
    st = replay(PROFILE, end_of(1), checkins=[check(1, 300)])
    assert not [x for x in kinds(st) if x.startswith("saved")] and st.pending is not None
    st = replay(PROFILE, end_of(2), checkins=[check(1, 300), check(2, 300)])
    assert [(a.kind, a.ref) for a in st.ledger if a.kind.startswith("saved")] == [("saved_10", month(1).isoformat())]
    spike = replay(PROFILE, end_of(2), checkins=[check(1, 9000), check(2, 300)])
    assert not [x for x in kinds(spike) if x.startswith("saved")]


def test_undeclared_costs_use_60_percent_of_income():
    p = GameProfile(START, "employee", INCOME, onboarding_money=0.0)
    st = replay(p, end_of(1), checkins=[check(1, 1800, logged_costs=0.0)])
    assert st.game_cushion == pytest.approx(1.0)


def test_unverified_spike_unlocks_nothing_until_it_holds():
    """C1: a sudden unexplained RM7,200 doesn't unlock levels; still there next month, it does."""
    st = replay(PROFILE, end_of(1), checkins=[check(1, 7200)])
    assert st.room_level == 1 and not st.milestones and "cushion_3" not in kinds(st)
    st = replay(PROFILE, end_of(2), checkins=[check(1, 7200), check(2, 7200)])
    assert st.room_level == 5 and st.milestones == {"0.5", "1", "2", "3"}
    gone = replay(PROFILE, end_of(2), checkins=[check(1, 7200), check(2, 0)])
    assert gone.room_level == 1 and not gone.milestones


def test_verified_progress_unlocks_straight_away():
    bonus = honest(1, 2400, 0, logged_in=5100.0, logged_out=2700.0)       # a logged RM2,100 bonus
    st = replay(PROFILE, end_of(1), checkins=[bonus])
    assert st.months[0].verified and st.room_level == 3 and "1" in st.milestones


def test_milestones_once_and_room_level_never_goes_down():
    ci = [honest(1, 1200, 0, logged_in=4200.0), honest(2, 2400, 1200, logged_in=4200.0), honest(3, 100, 2400)]
    st = replay(PROFILE, end_of(3), checkins=ci)
    assert [(a.kind, a.ref) for a in st.ledger if a.kind == "milestone"] == [("milestone", "0.5"), ("milestone", "1")]
    assert st.room_level == 3 and st.game_cushion < 0.1                   # level kept after the drop
    assert "cushion_builder" in st.badges


def test_room_levels_follow_the_best_confirmed_cushion():
    levels = [replay(PROFILE, end_of(1), checkins=[honest(1, 2400 * c, 0, logged_in=INCOME + 2400 * c)]).room_level
              for c in (0.4, 0.5, 1, 2, 3)]
    assert levels == [1, 2, 3, 4, 5]


# ---- garden (§8, P2)
def test_garden_opens_after_3_check_ins_for_everyone():
    """Even someone who saves nothing gets the garden on their 3rd monthly check-in."""
    flat = [honest(k, 0, 0) for k in range(1, 4)]
    assert not replay(PROFILE, end_of(2), checkins=flat[:2]).garden_open
    st = replay(PROFILE, end_of(3), checkins=flat)
    assert st.garden_open and st.qualifying_months == 0 and st.garden_level == 1


def test_qualifying_by_own_goal_or_by_cushion():
    st = replay(PROFILE, end_of(5), checkins=saver(5))                      # 10% goal met in months 4, 5
    assert st.qualifying_months == 2 and st.months[-1].goal == pytest.approx(300)
    rich = GameProfile(START, "employee", INCOME, onboarding_money=2400.0, typical_monthly_costs=2400.0)
    st = replay(rich, end_of(5), checkins=[honest(k, 2400, 2400) for k in range(1, 6)])
    assert st.qualifying_months == 2                                        # saves nothing, but holds 1 month


@pytest.mark.parametrize("prof, income, saved, met", [
    (GameProfile(START, "student", 800.0, 0.0), 800.0, 30.0, True),        # suggested RM30
    (GameProfile(START, "student", 800.0, 0.0), 800.0, 20.0, False),
    (GameProfile(START, "gig", 2000.0, 0.0), 2600.0, 130.0, True),          # 5% of this month's RM2,600
    (GameProfile(START, "gig", 2000.0, 0.0), 2600.0, 120.0, False),
    (GameProfile(START, "student", 300.0, 0.0, savings_goal=1.0), 300.0, 10.0, True),   # minimum RM10
    (GameProfile(START, "student", 300.0, 0.0, savings_goal=1.0), 300.0, 9.0, False),
    (GameProfile(START, "employee", 4000.0, 0.0, savings_goal=20.0), 4000.0, 79.0, False),  # minimum 2% = RM80
])
def test_personal_goals(prof, income, saved, met):
    ci = [honest(k, saved * k, saved * (k - 1), net_income=income, logged_in=income,
                 logged_out=income - saved, logged_costs=100.0) for k in range(1, 5)]
    st = replay(prof, end_of(4), checkins=ci)
    assert st.months[-1].goal_met is met and (st.qualifying_months == 1) is met


def test_goal_change_applies_from_next_month():
    p = GameProfile(START, "employee", INCOME, 0.0, typical_monthly_costs=2400.0, savings_goal=300.0)
    ci = [honest(k, 200 * k, 200 * (k - 1)) for k in range(1, 6)]
    st = replay(p, end_of(5), checkins=ci, goal_changes=[GoalChange(month(4) + timedelta(days=3), amount=200.0)])
    assert [m.goal_met for m in st.months] == [False, False, False, False, True]


def test_bad_month_pauses_never_resets():
    ci = saver(6) + [honest(7, 1700, 1800), honest(8, 2000, 1700)]
    st = replay(PROFILE, end_of(8), checkins=ci)
    assert [m.qualifying for m in st.months] == [False] * 3 + [True] * 3 + [False, True]
    assert st.qualifying_months == 4


def test_no_checkin_no_qualifying_month():
    st = replay(PROFILE, end_of(14), checkins=saver(10))
    assert st.qualifying_months == 7


@pytest.mark.parametrize("q, level, tier, slots", [(0, 1, 1, 0), (2, 2, 1, 1), (4, 3, 2, 1), (6, 4, 2, 2),
                                                   (12, 4, 3, 2), (18, 4, 3, 3), (24, 4, 4, 3)])
def test_unlock_schedule(q, level, tier, slots):
    st = replay(PROFILE, end_of(3 + q), checkins=saver(3 + q))
    assert (st.qualifying_months, st.garden_level, st.plant_tier, st.animal_slots) == (q, level, tier, slots)


def test_bed_grows_to_full_size():
    st = replay(PROFILE, end_of(13), checkins=saver(13))
    assert st.bed_step == 4 and len(st.bed()) == 5 * 6


# ---- time rules (C3, C4)
@pytest.mark.parametrize("ci, why", [
    (CheckIn(month(1), month(2) + timedelta(days=7), 300, 0, True), "a week after"),     # day 8 after: too late
    (CheckIn(month(2), month(1) + timedelta(days=27), 300, 0, True), "last day"),        # before the month starts
    (CheckIn(month(1), month(1) + timedelta(days=29), 300, 0, True), "last day"),        # 30 Jan: not over yet
    (CheckIn(date(2025, 12, 1), month(1) + timedelta(days=3), 300, 0, True), "before you joined"),
], ids=["too-late", "too-early", "before-last-day", "before-sign-up"])
def test_checkin_time_window(ci, why):
    with pytest.raises(GameRuleError, match=why):
        replay(PROFILE, end_of(2), checkins=[ci])


@pytest.mark.parametrize("on", [date(2026, 1, 31), date(2026, 2, 1), date(2026, 2, 7)])
def test_a_month_can_be_checked_in_from_its_last_day_for_a_week(on):
    st = replay(PROFILE, end_of(2), checkins=[CheckIn(month(1), on, 300, 0, True)])
    assert st.check_ins == 1


def test_one_checkin_per_month():
    with pytest.raises(GameRuleError, match="already"):
        replay(PROFILE, end_of(1), checkins=[check(1, 300), check(1, 400)])


def test_non_strict_replay_skips_invalid_rows():
    """C4: a bad row in the database never breaks the user's game."""
    ci = saver(2) + [CheckIn(date(2025, 11, 1), month(2) + timedelta(days=2), 9999, 0, True)]
    st = replay(PROFILE, end_of(2), checkins=ci, actions=[Plant(end_of(2), (0, 0), "serai")], strict=False)
    assert st.check_ins == 2 and len(st.rejected) == 2 and not st.plants


def test_catch_up_checkins_apply_oldest_month_first():
    late = month(3) + timedelta(days=5)
    ci = [CheckIn(month(2), late, 600, 0, True, logged_in=3000, logged_out=2700),
          CheckIn(month(1), month(2) + timedelta(days=5), 300, 0, True, logged_in=3000, logged_out=2700)]
    st = replay(PROFILE, late, checkins=ci)
    assert [m.month for m in st.months] == [month(1), month(2)]
    assert [x for x in kinds(st) if x.startswith("saved")] == ["saved_10", "saved_10"]


# ---- choices and planting (D-69, D-74)
def rich_history(k: int):
    """Logs every day and saves 10% for k months."""
    return dict(days=every_day(end_of(k)), checkins=saver(k))


def test_choices_earned_every_200_points_plus_the_welcome_choice():
    st = replay(PROFILE, end_of(12), **rich_history(12))
    assert st.choices_earned == st.points // 200 + 1 and st.choices_available == st.choices_earned


def test_planting_rules():
    k = 5                                                                   # garden open, G2, tier 1
    cell = min(bed_cells(2))
    st = replay(PROFILE, end_of(k), **rich_history(k), actions=[Plant(end_of(k), cell, "serai")])
    assert st.garden_level == 2 and st.plants[cell].kind == "serai" and st.choices_used == 1
    bad = [(Plant(end_of(k), cell, "orchid"), "unlocks"),
           (Plant(end_of(k), (0, 0), "serai"), "flower bed"),
           (Plant(end_of(k), (99, 99), "durian"), "flower bed")]
    for action, why in bad:
        with pytest.raises(GameRuleError, match=why):
            replay(PROFILE, end_of(k), **rich_history(k), actions=[action])
    with pytest.raises(GameRuleError, match="already growing"):
        replay(PROFILE, end_of(k), **rich_history(k),
               actions=[Plant(end_of(k), cell, "serai"), Plant(end_of(k), cell, "chilli")])
    with pytest.raises(GameRuleError, match="isn't open"):
        replay(PROFILE, end_of(2), **rich_history(2), actions=[Plant(end_of(2), cell, "serai")])


def test_no_choice_no_planting():
    """G9: once every choice is spent, nothing more unlocks until more points come."""
    k = 5
    available = replay(PROFILE, end_of(k), checkins=saver(k)).choices_available
    items = (load_game()["decorations"]["room"] + load_game()["decorations"]["garden"])[:available]
    spend = [Decorate(end_of(k), item, f"spot:{i}") for i, item in enumerate(items)]
    st = replay(PROFILE, end_of(k), checkins=saver(k), actions=spend)
    assert st.choices_available == 0
    with pytest.raises(GameRuleError, match="no choice"):
        replay(PROFILE, end_of(k), checkins=saver(k), actions=spend + [Plant(end_of(k), min(bed_cells(2)), "serai")])


def test_dig_goes_to_the_seed_box_and_replanting_is_free_and_keeps_growth():
    k, cell = 5, min(bed_cells(2))
    other = max(bed_cells(2))
    st = replay(PROFILE, end_of(k + 1), **rich_history(k + 1), actions=[
        Plant(end_of(k), cell, "serai"), Dig(end_of(k) + timedelta(days=20), cell),
        Plant(end_of(k) + timedelta(days=21), other, "serai")])
    assert st.choices_used == 1
    assert st.plants[other].growing_days == 20 + (end_of(k + 1) - end_of(k) - timedelta(days=21)).days


# ---- growth, really bad months (D-73, D-74, C5, I3)
def test_plants_grow_seedling_young_full_on_growing_days():
    k, cell = 5, min(bed_cells(2))
    for days, stage in [(6, "seedling"), (7, "young"), (20, "young"), (21, "full")]:
        st = replay(PROFILE, end_of(k) + timedelta(days=days), **rich_history(k), actions=[Plant(end_of(k), cell, "chilli")])
        assert st.plant_stage(st.plants[cell]) == stage, days


def test_red_alone_keeps_plants_growing_but_a_really_bad_month_pauses():
    """C5: someone in Red who is paying their loans down still grows; only a really bad month pauses."""
    k, cell = 5, min(bed_cells(2))
    plant = [Plant(end_of(k), cell, "chilli")]
    red = rich_history(k + 1)
    red["checkins"][-1] = honest(k + 1, 1800, 1500, band="RED")
    st = replay(PROFILE, end_of(k + 1), **red, actions=plant)
    assert st.plants[cell].growing_days == (end_of(k + 1) - end_of(k)).days
    bad = rich_history(k + 1)
    bad["checkins"][-1] = honest(k + 1, 1800, 1500, band="RED", shortfall=True)
    st = replay(PROFILE, end_of(k + 1), **bad, actions=plant)
    assert st.plants[cell].growing_days == (bad["checkins"][-1].on - end_of(k)).days - 1


@pytest.mark.parametrize("ci, bad", [
    (dict(band="RED", shortfall=True), True),
    (dict(band="RED", forecast_probability=0.30, forecast_base_rate=0.12), True),
    (dict(band="RED", forecast_probability=0.20, forecast_base_rate=0.12), False),
    (dict(band="RED"), False),
    (dict(band="YELLOW", shortfall=True), False),
])
def test_really_bad_definition(ci, bad):
    st = replay(PROFILE, end_of(1), checkins=[check(1, 0, **ci)])
    assert st.really_bad is bad
    assert (st.mood == "concerned_hopeful") is bad


def test_two_really_bad_months_rest_calmly_and_suggest_akpk():
    bad = dict(band="RED", shortfall=True)
    one = replay(PROFILE, end_of(1), checkins=[check(1, 0, **bad)])
    assert one.plant_look == "droop" and not one.suggest_akpk
    two = replay(PROFILE, end_of(2), checkins=[check(1, 0, **bad), check(2, 0, **bad)])
    assert two.plant_look == "rest" and two.suggest_akpk
    better = replay(PROFILE, end_of(3), checkins=[check(1, 0, **bad), check(2, 0, **bad), check(3, 0)])
    assert better.plant_look == "normal" and not better.suggest_akpk


def test_droop_recovers_and_never_loses_a_stage():
    k, cell = 5, min(bed_cells(2))
    hist = rich_history(k + 2)
    hist["checkins"][-2] = honest(k + 1, 1800, 1500, band="RED", shortfall=True)
    plant = [Plant(end_of(k) - timedelta(days=25), cell, "chilli")]
    during = replay(PROFILE, end_of(k + 1), **hist, actions=plant)
    assert during.really_bad and during.plant_stage(during.plants[cell]) == "full"
    after = replay(PROFILE, end_of(k + 2), **hist, actions=plant)
    assert not after.really_bad and after.plant_stage(after.plants[cell]) == "full"


def test_moods_follow_the_health_tier():
    moods = [replay(PROFILE, end_of(1), checkins=[check(1, 300, health_tier=t)]).mood
             for t in ("Healthy", "Coping", "Vulnerable")]
    assert moods == ["relaxed", "calm", "focused"]


def test_tree_needs_g4_and_grows_in_7_stages():
    with pytest.raises(GameRuleError, match="G4"):
        replay(PROFILE, end_of(8), **rich_history(8), actions=[BuyTree(end_of(8))])
    st = replay(PROFILE, end_of(9) + timedelta(days=200), **rich_history(9), actions=[BuyTree(end_of(9))])
    assert st.tree_stage() == 6


# ---- streaks and badges
def test_logging_streak_with_one_rest_day_a_week():
    days = [DayActivity(START + timedelta(days=i), entries=1) for i in range(40) if i != 10]
    st = replay(PROFILE, START + timedelta(days=39), days=days)
    assert st.streak == 39 and "honest_tracker" in st.badges
    two_missed = [d for d in days if d.day != START + timedelta(days=11)]
    assert replay(PROFILE, START + timedelta(days=39), days=two_missed).streak < 39


def test_steady_saver_badge():
    assert "steady_saver" in replay(PROFILE, end_of(3), checkins=saver(3)).badges
    assert "steady_saver" not in replay(PROFILE, end_of(3), checkins=saver(3, per_month=50)).badges


# ---- decorations and animals
def test_decorations_and_spots():
    k = 5
    st = replay(PROFILE, end_of(k), **rich_history(k), actions=[
        Decorate(end_of(k), "rug_green", "room:rug"), Decorate(end_of(k), "bench", "garden:a"),
        MoveDecoration(end_of(k), "bench", "garden:b")])
    assert st.decorations == {"rug_green": "room:rug", "bench": "garden:b"} and st.choices_used == 2
    with pytest.raises(GameRuleError, match="spot is taken"):
        replay(PROFILE, end_of(k), **rich_history(k), actions=[
            Decorate(end_of(k), "bench", "garden:a"), Decorate(end_of(k), "lantern", "garden:a")])
    with pytest.raises(GameRuleError, match="isn't open"):
        replay(PROFILE, end_of(2), **rich_history(2), actions=[Decorate(end_of(2), "bench", "garden:a")])
    st = replay(PROFILE, START, actions=[Decorate(START, "desk_plant", "room:desk")])
    assert "desk_plant" in st.decorations                                  # the welcome choice, on day 1


def test_animals_slot_then_extras_up_to_4():
    k = 25
    extras = [AddAnimal(end_of(k), "chicken") for _ in range(3)]
    st = replay(PROFILE, end_of(k), **rich_history(k), actions=[ChooseAnimal(end_of(k), "chicken")] + extras)
    assert st.animals == {"chicken": 4} and st.choices_used == 3
    with pytest.raises(GameRuleError, match="at most 4"):
        replay(PROFILE, end_of(k), **rich_history(k),
               actions=[ChooseAnimal(end_of(k), "chicken")] + extras + [AddAnimal(end_of(k), "chicken")])
    with pytest.raises(GameRuleError, match="slot"):
        replay(PROFILE, end_of(4), **rich_history(4), actions=[ChooseAnimal(end_of(4), "chicken")])


# ---- interactive objects (D-72)
def test_coin_jar_and_savings_plant():
    jars = [replay(PROFILE, end_of(1), checkins=[check(1, 2400 * c)]).coin_jar for c in (0.2, 0.5, 1, 2, 3)]
    assert jars == [0, 1, 2, 3, 4]                                          # shows money now, verified or not
    assert replay(PROFILE, end_of(6), checkins=saver(6)).savings_plant_stage == 4


# ---- invariants
def test_deterministic():
    a = replay(PROFILE, end_of(12), **rich_history(12))
    b = replay(PROFILE, end_of(12), **rich_history(12))
    assert a.points == b.points and a.ledger == b.ledger
