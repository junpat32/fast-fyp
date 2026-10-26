"""O2 pipeline invariants (spec §11, §13; CLAUDE.md rules 1-3). Small dataset for speed."""
import numpy as np
import pandas as pd
import pytest
import yaml

from generator.run import ROOT, generate
from ml.baselines import B2Markov, b1_score, cushion_bucket
from ml.evaluate import bootstrap, ci
from ml.features import FEATURES, build_features, check_no_lookahead


@pytest.fixture(scope="module")
def tables():
    cfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
    cfg["n_users"] = 150
    return generate(cfg, "medium", 4242, with_transactions=False)


def test_rule1_features_never_read_future_months(tables):
    assert check_no_lookahead(tables["monthly"], tables["users"], tables["flags"])


def test_rule3_no_hidden_traits_in_features():
    hidden = {"imp", "dis", "ovc", "sigma_inc", "consumption_ratio", "hidden_cost", "start_cushion_months"}
    assert not hidden & set(FEATURES)


def test_feature_rows_follow_label_rule(tables):
    X = build_features(tables["monthly"], tables["users"], tables["flags"], tables["labels"])
    assert set(X.t.unique()) <= set(range(3, 10))
    assert X.y.isin([0, 1]).all()
    assert (X.band_t != "INSUFFICIENT_INCOME").all()
    assert np.isfinite(X[FEATURES].to_numpy()).all()


def test_markov_chain_invariants(tables):
    mo = tables["monthly"]
    bw = mo.pivot(index="user_id", columns="month", values="band")
    cw = mo.pivot(index="user_id", columns="month", values="cushion_months")
    m = B2Markov().fit(bw, cw, bw.index[:100])
    assert np.allclose(m.P.sum(axis=1), 1.0)
    for band_rank, s in m.score_by_start.items():
        assert ((s >= 0) & (s <= 1 + 1e-12)).all()
        assert np.allclose(s[[0, 3, 6]], 1.0)          # lowest cushion bucket is a target for every band
    assert np.allclose(m.score_by_start[0][[3, 4, 5, 6, 7, 8]], 1.0)   # from Green, Yellow/Red are worse
    assert np.allclose(m.score_by_start[2][[0, 3, 6]], 1.0)           # from Red only the cushion target remains


def test_b1_formula():
    X = pd.DataFrame({"dsr_t": [0.49, 0.50, 0.9], "cushion_t": [2.0, 1.49, 0.2],
                      "flag_impulsivity": [0, 1, 1], "flag_overconfidence": [0, 0, 1],
                      "flag_delayed_correction": [0, 0, 1], "bnpl_active": [1, 2, 5]})
    assert list(b1_score(X)) == [0, 1 + 1 + 1 + 1, 1 + 1 + 3 + 1]


def test_cushion_buckets():
    assert list(cushion_bucket([0.0, 0.99, 1.0, 2.99, 3.0, 9])) == [0, 0, 1, 1, 2, 2]


def test_bootstrap_resamples_users_not_rows():
    df = pd.DataFrame({"user_id": np.repeat(np.arange(50), 4), "y": np.tile([0, 0, 0, 1], 50),
                       "a": np.random.default_rng(0).random(200)})
    boot = bootstrap(df, ["a"], 50, 1)
    lo, hi = ci(boot[:, 0], 0.95)
    assert boot.shape == (50, 1) and 0 <= lo <= hi <= 1
