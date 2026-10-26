"""The conformal adjustment of the Future Self range (sim/conformal.py, sim/recalibrate_monte_carlo.py, D-142)."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from sim import conformal
from sim import recalibrate_monte_carlo as recal
from sim.monte_carlo import MonthRange


def test_the_offset_is_the_finite_sample_order_statistic():
    assert conformal.tail_offset(np.arange(1, 10)) == 9          # n 9:  ceil(0.9 x 10) = 9
    assert conformal.tail_offset(np.arange(1, 20)) == 18         # n 19: ceil(0.9 x 20) = 18
    assert conformal.tail_offset(np.arange(100, 0, -1)) == 91    # order of the input doesn't matter


def test_too_few_users_cannot_be_calibrated():
    with pytest.raises(ValueError, match="too few"):
        conformal.tail_offset(np.arange(8))


def test_the_docstring_trace_holds():
    lower, _ = conformal.fit_cell(np.zeros(9), np.zeros(9),
                                  -np.array([-1.2, -0.9, -0.8, -0.5, -0.4, -0.3, -0.1, 0.2, 0.6]))
    assert lower == pytest.approx(0.6)
    _, upper = conformal.fit_cell(np.zeros(9), np.zeros(9),
                                  np.array([-2.0, -1.5, -1.1, -1.0, -0.8, -0.7, -0.6, -0.4, -0.3]))
    assert upper == pytest.approx(-0.3)
    assert conformal.adjust(1.0, 1.8, 3.0, 0.6, -0.3) == pytest.approx((0.4, 2.7))


def test_an_adjusted_range_reaches_its_target_on_new_exchangeable_users():
    # A range that is too narrow and too optimistic, as the Monte Carlo's was: misses mostly below.
    rng = np.random.default_rng(7)

    def users(n):
        centre = rng.normal(2, 1, n)
        return centre - 0.5, centre + 0.5, centre + rng.normal(-0.4, 1, n)

    lower, upper = conformal.fit_cell(*users(4000))
    lo, hi, y = users(40000)
    lo, hi = lo - lower, hi + upper
    assert 0.79 <= np.mean((lo <= y) & (y <= hi)) <= 0.82
    assert np.mean(y < lo) == pytest.approx(0.10, abs=0.015)
    assert np.mean(y > hi) == pytest.approx(0.10, abs=0.015)
    assert lower > upper                                         # the low end moves further


def test_a_range_that_was_too_wide_narrows():
    rng = np.random.default_rng(1)
    centre = rng.normal(0, 1, 500)
    lower, upper = conformal.fit_cell(centre - 3, centre + 3, centre + rng.normal(0, 0.5, 500))
    assert lower < 0 and upper < 0


@pytest.mark.parametrize("p10, p50, p90, lower, upper, expected", [
    (1.0, 1.5, 2.0, 0.2, 0.3, (0.8, 2.3)),       # widened both ways
    (0.1, 1.5, 2.0, 0.5, 0.0, (0.0, 2.0)),       # never below 0 (cash never ends below 0)
    (1.0, 1.5, 2.0, -0.9, -0.9, (1.5, 1.5)),     # narrowing stops at the middle path
])
def test_the_adjusted_range_keeps_its_order_and_floor(p10, p50, p90, lower, upper, expected):
    assert conformal.adjust(p10, p50, p90, lower, upper) == pytest.approx(expected)


def _table(value=(0.5, 0.25)):
    return {"offsets": {e: {str(n): [list(value)] * 6 for n in conformal.HISTORY}
                        for e in conformal.EMPLOYMENT}}


def test_calibrated_months_applies_the_users_cell_and_keeps_the_middle_path():
    months = tuple(MonthRange(m, 1.0, 2.0, 3.0) for m in (7, 8, 9, 10, 11, 12))
    table = _table()
    table["offsets"]["gig"]["4"][5] = [-0.5, 1.0]
    out = conformal.calibrated_months(months, "gig", 4, table)
    assert [m.month for m in out] == [7, 8, 9, 10, 11, 12]
    assert (out[0].p10, out[0].p50, out[0].p90) == (0.5, 2.0, 3.25)
    assert (out[5].p10, out[5].p50, out[5].p90) == (1.5, 2.0, 4.0)


@pytest.mark.parametrize("employment, n_history, n_months", [
    ("retired", 6, 6), ("gig", 2, 6), ("gig", 7, 6), ("gig", 6, 5)])
def test_a_forecast_without_a_cell_is_refused(employment, n_history, n_months):
    months = tuple(MonthRange(m, 1.0, 2.0, 3.0) for m in range(1, n_months + 1))
    with pytest.raises(ValueError, match="no conformal cell"):
        conformal.calibrated_months(months, employment, n_history, _table())


# ------------------------------------------------------------------ the runner

def _fake_world(monkeypatch, seen):
    users = pd.DataFrame([dict(user_id=1, employment_type="employee", festive_month=12,
                               has_car=False, has_motorbike=False)])
    rows = pd.DataFrame([dict(user_id=1, month=m, net_income=100, commitments_total=0,
                              outstanding_debt=0, cash=m * 10, spend_essential=10, spend_total=10,
                              spend_education=0, family_support=0, bnpl_purchases=0, pay_bnpl=0,
                              late_fees=0, event_shock_cost=0, event_minor_cost=0) for m in range(1, 13)])
    monkeypatch.setattr(recal, "generate", lambda *a, **kw: {"users": users, "monthly": rows})

    def forecast(history, profile, game, **kw):
        seen.append([r.month for r in history])
        # The true cushion is the month number (cash 10 x month over costs of 10): exact ranges cover.
        return SimpleNamespace(cushion=[SimpleNamespace(p10=m, p50=m, p90=m) for m in range(7, 13)])
    monkeypatch.setattr(recal, "simulate_future", forecast)


def test_collect_forecasts_only_from_months_before_the_origin_and_aligns_the_truth(monkeypatch):
    seen = []
    _fake_world(monkeypatch, seen)
    df = recal.collect("default", 1, n_users=1, paths=2)
    assert seen == [[4, 5, 6], [3, 4, 5, 6], [2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]]
    assert len(df) == 4 * 6
    assert (df.truth == df.h + 6).all() and (df.p10 == df.truth).all()


def test_fit_gives_every_type_history_and_month_ahead_a_cell():
    rng = np.random.default_rng(2)
    rows = [("default", 62001, u, e, n, h, 0.0, 1.0, 2.0, rng.normal(1, 1))
            for e in conformal.EMPLOYMENT for u in range(20) for n in conformal.HISTORY for h in range(1, 7)]
    df = pd.DataFrame(rows, columns=["world", "seed", "user_id", "employment_type", "n_history", "h",
                                     "p10", "p50", "p90", "truth"])
    table = recal.fit(df)
    assert table["users_per_type"] == {"employee": 20, "gig": 20, "student": 20}
    for e in conformal.EMPLOYMENT:
        assert set(table["offsets"][e]) == {"3", "4", "5", "6"}
        assert all(len(table["offsets"][e][n]) == 6 for n in table["offsets"][e])


def test_measures_count_coverage_tails_and_the_interval_score():
    m = recal.measures(lo=[0, 0, 0, 0], hi=[2, 2, 2, 2], med=[1, 1, 1, 1], y=[1, 1, -1, 3])
    assert (m["coverage"], m["below"], m["above"]) == (0.5, 0.25, 0.25)
    assert m["mean_width"] == 2
    assert m["interval_score"] == pytest.approx(2 + 10 * (1 + 1) / 4)   # width + 10 x distance outside


def test_the_primary_checks_follow_the_plan():
    def cell(cov, below, above, score):
        return {"coverage": cov, "below": below, "above": above, "interval_score": score}
    s = {f"{g}_n6_h6": {"raw": cell(0.73, 0.19, 0.08, 9.0), "adjusted": cell(0.80, 0.10, 0.10, 8.0)}
         for g in ("all",) + conformal.EMPLOYMENT}
    assert recal.primary(s)["all_hold"]
    s["gig_n6_h6"]["adjusted"]["coverage"] = 0.73
    assert recal.primary(s)["checks"] == {"P1": True, "P2": False, "P3": True, "P4": True}


@pytest.mark.parametrize("tracked, status, committed", [
    (True, "", True), (True, " M sim/monte_carlo_conformal.json\n", False), (False, "", False)])
def test_only_a_tracked_unchanged_table_counts_as_committed(monkeypatch, tracked, status, committed):
    def git(cmd, **kw):
        if "ls-files" in cmd:
            return SimpleNamespace(returncode=0 if tracked else 1, stdout="")
        return SimpleNamespace(returncode=0, stdout=status)
    monkeypatch.setattr(recal.subprocess, "run", git)
    assert recal.table_is_committed() is committed


def test_the_offsets_table_in_use_is_the_committed_one():
    """C1: the table the API reads is exactly the one committed before the evaluation."""
    assert recal.table_is_committed()


def test_evaluation_refuses_an_uncommitted_table(monkeypatch):
    monkeypatch.setattr(recal, "table_is_committed", lambda *a: False)
    with pytest.raises(SystemExit, match="commit"):
        recal.evaluate()


def test_calibration_refuses_to_overwrite_a_table(monkeypatch, tmp_path):
    existing = tmp_path / "table.json"
    existing.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(conformal, "TABLE", existing)
    with pytest.raises(SystemExit, match="runs once"):
        recal.calibrate()
