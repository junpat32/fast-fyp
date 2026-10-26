"""Structural robustness (D-139): the generator's alternative worlds are off by default and do what they say."""
import copy

import numpy as np
import pandas as pd
import pytest
import yaml

from generator.run import ROOT, generate
import ml.structural as st

BASE = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
N = 400


@pytest.fixture(scope="module")
def default():
    return generate({**copy.deepcopy(BASE), "n_users": N}, "medium", 61049, with_transactions=False)


def world(name):
    return generate(st.world_config(name, N), "medium", 61049, with_transactions=False)


def test_an_empty_alternative_is_exactly_the_frozen_world(default):
    same = generate({**copy.deepcopy(BASE), "n_users": N, "alternative": {}}, "medium", 61049, with_transactions=False)
    for k in ("users", "monthly", "flags", "labels", "latent", "latent_monthly"):
        assert same[k].equals(default[k]), k


def test_w1_impulsive_people_spend_more_under_pressure(default):
    def disc_after_pressure(t):
        m = t["monthly"].sort_values(["user_id", "month"]).copy()
        m["next_disc"] = m.groupby("user_id").spend_discretionary.shift(-1)
        lat = t["latent"].set_index("user_id").imp
        m["imp"] = m.user_id.map(lat)
        sel = (m.cushion_months < 1) & (m.imp > m.imp.median())
        return m.loc[sel, "next_disc"].mean()
    assert disc_after_pressure(world("W1 stress spending")) > disc_after_pressure(default)


def test_w2_job_loss_lasts_longer_and_income_ends_lower(default):
    def jobless_share(t):
        m = t["monthly"].merge(t["users"][["user_id", "employment_type"]], on="user_id")
        e = m[m.employment_type == "employee"]
        return (e.net_income == 0).mean(), e.groupby("user_id").net_income.last().mean()
    (j0, end0), (j2, end2) = jobless_share(default), jobless_share(world("W2 persistent income shocks"))
    assert j2 > j0 and end2 < end0


def test_w3_shocks_cluster_and_fall_more_on_unsteady_incomes(default):
    t3 = world("W3 correlated expenses")
    assert t3["monthly"].shock_count.mean() > default["monthly"].shock_count.mean()
    lat = t3["latent"].set_index("user_id").sigma_inc
    m = t3["monthly"].assign(volatile=lambda d: d.user_id.map(lat) > lat.median())
    assert m[m.volatile].shock_count.mean() > m[~m.volatile].shock_count.mean()


def test_pattern_differences_point_the_published_way_when_the_data_does():
    df = pd.DataFrame({"user_id": range(10), "income": np.arange(10.0) + 1, "ess_share": np.linspace(0.8, 0.4, 10),
                       "cushion12": np.linspace(0.1, 3, 10), "any_short": [1, 1, 1, 0, 1, 0, 0, 0, 0, 0],
                       "inc_cv": np.linspace(0.6, 0.0, 10), "bnpl_user": [True] * 5 + [False] * 5})
    df["inc_q"] = pd.qcut(df.income.rank(method="first"), 5, labels=False) + 1
    df["vol_t"] = pd.qcut(df.inc_cv.rank(method="first"), 3, labels=False) + 1
    s = st.pattern_stats(df)
    assert s["P1"] > 0 and s["P2"] > 0 and s["P3"] > 0 and s["P4"] > 0 and s["P5"] > 0
