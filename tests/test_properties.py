"""Property-based tests for the risk engine (O1; Q2a, D-131).

The scenario suite (test_scenarios.py) checks hand-picked cases. These tests state rules that must
hold for EVERY input and let Hypothesis generate the cases: hundreds per property, including the
awkward ones (zero, very large, just either side of a line). When one fails, Hypothesis shrinks it to
the smallest failing input. Derandomised and without an example database, so every run checks the
same cases: the evidence is reproducible.

Properties
  P1  one month's band is exactly the thresholds in shared/thresholds.json (B1, B2; rule 5)
  P2  hysteresis: after a Red month, Red holds down to the leave line, and only after Red (B3, B4)
  P3  a higher DSR never gives a better band, whatever the previous month
  P4  more debt payments, all else equal, never give a better shown band or a higher health score
  P5  income too low to judge always means "insufficient income": no band, no debt indicator (H2)
  P6  the shown band (D-49): never better than this month's band; a worse band shows at once; a
      better band only after K months that are all better, and then the worst of them
  P7  no flapping: after the shown band gets worse, it stays at least that bad for K months
  P8  the health score and its indicators stay within 0-100, and the tier matches the whole number the
      app shows, Math.round(score) (H1, H4). P8 found a real bug: 79.96 showed as "80, Coping" (D-131)
  P9  assess() on any realistic history: deterministic (Q1); advice ranked, no repeats, every text
      filled in (no {placeholder}, nan, None, inf or negative ringgit); a forecast in 0-1 with at most
      3 reasons, present exactly when there are 3+ months and income is judgeable (Q4)
"""
from __future__ import annotations

import math
import re
from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.assess import assess
from engine.bands import GREEN, INSUFFICIENT, RED, YELLOW, band, load_thresholds
from engine.features import UserProfile
from engine.health import health_score
from engine.state import MonthRecord, MonthState, compute_states

T = load_thresholds()
G, R, LEAVE = T["dsr"]["green_below"], T["dsr"]["red_at_or_above"], T["dsr"]["leave_red_below"]
FLOOR, K = T["insufficient_income_below_rm"], T["improvement_confirm_months"]
TIERS = T["health_score"]["tiers"]

MANY = settings(derandomize=True, database=None, deadline=None, max_examples=400)
FEWER = settings(derandomize=True, database=None, deadline=None, max_examples=80)     # assess() takes ~80 ms


def money(hi: float):
    """Ringgit and sen, as the app stores them (rule 9)."""
    return st.floats(0, hi, allow_nan=False, allow_infinity=False).map(lambda x: round(x, 2))


share = st.floats(0, 1, allow_nan=False)
dsrs = st.floats(0, 3, allow_nan=False, allow_infinity=False)
judgeable = st.floats(FLOOR, 50_000, allow_nan=False, allow_infinity=False)
previous = st.sampled_from([None, INSUFFICIENT, GREEN, YELLOW, RED])
# DSRs spread over 0-120%, half of them within 2 points of a line, where mistakes would hide
near_lines = st.one_of(st.floats(0, 1.2, allow_nan=False),
                       st.sampled_from([G, LEAVE, R]).flatmap(lambda x: st.floats(x - 0.02, x + 0.02)))


def plain(dsr: float) -> int:
    return GREEN if dsr < G else YELLOW if dsr < R else RED


@st.composite
def months(draw, n_min: int = 1, n_max: int = 12) -> list[MonthRecord]:
    """A realistic history: every field in a plausible RM range, consecutive calendar months."""
    n, start, out = draw(st.integers(n_min, n_max)), draw(st.integers(1, 12)), []
    for i in range(n):
        ess = draw(money(8_000))
        total = ess + draw(money(8_000))
        debt = draw(money(15_000))
        out.append(MonthRecord(
            net_income=draw(st.just(0.0) | money(20_000)), debt_payments=debt, outstanding_debt=draw(money(300_000)),
            cash=draw(money(100_000)), essential_spending=ess, total_spending=total,
            family_support=draw(money(2_000)), shortfall=draw(st.booleans()), month=(start + i - 1) % 12 + 1,
            bnpl_purchases=round(total * draw(share), 2), bnpl_new_count=draw(st.integers(0, 3)),
            bnpl_instalments=round(debt * draw(share), 2), personal_loan_balance=draw(money(100_000)),
            event_costs=draw(money(5_000)), shock_count=draw(st.integers(0, 3)), other_fees=draw(money(300)),
            savings_target=draw(st.none() | money(3_000)), education_spending=round(ess * draw(share), 2)))
    return out


@st.composite
def dsr_path(draw) -> list[MonthRecord]:
    """Up to two years at one judgeable income, with the DSR moving around the band lines."""
    income = draw(st.floats(1_000, 20_000, allow_nan=False))
    return [MonthRecord(net_income=income, debt_payments=d * income, outstanding_debt=0.0, cash=0.0,
                        essential_spending=0.0) for d in draw(st.lists(near_lines, min_size=1, max_size=24))]


@MANY
@given(dsrs, st.floats(0, 50_000, allow_nan=False))
def test_p1_one_month_band_is_exactly_the_thresholds(dsr, income):
    assert band(dsr, income, None) == (INSUFFICIENT if income < FLOOR else plain(dsr))


@MANY
@given(dsrs, judgeable, previous)
def test_p2_red_holds_down_to_the_leave_line_and_only_after_red(dsr, income, prev):
    expected = RED if prev == RED and LEAVE <= dsr < R else plain(dsr)
    assert band(dsr, income, prev) == expected


@MANY
@given(dsrs, dsrs, judgeable, previous)
def test_p3_a_higher_dsr_never_gives_a_better_band(d1, d2, income, prev):
    lo, hi = sorted((d1, d2))
    assert band(lo, income, prev) <= band(hi, income, prev)


