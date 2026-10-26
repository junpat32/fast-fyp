"""Secondary comparison (26 Oct brief A + C, D-134): does ML add value beyond simpler methods, and what
does the O2 outcome really measure?

    .venv\\Scripts\\python -m ml.secondary --dev   # debugging on the development dataset (seed 999), never reported
    .venv\\Scripts\\python -m ml.secondary         # the one run on the master data -> ml/results/SECONDARY_COMPARISON.md

**Exploratory** (D-132 N6): the O2, Monte Carlo and health-score results were seen before this was
planned, so nothing here is confirmatory, and the frozen O2 result is untouched. This plan was written
and committed before the first run on the master data.

Rows: the O2 rows (medium noise, master seed: 6,646 rows, 990 users), the same rows for every method.

Methods (each uses months t-2..t only, or months <= t for the Monte Carlo and the health score)
  lr        logistic regression, O2 out-of-fold; ranking by the raw score, probability = O2's own
            isotonic calibration fitted inside the training folds (lr_cal)
  xgb       XGBoost, the same way (xgb_cal)
  oracle    the latent-trait-informed benchmark (D-133), the same way; reference only
  b0        B0 base rates (the best O2 baseline), its own probability (B0_cal)
  mc        the app's Monte Carlo P(shortfall in 3 months) from up to 6 past months (the comparator's
            saved scores, D-98)
  health    the app's health score, risk = 100 - score
  cushion   months of costs covered by cash, risk = - cushion_t
  runway    cash runway: if cash fell over the window, months until it reaches zero at that pace,
            cash_t / max(0, -(cash_t - cash_{t-2}) / 2); no fall = no runway limit; risk = 1/(1 + runway),
            ties (no fall) broken by the smaller cushion
  Methods without a probability of the target (mc for the composite, health, cushion, runway) get one by
  isotonic regression cross-fitted over GroupKFold(5) by user: fitted on four fifths of the users,
  applied to the other fifth. No method is calibrated on the rows it is scored on. mc is also shown
  uncalibrated against the shortfall part, the target it estimates.

Targets (the label and its parts; outcomes only, never inputs)
  T1 the O2 label (band worse at t+3 or a shortfall in t+1..t+3)
  T2 shortfall in t+1..t+3        T3 band worse at t+3
  T4 debt pressure rising: DSR at t+3 at least 5 points above DSR at t (whatever the band)

Metrics, each with a 95% user-level bootstrap interval (1,000 resamples, users drawn with replacement)
  ranking      PR-AUC and ROC-AUC on every target; paired difference lr - method
  probability  (T1 only, and mc on T2) Brier score, Brier skill vs the base rate, expected calibration
               error (10 equal-count bins), calibration-in-the-large (mean predicted - observed),
               calibration slope (logistic regression of the outcome on logit(p)); paired Brier lr - method
  usefulness   (T1) net benefit at thresholds 10%, 20%, 30% (decision curves; 30% is the app's R10 line),
               recall and precision at 30%
  outcome      positives by part and starting band; lr per starting band; rows whose DSR rose 5+ points
               while the O2 label stayed negative

Reading rule, fixed before the run (for each method against lr, on T1)
  "ML better"   the interval of (lr - method) lies wholly on lr's side of 0
  "comparable"  the interval lies wholly inside the margin: PR-AUC +-0.05, ROC-AUC +-0.03, Brier +-0.003
                (about a third of O2's gain over B0, a common small-AUC margin, about 3.5% of lr's Brier)
  otherwise     "inconclusive"
Margins are judgements, stated here before any result. A method "comparable" in ranking and probability
is a legitimate finding (the brief: ML need not win).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from generator.run import FROZEN_SPEC, generate, sha256
from ml import exploratory as ex
from ml.mc_comparator import score_rows

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
RESULTS = ROOT / CFG["results_dir"]
THRESHOLDS = (0.10, 0.20, 0.30)
APP_LINE = 0.30                                         # thresholds.json advice.forecast_elevated (R10)
MARGIN = {"pr_auc": 0.05, "roc_auc": 0.03, "brier": 0.003}
DSR_RISE = 0.05
METHODS = ("lr", "xgb", "oracle", "b0", "mc", "health", "cushion", "runway")
OWN_PROB = {"lr": "lr_cal", "xgb": "xgb_cal", "oracle": "oracle_cal", "b0": "B0_cal"}
NAMES = {"lr": "Logistic regression (the app's model)", "xgb": "XGBoost", "oracle": "Oracle (hidden traits; reference)",
         "b0": "B0 base rates (best O2 baseline)", "mc": "Monte Carlo P(shortfall)", "health": "Health score",
         "cushion": "Cushion months", "runway": "Cash runway"}
TARGETS = {"T1": "O2 label", "T2": "shortfall part", "T3": "band-worse part", "T4": "DSR up 5+ points"}


# ---------------------------------------------------------------- scores
def runway_months(cash: np.ndarray, cash_before: np.ndarray) -> np.ndarray:
    """Months until cash reaches zero at the window's pace; inf when cash did not fall."""
    pace = (np.asarray(cash, float) - np.asarray(cash_before, float)) / 2          # = feature cash_slope3
    with np.errstate(divide="ignore"):
        return np.where(pace < 0, np.asarray(cash, float) / np.where(pace < 0, -pace, 1), np.inf)


