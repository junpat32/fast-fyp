"""Explanations and subgroup reliability (26 Oct brief E, D-137).

    .venv\\Scripts\\python -m ml.explain_fairness --dev   # debugging on the development dataset (seed 999), never reported
    .venv\\Scripts\\python -m ml.explain_fairness         # the one run on the master data -> ml/results/EXPLANATIONS_FAIRNESS.md

**Exploratory** (D-132 N6); this plan and its reading rules were committed before the first run on the master
data. The frozen O2 result and the app's model are untouched. The O2 rows (medium noise, master seed).

Part 1, how the shipped explanations behave (engine.forecast on every row's features; the model was fitted on
these rows, so this describes the explanation method, not accuracy)
  fidelity     largest |contributions + intercept - the model's raw score| over the rows (should be ~0)
  reference    share of rows where the headline's side (calibrated chance vs the base rate) differs from the
               side of the summed contributions (the reasons' reference point is the training average person)
  reasons      how many reasons are shown (0-3); share with each note (P6 demographics, P9 left-out patterns)
  left out     share of rows where a top-3 factor in the shown direction was left out by W1, and which features
  coverage     share of the shown direction's contribution mass that the shown reasons account for (median, IQR)

Part 2, reliability by group (O2's out-of-fold scores and in-fold calibration, so it is out of sample)
  groups       type of work; age group; lives with parents; sends money to family; type of work x age group
  minimum      a group is judged only with at least 100 users and 30 positive rows; smaller groups get counts only
  measures     rows, users, prevalence; PR-AUC and lift over chance; ROC-AUC; mean predicted - observed; ECE (5
               equal-count bins); at the app's 30% line: flagged share, recall, precision, false-positive rate.
               95% intervals from 1,000 user-level bootstrap resamples within the group
  reading rule (fixed before the run)
               "calibration concern"  the interval of (mean predicted - observed) excludes 0, or ECE > 0.03
               "ranking concern"      the group's ROC-AUC interval lies wholly below the all-rows ROC-AUC
               otherwise              "no concern found" (which is not proof of fairness)

Part 3, the 30% warning line and the options for unequal recall (descriptive)
  (a) one line for everyone (the app today)
  (b) a line per type of work chosen to give each type the all-rows recall at 30%; cross-fitted: each line is
      chosen on four fifths of the users (5 folds) and applied to the other fifth, so no line sees its own rows
  (c) dropping age and type of work: already tested and rejected (FA1, D-102), cited, not rerun
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from engine.forecast import FEATURES, REASON_WORDS, _eligible, _load, against_common_sense, forecast
from engine.bands import load_thresholds
from generator.run import FROZEN_SPEC, generate, sha256
from ml.features import build_features
from ml.secondary import boot_weights, ci, ece

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
RESULTS = ROOT / CFG["results_dir"]
LINE = 0.30
MIN_USERS, MIN_POS = 100, 30
ECE_CONCERN = 0.03
GROUPS = ("employment_type", "age_band", "lives_with_parents", "family_support", "type_x_age")


# ---------------------------------------------------------------- data
def tables(dev: bool) -> tuple[dict, pd.DataFrame]:
    if dev:
        gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
        gcfg["n_users"] = CFG["dev"]["n_users"]
        t = generate(gcfg, "medium", CFG["dev"]["seed"], with_transactions=False)
        return t, pd.read_parquet(RESULTS / "dev" / f"medium_seed{CFG['dev']['seed']}" / "oof.parquet")
    folder = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["spec_sha256"] != sha256(FROZEN_SPEC):
        raise SystemExit("Integrity check failed: the master data was not generated from the frozen spec")
    t = {k: pd.read_parquet(folder / f"{k}.parquet") for k in ("users", "monthly", "flags", "labels")}
    return t, pd.read_parquet(RESULTS / f"medium_seed{SEED}" / "oof.parquet")


# ---------------------------------------------------------------- part 1
def explanation_behaviour(X: pd.DataFrame) -> dict:
    art = _load()
    pipe, cal = art["model"], art["calibrator"]
    scaler, lr = pipe[0], pipe[-1]
    M = X[list(FEATURES)].to_numpy(dtype=float)
    contrib = scaler.transform(M) * lr.coef_[0]
    raw = pipe.decision_function(M)
    fidelity = float(np.max(np.abs(contrib.sum(axis=1) + lr.intercept_[0] - raw)))
    prob = cal.predict(pipe.predict_proba(M)[:, 1])
    disagree = float(np.mean((prob > art["base_rate"]) != (contrib.sum(axis=1) > 0)))
    shown = set(load_thresholds()["user_facing_flags"])
    n_reasons, notes, left_out, coverage = Counter(), Counter(), Counter(), []
    rows_left_out = 0
    for i in range(len(M)):
        fc = forecast(dict(zip(FEATURES, M[i])))
        n_reasons[len(fc.reasons)] += 1
        notes[fc.note] += 1
        raises = fc.probability > fc.base_rate
        c = contrib[i]
        order = np.argsort(-c) if raises else np.argsort(c)
        same_way = [j for j in order[:3] if (c[j] > 0 if raises else c[j] < 0)]
        dropped = [FEATURES[j] for j in same_way if _eligible(FEATURES[j], M[i, j], shown)
                   and FEATURES[j] in REASON_WORDS and against_common_sense(FEATURES[j], lr.coef_[0][j])]
        if dropped:
            rows_left_out += 1
            left_out.update(dropped)
        mass = c[c > 0].sum() if raises else -c[c < 0].sum()
        if mass > 0:
            coverage.append(sum(abs(r.contribution) for r in fc.reasons) / mass)
    cov = np.array(coverage)
    return {"rows": len(M), "fidelity_max_abs_error": fidelity, "headline_vs_sum_disagree": disagree,
            "reasons_shown": {str(k): v / len(M) for k, v in sorted(n_reasons.items())},
            "notes": {("none" if k is None else k): v / len(M) for k, v in notes.items()},
            "rows_with_top_factor_left_out": rows_left_out / len(M), "left_out_features": dict(left_out.most_common()),
            "coverage_median": float(np.median(cov)), "coverage_iqr": [float(np.quantile(cov, 0.25)), float(np.quantile(cov, 0.75))]}


# ---------------------------------------------------------------- part 2
def group_frame(t: dict, oof: pd.DataFrame) -> pd.DataFrame:
    u = t["users"][["user_id", "age_band", "lives_with_parents", "family_support"]]
    df = oof.merge(u, on="user_id", how="left")
    df["lives_with_parents"] = np.where(df.lives_with_parents.astype(bool), "lives with parents", "lives away")
    df["family_support"] = np.where(df.family_support.astype(bool), "sends money to family", "does not")
    df["type_x_age"] = df.employment_type + " " + df.age_band
    return df.assign(y=df.y.astype(int))


def at_line(y: np.ndarray, p: np.ndarray, line: float = LINE, w: np.ndarray | None = None) -> dict:
    w = np.ones(len(y)) if w is None else w
    flag = p >= line
    tp, fp = (w * (flag & (y == 1))).sum(), (w * (flag & (y == 0))).sum()
    pos, neg = (w * (y == 1)).sum(), (w * (y == 0)).sum()
    return {"flagged": float((w * flag).sum() / w.sum()), "recall": float(tp / pos) if pos else float("nan"),
            "precision": float(tp / (tp + fp)) if tp + fp else float("nan"), "fpr": float(fp / neg) if neg else float("nan")}


def measures(g: pd.DataFrame, w: np.ndarray | None = None) -> dict:
    y, s, p = g.y.to_numpy(), g.lr.to_numpy(), g.lr_cal.to_numpy()
    w = np.ones(len(y)) if w is None else w
    prev = float(np.average(y, weights=w))
    pr = float(average_precision_score(y, s, sample_weight=w))
    return {"prevalence": prev, "pr_auc": pr, "lift": pr / prev if prev else float("nan"),
            "roc_auc": float(roc_auc_score(y, s, sample_weight=w)), "citl": float(np.average(p, weights=w) - prev),
            "ece": ece(p, y.astype(float), bins=5, w=w), **at_line(y, p, w=w)}


def judged(g: pd.DataFrame) -> bool:
    return g.user_id.nunique() >= MIN_USERS and g.y.sum() >= MIN_POS


def subgroup_block(df: pd.DataFrame, B: int) -> dict:
    overall = measures(df)
    out = {"overall": overall, "groups": {}}
    for by in GROUPS:
        rows = []
        for name, g in df.groupby(by):
            r = {"group": name, "rows": len(g), "users": int(g.user_id.nunique()), "positives": int(g.y.sum())}
            if judged(g):
                r.update(measures(g))
                boots = []
                for w in boot_weights(g.user_id.to_numpy(), B, SEED):
                    keep = w > 0
                    sub = g[keep]
                    if 0 < sub.y.sum() < len(sub):
                        boots.append(measures(sub, w[keep]))
                for k in ("pr_auc", "roc_auc", "citl", "ece", "recall", "precision"):
                    r[f"{k}_ci"] = ci(np.array([b[k] for b in boots if not np.isnan(b[k])]))
                r["calibration_concern"] = (r["citl_ci"][0] > 0 or r["citl_ci"][1] < 0) or r["ece"] > ECE_CONCERN
                r["ranking_concern"] = r["roc_auc_ci"][1] < overall["roc_auc"]
            rows.append(r)
        out["groups"][by] = rows
    return out


# ---------------------------------------------------------------- part 3
def line_for_recall(y: np.ndarray, p: np.ndarray, target: float) -> float:
    """The highest line whose recall is at least `target` (so the fewest people are flagged)."""
    pos = np.sort(p[y == 1])[::-1]
    k = int(np.ceil(target * len(pos)))
    return float(pos[max(k, 1) - 1]) if len(pos) else LINE


def per_group_lines(df: pd.DataFrame, target: float) -> dict:
    df = df.reset_index(drop=True)
    p_line = np.empty(len(df))
    for tr, te in GroupKFold(5).split(df, df.y, df.user_id):
        train = df.iloc[tr]
        for name, g in train.groupby("employment_type"):
            line = line_for_recall(g.y.to_numpy(), g.lr_cal.to_numpy(), target)
            idx = te[(df.employment_type.to_numpy()[te] == name)]
            p_line[idx] = line
    flag = df.lr_cal.to_numpy() >= p_line
    out = {}
    for name, g in df.assign(flag=flag, line=p_line).groupby("employment_type"):
        y, f = g.y.to_numpy(), g.flag.to_numpy()
        tp, fp = (f & (y == 1)).sum(), (f & (y == 0)).sum()
        out[name] = {"line_median": float(g.line.median()), "flagged": float(f.mean()), "recall": float(tp / max(1, y.sum())),
                     "precision": float(tp / max(1, tp + fp)), "fpr": float(fp / max(1, (y == 0).sum()))}
    return out


def mitigation_block(df: pd.DataFrame) -> dict:
    target = at_line(df.y.to_numpy(), df.lr_cal.to_numpy())["recall"]
    one_line = {name: at_line(g.y.to_numpy(), g.lr_cal.to_numpy()) for name, g in df.groupby("employment_type")}
    return {"target_recall": target, "one_line": one_line, "per_group": per_group_lines(df, target)}


# ---------------------------------------------------------------- run and report
def run(dev: bool = False) -> dict:
    t, oof = tables(dev)
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    B = CFG["dev"]["bootstrap_resamples"] if dev else CFG["bootstrap_resamples"]
    df = group_frame(t, oof)
    res = {"dev": dev, "explanations": explanation_behaviour(X), "subgroups": subgroup_block(df, B),
           "mitigation": mitigation_block(df)}
    (RESULTS / ("dev" if dev else "") / "explanations_fairness.json").write_text(json.dumps(res, indent=1, default=str),
                                                                              encoding="utf-8")
    return res


def _pct(x):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.1%}"


def write(res: dict) -> str:
    e, sg, mt = res["explanations"], res["subgroups"], res["mitigation"]
    L = ["# Explanations and subgroup reliability (D-137)", ""]
    if res["dev"]:
        L += ["**DEVELOPMENT DATASET (seed 999): for debugging only, never reported.**", ""]
    L += ["**Exploratory** (D-132 N6): plan and reading rules committed before this run (`ml/explain_fairness.py` docstring). "
          "The frozen O2 result and the app's model are unchanged.", "",
          "## 1. How the shipped explanations behave", "",
          f"On {e['rows']:,} rows, with the app's model and its explanation rules:", "",
          f"- **Fidelity:** contributions plus the intercept reproduce the model's raw score to within "
          f"{e['fidelity_max_abs_error']:.1e} (exact, as a linear model should).",
          f"- **Reference point:** on {_pct(e['headline_vs_sum_disagree'])} of rows the headline's side (the calibrated chance "
          "against the base rate) differs from the side of the summed contributions, because the reasons compare a person with "
          "the training *average person* and the headline compares the chance with the *base rate*. The rule P5 shows only "
          "reasons pointing the headline's way, so no shown reason contradicts the headline.",
          "- **Reasons shown:** " + ", ".join(f"{k}: {_pct(v)}" for k, v in e["reasons_shown"].items()) + ".",
          "- **Notes:** " + "; ".join(f"{k}: {_pct(v)}" for k, v in e["notes"].items()) + ".",
          f"- **A top factor left out by W1:** {_pct(e['rows_with_top_factor_left_out'])} of rows (now always disclosed by P9). "
          "Features: " + (", ".join(f"{k} ({v})" for k, v in e["left_out_features"].items()) or "none") + ".",
          f"- **Coverage:** the shown reasons account for a median {_pct(e['coverage_median'])} (IQR {_pct(e['coverage_iqr'][0])}–"
          f"{_pct(e['coverage_iqr'][1])}) of the contribution pushing the shown way.", "",
          "## 2. Reliability by group (out of sample)", "",
          f"Judged only with at least {MIN_USERS} users and {MIN_POS} positive rows. All rows: PR-AUC {sg['overall']['pr_auc']:.3f}, "
          f"ROC-AUC {sg['overall']['roc_auc']:.3f}, mean predicted − observed {sg['overall']['citl']:+.4f}, "
          f"recall at 30% {sg['overall']['recall']:.2f}.", ""]
    for by in GROUPS:
        L += [f"### {by.replace('_', ' ')}", "",
              "| Group | Users | Rows | Positive | PR-AUC (lift) | ROC-AUC | Mean pred. − observed | ECE | Recall at 30% | Precision at 30% | Reading |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sg["groups"][by]:
            if "pr_auc" not in r:
                L.append(f"| {r['group']} | {r['users']} | {r['rows']} | {r['positives']} | too few to judge | | | | | | — |")
                continue
            read = ", ".join(k for k, f in (("calibration concern", r["calibration_concern"]), ("ranking concern", r["ranking_concern"])) if f) \
                or "no concern found"
            L.append(f"| {r['group']} | {r['users']} | {r['rows']} | {r['prevalence']:.1%} | {r['pr_auc']:.3f} [{r['pr_auc_ci'][0]:.3f}, "
                     f"{r['pr_auc_ci'][1]:.3f}] ({r['lift']:.1f}×) | {r['roc_auc']:.3f} [{r['roc_auc_ci'][0]:.3f}, {r['roc_auc_ci'][1]:.3f}] | "
                     f"{r['citl']:+.3f} [{r['citl_ci'][0]:+.3f}, {r['citl_ci'][1]:+.3f}] | {r['ece']:.3f} | {r['recall']:.2f} "
                     f"[{r['recall_ci'][0]:.2f}, {r['recall_ci'][1]:.2f}] | {r['precision']:.2f} | {read} |")
        L.append("")
    L += ["## 3. The 30% warning line: options for unequal recall (descriptive)", "",
          f"Target: the all-rows recall at 30%, {mt['target_recall']:.2f}. Option (b)'s lines are chosen on other users (5 folds).", "",
          "| Type of work | (a) one line: flagged | recall | precision | false-positive rate | (b) own line (median) | flagged | recall | precision | false-positive rate |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for name in mt["one_line"]:
        a, b = mt["one_line"][name], mt["per_group"][name]
        L.append(f"| {name} | {a['flagged']:.1%} | {a['recall']:.2f} | {a['precision']:.2f} | {a['fpr']:.1%} | {b['line_median']:.0%} | "
                 f"{b['flagged']:.1%} | {b['recall']:.2f} | {b['precision']:.2f} | {b['fpr']:.1%} |")
    L += ["", "(c) Dropping age and type of work was tested and rejected (FA1, D-102): gig workers would be under-warned "
          "(12.1% predicted where 16.6% got worse).", ""]
    text = "\n".join(L) + "\n"
    (RESULTS / ("dev" if res["dev"] else "") / "EXPLANATIONS_FAIRNESS.md").write_text(text, encoding="utf-8")
    return text


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", action="store_true", help="debug on the development dataset (never reported)")
    res = run(dev=ap.parse_args(argv).dev)
    print(write(res))
    return res


if __name__ == "__main__":
    main()