@MANY
@given(months(), st.data())
def test_p4_more_debt_never_gives_a_better_band_or_a_higher_score(records, data):
    more = [replace(r, debt_payments=r.debt_payments + data.draw(money(5_000))) for r in records]
    for a, b in zip(compute_states(records), compute_states(more)):
        assert (a.band == INSUFFICIENT) == (b.band == INSUFFICIENT)       # the same incomes
        assert b.band >= a.band
        assert health_score(b).score <= health_score(a).score


@MANY
@given(months(n_min=3), st.lists(st.floats(0, FLOOR, exclude_max=True, allow_nan=False), min_size=3, max_size=3))
def test_p5_income_too_low_to_judge_always_means_insufficient(records, low):
    records = records[:-3] + [replace(r, net_income=x) for r, x in zip(records[-3:], low)]
    s = compute_states(records)[-1]
    assert s.band == INSUFFICIENT and s.insufficient_income
    assert "debt" not in health_score(s).indicators


@MANY
@given(dsr_path())
def test_p6_the_shown_band_follows_d49(records):
    states = compute_states(records)
    raw, shown = [s.raw_band for s in states], [s.band for s in states]
    assert shown[0] == raw[0]
    for i in range(1, len(states)):
        assert shown[i] >= raw[i]                                          # never better than this month
        if raw[i] >= shown[i - 1]:
            assert shown[i] == raw[i]                                      # worse (or equal): at once
        if shown[i] < shown[i - 1]:                                        # better: only after K months...
            last_k = raw[i - K + 1:i + 1]
            assert i - K + 1 >= 0 and all(x < shown[i - 1] for x in last_k)
            assert shown[i] == max(last_k)                                 # ...and then the worst of them


@MANY
@given(dsr_path())
def test_p7_after_getting_worse_the_band_holds_for_k_months(records):
    shown = [s.band for s in compute_states(records)]
    for i in range(1, len(shown)):
        if shown[i] > shown[i - 1]:
            assert all(shown[j] >= shown[i] for j in range(i + 1, min(i + K, len(shown))))


def tier_of(shown: int) -> str:
    return "Healthy" if shown >= TIERS["healthy"] else "Coping" if shown >= TIERS["coping"] else "Vulnerable"


def check_health(s: MonthState) -> None:
    h = health_score(s)
    assert 0 <= h.score <= 100 and all(0 <= v <= 100 for v in h.indicators.values())
    assert h.tier == tier_of(math.floor(h.score + 0.5)), (h.score, h.tier)      # the app shows Math.round(score)


def state(cushion=1.0, rate=None, dsr=0.2, insufficient=False, shortfalls=0) -> MonthState:
    return MonthState(index=0, month=1, income_median3=3000.0, dsr=dsr, dti=0.0, band=GREEN, band_name="GREEN",
                      raw_band=GREEN, cushion_months=cushion, savings_rate3=rate, shortfalls_last3=shortfalls,
                      insufficient_income=insufficient)


@MANY
@given(months())
def test_p8_health_score_stays_in_range_and_the_tier_matches_the_score_shown(records):
    for s in compute_states(records):
        check_health(s)


@MANY
@given(st.floats(0, 6, allow_nan=False), st.none() | st.floats(-0.5, 0.5, allow_nan=False),
       st.floats(0, 1.5, allow_nan=False), st.booleans(), st.integers(0, 3))
def test_p8b_health_tier_matches_the_score_shown_across_the_whole_range(cushion, rate, dsr, insufficient, shortfalls):
    check_health(state(cushion, rate, dsr, insufficient, shortfalls))


# The cases P8 found (savings + bills only, so score = (savings + 100) / 2): before the fix the tier
# used the unrounded score while the app showed the rounded one
@pytest.mark.parametrize("cushion, shown, tier", [
    (1.7976, 80, "Healthy"),     # 79.96 -> 80.0: was "80, Coping"
    (1.7676, 80, "Healthy"),     # 79.46 -> 79.5 -> the app shows 80: was "80, Coping"
    (1.7640, 79, "Coping"),      # 79.40 -> 79
    (0.0, 50, "Coping"),
])
def test_p8_regression_the_number_and_the_tier_never_disagree(cushion, shown, tier):
    h = health_score(state(cushion=cushion, insufficient=True))
    assert math.floor(h.score + 0.5) == shown and h.tier == tier


profiles = st.builds(UserProfile, employment_type=st.sampled_from(["employee", "gig", "student"]),
                     age=st.integers(18, 35), lives_with_parents=st.booleans(), family_support=st.booleans(),
                     festive_month=st.none() | st.integers(1, 12))
UNFILLED = re.compile(r"[{}]|\bnan\b|\bNone\b|\binf\b|RM-", re.IGNORECASE)


@FEWER
@given(profiles, months())
def test_p9_assess_is_deterministic_and_its_advice_is_always_filled_in(profile, records):
    a = assess(profile, records)
    assert a == assess(profile, records)
    rules = [x["rule"] for x in a["advice"]]
    assert len(rules) == len(set(rules))
    assert [x["priority"] for x in a["advice"]] == sorted(x["priority"] for x in a["advice"])
    for x in a["advice"]:
        for part in ("title", "short", "text"):
            assert x[part] and not UNFILLED.search(x[part]), (x["rule"], part, x[part])
    assert (a["forecast"] is not None) == (len(records) >= 3 and not a["insufficient_income"])
    if a["forecast"]:
        assert 0 <= a["forecast"]["probability"] <= 1 and len(a["forecast"]["reasons"]) <= 3
    if a["insufficient_income"]:
        assert a["band"] == "INSUFFICIENT_INCOME" and "R01_insufficient_income" in rules
