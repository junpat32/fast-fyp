"""Secondary comparison (D-134): the building blocks behave as the plan says."""
import numpy as np
import pytest

import ml.secondary as sc


def test_runway_is_months_until_cash_runs_out_at_the_recent_pace():
    # cash fell 1,000 -> 600 over two months (pace -200 a month): 600 lasts 3 months
    r = sc.runway_months(np.array([600.0, 0.0, 900.0, 500.0]), np.array([1000.0, 400.0, 900.0, 300.0]))
    assert r[0] == pytest.approx(3.0)
    assert r[1] == 0.0                             # already out of cash
    assert np.isinf(r[2]) and np.isinf(r[3])       # flat or rising cash: no limit


def test_runway_risk_orders_shorter_runway_first_and_breaks_ties_by_cushion():
    risk = sc.runway_risk(np.array([0.0, 3.0, np.inf, np.inf]), np.array([5.0, 5.0, 0.5, 4.0]))
    assert risk[0] > risk[1] > risk[2] > risk[3]


def test_net_benefit_matches_its_definition():
    p, y = np.array([0.9, 0.8, 0.4, 0.1]), np.array([1, 0, 1, 0])
    # at 0.5: flags rows 0 and 1 -> 1 TP, 1 FP; NB = 1/4 - 1/4 * 0.5/0.5
    assert sc.net_benefit(p, y, 0.5) == pytest.approx(0.0)
    assert sc.net_benefit(p, y, 0.3) == pytest.approx(2 / 4 - 1 / 4 * 0.3 / 0.7)


def test_well_calibrated_probabilities_have_slope_near_one_and_small_ece():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.02, 0.6, 20000)
    y = (rng.random(20000) < p).astype(int)
    assert sc.calibration_slope(p, y) == pytest.approx(1.0, abs=0.1)
    assert sc.ece(p, y) < 0.02
    over = np.clip(p * 1.8, 0, 0.99)               # overconfident: slope below 1, positive mean gap
    assert sc.calibration_slope(over, y) < 0.9


def test_weighted_metrics_equal_unweighted_with_unit_weights():
    rng = np.random.default_rng(1)
    y, s = (rng.random(500) < 0.2).astype(int), rng.random(500)
    assert sc.ranking(y, s) == pytest.approx(sc.ranking(y, s, np.ones(500)))
    assert sc.brier(y, s) == pytest.approx(sc.brier(y, s, np.ones(500)))
    assert sc.ece(s, y) == pytest.approx(sc.ece(s, y, w=np.ones(500)))


def test_cross_fit_never_uses_a_users_own_rows():
    # the score is pure noise, but each user's rows share the user's outcome; a fit that saw the user
    # would learn it, a fit on other users can't
    rng = np.random.default_rng(2)
    users = np.repeat(np.arange(400), 5)
    y = np.repeat(rng.random(400) < 0.3, 5).astype(int)
    score = np.repeat(rng.random(400), 5)          # unique per user, unrelated to y
    p = sc.cross_fit(score, y, users)
    assert abs(np.corrcoef(p, y)[0, 1]) < 0.15


@pytest.mark.parametrize("lo, hi, margin, lower, expected", [
    (0.01, 0.05, 0.05, False, "ML better"),
    (-0.02, 0.03, 0.05, False, "comparable"),
    (-0.08, 0.01, 0.05, False, "inconclusive"),
    (-0.08, -0.01, 0.05, False, "method better"),
    (-0.004, -0.001, 0.003, True, "ML better"),          # Brier: lr lower is better
    (-0.002, 0.002, 0.003, True, "comparable"),
])
def test_reading_rule(lo, hi, margin, lower, expected):
    assert sc.verdict(lo, hi, margin, lower_is_better=lower) == expected
