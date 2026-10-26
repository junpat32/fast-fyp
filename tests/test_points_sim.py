"""T-14b: the cheater simulation (sim/points_sim.py, game_design §13, D-75). Honest reporting must
never lose to a way of gaming the app; the one known limit is tested as a finding."""
from datetime import timedelta

import pytest

from engine.game import replay
from sim.points_sim import CHEATS, KNOWN_LIMITS, MONTHS, make_life, month_end, months_ahead, run, strategy_inputs

LIFE = make_life()


@pytest.fixture(scope="module")
def runs():
    return {s: run(s, LIFE) for s in ["honest", "forgetful", "late_checker"] + CHEATS + KNOWN_LIMITS}


@pytest.mark.parametrize("cheat", CHEATS)
def test_no_cheat_beats_honest_in_any_month(runs, cheat):
    for honest, other in zip(runs["honest"], runs[cheat]):
        assert honest.points >= other.points, honest.k
        assert honest.room_level >= other.room_level, honest.k
        assert honest.qualifying_months >= other.qualifying_months, honest.k


@pytest.mark.parametrize("cheat", ["padder", "cost_hider", "debt_liar_logs"])
def test_lies_that_break_the_match_lose_the_logging_reward(runs, cheat):
    assert runs[cheat][-1].verified_months == 0
    assert runs[cheat][-1].points < runs["honest"][-1].points


def test_borrowing_and_spikes_cost_more_than_they_give(runs):
    assert runs["borrower"][-1].points < runs["honest"][-1].points
    assert runs["spike_liar"][-1].points < runs["honest"][-1].points


def test_backdated_and_pre_sign_up_check_ins_are_rejected(runs):
    assert runs["backdater"][-1].rejected == 4


def test_honest_but_forgetful_users_are_still_verified(runs):
    assert runs["forgetful"][-1].verified_months >= MONTHS - 1


def test_checking_in_late_changes_nothing(runs):
    """D-77: money and debt are as at the end of the month, so a check-in 5 days later earns exactly
    the same for every month."""
    for honest, late in zip(runs["honest"], runs["late_checker"]):
        assert (late.points, late.room_level, late.qualifying_months, late.verified_months) == \
            (honest.points, honest.room_level, honest.qualifying_months, honest.verified_months)
    end = month_end(MONTHS) + timedelta(days=7)

    def month_awards(name):
        inp = strategy_inputs(name, LIFE)
        st = replay(inp.pop("profile"), end, **inp)
        return sorted((a.kind, a.ref, a.points) for a in st.ledger if a.kind not in ("card", "streak", "welcome"))
    assert month_awards("late_checker") == month_awards("honest")


def test_finding_a_small_lie_every_month_passes_the_check(runs):
    """KNOWN LIMIT (reported in sim/results/points_sim.md): hiding RM300 a month moved out of
    investments passes the 10% tolerance and gains saving points; bounded by the saving tiers."""
    gap = runs["section_liar"][-1].points - runs["honest"][-1].points
    assert 0 < gap <= MONTHS * 60
    assert months_ahead(runs["section_liar"], runs["honest"]) > 0


def test_finding_a_constant_balance_lie_passes_the_check_after_month_1(runs):
    """KNOWN LIMIT: verification checks changes, not levels. A user who claims RM1,000 more every
    month is unverified only in month 1, gains a little and reaches room levels early."""
    liar, honest = runs["balance_liar"], runs["honest"]
    assert liar[-1].verified_months == MONTHS - 1
    assert 0 <= liar[-1].points - honest[-1].points <= MONTHS * 60
    assert min(s.k for s in liar if s.room_level >= 3) < min(s.k for s in honest if s.room_level >= 3)


def test_hiding_income_no_longer_pays_for_a_steady_income(runs):
    """I1 (D-89, Patrick 2026-10-15): income is self-reported, and leaving equal amounts of salary
    and spending out of the logs still passes the check, but the rewards use the larger of the
    confirmed and the declared income (G13): it was +2,580 points; now nothing."""
    liar, honest = runs["income_hider"], runs["honest"]
    assert liar[-1].verified_months == MONTHS
    assert [(x.points, x.room_level, x.qualifying_months) for x in liar] == \
        [(y.points, y.room_level, y.qualifying_months) for y in honest]


@pytest.mark.parametrize("who", ["non_saver", "student", "gig"])
def test_hiding_income_never_unlocks_anything_earlier(who):
    """G13 covers the default goal and the cost floor too: before, a non-saver's smaller goal gave 13
    garden months instead of 6 and a gig worker reached room level 2 in month 1 instead of 5. Honest
    users lose nothing. A gig worker still gains a little in above-average months (known limit,
    bounded by one saving-tier gap a month)."""
    life = make_life(who=who)
    liar, honest = run("income_hider", life), run("honest", life)
    assert all(x.room_level <= y.room_level and x.qualifying_months <= y.qualifying_months
               for x, y in zip(liar, honest))
    gap = liar[-1].points - honest[-1].points
    assert gap == 0 if who != "gig" else 0 <= gap <= MONTHS * 60


def test_shifting_money_with_fake_entries_after_month_end_is_never_verified(runs):
    """D-77 doesn't add a new way to gain points: made-up entries dated after month end raise the
    month-end balance but break the next month's match, every month."""
    shifter, honest = runs["month_shifter"], runs["honest"]
    assert shifter[-1].verified_months == 0
    assert all(s.points <= h.points for s, h in zip(shifter, honest))


@pytest.mark.parametrize("who", ["employee", "student", "gig", "non_saver"])
def test_reward_order_for_every_kind_of_person(who):
    """R6: check-ins < logging < good financial health, for each honest persona."""
    t = run("honest", make_life(who=who))[-1].tiers
    assert t["checkin"] < t["logging"] < t["health"]


def test_garden_is_fair_to_students_and_gig_workers():
    """P2: own goals let a student or gig worker grow the garden like an employee."""
    employee = run("honest", make_life())[-1].qualifying_months
    for who in ("student", "gig"):
        assert run("honest", make_life(who=who))[-1].qualifying_months >= employee - 3


def test_saving_dominates():
    saver = run("honest", make_life())[-1]
    non_saver = run("honest", make_life(who="non_saver"))[-1]
    assert saver.points >= 1.5 * non_saver.points and saver.qualifying_months > 2 * non_saver.qualifying_months


def test_rough_patch_never_takes_progress_away():
    snaps = run("honest", make_life(rough_patch=True))
    for a, b in zip(snaps, snaps[1:]):
        assert b.qualifying_months >= a.qualifying_months and b.room_level >= a.room_level
        assert b.points >= a.points
