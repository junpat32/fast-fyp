"""T-25 (D-88): the one-at-a-time sensitivity analysis (ml/run_sensitivity.py). These tests check the
variants and the generator switches on tiny data; they never run the analysis itself."""
import copy

import numpy as np
import pandas as pd
import pytest
import yaml

import generator.bands as gb
from generator.run import ROOT, generate
from ml.run_sensitivity import (DEFAULT, NOT_VARIED, VARIANTS, insufficient_threshold, variant_config,
                                write_report)

BASE = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def test_every_row_of_the_register_is_varied_or_listed():
    """Spec §16: 30 assumptions; 28 are varied here (some in two parts), 2 the spec itself doesn't vary."""
    keys = {v.key for v in VARIANTS}
    register = [{"wage_spread"}, {"employment_mix"}, {"gig_median", "gig_cv"}, {"consumption"}, {"job_loss"},
                {"gig_spread"}, {"festive"}, {"shock_scale"}, {"semester"}, {"bnpl_share", "bnpl_rate"},
                {"pl_holding", "pl_payment"}, {"family_holding", "family_amount"}, {"parents_share", "parents_housing"},
                {"vehicle_payment"}, {"vehicle_own_employee"}, {"vehicle_own_student"}, {"vehicle_loan"},
                {"pay_rise", "gig_slow"}, {"rho_imp_dis", "rho_imp_ovc"}, {"insufficient"},
                {"cushion_shift", "cushion_cap"}, {"card_holding"}, {"card_limit"}, {"budget_rule"},
                {"correction_months", "correction_kappa"}, {"goal_stickiness"}, {"card_start_balance"}, {"car_tenure"}]
    assert set().union(*register) == keys
    assert len(register) + len(NOT_VARIED) == 30
    assert len({(v.key, v.setting) for v in VARIANTS}) == len(VARIANTS) == 67


@pytest.mark.parametrize("v", VARIANTS, ids=lambda v: f"{v.key}:{v.setting}")
def test_one_change_per_variant_on_a_copy(v):
    """V2: the variant changes its own setting(s) on a deep copy; the base config is untouched."""
    before = copy.deepcopy(BASE)
    cfg = variant_config(BASE, v)
    assert BASE == before
    changed = {k for k, val in flat(cfg).items() if flat(BASE).get(k, object()) != val}
    if v.insufficient_rm is not None:
        assert not changed and v.insufficient_rm != gb.SPEC_V1["insufficient_income_below_rm"]
    else:
        assert changed, "the variant changes nothing"
        assert len({k.rsplit(".", 1)[0] for k in changed}) <= 2       # one assumption (at most two sibling groups)


@pytest.mark.parametrize("v", VARIANTS, ids=lambda v: f"{v.key}:{v.setting}")
def test_variant_values_stay_valid(v):
    cfg = variant_config(BASE, v)
    mix = cfg["population"]["employment_mix"]
    assert sum(mix.values()) == pytest.approx(1.0)
    assert sum(b[0] for b in cfg["cushion_buckets"]) == pytest.approx(1.0)
    assert all(lo < hi for _, lo, hi in cfg["cushion_buckets"])
    t = cfg["traits"]
    corr = np.eye(3)
    corr[0, 1] = corr[1, 0] = t["rho_imp_dis"]
    corr[0, 2] = corr[2, 0] = t["rho_imp_ovc"]
    np.linalg.cholesky(corr)                                           # still a valid correlation matrix
    probs = [cfg["debt"]["personal_loan"]["p"], cfg["debt"]["family_support"]["p"], cfg["debt"]["vehicle_loan"]["p"],
             cfg["debt"]["bnpl"]["user_share"], cfg["debt"]["credit_card"]["share_of_workers"],
             cfg["income"]["pay_rise"]["p"], cfg["income"]["gig_slow"]["p"], cfg["income"]["job_loss"]["p_young"],
             *cfg["spending"]["living_with_parents"].values(), *cfg["debt"]["vehicles"]["employee"].values(),
             cfg["debt"]["vehicles"]["student"]["car"]]
    assert all(0 <= p <= 1 for p in probs)