def runway_risk(runway: np.ndarray, cushion: np.ndarray) -> np.ndarray:
    return 1 / (1 + runway) + 1e-6 / (1 + np.maximum(np.asarray(cushion, float), 0))


def cross_fit(score: np.ndarray, y: np.ndarray, groups: np.ndarray, folds: int = 5) -> np.ndarray:
    """Isotonic probability for each row from a fit on the other users only."""
    out = np.empty(len(y))
    for tr, te in GroupKFold(folds).split(score, y, groups):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(score[tr], y[tr])
        out[te] = iso.predict(score[te])
    return out


# ---------------------------------------------------------------- metrics
def ece(p: np.ndarray, y: np.ndarray, bins: int = 10, w: np.ndarray | None = None) -> float:
    w = np.ones(len(p)) if w is None else w
    order = np.argsort(p, kind="stable")
    total = w.sum()
    return float(sum(w[b].sum() / total * abs(np.average(p[b], weights=w[b]) - np.average(y[b], weights=w[b]))
                     for b in np.array_split(order, bins) if w[b].sum() > 0))


def calibration_slope(p: np.ndarray, y: np.ndarray) -> float:
    z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    return float(LogisticRegression(C=np.inf, max_iter=1000).fit(z, y).coef_[0][0])


def net_benefit(p: np.ndarray, y: np.ndarray, pt: float) -> float:
    flag = p >= pt
    n = len(y)
    return float((flag & (y == 1)).sum() / n - (flag & (y == 0)).sum() / n * pt / (1 - pt))


def ranking(y, s, w=None) -> dict:
    return {"pr_auc": float(average_precision_score(y, s, sample_weight=w)),
            "roc_auc": float(roc_auc_score(y, s, sample_weight=w))}


def brier(y, p, w=None) -> float:
    return float(np.average((p - y) ** 2, weights=w))


def boot_weights(users: np.ndarray, B: int, seed: int):
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(users, return_inverse=True)
    for _ in range(B):
        yield np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))[inv].astype(float)


def ci(a, level: float = 0.95) -> list[float]:
    lo = (1 - level) / 2
    return [float(np.quantile(a, lo)), float(np.quantile(a, 1 - lo))]


def verdict(lo: float, hi: float, margin: float, lower_is_better: bool = False) -> str:
    """Reading rule (docstring): interval of lr - method."""
    if lower_is_better:
        lo, hi = -hi, -lo                       # for Brier, lr better means lr - method < 0
    if lo > 0:
        return "ML better"
    if -margin < lo and hi < margin:
        return "comparable"
    if hi < 0:
        return "method better"
    return "inconclusive"


