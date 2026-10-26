"""DSR bands with hysteresis (spec §6). Canonical implementation: the generator, the API and
the tests all use this module. Thresholds come from shared/thresholds.json only (rule 5).

Band codes: INSUFFICIENT = -1, GREEN = 0, YELLOW = 1, RED = 2 (higher = worse).

Invariants
  B1  income below the insufficient-income threshold -> INSUFFICIENT, whatever the DSR
  B2  DSR < green_below -> GREEN; < red_at_or_above -> YELLOW; otherwise RED
  B3  hysteresis: if last month was RED and leave_red_below <= DSR < red_at_or_above -> RED
  B4  hysteresis needs a real RED month: after INSUFFICIENT (or with no previous month)
      the plain thresholds apply (D-27)
This module gives the band for ONE month. The app shows bands with an extra sequence rule
(a better band appears only after it has held for 2 months, D-49), applied in engine/state.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

INSUFFICIENT, GREEN, YELLOW, RED = -1, 0, 1, 2
NAMES = {INSUFFICIENT: "INSUFFICIENT_INCOME", GREEN: "GREEN", YELLOW: "YELLOW", RED: "RED"}

_THRESHOLDS_PATH = Path(__file__).resolve().parents[1] / "shared" / "thresholds.json"


def load_thresholds(path: Path = _THRESHOLDS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def band_array(dsr: np.ndarray, income_median3: np.ndarray, prev_band: np.ndarray | None,
               thresholds: dict | None = None) -> np.ndarray:
    """Vectorised band for one month. prev_band is None for the first month."""
    t = thresholds or load_thresholds()
    green, red, leave = t["dsr"]["green_below"], t["dsr"]["red_at_or_above"], t["dsr"]["leave_red_below"]
    dsr = np.asarray(dsr, dtype=float)
    out = np.where(dsr < green, GREEN, np.where(dsr < red, YELLOW, RED))
    if prev_band is not None:
        sticky = (np.asarray(prev_band) == RED) & (dsr >= leave) & (dsr < red)
        out = np.where(sticky, RED, out)
    out = np.where(np.asarray(income_median3, dtype=float) < t["insufficient_income_below_rm"], INSUFFICIENT, out)
    return out.astype(np.int8)


def band(dsr: float, income_median3: float, prev_band: int | None, thresholds: dict | None = None) -> int:
    """Scalar wrapper (used by the API and the tests)."""
    prev = None if prev_band is None else np.array([prev_band])
    return int(band_array(np.array([dsr]), np.array([income_median3]), prev, thresholds)[0])
