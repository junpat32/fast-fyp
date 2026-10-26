"""Metrics, user-level bootstrap and leakage alarms (spec §13, frozen)."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def pr_auc(y, s, w=None) -> float:
    return float(average_precision_score(y, s, sample_weight=w))


def secondary(y, score, pred, calibrated=None, probabilistic=True) -> dict:
    """pred: 0/1 labels from the per-fold thresholds (each chosen on inner-CV predictions, D-44)."""
    out = {"threshold": "per fold (max F1 on inner-CV predictions of the training folds)",
           "recall_pos": float(recall_score(y, pred, zero_division=0)),
           "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
           "confusion": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
           "brier_raw": float(brier_score_loss(y, np.clip(score, 0, 1))) if probabilistic else None}
    if calibrated is not None:
        out["brier_calibrated"] = float(brier_score_loss(y, calibrated))
    return out


def bootstrap(df: pd.DataFrame, contenders: list[str], B: int, seed: int) -> np.ndarray:
    """User-level bootstrap: resample users with replacement; rows weighted by how often their user
    was drawn. Returns a B x K matrix of PR-AUCs."""
    rng = np.random.default_rng(seed)
    users = df.user_id.to_numpy()
    uniq, inv = np.unique(users, return_inverse=True)
    y = df.y.to_numpy()
    S = df[contenders].to_numpy()
    out = np.zeros((B, len(contenders)))
    for b in range(B):
        counts = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        w = counts[inv].astype(float)
        keep = w > 0
        for k in range(len(contenders)):
            out[b, k] = average_precision_score(y[keep], S[keep, k], sample_weight=w[keep])
    return out


def ci(samples: np.ndarray, level: float) -> tuple[float, float]:
    a = (1 - level) / 2
    return float(np.quantile(samples, a)), float(np.quantile(samples, 1 - a))


def pairwise(boot: np.ndarray, point: dict, contenders: list[str], level: float) -> list[dict]:
    rows = []
    for i, j in itertools.combinations(range(len(contenders)), 2):
        d = boot[:, i] - boot[:, j]
        lo, hi = ci(d, level)
        rows.append({"a": contenders[i], "b": contenders[j],
                     "delta": point[contenders[i]] - point[contenders[j]], "ci_low": lo, "ci_high": hi})
    return rows


def single_feature_pr_auc(X: pd.DataFrame, y, groups, features: list[str], folds: int) -> dict:
    """Leakage alarm: out-of-fold PR-AUC of a logistic model on each feature alone."""
    out = {}
    for f in features:
        v = X[[f]].to_numpy(dtype=float)
        if np.nanstd(v) == 0:
            out[f] = float(np.mean(y))
            continue
        oof = np.zeros(len(y))
        for tr, te in GroupKFold(folds).split(v, y, groups):
            m = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000))
            m.fit(v[tr], y[tr])
            oof[te] = m.predict_proba(v[te])[:, 1]
        out[f] = pr_auc(y, oof)
    return out
