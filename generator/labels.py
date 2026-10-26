"""Label (spec §11, frozen): y(u,t) = 1 if band(t+3) is worse than band(t), or any
shortfall in t+1..t+3. Rows where band(t) or band(t+3) is INSUFFICIENT are excluded
(kept with y = NA and an exclusion reason, so the count can be reported).
t runs over calendar months 3..9 (features need t-2 >= 1; the label needs t+3 <= 12).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .bands import INSUFFICIENT

HORIZON = 3


def build_labels(user_id: np.ndarray, band: np.ndarray, shortfall: np.ndarray) -> pd.DataFrame:
    n, M = band.shape
    rows = []
    for t in range(3, M - HORIZON + 1):                 # calendar months 3..9
        i = t - 1                                       # 0-based index of month t
        b_t, b_t3 = band[:, i], band[:, i + HORIZON]
        short_any = shortfall[:, i + 1:i + 1 + HORIZON].any(axis=1)
        excluded = (b_t == INSUFFICIENT) | (b_t3 == INSUFFICIENT)
        worsened = (b_t3 > b_t) & ~excluded
        y = pd.array(np.where(excluded, pd.NA, (worsened | short_any).astype(int)), dtype="Int8")
        rows.append(pd.DataFrame({
            "user_id": user_id, "t": t, "y": y,
            "band_t": b_t, "band_t3": b_t3,
            "worsened": worsened, "shortfall_t1_t3": short_any,
            "exclusion_reason": np.where(excluded, "insufficient_income", ""),
        }))
    return pd.concat(rows, ignore_index=True)
