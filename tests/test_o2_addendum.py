"""D-98: the O2 addendum reports every pre-registered item from the saved run (no re-run), and the
Monte Carlo comparator looks only backwards. Skips when the synthetic data isn't on this machine."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import ml.mc_comparator as mc
from ml import report_addendum as ra
from ml.report import secondary_table

HAVE_DATA = (ra.DATA / f"medium_seed{ra.SEED}" / "labels.parquet").exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="synthetic data not generated on this machine")


@needs_data
def test_addendum_covers_every_pre_registered_item_for_every_noise_level():
    text = ra.render(ra.load_metrics(), ra.exclusions(), "x" * 64, "x" * 64)
    for item, _ in ra.CHECKLIST:
        assert item in text
    for nz in ra.NOISE:
        assert text.count(f"### {nz}") == 3                         # secondary, breakdown, by type
    assert "| medium | 7000 | 354 | 5.1% | insufficient income 354 |" in text
    assert "matches" in text and "B0 and B2 have identical confusion matrices" in text


@needs_data
def test_shared_tables_reproduce_the_original_report_exactly():
    """The refactor of ml/report.py changed nothing the 2026-10-12 report printed."""
    original = (ra.RESULTS / "O2_REPORT.md").read_text(encoding="utf-8")
    for line in secondary_table(ra.load_metrics()["medium"]):
        assert line in original


@needs_data
def test_a_changed_frozen_spec_is_flagged():
    text = ra.render(ra.load_metrics(), ra.exclusions(), "a" * 64, "b" * 64)
    assert "**DOES NOT MATCH**" in text


# ---- the comparator (rule 1: only months up to t)
def month(k):
    return SimpleNamespace(net_income=3000, commitments_total=300, outstanding_debt=5000, cash=1000 + k,
                           spend_essential=1500, spend_total=2200, family_support=0, month=k, bnpl_purchases=0,
                           pay_bnpl=0, spend_education=0, late_fees=0, event_shock_cost=0, event_minor_cost=0)


@pytest.mark.parametrize("t, months", [(3, [1, 2, 3]), (5, [1, 2, 3, 4, 5]), (9, [4, 5, 6, 7, 8, 9])])
def test_comparator_history_is_up_to_six_past_months_only(monkeypatch, t, months):
    seen = {}

    def fake(hist, profile, game, *, seed, paths, horizon):
        seen.update(months=[h.month for h in hist], horizon=horizon, paths=paths, seed=seed, cash=game.counted_money)
        return SimpleNamespace(shortfall_probability=0.25)

    monkeypatch.setattr(mc, "simulate_future", fake)
    user = SimpleNamespace(user_id=7, employment_type="employee", festive_month=3, has_car=False, has_motorbike=True)
    assert mc.score([month(k) for k in range(1, 13)], user, t) == 0.25
    assert seen["months"] == months and seen["horizon"] == 3 and seen["paths"] == 2000
    assert seen["seed"] == 50_000 + 700 + t and seen["cash"] == 1000 + t


def test_comparator_scores_one_real_row():
    user = SimpleNamespace(user_id=1, employment_type="gig", festive_month=1, has_car=False, has_motorbike=True)
    p = mc.score([month(k) for k in range(1, 13)], user, 6)
    assert 0 <= p <= 1 and p == mc.score([month(k) for k in range(1, 13)], user, 6)     # reproducible


def test_comparator_evaluation_shape():
    rng = np.random.default_rng(0)
    n = 300
    oof = pd.DataFrame({"user_id": np.repeat(np.arange(60), 5), "t": np.tile(np.arange(3, 8), 60),
                        "y": rng.integers(0, 2, n), "shortfall_t1_t3": rng.integers(0, 2, n).astype(bool),
                        "lr": rng.random(n), "B0": rng.random(n)})
    r = mc.evaluate(oof, rng.random(n), B=20, seed=1, level=0.95)
    for target in ("label", "shortfall_part"):
        assert set(r[target]["point"]) == {"mc", "lr", "B0"} and len(r[target]["mc_minus_lr"]) == 3


# ---- the overnight runner (Patrick runs it; here with stand-in jobs)
def test_overnight_keeps_going_after_a_failure_and_logs_everything(tmp_path, capsys):
    from ml import overnight
    ran = []

    def boom():
        raise RuntimeError("stand-in failure")

    status = overnight.main([("first", lambda: ran.append(1)), ("second", boom), ("third", lambda: ran.append(3))],
                            log=tmp_path / "log.txt")
    assert ran == [1, 3] and status == {"first": "done", "second": "FAILED (see above)", "third": "done"}
    text = (tmp_path / "log.txt").read_text(encoding="utf-8")
    assert "stand-in failure" in text and "ALL FINISHED" in text
