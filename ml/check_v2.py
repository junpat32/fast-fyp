"""FA1 check (D-102): does the forecast stay calibrated in every group without age and type of work?

    .venv\\Scripts\\python -m ml.check_v2       # about a minute -> ml/results/FORECAST_V2_CHECK.md

**Adoption rule, written before any result was computed** (Patrick, "FA1 a", 2026-10-17): the app
switches to the model without age and type of work (forecast_v2) only if, for **every** employment
type and **every** age group,
  (1) its mean calibrated probability is within 2 percentage points of the group's observed rate, and
  (2) its expected calibration error (5 equal-count bins) is at most 0.015 worse than the current
      model's (a practical tolerance for sampling noise in groups of 900-4,500 rows).
Otherwise the app keeps forecast_v1 and the report says why.

Both models are judged the same way, out of sample: GroupKFold(5) by user; in each outer fold the
logistic regression (the medium run's C, no tuning) is fitted on the training users, an isotonic
calibrator is fitted on inner GroupKFold(3) predictions of those training users, and both are applied
to the held-out users. Medium noise, master seed, the O2 rows. Exploratory (after O2), app only: the
O2 result is not touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold

from ml.evaluate import bootstrap, ci, pr_auc
from ml.features import FEATURES, build_features
from ml.models import fit_fixed

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
DATA = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
RESULTS = ROOT / CFG["results_dir"]
OUT = RESULTS / "FORECAST_V2_CHECK.md"
MEAN_GAP, ECE_TOLERANCE = 0.02, 0.015                     # the adoption rule (docstring)
V2_FEATURES = [f for f in FEATURES if not f.startswith(("type_", "age_"))]


def calibrated_oof(X: pd.DataFrame, feats: list[str], C: float) -> np.ndarray:
    Xm, y, g = X[feats].to_numpy(dtype=float), X.y.to_numpy(), X.user_id.to_numpy()
    out = np.zeros(len(y))
    for tr, te in GroupKFold(CFG["outer_folds"]).split(Xm, y, g):
        inner = np.zeros(len(tr))
        for itr, iva in GroupKFold(CFG["inner_folds"]).split(Xm[tr], y[tr], g[tr]):
            inner[iva] = fit_fixed("lr", CFG, C, None, Xm[tr][itr], y[tr][itr]).predict_proba(Xm[tr][iva])[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(inner, y[tr])
        model = fit_fixed("lr", CFG, C, None, Xm[tr], y[tr])
        out[te] = iso.predict(model.predict_proba(Xm[te])[:, 1])
    return out


def ece(p: np.ndarray, y: np.ndarray, bins: int = 5) -> float:
    """Expected calibration error over equal-count bins: the row-weighted mean |predicted - observed|."""
    order = np.argsort(p, kind="stable")
    return float(sum(len(b) / len(p) * abs(p[b].mean() - y[b].mean()) for b in np.array_split(order, bins)))


def group_table(df: pd.DataFrame, by: str) -> list[dict]:
    rows = []
    for name, g in df.groupby(by):
        y = g.y.to_numpy()
        r = {"group": name, "rows": len(g), "observed": y.mean()}
        for m in ("v1", "v2"):
            p = g[m].to_numpy()
            r[f"{m}_mean"], r[f"{m}_ece"], r[f"{m}_pr_auc"] = p.mean(), ece(p, y), pr_auc(y, p)
        r["pass_mean"] = abs(r["v2_mean"] - r["observed"]) <= MEAN_GAP
        r["pass_ece"] = r["v2_ece"] <= r["v1_ece"] + ECE_TOLERANCE
        rows.append(r)
    return rows


def run() -> dict:
    t = {k: pd.read_parquet(DATA / f"{k}.parquet") for k in ("users", "monthly", "flags", "labels")}
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    X = X.merge(t["users"][["user_id", "age_band"]], on="user_id", how="left")
    C = json.loads((RESULTS / f"medium_seed{SEED}" / "metrics.json").read_text(encoding="utf-8"))["chosen_params"]["lr"]["param"]
    df = X[["user_id", "y", "employment_type", "age_band"]].assign(v1=calibrated_oof(X, list(FEATURES), C),
                                                                    v2=calibrated_oof(X, V2_FEATURES, C))
    boot = bootstrap(df, ["v1", "v2"], 1000, SEED)
    overall = {m: {"pr_auc": pr_auc(df.y, df[m]), "mean": df[m].mean(), "ece": ece(df[m].to_numpy(), df.y.to_numpy())}
               for m in ("v1", "v2")}
    groups = {by: group_table(df, by) for by in ("employment_type", "age_band")}
    passed = all(r["pass_mean"] and r["pass_ece"] for rows in groups.values() for r in rows)
    return {"C": C, "overall": overall, "delta": overall["v2"]["pr_auc"] - overall["v1"]["pr_auc"],
            "delta_ci": ci(boot[:, 1] - boot[:, 0], CFG["ci_level"]), "groups": groups, "adopt": passed,
            "observed": df.y.mean()}


def write(res: dict) -> str:
    o = res["overall"]
    verdict = "**ADOPT forecast_v2** (every group passes both conditions)" if res["adopt"] else \
        "**KEEP forecast_v1** (at least one group fails a condition)"
    L = ["# FA1 check: the forecast without age and type of work (D-102)", "",
         "Exploratory, for the app only (the O2 result is unchanged). The adoption rule was written before any result "
         "was computed: every work type and age group must have (1) a mean predicted chance within 2 points of its "
         "observed rate and (2) a calibration error (ECE, 5 equal-count bins) at most 0.015 worse than the current "
         f"model. Both models out of sample, calibrated on training folds only; logistic regression, C = {res['C']}.", "",
         f"## Verdict: {verdict}", "",
         "| | Current model (v1, 32 inputs) | Without age and work type (v2, 25 inputs) |", "|---|---|---|",
         f"| PR-AUC | {o['v1']['pr_auc']:.3f} | {o['v2']['pr_auc']:.3f} |",
         f"| Mean predicted (observed {res['observed']:.1%}) | {o['v1']['mean']:.1%} | {o['v2']['mean']:.1%} |",
         f"| Calibration error (ECE) | {o['v1']['ece']:.3f} | {o['v2']['ece']:.3f} |", "",
         f"PR-AUC difference v2 − v1: {res['delta']:+.3f} [{res['delta_ci'][0]:+.3f}, {res['delta_ci'][1]:+.3f}].", ""]
    for by, title in (("employment_type", "Type of work"), ("age_band", "Age group")):
        L += [f"## {title}", "", "| Group | Rows | Observed | v1 mean | v2 mean | v1 ECE | v2 ECE | v1 PR-AUC | v2 PR-AUC | "
              "Passes |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in res["groups"][by]:
            ok = "yes" if r["pass_mean"] and r["pass_ece"] else ("NO (mean)" if not r["pass_mean"] else "NO (ECE)")
            L.append(f"| {r['group']} | {r['rows']} | {r['observed']:.1%} | {r['v1_mean']:.1%} | {r['v2_mean']:.1%} | "
                     f"{r['v1_ece']:.3f} | {r['v2_ece']:.3f} | {r['v1_pr_auc']:.3f} | {r['v2_pr_auc']:.3f} | {ok} |")
        L.append("")
    text = "\n".join(L) + "\n"
    OUT.write_text(text, encoding="utf-8")
    return text


def main() -> dict:
    res = run()
    print(write(res))
    return res


if __name__ == "__main__":
    main()
