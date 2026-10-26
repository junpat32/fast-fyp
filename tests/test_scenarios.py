"""O1 scenario suite (T-11): the risk engine must pass 100% of these (OBJECTIVES.md O1).

Required by O1: the 5 FYP1 scenarios, the 59/60/61% boundary, zero income, gig-income band
flapping and festive months. The FYP1 scenarios (FYP1 report, chapter 3, "Scenario-Based Validation
Method") are at the end; where a later decision changed FYP1's expected output, the test follows the
current design and docs/fyp1_corrections.md says why (D-103).
"""
from datetime import timedelta

import pytest

from engine.bands import GREEN, INSUFFICIENT, RED, YELLOW
from engine.game import replay
from engine.health import health_score
from engine.rules import Context, advise
from engine.state import MonthRecord, compute_states
from test_game import PROFILE, START, check, end_of, every_day


def rec(income, debt, cash=3000.0, essentials=1200.0, spending=None, shortfall=False, month=None, owed=None):
    return MonthRecord(net_income=income, debt_payments=debt, outstanding_debt=owed if owed is not None else debt * 24,
                       cash=cash, essential_spending=essentials,
                       total_spending=spending if spending is not None else essentials + 600,
                       shortfall=shortfall, month=month)


def last(records):
    return compute_states(records)[-1]


def rules_of(state, **kw):
    return [a.rule for a in advise(Context(state=state, **kw))]


# ---------------- band boundaries (59 / 60 / 61%) ----------------
@pytest.mark.parametrize("dsr, expected", [(0.59, YELLOW), (0.60, RED), (0.61, RED)])
def test_sc01_03_boundary_59_60_61(dsr, expected):
    s = last([rec(3000, 3000 * dsr)] * 3)
    assert s.band == expected


# ---------------- zero income ----------------
def test_sc04_zero_income_gives_no_band_and_explains_why():
    s = last([rec(0, 400, cash=500)] * 3)
    assert s.band == INSUFFICIENT and s.insufficient_income
    assert "R01_insufficient_income" in rules_of(s)
    assert "debt" not in health_score(s).indicators          # H2: never guessed


def test_sc05_one_zero_month_does_not_remove_the_band():
    s = last([rec(3000, 500), rec(3000, 500), rec(0, 500)])  # median of 3 smooths a single gap
    assert s.band == GREEN and s.income_median3 == 3000


# ---------------- gig-income band flapping ----------------
def _flip_backs(bands):
    return sum(1 for a, b, c in zip(bands, bands[1:], bands[2:]) if a == c and b != a)


def test_sc06_gig_income_noise_around_the_green_line_does_not_flap():
    """Realistic gig pattern: income wobbles +-20% around RM2,300 with RM680 of instalments, so
    the raw monthly DSR crosses 30% again and again. This is where 94 of 99 flip-backs happened in
    the synthetic data (docs/checks/band_flapping_check.py); the Green buffer (D-49) must hold."""
    incomes = [2300, 1950, 2700, 2050, 2600, 1900, 2750, 2100, 2500]
    states = compute_states([rec(i, 680) for i in incomes])
    raw = [680 / i >= 0.30 for i in incomes]
    assert sum(1 for a, b in zip(raw, raw[1:]) if a != b) >= 4        # the raw DSR really does cross the line
    assert _flip_backs([s.band for s in states]) == 0


def test_sc06b_perfectly_alternating_income_at_the_red_line_does_not_flap():
    """The original flapping scenario (alternating high/low income makes the 3-month median itself
    alternate). It failed under the v1 rule and under the 27% buffer; the 2-month confirmation (D-49)
    holds it. Unchanged from the first version of this test."""
    incomes = [2500, 1500, 2600, 1400, 2700, 1500, 2600]
    states = compute_states([rec(i, 1300) for i in incomes])
    assert _flip_backs([s.band for s in states]) == 0


def test_sc07_hysteresis_keeps_red_until_below_55():
    states = compute_states([rec(3000, 1900), rec(3000, 1710), rec(3000, 1600), rec(3000, 1600)])  # 63, 57, 53, 53%
    assert [s.raw_band for s in states] == [RED, RED, YELLOW, YELLOW]     # hysteresis (D-05)
    assert [s.band for s in states] == [RED, RED, RED, YELLOW]            # shown once it holds 2 months (D-49)


# ---------------- improvement confirmation (D-49) ----------------
def _bands_for(dsrs, income=3000):
    return compute_states([rec(income, income * d) for d in dsrs])


def test_sc17_worsening_is_shown_at_once():
    s = _bands_for([0.20, 0.35, 0.65])
    assert [x.band for x in s] == [GREEN, YELLOW, RED]