# ---------------------------------------------------------------- data
def frame(dev: bool) -> pd.DataFrame:
    if dev:
        gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
        gcfg["n_users"] = CFG["dev"]["n_users"]
        t = generate(gcfg, "medium", CFG["dev"]["seed"], with_transactions=False)
        oof = pd.read_parquet(RESULTS / "dev" / f"medium_seed{CFG['dev']['seed']}" / "oof.parquet")
        mc = score_rows(oof, t["monthly"], t["users"])
    else:
        folder = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        if meta["spec_sha256"] != sha256(FROZEN_SPEC):
            raise SystemExit("Integrity check failed: the master data was not generated from the frozen spec")
        t = ex.tables()
        oof = pd.read_parquet(RESULTS / f"medium_seed{SEED}" / "oof.parquet")
        saved = pd.read_parquet(RESULTS / "mc_comparator.parquet")
        if not (saved.user_id.to_numpy() == oof.user_id.to_numpy()).all() or not (saved.t.to_numpy() == oof.t.to_numpy()).all():
            raise SystemExit("the saved Monte Carlo scores are not in the O2 row order")
        mc = saved.mc.to_numpy()
    df = ex.per_row_engine(t, oof.merge(t["users"][["user_id", "age_band"]], on="user_id", how="left"))
    mo = t["monthly"].set_index(["user_id", "month"])
    key = list(zip(df.user_id, df.t))
    cash = mo.cash.reindex(key).to_numpy()
    cash_before = mo.cash.reindex([(u, m - 2) for u, m in key]).to_numpy()
    cushion = mo.cushion_months.reindex(key).to_numpy()
    dsr_t, dsr_t3 = mo.dsr.reindex(key).to_numpy(), mo.dsr.reindex([(u, m + 3) for u, m in key]).to_numpy()
    rw = runway_months(cash, cash_before)
    return df.assign(mc=mc, cushion_t=cushion, runway_m=rw, s_lr=df.lr, s_xgb=df.xgb, s_oracle=df.oracle,
                     s_b0=df.B0, s_mc=mc, s_health=100 - df.health, s_cushion=-cushion,
                     s_runway=runway_risk(rw, cushion),
                     T1=df.y.astype(int), T2=df.shortfall_t1_t3.astype(int), T3=df.worsened.astype(int),
                     T4=((dsr_t3 - dsr_t) >= DSR_RISE).astype(int), dsr_rise=dsr_t3 - dsr_t)


def probabilities(df: pd.DataFrame) -> pd.DataFrame:
    g, y = df.user_id.to_numpy(), df.T1.to_numpy()
    p = {f"p_{m}": df[c].to_numpy() for m, c in OWN_PROB.items()}
    for m in ("mc", "health", "cushion", "runway"):
        p[f"p_{m}"] = cross_fit(df[f"s_{m}"].to_numpy(), y, g)
    return df.assign(**p)


# ---------------------------------------------------------------- analysis
def compare(df: pd.DataFrame, B: int) -> dict:
    users = df.user_id.to_numpy()
    res = {"rows": len(df), "users": int(df.user_id.nunique()), "targets": {}}
    for tk in TARGETS:
        y = df[tk].to_numpy()
        point = {m: ranking(y, df[f"s_{m}"].to_numpy()) for m in METHODS}
        boots = {m: [] for m in METHODS}
        for w in boot_weights(users, B, SEED):
            keep = w > 0
            for m in METHODS:
                boots[m].append(ranking(y[keep], df[f"s_{m}"].to_numpy()[keep], w[keep]))
        rows = {}
        for m in METHODS:
            pr = np.array([b["pr_auc"] for b in boots[m]]); roc = np.array([b["roc_auc"] for b in boots[m]])
            lr_pr = np.array([b["pr_auc"] for b in boots["lr"]]); lr_roc = np.array([b["roc_auc"] for b in boots["lr"]])
            rows[m] = {**point[m], "pr_auc_ci": ci(pr), "roc_auc_ci": ci(roc),
                       "d_pr_auc": point["lr"]["pr_auc"] - point[m]["pr_auc"], "d_pr_auc_ci": ci(lr_pr - pr),
                       "d_roc_auc": point["lr"]["roc_auc"] - point[m]["roc_auc"], "d_roc_auc_ci": ci(lr_roc - roc)}
        res["targets"][tk] = {"prevalence": float(y.mean()), "methods": rows}
    return res


