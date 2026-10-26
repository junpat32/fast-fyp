"""3-month deterioration forecast for one user, with plain-language reasons (Must: SHAP explanation).

Model: ml/artifacts/forecast_v1.joblib (logistic regression chosen by the pre-registered O2 rule,
isotonic-calibrated; see forecast_v1.json). For a linear model the SHAP value of feature j is
coef_j x (standardised x_j), so reasons are exact, not approximated.

Invariants
  P1  the probability shown is the CALIBRATED one (D-44); raw class-weighted scores are never shown
  P2  reasons never cite a flag that failed check S14 (D-41): only "user_facing_flags" may appear
  P3  inputs must be features from engine.features (same definitions as O2; tests/test_equivalence.py)
  P4  reasons are things a user can read and act on: no demographics (age, user type), no band
      indicators (the band is shown on its own), and a yes/no feature only when it is "yes"
  P5  above the training base rate the reasons are what RAISES the risk; at or below it, what is
      KEEPING the risk low (so a low-risk user isn't shown noise as "reasons")
  P6  honesty: if a hidden demographic factor (user type, age group) is among the top factors in
      that direction, a note says so instead of silently leaving it out
  P7  never 0% or 100%: the isotonic calibration's end bins rest on few training rows, so the
      probability shown stays between 2% and 98% (D-90; the side of the base rate is unchanged)
  P8  each reason has plain words for the user's side of the training average (reasons.yaml,
      D-92); with "explanations.drop_counterintuitive" on, a reason whose coefficient points against
      common sense (related features overlapping, e.g. savings rate) is left out (decision W1)
  P9  honesty for P8: if a reason left out that way is among the top factors in the shown direction,
      the note says other patterns also affect the estimate, so the reasons never claim to be the
      whole story (D-137)

Units (D-133): a contribution is coefficient x standardised value, in log-odds of the model's raw
(class-weighted) score, relative to the training average; contributions plus the intercept give that
raw logit exactly. The probability shown is calibrated afterwards, so a contribution is never "N% of
the risk", and it describes the model's arithmetic, not a cause.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import yaml

from .bands import load_thresholds
from .features import FEATURES, LABELS

ARTIFACT = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "forecast_v1.joblib"
REASON_WORDS = yaml.safe_load(Path(__file__).with_name("reasons.yaml").read_text(encoding="utf-8"))
FLAG_FEATURES = {"flag_impulsivity": "impulsivity", "flag_overconfidence": "overconfidence",
                 "flag_delayed_correction": "delayed_correction"}
PROB_FLOOR = 0.02                                                       # P7
# P6 and P9: what a note discloses when top factors can't be shown as reasons. DRAFT wording (W2)
NOTES = {(False, False): None,
         (True, False): "Your type of work and age group also affect this estimate.",
         (False, True): "Some other patterns in the data also affect this estimate.",
         (True, True): "Your type of work and age group, and some other patterns in the data, also affect this estimate."}
BINARY = {f for f in FEATURES if f.startswith(("type_", "age_", "band_", "flag_"))} | {
    "has_personal_loan", "lives_with_parents", "family_support", "shortfall_last3", "festive_next3", "semester_next3"}


@dataclass
class Reason:
    feature: str
    label: str
    value: float
    contribution: float     # SHAP value (log-odds units, before calibration)
    direction: str          # "raises" or "lowers"
    text: str = ""          # plain words for the user (P8)


@dataclass
class Forecast:
    probability: float      # calibrated chance of getting worse in the next 3 months
    base_rate: float        # share of people who got worse in the training data
    reasons: list[Reason]   # up to 3; see P5 for their direction
    version: str
    note: str | None = None  # P6


@lru_cache(maxsize=1)
def _load(path: str = str(ARTIFACT)) -> dict:
    art = joblib.load(path)
    if list(art["features"]) != list(FEATURES):
        raise RuntimeError("forecast artifact was built with a different feature list")
    card = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    art["base_rate"] = float(card["trained_on"]["prevalence"])
    return art


def _eligible(f: str, value: float, shown_flags: set) -> bool:
    if f.startswith(("type_", "age_", "band_")):                       # P4
        return False
    if f in FLAG_FEATURES and FLAG_FEATURES[f] not in shown_flags:     # P2
        return False
    if f in BINARY and value != 1:                                     # P4: only a "yes" is a reason
        return False
    return True


def against_common_sense(feature: str, coef: float) -> bool:
    """The model raises the risk when this feature is high, but common sense says it lowers it (or
    the reverse): the model is offsetting a related feature (P8, decision W1)."""
    return (coef > 0) != (REASON_WORDS[feature]["expected"] == "raises")


def forecast(features: dict, top: int = 3) -> Forecast:
    art = _load()
    x = np.array([[features[f] for f in FEATURES]], dtype=float)
    pipe = art["model"]
    raw = float(pipe.predict_proba(x)[0, 1])
    prob = float(art["calibrator"].predict([raw])[0])
    scaler, lr = pipe[0], pipe[-1]
    z = scaler.transform(x)[0]
    contrib = z * lr.coef_[0]
    t = load_thresholds()
    shown = set(t["user_facing_flags"])
    drop = t.get("explanations", {}).get("drop_counterintuitive", False)
    raises = prob > art["base_rate"]                                   # P5
    order = np.argsort(-contrib) if raises else np.argsort(contrib)
    reasons = []
    for j in order:
        if len(reasons) == top or (contrib[j] <= 0 if raises else contrib[j] >= 0):
            break
        f = FEATURES[j]
        if _eligible(f, x[0, j], shown) and not (drop and against_common_sense(f, lr.coef_[0][j])):
            reasons.append(Reason(f, LABELS[f], float(x[0, j]), float(contrib[j]),
                                  "raises" if raises else "lowers",
                                  REASON_WORDS[f]["high" if z[j] > 0 else "low"]))      # P8
    same_way = [j for j in order[:top] if (contrib[j] > 0 if raises else contrib[j] < 0)]
    hidden_demo = any(FEATURES[j].startswith(("type_", "age_")) and x[0, j] == 1 for j in same_way)
    hidden_other = drop and any(_eligible(FEATURES[j], x[0, j], shown) and against_common_sense(FEATURES[j], lr.coef_[0][j])
                                for j in same_way)                                       # P9
    note = NOTES[(hidden_demo, hidden_other)]                                          # P6, P9
    shown_prob = min(max(prob, PROB_FLOOR), 1 - PROB_FLOOR)            # P7
    return Forecast(probability=round(shown_prob, 4), base_rate=round(art["base_rate"], 4), reasons=reasons,
                    version=art["version"], note=note)
