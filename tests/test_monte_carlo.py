"""T-15: deterministic mechanics and untuned synthetic coverage."""
import numpy as np
import pytest
import yaml

from engine.state import MonthRecord
from generator.run import ROOT, generate
from sim.monte_carlo import (DebtPlan, FutureProfile, GameSnapshot,
                             compare_debt_plans, simulate_future)
import sim.monte_carlo as monte_carlo


def _history(incomes=(2500, 2500, 2500), month=3):
    return [MonthRecord(net_income=x, debt_payments=200, outstanding_debt=2000,
                        cash=1000, essential_spending=900, total_spending=1500,
                        month=month - len(incomes) + i + 1)
            for i, x in enumerate(incomes)]


GAME = GameSnapshot(1000, 0, 1100, 2)


def test_seed_ranges_probabilities_and_tail():
    args = (_history(), FutureProfile("employee", has_motorbike=True), GAME)
    a = simulate_future(*args, seed=51, paths=300)
    assert a == simulate_future(*args, seed=51, paths=300)
    assert len(a.cushion) == 6
    assert all(0 <= x.p10 <= x.p50 <= x.p90 for x in a.cushion)
    assert 0 <= a.shortfall_probability <= 1
    assert a.expected_shortfall <= a.cash_flow_at_risk
    assert 2 <= a.median_path_room_level <= 5


def test_zero_income_and_existing_room_never_downgrades():
    h = _history((0, 0, 0))
    result = simulate_future(h, FutureProfile("student"), GameSnapshot(0, 0, 1100, 4),
                             seed=1, paths=200)
    assert result.shortfall_probability == 1
    assert result.median_path_room_level == 4
    assert result.cushion[-1].p90 == 0


def test_gig_history_has_wider_range_at_same_average():
    emp = simulate_future(_history(), FutureProfile("employee"), GAME, seed=15, paths=1000)
    gig = simulate_future(_history((1000, 2500, 4000)), FutureProfile("gig"), GAME,
                          seed=15, paths=1000)
    assert gig.cushion[-1].p90 - gig.cushion[-1].p10 > emp.cushion[-1].p90 - emp.cushion[-1].p10


def test_festive_calendar_widens_cost_outcome():
    h = _history(month=3)
    festive = simulate_future(h, FutureProfile("employee", festive_month=4), GAME,
                               seed=123, paths=1000, horizon=1)
    usual = simulate_future(h, FutureProfile("employee"), GAME,
                            seed=123, paths=1000, horizon=1)
    assert festive.cushion[0].p50 < usual.cushion[0].p50


def test_invalid_inputs():
    with pytest.raises(ValueError):
        simulate_future(_history()[:2], FutureProfile("gig"), GAME, seed=0)
    with pytest.raises(ValueError):
        simulate_future(_history(), FutureProfile("gig"), GAME, seed=0, paths=1)


def test_avalanche_and_snowball_use_explicit_rates():
    debts = [DebtPlan("credit_card", 3000, 100, 0.18),
             DebtPlan("ptptn", 1000, 50, 0.01)]
    result = compare_debt_plans(debts, 200)
    assert result.avalanche_months is not None
    assert result.snowball_months is not None
    assert result.avalanche_interest <= result.snowball_interest


def test_bnpl_purchases_repaid_over_three_months(monkeypatch):
    monkeypatch.setattr(monte_carlo, '_deck', lambda: {'deck': []})
    h = [MonthRecord(0, 100, 0, 1000, 100, 400, month=m,
                     bnpl_purchases=300, bnpl_instalments=100)
         for m in (1, 2, 3)]
    result = simulate_future(h, FutureProfile('gig'), GAME, seed=3,
                             paths=100, horizon=3)
    assert result.cushion[0].p50 == pytest.approx(600 / ((200 + 200 + 400) / 3))
    assert result.cushion[1].p50 == pytest.approx(200 / ((200 + 400 + 400) / 3))
    assert result.cushion[2].p50 == 0


def test_semester_uplift_applies_only_to_education_essentials(monkeypatch):
    monkeypatch.setattr(monte_carlo, '_deck', lambda: {'deck': []})
    h = [MonthRecord(0, 0, 0, 1000, 200, 200, month=7,
                     education_spending=100) for _ in range(3)]
    g = GameSnapshot(1000, 0, 200, 1)
    semester = simulate_future(h, FutureProfile('student'), g,
                               seed=4, paths=100, horizon=1)
    regular = simulate_future(h, FutureProfile('student', semester_months=()), g,
                              seed=4, paths=100, horizon=1)
    assert semester.cushion[0].p50 == pytest.approx(785 / ((200 + 200 + 215) / 3))
    assert regular.cushion[0].p50 == pytest.approx(800 / 200)


def _records(rows):
    return [MonthRecord(net_income=float(r.net_income), debt_payments=float(r.commitments_total),
                        outstanding_debt=float(r.outstanding_debt), cash=float(r.cash),
                        essential_spending=float(r.spend_essential), total_spending=float(r.spend_total),
                        bnpl_purchases=float(r.bnpl_purchases),
                        bnpl_instalments=float(r.pay_bnpl),
                        education_spending=float(r.spend_education),
                        family_support=float(r.family_support),
                        event_costs=float(r.event_shock_cost + r.event_minor_cost),
                        other_fees=float(r.late_fees), month=int(r.month))
            for r in rows.itertuples()]


@pytest.fixture(scope="module")
def coverage():
    cfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
    cfg["n_users"] = 120
    data = generate(cfg, "medium", 20261015, with_transactions=False)
    by_user = data["monthly"].groupby("user_id", sort=False)
    outcomes = []
    for u in data["users"].itertuples():
        rows = by_user.get_group(u.user_id).sort_values("month")
        recs = _records(rows)
        profile = FutureProfile(u.employment_type, int(u.festive_month),
                                bool(u.has_car), bool(u.has_motorbike))
        for observed in (3, 6):
            # Only observations available at the forecast date are passed in.
            game = GameSnapshot(recs[observed - 1].cash, 0,
                                max(1, np.mean([r.essential_spending + r.debt_payments
                                                for r in recs[:observed]])), 1)
            result = simulate_future(recs[:observed], profile, game,
                                     seed=1000 + int(u.user_id) + observed,
                                     paths=500, horizon=6)
            truth = recs[observed + 5].cash / max(1, np.mean([
                r.essential_spending + r.debt_payments
                for r in recs[observed + 3:observed + 6]]))
            hit = result.cushion[-1].p10 <= truth <= result.cushion[-1].p90
            outcomes.append((observed, u.employment_type, hit))
    return outcomes


def test_calibration_reports_actual_coverage(coverage):
    for observed in (3, 6):
        group = [hit for n, _, hit in coverage if n == observed]
        print(f"\nT-15 synthetic terminal P10-P90 coverage, {observed} observed months: "
              f"{sum(group)}/{len(group)} = {np.mean(group):.1%}")
        for kind in ("employee", "gig", "student"):
            subset = [hit for n, t, hit in coverage if n == observed and t == kind]
            print(f"  {kind}: {sum(subset)}/{len(subset)} = {np.mean(subset):.1%}")
        assert len(group) == 120
