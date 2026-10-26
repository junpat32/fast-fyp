"""Explanation fidelity and honesty (26 Oct brief E, D-137): the reasons are the model's exact arithmetic,
point the way the model does, and never hide a top factor without saying so."""
import numpy as np
import pytest

from engine.bands import load_thresholds
from engine.forecast import BINARY, FEATURES, NOTES, REASON_WORDS, _load, against_common_sense, forecast

ART = _load()
SCALER, LR = ART["model"][0], ART["model"][-1]
COEF = LR.coef_[0]
CONTINUOUS = [f for f in FEATURES if f not in BINARY]


def at_mean(**changes) -> dict:
    x = dict(zip(FEATURES, SCALER.mean_))
    x.update(changes)
    return x


def pushed(feature: str, logit: float) -> dict:
    """Everything at the training average except one feature, moved so its contribution is `logit`."""
    j = FEATURES.index(feature)
    return at_mean(**{feature: SCALER.mean_[j] + logit / COEF[j] * SCALER.scale_[j]})


def test_contributions_plus_intercept_are_exactly_the_models_score():
    rng = np.random.default_rng(0)
    for _ in range(200):
        z = rng.normal(0, 1.5, len(FEATURES))
        x = SCALER.mean_ + z * SCALER.scale_
        contrib = SCALER.transform([x])[0] * COEF
        assert contrib.sum() + LR.intercept_[0] == pytest.approx(float(ART["model"].decision_function([x])[0]), abs=1e-9)


def test_at_the_training_average_no_feature_contributes_and_there_are_no_reasons():
    f = forecast(at_mean())
    assert f.reasons == [] and f.note is None


@pytest.mark.parametrize("seed", range(20))
def test_every_reason_points_the_way_the_headline_does(seed):
    rng = np.random.default_rng(seed)
    x = dict(zip(FEATURES, SCALER.mean_ + rng.normal(0, 1.5, len(FEATURES)) * SCALER.scale_))
    for f in BINARY:                                       # yes/no features must be 0 or 1 to be reasons
        x[f] = float(rng.random() < 0.5)
    fc = forecast(x)
    raises = fc.probability > fc.base_rate
    for r in fc.reasons:
        assert r.direction == ("raises" if raises else "lowers")
        assert (r.contribution > 0) == raises
    assert [abs(r.contribution) for r in fc.reasons] == sorted((abs(r.contribution) for r in fc.reasons), reverse=True)


def test_a_top_factor_left_out_by_w1_is_disclosed_p9():
    assert load_thresholds()["explanations"]["drop_counterintuitive"]
    odd = [f for f in CONTINUOUS if f in REASON_WORDS
           and against_common_sense(f, COEF[FEATURES.index(f)])]
    assert odd, "forecast_v1 has counter-intuitive coefficients (D-92); the test needs one"
    for f in odd:
        fc = forecast(pushed(f, 6.0))                      # the only factor, pushing the risk up hard
        assert fc.probability > fc.base_rate
        assert f not in [r.feature for r in fc.reasons]    # left out (W1) ...
        assert fc.note == NOTES[(False, True)]             # ... and said so (P9)


def test_a_common_sense_top_factor_is_shown_and_needs_no_note():
    normal = [f for f in CONTINUOUS if not f.startswith(("type_", "age_", "band_"))
              and not against_common_sense(f, COEF[FEATURES.index(f)])]
    for f in normal:
        fc = forecast(pushed(f, 6.0))
        assert [r.feature for r in fc.reasons] == [f]
        assert fc.note is None
