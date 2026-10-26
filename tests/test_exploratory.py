"""D-101: the exploratory checks' building blocks (the full run reads the synthetic data, which tests
don't need)."""
import pandas as pd
import pytest

from engine.features import FEATURES
from engine.rules import _ADVICE
from ml import exploratory as ex


def test_every_driver_with_advice_is_a_real_feature_and_rule():
    rules = {k.split("_")[0] for k in _ADVICE}
    for feature, addressed_by in ex.RULE_FOR.items():
        assert feature in FEATURES
        assert all(r.split(" ")[0] in rules for r in addressed_by)


@pytest.mark.parametrize("word, n", [("cushion", 2), ("debt", 1), ("essentials", 3), ("money", 2), ("RM400", 1),
                                     ("simple", 2), ("make", 1)])
def test_syllable_rule(word, n):
    assert ex.syllables(word) == n


def test_flesch_prefers_short_plain_sentences():
    plain, hard = ex.flesch("Save a little each week."), ex.flesch(
        "Accumulating discretionary expenditure considerably jeopardises liquidity.")
    assert plain[0] > 60 > hard[0] and plain[1] < hard[1]


def test_reliability_bins_cover_every_row():
    g = pd.DataFrame({"lr_cal": [i / 100 for i in range(100)], "y": [int(i >= 80) for i in range(100)]})
    bins = ex.reliability(g)
    assert len(bins) == 5 and sum(n for *_, n in bins) == 100
    assert bins[0][1] == 0 and bins[-1][1] == 1                        # lowest bin never, highest always


def test_readability_covers_every_text_the_app_shows():
    texts = ex.readability()
    advice = sum(1 for v in _ADVICE.values() for k in v if k.startswith("text"))
    assert sum(t["what"].startswith("advice") for t in texts) == advice
    assert any(t["what"].startswith("forecast note") for t in texts)


def test_ece_and_the_fa1_rule():
    import numpy as np
    from ml import check_v2 as cv
    p = np.array([0.1] * 50 + [0.5] * 50)
    y = np.array([0] * 45 + [1] * 5 + [0] * 25 + [1] * 25)
    assert cv.ece(p, y, bins=2) < 1e-9                                  # each bin's rate equals its prediction
    assert abs(cv.ece(np.full(100, 0.5), np.zeros(100)) - 0.5) < 1e-9
    assert (cv.MEAN_GAP, cv.ECE_TOLERANCE) == (0.02, 0.015)                         # the rule written in advance
    assert not any(f.startswith(("type_", "age_")) for f in cv.V2_FEATURES) and len(cv.V2_FEATURES) == 25