def probability_block(df: pd.DataFrame, B: int) -> dict:
    users, y = df.user_id.to_numpy(), df.T1.to_numpy().astype(float)
    out = {}
    for m in METHODS:
        p = df[f"p_{m}"].to_numpy()
        out[m] = {"brier": brier(y, p), "brier_skill": 1 - brier(y, p) / brier(y, np.full(len(y), y.mean())),
                  "ece": ece(p, y), "citl": float(p.mean() - y.mean()), "slope": calibration_slope(p, y),
                  "net_benefit": {str(pt): net_benefit(p, y, pt) for pt in THRESHOLDS},
                  "recall_at_line": float(((p >= APP_LINE) & (y == 1)).sum() / max(1, y.sum())),
                  "precision_at_line": float(((p >= APP_LINE) & (y == 1)).sum() / max(1, (p >= APP_LINE).sum())),
                  "flagged_at_line": float((p >= APP_LINE).mean())}
    d = {m: [] for m in METHODS}
    for w in boot_weights(users, B, SEED):
        keep = w > 0
        b_lr = brier(y[keep], df.p_lr.to_numpy()[keep], w[keep])
        for m in METHODS:
            d[m].append(b_lr - brier(y[keep], df[f"p_{m}"].to_numpy()[keep], w[keep]))
    for m in METHODS:
        out[m]["d_brier"] = out["lr"]["brier"] - out[m]["brier"]
        out[m]["d_brier_ci"] = ci(np.array(d[m]))
    y2 = df.T2.to_numpy().astype(float)
    mc = df.mc.to_numpy()
    out["mc_on_shortfall_uncalibrated"] = {"brier": brier(y2, mc), "ece": ece(mc, y2), "citl": float(mc.mean() - y2.mean()),
                                           "slope": calibration_slope(mc, y2), "prevalence": float(y2.mean())}
    out["treat_all"] = {str(pt): float(y.mean() - (1 - y.mean()) * pt / (1 - pt)) for pt in THRESHOLDS}
    return out


def outcome_block(df: pd.DataFrame) -> dict:
    pos = df[df.T1 == 1]
    parts = {"shortfall only": int(((pos.T2 == 1) & (pos.T3 == 0)).sum()), "band worse only": int(((pos.T2 == 0) & (pos.T3 == 1)).sum()),
             "both": int(((pos.T2 == 1) & (pos.T3 == 1)).sum())}
    by_band = []
    for band, g in df.groupby("band_t"):
        row = {"band": band, "rows": len(g), "T1": float(g.T1.mean()), "T2": float(g.T2.mean()), "T3": float(g.T3.mean()),
               "T4": float(g.T4.mean()), "mean_p_lr": float(g.p_lr.mean())}
        for tk in ("T1", "T2"):
            row[f"lr_pr_auc_{tk}"] = float(average_precision_score(g[tk], g.s_lr)) if 0 < g[tk].sum() < len(g) else None
        by_band.append(row)
    hidden = df[(df.T4 == 1) & (df.T1 == 0)]
    return {"positives": parts, "by_band": by_band, "red_rows_band_worse": int(df[(df.band_t == "RED") & (df.T3 == 1)].shape[0]),
            "dsr_up_label_negative": {"rows": len(hidden), "share_of_rows": float(len(hidden) / len(df)),
                                      "share_of_dsr_up": float(len(hidden) / max(1, df.T4.sum())),
                                      "median_rise": float(hidden.dsr_rise.median()) if len(hidden) else None,
                                      "by_band": {b: int(n) for b, n in hidden.band_t.value_counts().items()}},
            "t4_and_t1_overlap": float(((df.T4 == 1) & (df.T1 == 1)).sum() / max(1, df.T4.sum()))}


def readings(cmp: dict, prob: dict) -> dict:
    out = {}
    for m in METHODS:
        if m == "lr":
            continue
        r = cmp["targets"]["T1"]["methods"][m]
        out[m] = {"pr_auc": verdict(*r["d_pr_auc_ci"], MARGIN["pr_auc"]),
                  "roc_auc": verdict(*r["d_roc_auc_ci"], MARGIN["roc_auc"]),
                  "brier": verdict(*prob[m]["d_brier_ci"], MARGIN["brier"], lower_is_better=True)}
    return out


