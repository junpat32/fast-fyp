"""Baselines B0-B2 (spec §13, frozen).

B0  persistence with base rates: P(y | band_t, cushion bucket), estimated on training rows
B1  rule heuristic: 1[DSR >= 0.5] + 1[cushion < 1.5] + active flags + 1[active BNPL >= 2]; no fitting
B2  Markov chain over band x cushion bucket (9 states), Laplace alpha = 1, training users only;
    score = P(reach a worse band or the lowest cushion bucket within 3 steps), targets absorbing
Cushion buckets: {<1, 1-3, >=3 months} (spec §13).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BAND_RANK = {"GREEN": 0, "YELLOW": 1, "RED": 2}
HORIZON = 3


def cushion_bucket(c) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c < 1, 0, np.where(c < 3, 1, 2))


def state_of(band: np.ndarray, cushion: np.ndarray) -> np.ndarray:
    return np.array([BAND_RANK[b] for b in band]) * 3 + cushion_bucket(cushion)


# ---------------- B0 ----------------
class B0:
    def fit(self, X: pd.DataFrame, y: np.ndarray):
        key = X.band_t.to_numpy() + "|" + cushion_bucket(X.cushion_t).astype(str)
        df = pd.DataFrame({"k": key, "y": y})
        self.table = df.groupby("k").y.mean().to_dict()
        self.prior = float(np.mean(y))
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        key = X.band_t.to_numpy() + "|" + cushion_bucket(X.cushion_t).astype(str)
        return np.array([self.table.get(k, self.prior) for k in key])


# ---------------- B1 ----------------
def b1_score(X: pd.DataFrame) -> np.ndarray:
    flags = X.flag_impulsivity + X.flag_overconfidence + X.flag_delayed_correction
    return ((X.dsr_t >= 0.5).astype(float) + (X.cushion_t < 1.5).astype(float) + flags
            + (X.bnpl_active >= 2).astype(float)).to_numpy()


# ---------------- B2 ----------------
class B2Markov:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    def fit(self, band_wide: pd.DataFrame, cushion_wide: pd.DataFrame, train_users) -> "B2Markov":
        """band_wide / cushion_wide: users x months (observable monthly data)."""
        b = band_wide.loc[list(train_users)].to_numpy()
        c = cushion_wide.loc[list(train_users)].to_numpy(dtype=float)
        counts = np.zeros((9, 9))
        for m in range(b.shape[1] - 1):
            ok = (b[:, m] != "INSUFFICIENT_INCOME") & (b[:, m + 1] != "INSUFFICIENT_INCOME")
            s0 = state_of(b[ok, m], c[ok, m])
            s1 = state_of(b[ok, m + 1], c[ok, m + 1])
            np.add.at(counts, (s0, s1), 1)
        self.P = (counts + self.alpha) / (counts + self.alpha).sum(axis=1, keepdims=True)
        # precompute the 3-step hitting probability for each start band
        self.score_by_start = {}
        for band_rank in range(3):
            targets = [s for s in range(9) if s // 3 > band_rank or s % 3 == 0]
            Q = self.P.copy()
            Q[targets] = np.eye(9)[targets]
            Q3 = np.linalg.matrix_power(Q, HORIZON)
            hit = Q3[:, targets].sum(axis=1)
            hit[targets] = 1.0
            self.score_by_start[band_rank] = hit
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        s = state_of(X.band_t.to_numpy(), X.cushion_t.to_numpy())
        r = np.array([BAND_RANK[b] for b in X.band_t])
        return np.array([self.score_by_start[ri][si] for ri, si in zip(r, s)])
