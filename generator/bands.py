"""Band calculator for the generator: the canonical engine/bands.py logic, pinned to the FROZEN
spec-v1.0 thresholds (shared/thresholds_spec_v1.json), so the O2 datasets stay reproducible
even when the app's live rule changes (D-49)."""
from pathlib import Path

from engine.bands import GREEN, INSUFFICIENT, NAMES, RED, YELLOW, load_thresholds  # noqa: F401
from engine.bands import band as _band
from engine.bands import band_array as _band_array

SPEC_V1 = load_thresholds(Path(__file__).resolve().parents[1] / "shared" / "thresholds_spec_v1.json")


def band_array(dsr, income_median3, prev_band, thresholds=None):
    return _band_array(dsr, income_median3, prev_band, thresholds or SPEC_V1)


def band(dsr, income_median3, prev_band, thresholds=None):
    return _band(dsr, income_median3, prev_band, thresholds or SPEC_V1)
