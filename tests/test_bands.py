"""Band boundary tests from generator_spec.md §6 (also part of the O1 scenario suite)."""
import pytest

from generator.bands import GREEN, INSUFFICIENT, RED, YELLOW, band, load_thresholds

INC = 3000.0  # a normal income, well above the insufficient-income threshold


@pytest.mark.parametrize("dsr, prev, expected", [
    (0.59, None, YELLOW),     # just below Red
    (0.60, None, RED),        # exactly 60% is Red (D-04)
    (0.61, None, RED),
    (0.29, None, GREEN),
    (0.30, None, YELLOW),     # exactly 30% is Yellow
    (0.57, RED, RED),         # hysteresis: stays Red until below 55%
    (0.55, RED, RED),         # 55% itself is still Red
    (0.54, RED, YELLOW),      # leaves Red below 55%
    (0.57, YELLOW, YELLOW),   # hysteresis only applies after a Red month
    (0.57, INSUFFICIENT, YELLOW),  # D-27: needs a real Red month
    (0.20, RED, GREEN),       # a big drop goes straight to Green
])
def test_boundaries(dsr, prev, expected):
    assert band(dsr, INC, prev) == expected


def test_zero_income_is_insufficient_not_a_band():
    assert band(0.0, 0.0, None) == INSUFFICIENT
    assert band(9.9, 0.0, RED) == INSUFFICIENT


def test_insufficient_threshold_edge():
    limit = load_thresholds()["insufficient_income_below_rm"]
    assert band(0.10, limit - 0.01, None) == INSUFFICIENT
    assert band(0.10, limit, None) == GREEN


def test_thresholds_file_matches_claude_md_rule_5():
    t = load_thresholds()["dsr"]
    assert (t["green_below"], t["red_at_or_above"], t["leave_red_below"]) == (0.30, 0.60, 0.55)
    assert load_thresholds()["improvement_confirm_months"] == 2      # D-49


def test_generator_uses_the_frozen_v1_per_month_rule():
    """The generator applies the per-month v1 rule only; the app's 2-month confirmation (D-49)
    lives in engine/state.py and never reaches the O2 data."""
    from generator.bands import SPEC_V1
    assert "improvement_confirm_months" not in SPEC_V1
    assert band(0.28, INC, YELLOW) == GREEN
