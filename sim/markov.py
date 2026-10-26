"""Expected months to recover, from the Markov chain over band x cushion (OBJECTIVES "Must (cheap)", D-143).

The chain is O2's baseline B2 (ml.baselines.B2Markov): 9 states, state = band rank x 3 + cushion bucket
(under 1, 1-3, 3+ months), Laplace alpha 1, insufficient-income months skipped. B2 asks how likely
things get worse; this module asks the reverse question of the same chain: how long until they get better.

Invariants
  K1  One chain: the transition matrix comes from B2Markov.fit, never a second definition.
  K2  First-order and time-homogeneous: next month depends only on this month's state. That is the
      model's assumption, not a fact; sim/markov_recovery.py checks it against held-out users.
  K3  Every state can reach the target (Laplace smoothing makes every transition positive), so I - Q is
      invertible and the mean is finite; a chain where that fails is refused.
  K4  A start state already in the target needs 0 months.

Pseudo-code (target set R; T = the other states; Q = P restricted to T)
  mean months from each s in T:   m = (I - Q)^-1 1          (fundamental matrix; Kemeny and Snell 1960)
  P(in R within k months):        make R absorbing (its rows = identity), A = that matrix,
                                  within_k = (A^k)[:, R] summed over R
  median months:                  smallest k with within_k >= 0.5

Cost: O(S^3) for the inverse and O(K S^3) for K steps of A^k; S = 9 states, K <= 120.

Trace (3 states A, B and the target R; rows sum to 1):
        to A   to B   to R
  A     0.5    0.3    0.2        m_A = 1 + 0.5 m_A + 0.3 m_B  ->  m_A = 4.21 months
  B     0.2    0.5    0.3        m_B = 1 + 0.2 m_A + 0.5 m_B  ->  m_B = 3.68 months
  R     0      0      1          within 1 from A = 0.20; within 2 = 0.20 + 0.5 x 0.20 + 0.3 x 0.30 = 0.39
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.baselines import B2Markov

BANDS = ("Green", "Yellow", "Red")
BUCKETS = ("under 1 month", "1-3 months", "3+ months")
N_STATES = 9
RECOVERED = (1, 2)                     # Green with at least 1 month of cushion: the reverse of B2's targets
OUT_OF_RED = tuple(range(6))           # any band but Red
TARGETS = {"recovered": RECOVERED, "out_of_red": OUT_OF_RED}
MAX_MONTHS = 120


def name(state: int) -> str:
    return f"{BANDS[state // 3]}, cushion {BUCKETS[state % 3]}"


def transition_matrix(band_wide: pd.DataFrame, cushion_wide: pd.DataFrame, users) -> np.ndarray:
    """B2's transition matrix fitted on `users` only (K1)."""
    return B2Markov().fit(band_wide, cushion_wide, users).P


def recovery(P: np.ndarray, target, ks=(3, 6, 12)) -> dict[int, dict]:
    """For every start state: mean and median months to reach `target`, and P(reached within each k)."""
    P = np.asarray(P, dtype=float)
    target = sorted(set(target))
    rest = [s for s in range(len(P)) if s not in target]
    Q = P[np.ix_(rest, rest)]
    try:
        mean_rest = np.linalg.solve(np.eye(len(rest)) - Q, np.ones(len(rest)))
    except np.linalg.LinAlgError:
        raise ValueError("some state cannot reach the target (K3)") from None
    if not np.isfinite(mean_rest).all() or (mean_rest < 1 - 1e-9).any():
        raise ValueError("some state cannot reach the target (K3)")
    A = P.copy()
    A[target] = np.eye(len(P))[target]
    within, step = {}, np.eye(len(P))
    median = {s: None for s in rest}
    for k in range(1, MAX_MONTHS + 1):
        step = step @ A
        reached = step[:, target].sum(axis=1)
        within[k] = reached
        for s in rest:
            if median[s] is None and reached[s] >= 0.5 - 1e-12:
                median[s] = k
    out = {}
    for s in range(len(P)):
        if s in target:
            out[s] = {"mean": 0.0, "median": 0, **{f"within_{k}": 1.0 for k in ks}}   # K4
        else:
            out[s] = {"mean": float(mean_rest[rest.index(s)]), "median": median[s],
                      **{f"within_{k}": float(within[k][s]) for k in ks}}
    return out
