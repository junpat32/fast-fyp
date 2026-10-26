"""Outputs that spec §13 says are always reported: tables, reliability plots, SHAP global
summary + 3 persona explanations, label breakdowns, leakage alarms, robustness."""
from __future__ import annotations

import datetime as dt
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402

from generator.run import FROZEN_SPEC, sha256  # noqa: E402
from ml.features import FEATURES  # noqa: E402
from ml.models import fit_fixed  # noqa: E402

from engine.features import LABELS as PLAIN  # noqa: E402  (one list of plain-language names)
LABEL = {"B0": "B0 base rates", "B1": "B1 rule heuristic", "B2": "B2 Markov chain", "lr": "Logistic regression",
         "rf": "Random forest", "xgb": "XGBoost", "oracle": "Oracle (hidden traits; reference only)"}


def reliability_plot(oof, model, path, title):
    fig, ax = plt.subplots(figsize=(5, 5))
    for col, lbl in ((model, "raw (class-weighted)"), (model + "_cal", "after isotonic calibration")):
        if oof[col].notna().all():
            fx, fy = calibration_curve(oof.y, np.clip(oof[col], 0, 1), n_bins=10, strategy="quantile")
            ax.plot(fy, fx, marker="o", label=lbl)
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect calibration")
    ax.set_xlabel("predicted probability")
    ax.set_ylabel("observed share getting worse")
    ax.set_title(f"Reliability: {LABEL[model]}, {title}")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _shap_values(model_name, model, Xs):
    if model_name == "lr":
        scaler, lr = model[0], model[-1]
        return (scaler.transform(Xs) - 0.0) * lr.coef_[0] - (0.0)   # centred inputs: contribution = coef * z
    sv = shap.TreeExplainer(model).shap_values(Xs)
    sv = np.asarray(sv)
    if sv.ndim == 3:                       # (n, features, classes) or (classes, n, features)
        sv = sv[..., 1] if sv.shape[-1] == 2 else sv[1]
    return sv


