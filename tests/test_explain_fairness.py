"""Explanations and subgroup reliability (D-137): the building blocks behave as the plan says."""
import numpy as np
import pandas as pd
import pytest

import ml.explain_fairness as ef


def test_a_group_is_judged_only_with_enough_users_and_positives():
    big = pd.DataFrame({"user_id": np.repeat(np.arange(120), 3), "y": ([1] + [0] * 2) * 120})
    small_users = big[big.user_id < 99]
    few_pos = big.assign(y=0).copy()
    few_pos.loc[few_pos.index[:29], "y"] = 1
    assert ef.judged(big) and not ef.judged(small_users) and not ef.judged(few_pos)


def test_measures_at_the_line_match_their_definitions():
    y = np.array([1, 1, 0, 0, 0, 1])
    p = np.array([0.9, 0.2, 0.4, 0.1, 0.05, 0.31])
    m = ef.at_line(y, p, 0.30)
    # flagged: 0.9, 0.4, 0.31 -> TP 2, FP 1; positives 3, negatives 3
    assert m == pytest.approx({"flagged": 0.5, "recall": 2 / 3, "precision": 2 / 3, "fpr": 1 / 3})


def test_line_for_recall_is_the_highest_line_reaching_the_target():
    y = np.array([1, 1, 1, 1, 0, 0])
    p = np.array([0.9, 0.7, 0.5, 0.3, 0.8, 0.1])
    line = ef.line_for_recall(y, p, 0.5)                       # 2 of 4 positives needed
    assert line == 0.7
    assert ef.at_line(y, p, line)["recall"] >= 0.5
    assert ef.at_line(y, p, line + 1e-9)["recall"] < 0.5        # any higher line misses the target


def test_per_group_lines_reach_about_the_target_recall_out_of_sample():
    rng = np.random.default_rng(3)
    n_users, per = 600, 6
    users = np.repeat(np.arange(n_users), per)
    kind = np.repeat(rng.choice(["employee", "gig", "student"], n_users, p=[0.6, 0.2, 0.2]), per)
    base = np.select([kind == "employee", kind == "gig"], [0.08, 0.17], 0.23)
    p = np.clip(base * rng.lognormal(0, 0.8, len(users)), 0.001, 0.99)
    y = (rng.random(len(users)) < p).astype(int)
    df = pd.DataFrame({"user_id": users, "employment_type": kind, "y": y, "lr_cal": p})
    out = ef.per_group_lines(df, 0.5)
    for name, r in out.items():
        assert r["recall"] == pytest.approx(0.5, abs=0.12), name
