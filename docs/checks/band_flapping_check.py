"""How often do bands flip month to month under alternative income definitions? (T-11 finding)
Data-level analysis on the medium synthetic dataset; uses the canonical engine.bands rules."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine.bands import INSUFFICIENT, RED, band_array, load_thresholds  # noqa: E402

D = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "medium_seed20261009"
mo = pd.read_parquet(D / "monthly.parquet")
users = pd.read_parquet(D / "users.parquet").set_index("user_id")
inc = mo.pivot(index="user_id", columns="month", values="net_income").to_numpy()
debt = mo.pivot(index="user_id", columns="month", values="commitments_total").to_numpy()
types = users.loc[mo.user_id.unique(), "employment_type"].to_numpy()
t = load_thresholds(Path(__file__).resolve().parents[2] / "shared" / "thresholds_spec_v1.json")   # v1 baseline, no buffer


def income_measure(kind, m):
    lo = max(0, m - (5 if kind == "median6" else 2))
    w = inc[:, lo:m + 1]
    return w.mean(axis=1) if kind == "mean3" else np.median(w, axis=1)


def bands(kind, confirm_red=False):
    out, prev, prev_raw_red = [], None, np.zeros(len(inc), bool)
    for m in range(12):
        base = income_measure("median3" if kind == "confirm" else kind, m)
        with np.errstate(divide="ignore", invalid="ignore"):
            dsr = np.where(base > 0, debt[:, m] / base, 9.99)
        b = band_array(np.minimum(dsr, 9.99), base, prev, t)
        if kind == "confirm":   # enter Red only after 2 consecutive months at >= 60%
            raw_red = (dsr >= t["dsr"]["red_at_or_above"]) & (base >= t["insufficient_income_below_rm"])
            entering = (b == RED) & ((prev != RED) if prev is not None else True) & ~prev_raw_red
            b = np.where(entering, np.int8(1), b)
            prev_raw_red = raw_red
        out.append(b)
        prev = b
    return np.array(out).T


rows = []
for kind in ("median3", "mean3", "median6", "confirm"):
    B = bands(kind)
    valid = (B[:, 1:] != INSUFFICIENT) & (B[:, :-1] != INSUFFICIENT)
    flips = ((B[:, 1:] != B[:, :-1]) & valid).sum(axis=1)
    reversals = ((B[:, 2:] == B[:, :-2]) & (B[:, 1:-1] != B[:, 2:]) & valid[:, 1:] & valid[:, :-1]).sum(axis=1)
    for typ in ("employee", "gig", "student", "all"):
        sel = types == typ if typ != "all" else np.ones(len(types), bool)
        rows.append({"income measure": kind, "type": typ,
                     "band changes / user-year": flips[sel].mean().round(3),
                     "flip-backs (A-B-A) / user-year": reversals[sel].mean().round(3),
                     "users with any flip-back": f"{(reversals[sel] > 0).mean():.1%}",
                     "Red user-months": f"{(B[sel] == RED).mean():.1%}"})
print(pd.DataFrame(rows).to_string(index=False))

# Which boundary do flip-backs (A-B-A) happen at, under the current rule (median3)?
B = bands("median3")
gy = yr = 0
for m in range(1, 11):
    a, b, c = B[:, m - 1], B[:, m], B[:, m + 1]
    fb = (a == c) & (b != a) & (a != INSUFFICIENT) & (b != INSUFFICIENT)
    pair = np.minimum(a, b)[fb]
    gy += (pair == 0).sum()
    yr += (pair == 1).sum()
print(f"\nflip-backs at the Green/Yellow line: {gy}; at the Yellow/Red line: {yr}")

# Candidate: a buffer at the Green/Yellow line too (leave Yellow for Green only below 27%)
out, prev = [], None
for m in range(12):
    base = income_measure("median3", m)
    with np.errstate(divide="ignore", invalid="ignore"):
        dsr = np.where(base > 0, debt[:, m] / base, 9.99)
    b = band_array(np.minimum(dsr, 9.99), base, prev, t)
    if prev is not None:
        b = np.where((prev == 1) & (b == 0) & (dsr >= 0.27), np.int8(1), b)
    out.append(b)
    prev = b
B2 = np.array(out).T
valid = (B2[:, 1:] != INSUFFICIENT) & (B2[:, :-1] != INSUFFICIENT)
rev = ((B2[:, 2:] == B2[:, :-2]) & (B2[:, 1:-1] != B2[:, 2:]) & valid[:, 1:] & valid[:, :-1]).sum(axis=1)
for typ in ("employee", "gig", "student", "all"):
    sel = types == typ if typ != "all" else np.ones(len(types), bool)
    print(f"median3 + Green/Yellow buffer (27%), {typ:8s}: users with any flip-back {(rev[sel] > 0).mean():.1%}")


# Candidate: asymmetric confirmation. A worse band is shown at once; a better band only after the
# underlying (v1) band has been better than the shown band for 2 consecutive months.
def shown_bands(buffer=False):
    raw_prev, shown_prev, pending = None, None, np.zeros(len(inc), int)
    out = []
    for m in range(12):
        base = income_measure("median3", m)
        with np.errstate(divide="ignore", invalid="ignore"):
            dsr = np.where(base > 0, debt[:, m] / base, 9.99)
        raw = band_array(np.minimum(dsr, 9.99), base, raw_prev, t)
        if buffer and raw_prev is not None:
            raw = np.where((raw_prev >= 1) & (raw == 0) & (dsr >= 0.27), np.int8(1), raw)
        if shown_prev is None:
            shown = raw
        else:
            better = (raw < shown_prev) & (raw != INSUFFICIENT) & (shown_prev != INSUFFICIENT)
            pending = np.where(better, pending + 1, 0)
            shown = np.where(better & (pending < 2), shown_prev, raw)
        out.append(shown)
        raw_prev, shown_prev = raw, shown
    return np.array(out).T


for label, buf in (("2-month confirmation for improvements", False), ("confirmation + 27% buffer", True)):
    S = shown_bands(buf)
    valid = (S[:, 1:] != INSUFFICIENT) & (S[:, :-1] != INSUFFICIENT)
    rv = ((S[:, 2:] == S[:, :-2]) & (S[:, 1:-1] != S[:, 2:]) & valid[:, 1:] & valid[:, :-1]).sum(axis=1)
    ch = ((S[:, 1:] != S[:, :-1]) & valid).sum(axis=1)
    for typ in ("gig", "all"):
        sel = types == typ if typ != "all" else np.ones(len(types), bool)
        print(f"{label:40s} {typ:4s}: users with any flip-back {(rv[sel] > 0).mean():.1%}; "
              f"changes/user-year {ch[sel].mean():.2f}; Red user-months {(S[sel] == RED).mean():.1%}")