def run(dev: bool = False) -> dict:
    df = probabilities(frame(dev))
    B = CFG["dev"]["bootstrap_resamples"] if dev else CFG["bootstrap_resamples"]
    cmp, prob = compare(df, B), probability_block(df, B)
    res = {"dev": dev, "comparison": cmp, "probability": prob, "outcome": outcome_block(df), "readings": readings(cmp, prob),
           "runway_unlimited_share": float(np.isinf(df.runway_m).mean())}
    out = RESULTS / ("dev" if dev else "") / "secondary_comparison.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ---------------------------------------------------------------- report
def _f(x, d=3):
    return "n/a" if x is None else f"{x:.{d}f}"


def _ci(c, d=3):
    return f"[{c[0]:+.{d}f}, {c[1]:+.{d}f}]"


def write(res: dict) -> str:
    cmp, prob, oc, rd = res["comparison"], res["probability"], res["outcome"], res["readings"]
    L = ["# Secondary comparison: ML against simpler methods, and what the outcome measures (D-134)", ""]
    if res["dev"]:
        L += ["**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**", ""]
    L += ["**Exploratory** (D-132 N6): planned after the O2, Monte Carlo and health-score results were seen; the plan and the "
          "reading rule were committed before this run (`ml/secondary.py` docstring). The frozen O2 result is unchanged. "
          f"{cmp['rows']:,} rows from {cmp['users']:,} users; 95% user-level bootstrap intervals.", "",
          "## What each method predicts", "",
          "| Method | Output | Target it was built for | Horizon | Inputs |", "|---|---|---|---|---|",
          "| Logistic regression, XGBoost | probability (calibrated inside the training folds) | the O2 label | 3 months | 32 features, months t−2..t |",
          "| Oracle | probability | the O2 label | 3 months | the same + hidden traits (reference only) |",
          "| B0 base rates | probability | the O2 label | 3 months | band and cushion bucket at t |",
          "| Monte Carlo | probability of a shortfall | **shortfalls only** | 3 months | the user's last ≤ 6 months |",
          "| Health score | 0–100 score of **today** | none (describes the present) | — | months t−2..t |",
          "| Cushion months | months of costs covered by cash | none | — | month t |",
          "| Cash runway | months until cash runs out at its recent pace | none | — | months t−2..t |", "",
          "Methods without a probability of the O2 label get one by isotonic regression fitted on other users (5 folds).", "",
          "## 1. Ranking: PR-AUC on each target", "",
          "| Method | " + " | ".join(f"{k}: {v} ({cmp['targets'][k]['prevalence']:.1%})" for k, v in TARGETS.items()) + " |",
          "|---|" + "---|" * len(TARGETS)]
    for m in METHODS:
        L.append(f"| {NAMES[m]} | " + " | ".join(
            f"{cmp['targets'][k]['methods'][m]['pr_auc']:.3f} [{cmp['targets'][k]['methods'][m]['pr_auc_ci'][0]:.3f}, "
            f"{cmp['targets'][k]['methods'][m]['pr_auc_ci'][1]:.3f}]" for k in TARGETS) + " |")
    L += ["", "## 2. The O2 label: ML against each method (reading rule fixed before the run)", "",
          "Differences are logistic regression minus the method. Margins for \"comparable\": PR-AUC ±0.05, ROC-AUC ±0.03, Brier ±0.003.", "",
          "| Method | ΔPR-AUC | ΔROC-AUC | ΔBrier (negative = ML better) | Ranking (PR) | Ranking (ROC) | Probability (Brier) |",
          "|---|---|---|---|---|---|---|"]
    t1 = cmp["targets"]["T1"]["methods"]
    for m in METHODS:
        if m == "lr":
            continue
        r, p = t1[m], prob[m]
        L.append(f"| {NAMES[m]} | {r['d_pr_auc']:+.3f} {_ci(r['d_pr_auc_ci'])} | {r['d_roc_auc']:+.3f} {_ci(r['d_roc_auc_ci'])} | "
                 f"{p['d_brier']:+.4f} {_ci(p['d_brier_ci'], 4)} | {rd[m]['pr_auc']} | {rd[m]['roc_auc']} | {rd[m]['brier']} |")
    L += ["", "## 3. Probabilities on the O2 label", "",
          "| Method | ROC-AUC | Brier | Brier skill | ECE (10 bins) | Mean predicted − observed | Calibration slope |",
          "|---|---|---|---|---|---|---|"]
    for m in METHODS:
        p = prob[m]
        L.append(f"| {NAMES[m]} | {t1[m]['roc_auc']:.3f} | {p['brier']:.4f} | {p['brier_skill']:+.3f} | {p['ece']:.4f} | "
                 f"{p['citl']:+.4f} | {p['slope']:.2f} |")
    mc = prob["mc_on_shortfall_uncalibrated"]
    L += ["", f"The Monte Carlo's own probability, **uncalibrated, against the shortfall part** it estimates "
          f"(prevalence {mc['prevalence']:.1%}): Brier {mc['brier']:.4f}, ECE {mc['ece']:.4f}, mean predicted − observed "
          f"{mc['citl']:+.4f}, slope {mc['slope']:.2f}.", "",
          "## 4. Usefulness at a decision line (O2 label)", "",
          "Net benefit = true positives / n − false positives / n × t / (1 − t): above 0 and above \"warn everyone\" means warnings at "
          "that line do more good than harm (Vickers & Elkin 2006). 30% is the app's R10 line.", "",
          "| Method | Net benefit at 10% | 20% | 30% | Flagged at 30% | Recall at 30% | Precision at 30% |", "|---|---|---|---|---|---|---|"]
    for m in METHODS:
        p = prob[m]
        nb = p["net_benefit"]
        L.append(f"| {NAMES[m]} | {nb['0.1']:+.4f} | {nb['0.2']:+.4f} | {nb['0.3']:+.4f} | {p['flagged_at_line']:.1%} | "
                 f"{p['recall_at_line']:.2f} | {p['precision_at_line']:.2f} |")
    ta = prob["treat_all"]
    L.append(f"| Warn everyone | {ta['0.1']:+.4f} | {ta['0.2']:+.4f} | {ta['0.3']:+.4f} | 100% | 1.00 | — |")
    pos = oc["positives"]
    total = sum(pos.values())
    L += ["", "## 5. What the outcome measures", "",
          f"Positives of the O2 label: shortfall only {pos['shortfall only']} ({pos['shortfall only'] / total:.0%}), band worse only "
          f"{pos['band worse only']} ({pos['band worse only'] / total:.0%}), both {pos['both']} ({pos['both'] / total:.0%}). "
          f"Rows starting in Red whose band got worse: {oc['red_rows_band_worse']} (Red can't get worse).", "",
          "| Starting band | Rows | O2 label | Shortfall | Band worse | DSR up 5+ points | Mean predicted (lr) | lr PR-AUC, O2 label | lr PR-AUC, shortfall |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(oc["by_band"], key=lambda r: ["GREEN", "YELLOW", "RED"].index(r["band"])):
        L.append(f"| {r['band']} | {r['rows']} | {r['T1']:.1%} | {r['T2']:.1%} | {r['T3']:.1%} | {r['T4']:.1%} | {r['mean_p_lr']:.1%} | "
                 f"{_f(r['lr_pr_auc_T1'])} | {_f(r['lr_pr_auc_T2'])} |")
    h = oc["dsr_up_label_negative"]
    L += ["", f"**Debt pressure the label misses:** {h['rows']} rows ({h['share_of_rows']:.1%} of all rows; "
          f"{h['share_of_dsr_up']:.0%} of the rows whose DSR rose 5+ points) had DSR rise by 5+ points (median "
          f"{_f(h['median_rise'] * 100 if h['median_rise'] is not None else None, 1)} points) with no band change and no shortfall, "
          f"so the O2 label called them negative. By starting band: "
          + ", ".join(f"{b} {n}" for b, n in h["by_band"].items()) + ".", "",
          f"Share of rows with no cash fall in the window (unlimited runway): {res['runway_unlimited_share']:.1%}.", ""]
    text = "\n".join(L) + "\n"
    out = RESULTS / ("dev" if res["dev"] else "") / "SECONDARY_COMPARISON.md"
    out.write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", action="store_true", help="debug on the development dataset (never reported)")
    res = run(dev=ap.parse_args(argv).dev)
    print(write(res))
    return res


if __name__ == "__main__":
    main()