def test_sc18_improvement_shows_only_after_two_months_at_the_level_both_confirm():
    s = _bands_for([0.65, 0.40, 0.20, 0.20, 0.40])          # raw R, Y, G, G, Y
    assert [x.raw_band for x in s] == [RED, YELLOW, GREEN, GREEN, YELLOW]
    assert [x.band for x in s] == [RED, RED, YELLOW, GREEN, YELLOW]


def test_sc19_a_one_month_improvement_is_not_shown():
    s = _bands_for([0.35, 0.25, 0.35, 0.25, 0.35])          # raw Y, G, Y, G, Y
    assert all(x.band == YELLOW for x in s)


def test_sc20_red_below_the_red_line_explains_the_hysteresis():
    """57% after a Red month is still Red (B3): the advice must not say "Red is 60% or more" (D-92)."""
    s = compute_states([rec(3000, 1900), rec(3000, 1710)])[-1]                      # 63%, then 57%
    red = next(a for a in advise(Context(state=s)) if a.rule == "R03_red_band")
    assert "57%" in red.text and "under the Red line of 60%" in red.text and "below 55%" in red.text
    assert "AKPK" in red.text


def test_sc21_red_waiting_for_an_improvement_says_so():
    s = compute_states([rec(3000, 1900), rec(3000, 1710), rec(3000, 1600)])[-1]    # 53%: raw Yellow, shown Red
    assert (s.band, s.raw_band) == (RED, YELLOW)
    red = next(a for a in advise(Context(state=s)) if a.rule == "R03_red_band")
    assert "53%" in red.text and "out of the Red range" in red.text and "2 months in a row" in red.text


def test_sc22_yellow_waiting_for_green_explains_the_wait():
    s = _bands_for([0.35, 0.25])[-1]                                                 # raw Green, shown Yellow
    assert (s.band, s.raw_band) == (YELLOW, GREEN)
    adv = {a.rule: a for a in advise(Context(state=s))}
    assert "Green range" in adv["R13_band_improving"].text and "25%" in adv["R13_band_improving"].text
    assert "R13_band_improving" not in rules_of(_bands_for([0.25, 0.25])[-1])       # nothing waiting


def test_sc08_after_insufficient_income_hysteresis_needs_a_real_red_month():
    states = compute_states([rec(0, 1710), rec(0, 1710), rec(0, 1710), rec(3000, 1710), rec(3000, 1710)])
    assert states[2].band == INSUFFICIENT
    assert states[-1].band == YELLOW          # 57% after an insufficient-income spell -> Yellow (D-27)


# ---------------- festive months ----------------
def test_sc09_festive_spending_spike_does_not_change_the_band():
    normal = last([rec(3000, 600, spending=2000)] * 3)
    festive = last([rec(3000, 600, spending=2000), rec(3000, 600, spending=2000),
                    rec(3000, 600, spending=2800, month=3)])
    assert normal.band == festive.band == GREEN       # bands depend on debt payments, not spending


def test_sc10_festive_month_never_triggers_spending_swings_advice():
    s = last([rec(3000, 600)] * 3)
    r = rules_of(s, festive_month=True, flags={"impulsivity": True})
    assert "R08_spending_swings" not in r and "R09_festive_month" in r


# ---------------- liquidity, BNPL, shortfalls ----------------
def test_sc11_thin_cushion_gives_first_goal_with_amount():
    s = last([rec(2500, 300, cash=400, essentials=1000)] * 3)
    adv = advise(Context(state=s, cash=400, essentials_and_debts=1300))
    first = next(a for a in adv if a.rule == "R05_build_first_cushion")
    assert "RM900" in first.text                      # 1 x 1,300 - 400


def test_sc12_bnpl_plans_and_recent_shortfall_are_flagged():
    s = last([rec(2500, 500), rec(2500, 500), rec(2500, 500, shortfall=True)])
    r = rules_of(s, bnpl_plans=3, bnpl_monthly=240)
    assert r[0] == "R02_recent_shortfall" and "R07_bnpl_load" in r
    assert health_score(s).indicators["bills"] == 50


def test_sc13_only_validated_flags_reach_the_user():
    s = last([rec(3000, 600)] * 3)
    r = rules_of(s, flags={"overconfidence": True, "delayed_correction": True})   # failed S14 (D-41)
    assert not any("overconfidence" in x or "correction" in x for x in r)
    assert "R08_spending_swings" in rules_of(s, flags={"impulsivity": True})


def test_sc14_healthy_user_gets_encouragement_only():
    s = last([rec(4000, 600, cash=9000, essentials=1500, spending=2400)] * 3)
    hs = health_score(s)
    assert hs.tier == "Healthy" and hs.score >= 80
    assert rules_of(s) == ["R12_doing_well"]


def test_sc15_student_low_income_no_debt_is_green_not_insufficient():
    s = last([rec(800, 0, cash=600, essentials=500, spending=700)] * 3)
    assert s.band == GREEN and not s.insufficient_income


