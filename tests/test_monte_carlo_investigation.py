"""Verify that the audit uses the same origin and never supplies future records."""
from types import SimpleNamespace
import pandas as pd
import pytest
from sim import investigate_monte_carlo as audit


@pytest.mark.parametrize('n_history', [3, 6])
def test_audit_forecast_origin_and_target_alignment(monkeypatch, n_history):
    user = dict(user_id=1, employment_type='employee', festive_month=12,
                has_car=False, has_motorbike=False)
    rows = [dict(user_id=1, month=m, net_income=100, commitments_total=0,
                 outstanding_debt=0, cash=m*10, spend_essential=10,
                 spend_total=10, spend_education=0, family_support=0,
                 bnpl_purchases=0, pay_bnpl=0,
                 late_fees=0, event_shock_cost=0, event_minor_cost=0)
            for m in range(1,13)]
    monkeypatch.setattr(audit, 'generate', lambda *a, **kw:
                        {'users':pd.DataFrame([user]), 'monthly':pd.DataFrame(rows)})
    def forecast(history, profile, game, **kw):
        assert [r.month for r in history] == list(range(7-n_history,7))
        assert game.counted_money == 60
        # True future cushion is calendar month number; exact intervals must cover.
        return SimpleNamespace(cushion=[SimpleNamespace(p10=m,p50=m,p90=m)
                                        for m in range(7,13)])
    monkeypatch.setattr(audit, 'simulate_future', forecast)
    scores = audit.world(1, 'full', n_history)
    for h in (1,3,6):
        assert scores[f'all_h{h}']['coverage'] == 1
        assert scores[f'all_h{h}']['median_error'] == 0