def shap_outputs(tables, X, cfg, res, folder):
    """Global SHAP summary for the best ML model (refit on all rows with its chosen setting) and
    top-3 reasons for one typical at-risk employee, gig worker and student."""
    best = res["best_ml"]
    p = res["chosen_params"][best]
    Xm, y = X[FEATURES].to_numpy(dtype=float), X.y.to_numpy()
    model = fit_fixed(best, cfg, p["param"], p["n_rounds"], Xm, y)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(Xm), size=min(800, len(Xm)), replace=False)
    sv = _shap_values(best, model, Xm[idx])
    plt.figure()
    shap.summary_plot(sv, Xm[idx], feature_names=[PLAIN[f] for f in FEATURES], show=False, max_display=15)
    plt.tight_layout()
    plt.savefig(folder / "shap_summary.png", dpi=120)
    plt.close("all")
    imp = pd.Series(np.abs(sv).mean(axis=0), index=FEATURES).sort_values(ascending=False)
    lines = [f"# SHAP: {LABEL[best]} (medium noise)\n", "## Global importance (mean |SHAP|), top 15\n",
             "| Rank | Feature | Mean abs SHAP |", "|---|---|---|"]
    lines += [f"| {i + 1} | {PLAIN[f]} | {v:.4f} |" for i, (f, v) in enumerate(imp.head(15).items())]
    lines += ["\n## Three persona explanations (top-3 reasons pushing risk up)\n",
              "Each persona is the positive case with the median predicted risk for its user type.\n"]
    proba = model.predict_proba(Xm)[:, 1]
    for typ in ("employee", "gig", "student"):
        cand = np.flatnonzero((X.employment_type.to_numpy() == typ) & (y == 1))
        if cand.size == 0:
            continue
        r = cand[np.argsort(proba[cand])[len(cand) // 2]]
        s = _shap_values(best, model, Xm[[r]])[0]
        top = np.argsort(-s)[:3]
        lines.append(f"### {typ.capitalize()} (user {X.user_id.iloc[r]}, month {X.t.iloc[r]}): "
                     f"predicted risk {proba[r]:.0%}")
        for j in top:
            lines.append(f"- {PLAIN[FEATURES[j]]} = {Xm[r, j]:.2f} (pushes risk {'up' if s[j] > 0 else 'down'}, "
                         f"SHAP {s[j]:+.3f})")
        lines.append("")
    (folder / "shap_personas.md").write_text("\n".join(lines), encoding="utf-8")


def _fmt_ci(c):
    return f"[{c[0]:.3f}, {c[1]:.3f}]"


# ---- tables shared by write_report and ml/report_addendum.py (one noise level's metrics.json each)
def secondary_table(r: dict) -> list[str]:
    L = ["| Contender | Recall (positives) | Macro-F1 | Brier raw | Brier calibrated | Confusion [[TN, FP], [FN, TP]] |",
         "|---|---|---|---|---|---|"]
    for c, s in r["secondary"].items():
        br = "n/a (not a probability)" if s["brier_raw"] is None else f"{s['brier_raw']:.4f}"
        L.append(f"| {LABEL[c]} | {s['recall_pos']:.3f} | {s['macro_f1']:.3f} | {br} | "
                 f"{s.get('brier_calibrated', float('nan')):.4f} | {s['confusion']} |")
    return L


def breakdown_lines(r: dict) -> list[str]:
    comp = r["components"]
    tot = sum(comp.values())
    return [f"Positives: band worsening only {comp['band_only']} ({comp['band_only'] / tot:.0%}), "
            f"shortfall only {comp['shortfall_only']} ({comp['shortfall_only'] / tot:.0%}), "
            f"both {comp['both']} ({comp['both'] / tot:.0%}).\n",
            "| Starting band | Rows | Positive rate |", "|---|---|---|"] + \
        [f"| {b} | {v['count']} | {v['mean']:.1%} |" for b, v in r["by_start_band"].items()]


def by_type_table(r: dict) -> list[str]:
    return ["| Type | " + " | ".join(LABEL[c] for c in r["point"]) + " |", "|---|" + "---|" * len(r["point"])] + \
        [f"| {t} | " + " | ".join(f"{v[c]:.3f}" for c in r["point"]) + " |" for t, v in r["pr_auc_by_type"].items()]


def write_report(results, rob, cfg, out, dev, elapsed):
    L = []
    title = "O2 results: DEVELOPMENT RUN (debugging only, NOT the pre-registered result)" if dev \
        else "O2 results (pre-registered evaluation, spec v1.0 §13)"
    L += [f"# {title}\n", f"Generated {dt.date.today().isoformat()} · run time {elapsed / 60:.1f} min · "
          f"frozen spec SHA-256 `{sha256(FROZEN_SPEC)}`\n"]
    if not dev:
        L.append("The pipeline was written and debugged on a separate development dataset (seed "
                 f"{cfg['dev']['seed']}, {cfg['dev']['n_users']} users). This run is the first time it touched the "
                 "master-seed datasets.\n")
    m = results.get("medium")
    if m:
        verdict = "PASS" if m["criterion_pass"] else "NOT MET (valid negative finding)"
        L += ["## Success criterion (medium noise, " + ("DEVELOPMENT seed, not the criterion" if dev else "master seed")
              + ")\n",
              f"**{verdict}.** Best ML = **{LABEL[m['best_ml']]}** (PR-AUC {m['point'][m['best_ml']]:.3f}); "
              f"best baseline = **{LABEL[m['best_baseline']]}** ({m['point'][m['best_baseline']]:.3f}). "
              f"ΔPR-AUC = **{m['delta']:+.3f}**, 95% CI [{m['delta_ci'][0]:+.3f}, {m['delta_ci'][1]:+.3f}] "
              f"(criterion: lower bound > 0). Label prevalence {m['prevalence']:.1%}, "
              f"{m['n_rows']} rows from {m['n_users']} users.\n",
              f"Model choice for the app (simplest whose CI overlaps the best): **{LABEL[m['app_model']]}**.\n"]
    L += ["## PR-AUC by contender and noise level (95% user-level bootstrap CI)\n",
          "| Contender | " + " | ".join(results) + " |", "|---|" + "---|" * len(results)]
    for c in ["B0", "B1", "B2", "lr", "rf", "xgb", "oracle"]:
        L.append(f"| {LABEL[c]} | " + " | ".join(
            f"{r['point'][c]:.3f} {_fmt_ci(r['ci'][c])}" if c in r["point"] else "n/a" for r in results.values()) + " |")
    for nz, r in results.items():
        L.append(f"\n{nz}: prevalence {r['prevalence']:.1%}; best ML {LABEL[r['best_ml']]} vs best baseline "
                 f"{LABEL[r['best_baseline']]}: Δ {r['delta']:+.3f} [{r['delta_ci'][0]:+.3f}, {r['delta_ci'][1]:+.3f}]")
    if m:
        L += ["\n## Pairwise differences (medium)\n", "| A | B | Δ PR-AUC | 95% CI |", "|---|---|---|---|"]
        L += [f"| {LABEL[p['a']]} | {LABEL[p['b']]} | {p['delta']:+.3f} | [{p['ci_low']:+.3f}, {p['ci_high']:+.3f}] |"
              for p in m["pairwise"]]
        for nz, r in results.items():                     # every noise level (spec §13 "always reported")
            L += [f"\n## Secondary metrics ({nz})\n"] + secondary_table(r)
            L += [f"\n## Label breakdown ({nz})\n"] + breakdown_lines(r)
            L += [f"\n### PR-AUC by employment type ({nz})\n"] + by_type_table(r)
        lk = m.get("leakage")
        if lk:
            L += ["\n## Leakage alarms (medium)\n",
                  f"- Any model PR-AUC > 0.95: {lk['any_model_over_0.95'] or 'none'}",
                  f"- Shuffled-label PR-AUC: " + ", ".join(f"{LABEL[c]} {v:.3f}" for c, v in lk["shuffled_pr_auc"].items())
                  + f" (prevalence {lk['shuffled_prevalence']:.3f}; outside ±0.03: {lk['shuffled_outside_tolerance'] or 'none'})",
                  f"- Highest single-feature PR-AUC: {PLAIN[lk['single_feature_max'][0]]} {lk['single_feature_max'][1]:.3f} "
                  f"(over 0.90: {lk['single_feature_over_0.90'] or 'none'})",
                  f"- Feature-timestamp test: {'pass' if lk['feature_timestamp_test_pass'] else 'FAIL'}",
                  f"- **Any alarm: {'YES, stop and audit' if lk['any_alarm'] else 'no'}**"]
        L += ["\n## Chosen hyperparameters (most frequent across outer folds)\n",
              "```", json.dumps(m["chosen_params"], indent=1), "```",
              "\nReliability plots (raw and after isotonic calibration): `<noise>_seed*/reliability.png` for every "
              "noise level. SHAP: `medium_seed*/shap_summary.png`, `medium_seed*/shap_personas.md`."]
    if rob:
        df = pd.DataFrame(rob)
        L += ["\n## Robustness (reported, not pass/fail; hyperparameters reused from the medium run, D-44)\n",
              "| Noise | Seeds | Median ΔPR-AUC | Share of seeds with Δ > 0 | Median prevalence |", "|---|---|---|---|---|"]
        for nz, g in df.groupby("noise", sort=False):
            L.append(f"| {nz} | {len(g)} | {g.delta.median():+.3f} | {(g.delta > 0).mean():.0%} | {g.prevalence.median():.1%} |")
    L += ["\n## Notes\n",
          "- Comparator (Should): the app's Monte Carlo P(shortfall in 3 months) is scored separately by "
          "`python -m ml.mc_comparator` (reported, not part of the criterion; see `O2_ADDENDUM.md`).",
          "- The oracle uses hidden traits and is a reference ceiling only (CLAUDE.md rule 3)."]
    (out / "O2_REPORT.md").write_text("\n".join(L), encoding="utf-8")