def test_sc16_red_band_mentions_free_counselling_not_products():
    s = last([rec(2000, 1400)] * 3)
    adv = advise(Context(state=s))
    red = next(a for a in adv if a.rule == "R03_red_band")
    assert "AKPK" in red.text
    for banned in ("invest", "unit trust", "apply for a loan", "credit card offer"):
        assert banned not in " ".join(a.text.lower() for a in adv)


# ---------------- the five FYP1 scenarios (D-103; differences: docs/fyp1_corrections.md) ----------------
# FYP1's inputs, read as NET income (rule 6: DSR divides by net income; FYP1 wrote "gross").
def test_fyp1_scenario_1_green_stable_user():
    """FYP1 S1: RM5,000 income, RM1,100 debt payments (DSR 22%), saving 12%, no flags, a six-month
    streak. Expected: Green, a positive message and no corrective advice, streak points.
    FYP1 gives no savings balance; a stable user is given a cushion of over 3 months."""
    s = last([rec(5000, 1100, cash=10000, essentials=2000, spending=5000 - 1100 - 600)] * 3)   # saves 600 = 12%
    assert s.band == GREEN and round(s.savings_rate3, 2) == 0.12
    assert rules_of(s, cash=10000, essentials_and_debts=3100) == ["R12_doing_well"]
    end = START + timedelta(days=182)                                    # six months of daily logging
    st = replay(PROFILE, end, days=every_day(end, entries=1))
    assert [a.ref for a in st.ledger if a.kind == "streak"] == ["7", "30", "100"]


def test_fyp1_scenario_2_yellow_early_warning():
    """FYP1 S2: RM4,200, RM1,680 debt payments (DSR 40%), saving 4%, the impulsivity flag active.
    Expected: Yellow, the impulsivity prompt, no Red alarm. FYP1 also expected a debt-load message:
    the band card shows the debt share instead (SC2), so there is no separate advice below 50%."""
    s = last([rec(4200, 1680, cash=3000, essentials=1600, spending=4200 - 1680 - 168)] * 3)   # saves 168 = 4%
    r = rules_of(s, flags={"impulsivity": True}, cash=3000, essentials_and_debts=3280)
    assert s.band == YELLOW and round(s.dsr, 2) == 0.40 and "R08_spending_swings" in r
    assert "R03_red_band" not in r and "R04_near_red" not in r


def test_fyp1_scenario_3_red_urgent():
    """FYP1 S3: RM3,600, RM2,340 debt payments (DSR 65%), saving 0%, impulsivity and "loss aversion"
    flags. Now: Red with AKPK counselling and the impulsivity prompt; the second flag (now "delayed
    correction") failed validation and is never shown (D-41); points are never paused (D-11)."""
    s = last([rec(3600, 2340, cash=500, essentials=1000, spending=3600 - 2340)] * 3)          # saves nothing
    adv = advise(Context(state=s, flags={"impulsivity": True, "delayed_correction": True}, cash=500,
                         essentials_and_debts=3340))
    rules = [a.rule for a in adv]
    assert s.band == RED and "R08_spending_swings" in rules and not any("correction" in x for x in rules)
    assert "AKPK" in next(a for a in adv if a.rule == "R03_red_band").text
    st = replay(PROFILE, end_of(1), checkins=[check(1, 0, band="RED")])
    assert any(a.kind == "checkin" and a.points > 0 for a in st.ledger)    # a Red month still earns its check-in


@pytest.mark.parametrize("debt, expected", [(2360, YELLOW), (2400, RED), (2440, RED)])
def test_fyp1_scenario_4_boundary_at_rm4000(debt, expected):
    """FYP1 S4 at RM4,000: 59% Yellow and 61% Red as FYP1 said; 60% exactly is RED (CLAUDE.md rule 5,
    the frozen spec; FYP1 had it Yellow: SC1, D-103)."""
    assert last([rec(4000, debt)] * 3).band == expected


def test_fyp1_scenario_5_recovery():
    """FYP1 S5: Red at 68% for two months, then 52%, then 44%. Now: the improvement is acknowledged in
    month 3 and Yellow shows in month 4, once it has held 2 months (D-49; FYP1 said month 3). The
    "Recovery Champion" badge is deferred to T-24's "back on track" bonus (SC3)."""
    states = compute_states([rec(4000, 2720), rec(4000, 2720), rec(4000, 2080), rec(4000, 1760)])
    assert [s.raw_band for s in states] == [RED, RED, YELLOW, YELLOW]
    assert [s.band for s in states] == [RED, RED, RED, YELLOW]
    month3 = next(a for a in advise(Context(state=states[2])) if a.rule == "R03_red_band")
    assert "Good progress" in month3.text and "Red is" not in month3.text
    assert "R03_red_band" not in rules_of(states[3])
