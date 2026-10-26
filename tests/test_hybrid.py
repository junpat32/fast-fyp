"""Hybrid check (D-130): the Monte Carlo input reads months t-2..t only (rule 1), and the adoption rule."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import ml.check_hybrid as hy

USER = SimpleNamespace(user_id=7, employment_type="employee", festive_month=1, has_car=False, has_motorbike=True)


def _month(m: int) -> SimpleNamespace:
    return SimpleNamespace(net_income=2000.0, commitments_total=300.0, outstanding_debt=5000.0, cash=800.0 + m,
                           spend_essential=900.0, spend_total=1500.0, family_support=0.0, month=m,
                           bnpl_purchases=0.0, pay_bnpl=0.0, spend_education=0.0, late_fees=0.0,
                           event_shock_cost=0.0, event_minor_cost=0.0)


ROWS = [_month(m) for m in range(1, 13)]


@pytest.mark.parametrize("t, months", [(3, [1, 2, 3]), (5, [3, 4, 5]), (9, [7, 8, 9])])
def test_monte_carlo_input_reads_months_t_minus_2_to_t_only(monkeypatch, t, months):
    seen = {}

    def fake(hist, profile, game, seed, paths, horizon):
        seen.update(months=[h.month for h in hist], seed=seed, paths=paths, horizon=horizon)
        return SimpleNamespace(shortfall_probability=0.25)

    monkeypatch.setattr(hy, "simulate_future", fake)
    assert hy.mc_shortfall(ROWS, USER, t) == 0.25
    assert seen == {"months": months, "seed": 50_000 + 100 * 7 + t, "paths": 2000, "horizon": 3}


def test_the_real_monte_carlo_gives_a_probability():
    assert 0.0 <= hy.mc_shortfall(ROWS, USER, 6) <= 1.0


def test_logit_clip_is_finite_at_0_and_1_and_symmetric():
    z = hy.logit_clip([0.0, 0.5, 1.0])
    assert np.all(np.isfinite(z))
    assert z[1] == pytest.approx(0.0)
    assert z[0] == pytest.approx(-z[2])


def _groups(pass_mean=True, pass_ece=True) -> dict:
    return {"employment_type": [{"pass_mean": True, "pass_ece": True}, {"pass_mean": pass_mean, "pass_ece": pass_ece}],
            "age_band": [{"pass_mean": True, "pass_ece": True}]}


@pytest.mark.parametrize("low, groups, seconds, adopt", [
    (0.004, _groups(), 0.01, True),
    (0.0, _groups(), 0.01, False),                    # the lower bound must be above 0, not equal to it
    (-0.010, _groups(), 0.01, False),
    (0.004, _groups(pass_mean=False), 0.01, False),
    (0.004, _groups(pass_ece=False), 0.01, False),
    (0.004, _groups(), 0.5, False),                   # under 0.5 s, strictly
])
def test_the_adoption_rule_needs_all_three_conditions(low, groups, seconds, adopt):
    assert hy.verdict(low, groups, seconds)["adopt"] is adopt


def test_group_rows_apply_the_d102_calibration_test():
    y = ([1] * 40 + [0] * 160) * 2                     # observed rate exactly 20% in both groups
    df = pd.DataFrame({"g": ["a"] * 200 + ["b"] * 200, "y": y, "v1": 0.2,
                       "v3": np.r_[np.full(200, 0.21), np.full(200, 0.5)]})
    rows = {r["group"]: r for r in hy.group_rows(df, "g")}
    assert rows["a"]["pass_mean"] and rows["a"]["pass_ece"]                 # 1 point off, ECE 0.01 worse
    assert not rows["b"]["pass_mean"] and not rows["b"]["pass_ece"]         # 30 points off
