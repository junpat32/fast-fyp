"""Expected months to recover from the Markov chain (sim/markov.py, sim/markov_recovery.py, D-143)."""
import numpy as np
import pandas as pd
import pytest

from ml.baselines import B2Markov
from sim import markov
from sim import markov_recovery as mr

TOY = np.array([[0.5, 0.3, 0.2],
                [0.2, 0.5, 0.3],
                [0.0, 0.0, 1.0]])


def test_the_docstring_trace_holds():
    r = markov.recovery(TOY, target=[2], ks=(1, 2))
    assert r[0]["mean"] == pytest.approx(1.6 / 0.38)              # 4.21 months
    assert r[1]["mean"] == pytest.approx(2 + 0.4 * 1.6 / 0.38)    # 3.68 months
    assert r[0]["within_1"] == pytest.approx(0.2)
    assert r[0]["within_2"] == pytest.approx(0.39)


def test_a_state_already_in_the_target_needs_no_months():
    assert markov.recovery(TOY, target=[2])[2] == {"mean": 0.0, "median": 0, "within_3": 1.0,
                                                    "within_6": 1.0, "within_12": 1.0}


def test_the_median_is_the_first_month_with_at_least_an_even_chance():
    r = markov.recovery(TOY, target=[2])
    within = [np.linalg.matrix_power(TOY, k)[0, 2] for k in range(1, 20)]     # R is already absorbing in TOY
    assert r[0]["median"] == 1 + next(i for i, p in enumerate(within) if p >= 0.5)


def test_the_mean_matches_a_simulation_of_the_chain():
    rng = np.random.default_rng(7)
    times = []
    for _ in range(20000):
        s, t = 0, 0
        while s != 2:
            s, t = rng.choice(3, p=TOY[s]), t + 1
        times.append(t)
    assert np.mean(times) == pytest.approx(markov.recovery(TOY, [2])[0]["mean"], rel=0.03)


def test_a_chain_where_a_state_cannot_reach_the_target_is_refused():
    stuck = np.array([[1.0, 0.0, 0.0], [0.2, 0.5, 0.3], [0.0, 0.0, 1.0]])
    with pytest.raises(ValueError, match="cannot reach"):
        markov.recovery(stuck, target=[2])


def test_the_targets_are_green_with_a_cushion_and_anything_but_red():
    assert [markov.name(s) for s in markov.RECOVERED] == ["Green, cushion 1-3 months", "Green, cushion 3+ months"]
    assert all(not markov.name(s).startswith("Red") for s in markov.OUT_OF_RED)
    assert {markov.name(s).split(",")[0] for s in range(9) if s not in markov.OUT_OF_RED} == {"Red"}


def _wide(paths):
    """paths: {user: [(band, cushion), ...]} -> band and cushion frames, users x months."""
    band = pd.DataFrame({u: [b for b, _ in p] for u, p in paths.items()}).T
    cush = pd.DataFrame({u: [c for _, c in p] for u, p in paths.items()}).T
    band.columns = cush.columns = range(1, band.shape[1] + 1)
    return band, cush


def test_the_chain_is_the_o2_baseline_chain():
    rng = np.random.default_rng(1)
    paths = {u: [(rng.choice(["GREEN", "YELLOW", "RED"]), rng.uniform(0, 5)) for _ in range(12)] for u in range(30)}
    band, cush = _wide(paths)
    assert np.array_equal(markov.transition_matrix(band, cush, range(10)),
                          B2Markov().fit(band, cush, range(10)).P)


def test_observed_recovery_counts_only_full_windows_and_skips_insufficient_income_starts():
    path = [("RED", 0.5), ("RED", 0.5), ("INSUFFICIENT_INCOME", 0.5), ("YELLOW", 0.5), ("GREEN", 2.0),
            ("GREEN", 2.0)] + [("GREEN", 2.0)] * 6
    band, cush = _wide({7: path})
    o = mr.observed(mr.states(band, cush), [7], markov.RECOVERED, k=3)
    # Starts: month 1 (Red), 2 (Red), 4 (Yellow); month 3 is insufficient income; months 5+ are recovered.
    assert o.state.tolist() == [6, 6, 3]
    assert o.reached.tolist() == [False, True, True]               # month 1 + 3 = month 4: not yet Green
    assert len(mr.observed(mr.states(band, cush), [7], markov.RECOVERED, k=11)) == 1   # only month 1 fits


def test_part_b_fits_each_chain_on_training_users_only(monkeypatch):
    rng = np.random.default_rng(2)
    paths = {u: [(rng.choice(["GREEN", "YELLOW", "RED"]), rng.uniform(0, 5)) for _ in range(12)] for u in range(50)}
    band, cush = _wide(paths)
    fitted = []
    real = markov.transition_matrix

    def spy(b, c, users):
        fitted.append(set(users))
        return real(b, c, users)
    monkeypatch.setattr(markov, "transition_matrix", spy)
    res = mr.part_b(band, cush, boot=20)
    assert len(fitted) == mr.FOLDS
    assert all(len(f) == 40 for f in fitted)                                   # 50 users, 5 folds
    assert set.union(*[set(range(50)) - f for f in fitted]) == set(range(50))  # each user held out once
    assert res["overall"] in ("consistent", "not consistent")


def test_a_verdict_needs_enough_start_months():
    paths = {u: [("RED", 0.5)] * 12 for u in range(3)} | {u: [("GREEN", 2.0)] * 12 for u in range(3, 50)}
    band, cush = _wide(paths)
    res = mr.part_b(band, cush, boot=20)
    red = res["cells"]["recovered"]["k3"]["Red, cushion under 1 month"]
    assert red["starts"] == 3 * 9 and red["verdict"] == "too few"