def test_insufficient_threshold_is_swapped_for_one_variant_and_put_back():
    original = gb.SPEC_V1
    with insufficient_threshold(500):
        assert gb.SPEC_V1["insufficient_income_below_rm"] == 500
        assert gb.SPEC_V1["dsr"] == original["dsr"]
    assert gb.SPEC_V1 is original
    with pytest.raises(RuntimeError), insufficient_threshold(200):
        raise RuntimeError
    assert gb.SPEC_V1 is original


def tiny(cfg):
    cfg = copy.deepcopy(cfg)
    cfg["n_users"] = 40
    return generate(cfg, "medium", 20261009, with_transactions=False)


def test_generator_switches_change_nothing_by_default():
    """The two new switches (goal stickiness scale, higher credit limit above RM3,000) are absent from
    config.yaml; set to their neutral values they give byte-identical data, so the O2 datasets stand."""
    neutral = copy.deepcopy(BASE)
    neutral["behaviour"]["goal_stickiness_scale"] = 1.0
    neutral["debt"]["credit_card"]["limit_multiple_high"] = neutral["debt"]["credit_card"]["limit_multiple"]
    neutral["debt"]["credit_card"]["high_income_gross"] = 10 ** 9
    a, b = tiny(BASE), tiny(neutral)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_generator_switches_do_change_what_they_should():
    off = next(v for v in VARIANTS if v.key == "goal_stickiness" and v.setting == "off")
    limit = next(v for v in VARIANTS if v.key == "card_limit")
    base = tiny(BASE)
    assert not base["monthly"].savings_target.equals(tiny(variant_config(BASE, off))["monthly"].savings_target)
    high = tiny(variant_config(BASE, limit))["users"]
    rich = base["users"].has_credit_card & (base["users"].credit_limit > 2 * 3000)
    assert rich.any() and np.allclose(high.credit_limit[rich], base["users"].credit_limit[rich] * 1.5, atol=0.02)
    assert (high.credit_limit[~rich] == base["users"].credit_limit[~rich]).all()


def test_report(tmp_path):
    cols = dict(rows=6000, B0=0.28, B1=0.23, B2=0.26, lr=0.44, rf=0.42, xgb=0.43, best_ml="lr", best_baseline="B0",
                red_share=0.05, insufficient_share=0.01)
    rows = pd.DataFrame([
        {"key": "default", "assumption": DEFAULT.assumption, "setting": "-", "prevalence": 0.12, "delta": 0.16, **cols},
        {"key": "shock_scale", "assumption": "Shock scale k", "setting": "0.5", "prevalence": 0.08, "delta": 0.10, **cols},
        {"key": "shock_scale", "assumption": "Shock scale k", "setting": "1.7", "prevalence": 0.17, "delta": -0.01, **cols}])
    text = write_report(rows, tmp_path, {"lr": {"param": 0.1, "n_rounds": None}}, 1000, 900)
    assert (tmp_path / "SENSITIVITY.md").read_text(encoding="utf-8") == text
    assert "Δ > 0) in 1 of 2 settings" in text and "Smallest Δ: -0.010" in text
    assert text.index("| Shock scale k | 1.7 |") < text.index("| Shock scale k | 0.5 |")     # biggest change first
    assert all(x in text for x in NOT_VARIED)


def test_insufficient_share_counts_the_generators_own_band_label():
    """The generator labels these months "INSUFFICIENT_INCOME"; the summary once compared with
    "INSUFFICIENT" and always reported 0% (found on Patrick's --dev check, 2026-10-17)."""
    data = generate({**copy.deepcopy(BASE), "n_users": 60}, "medium", 7, with_transactions=False)
    from engine.bands import INSUFFICIENT, NAMES
    assert NAMES[INSUFFICIENT] in set(data["monthly"].band)
    src = (ROOT / "ml" / "run_sensitivity.py").read_text(encoding="utf-8")
    assert 'band == "INSUFFICIENT")' not in src
