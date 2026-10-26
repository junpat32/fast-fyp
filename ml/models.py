"""ML models with nested tuning (spec §13, frozen; D-44).

For one outer training set:
  tune      inner GroupKFold(3) over the grid; pick the highest inner PR-AUC
            (ties -> the earlier, simpler setting: grids are ordered simplest first)
  refit     the chosen setting on the whole outer training set
  threshold maximise F1 on the inner out-of-fold predictions of the chosen setting
  calibrate isotonic regression fitted on the same inner out-of-fold predictions
XGBoost: early stopping on each inner validation fold; the refit uses the median best
iteration of the chosen depth (no validation set exists at refit).
"""
from __future__ import annotations

import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261009


def make_model(name: str, param, cfg: dict, spw: float = 1.0, n_rounds: int | None = None, early: bool = False):
    g, nj = cfg["grids"], cfg["n_jobs"]
    if name == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=param, class_weight="balanced", max_iter=5000))
    if name == "rf":
        return RandomForestClassifier(n_estimators=g["rf"]["n_estimators"], max_depth=param,
                                      class_weight="balanced", n_jobs=nj, random_state=SEED)
    if name in ("xgb", "oracle"):
        return xgb.XGBClassifier(max_depth=param, learning_rate=g["xgb"]["learning_rate"],
                                 n_estimators=n_rounds or g["xgb"]["max_rounds"], scale_pos_weight=spw,
                                 eval_metric="aucpr", tree_method="hist", n_jobs=nj, random_state=SEED,
                                 early_stopping_rounds=g["xgb"]["early_stopping_rounds"] if early else None)
    raise ValueError(name)


def grid_of(name: str, cfg: dict) -> list:
    g = cfg["grids"]
    return {"lr": g["lr"]["C"], "rf": g["rf"]["max_depth"], "xgb": g["xgb"]["max_depth"],
            "oracle": g["xgb"]["max_depth"]}[name]


def _spw(y) -> float:
    pos = max(1, int(np.sum(y)))
    return (len(y) - pos) / pos


def _fit_predict(name, param, cfg, Xtr, ytr, Xva=None, yva=None, n_rounds=None):
    """Fit and predict; for XGB with a validation set, early-stop and return the best iteration."""
    if name in ("xgb", "oracle") and Xva is not None and n_rounds is None:
        m = make_model(name, param, cfg, spw=_spw(ytr), early=True)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        return m.predict_proba(Xva)[:, 1], m.best_iteration + 1, m
    m = make_model(name, param, cfg, spw=_spw(ytr), n_rounds=n_rounds)
    m.fit(Xtr, ytr)
    return (m.predict_proba(Xva)[:, 1] if Xva is not None else None), n_rounds, m


def f1_threshold(y, s) -> float:
    p, r, th = precision_recall_curve(y, s)
    f1 = np.where(p[:-1] + r[:-1] > 0, 2 * p[:-1] * r[:-1] / np.maximum(p[:-1] + r[:-1], 1e-12), 0)
    return float(th[int(np.argmax(f1))])


def tune_and_fit(name: str, cfg: dict, X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict:
    """Inner-CV tuning on one outer training set, then refit. Returns the fitted model and extras."""
    inner = GroupKFold(n_splits=cfg["inner_folds"])
    best = None
    for param in grid_of(name, cfg):
        oof, iters = np.zeros(len(y)), []
        for tr, va in inner.split(X, y, groups):
            pred, it, _ = _fit_predict(name, param, cfg, X[tr], y[tr], X[va], y[va])
            oof[va] = pred
            iters.append(it)
        score = average_precision_score(y, oof)
        if best is None or score > best["inner_pr_auc"] + 1e-12:
            best = {"param": param, "inner_pr_auc": score, "inner_oof": oof,
                    "n_rounds": int(np.median(iters)) if name in ("xgb", "oracle") else None}
    _, _, model = _fit_predict(name, best["param"], cfg, X, y, n_rounds=best["n_rounds"])
    best["model"] = model
    best["threshold"] = f1_threshold(y, best["inner_oof"])
    best["iso"] = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(best["inner_oof"], y)
    return best


def fit_fixed(name: str, cfg: dict, param, n_rounds, X, y):
    """Robustness runs: no re-tuning (D-44)."""
    _, _, model = _fit_predict(name, param, cfg, X, y, n_rounds=n_rounds)
    return model
