"""Exploratory checks (D-101). **Decided after the O2 results were seen**, so they are reported as
exploratory, never as pre-registered evidence, and nothing here changes the O2 result or the app.

    .venv\\Scripts\\python -m ml.exploratory      # about a minute -> ml/results/EXPLORATORY.md

  1 fairness      per employment type and age group, from the saved out-of-fold predictions:
                  base rate, PR-AUC (user-level bootstrap CI), lift over chance, calibration (mean and
                  a binned reliability table), and recall / precision at the model's own threshold
  2 demographics  logistic regression refitted without age and type of work (same features otherwise,
                  the medium run's chosen C, no tuning) against the same model with them
  3 health score  does the app's health score (and each of its four parts) rank who gets worse?
  4 advice        does each advice rule fire for people who really get worse more often? And how much
                  of what drives the model's forecast does some advice rule address?
  5 readability   Flesch reading ease and grade level of every text the app shows (approximate:
                  syllables are counted by a vowel-group rule)
Medium noise, master seed, the same 6,646 rows as O2 throughout.
"""
from __future__ import annotations

import re
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold

from engine.assess import RED_NOTE
from engine.bands import load_thresholds
from engine.forecast import REASON_WORDS, _load
from engine.health import health_score
from engine.rules import _ADVICE, Context, advise, limits
from engine.state import MonthRecord, compute_states
from ml.evaluate import bootstrap, ci, pr_auc
from ml.features import FEATURES, build_features
from ml.models import fit_fixed

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
SEED = CFG["master_seed"]
DATA = ROOT / CFG["data_dir"] / f"medium_seed{SEED}"
RESULTS = ROOT / CFG["results_dir"]
OUT = RESULTS / "EXPLORATORY.md"
B = 1000

# what each advice rule acts on (the forecast's features), for the coverage check (section 4)
RULE_FOR = {"dsr_t": ["R03", "R04", "R13"], "cushion_t": ["R05", "R06"], "shortfall_last3": ["R02"],
            "bnpl_active": ["R07"], "bnpl_new3": ["R07"], "savings_rate3": ["R11"], "disc_cv3": ["R08"],
            "overrun_count3": ["R08"], "flag_impulsivity": ["R08"], "festive_next3": ["R09"],
            "inc_median3": ["R01 (only when income is too low to judge)"]}
NOT_ACTIONABLE = ("type_", "age_", "band_")            # demographics, and the band shown on its own


def tables() -> dict:
    return {k: pd.read_parquet(DATA / f"{k}.parquet") for k in ("users", "monthly", "flags", "labels")}


def oof_frame(users: pd.DataFrame) -> pd.DataFrame:
    oof = pd.read_parquet(RESULTS / f"medium_seed{SEED}" / "oof.parquet")
    return oof.merge(users[["user_id", "age_band"]], on="user_id", how="left")


# ---------------------------------------------------------------- 1 fairness
def _pr_auc_ci(g: pd.DataFrame, col: str) -> tuple:
    boot = bootstrap(g.assign(s=g[col]), ["s"], B, SEED)[:, 0]
    return pr_auc(g.y, g[col]), *ci(boot, CFG["ci_level"])


def reliability(g: pd.DataFrame, bins: int = 5) -> list[tuple]:
    """(mean predicted, observed rate, rows) per quantile bin of the calibrated probability."""
    q = pd.qcut(g.lr_cal.rank(method="first"), bins, labels=False)
    return [(float(h.lr_cal.mean()), float(h.y.mean()), int(len(h))) for _, h in g.groupby(q)]


def fairness(oof: pd.DataFrame) -> dict:
    out = {}
    for by in ("employment_type", "age_band"):
        rows = []
        for name, g in oof.groupby(by):
            p, lo, hi = _pr_auc_ci(g, "lr")
            rows.append({"group": name, "rows": len(g), "prevalence": g.y.mean(), "pr_auc": p, "ci": (lo, hi),
                         "lift": p / g.y.mean(), "mean_pred": g.lr_cal.mean(),
                         "recall": recall_score(g.y, g.lr_label, zero_division=0),
                         "precision": precision_score(g.y, g.lr_label, zero_division=0),
                         "reliability": reliability(g)})
        out[by] = rows
    return out


# ---------------------------------------------------------------- 2 without demographics
def lr_oof(X: pd.DataFrame, feats: list[str], C: float) -> np.ndarray:
    Xm, y, groups = X[feats].to_numpy(dtype=float), X.y.to_numpy(), X.user_id.to_numpy()
    out = np.zeros(len(y))
    for tr, te in GroupKFold(CFG["outer_folds"]).split(Xm, y, groups):
        out[te] = fit_fixed("lr", CFG, C, None, Xm[tr], y[tr]).predict_proba(Xm[te])[:, 1]
    return out


def without_demographics(t: dict, C: float) -> dict:
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    no_demo = [f for f in FEATURES if not f.startswith(("type_", "age_"))]
    df = X[["user_id", "y", "employment_type"]].assign(with_demo=lr_oof(X, list(FEATURES), C),
                                                        without=lr_oof(X, no_demo, C))
    boot = bootstrap(df, ["with_demo", "without"], B, SEED)
    point = {c: pr_auc(df.y, df[c]) for c in ("with_demo", "without")}
    by_type = {name: {c: average_precision_score(g.y, g[c]) for c in ("with_demo", "without")}
               for name, g in df.groupby("employment_type")}
    return {"point": point, "delta": point["without"] - point["with_demo"],
            "delta_ci": ci(boot[:, 1] - boot[:, 0], CFG["ci_level"]), "by_type": by_type,
            "dropped": [f for f in FEATURES if f not in no_demo], "C": C}


# ---------------------------------------------------------------- 3 health score and 4 advice
def record(r) -> MonthRecord:
    return MonthRecord(net_income=r.net_income, debt_payments=r.commitments_total, outstanding_debt=r.outstanding_debt,
                       cash=r.cash, essential_spending=r.spend_essential, total_spending=r.spend_total,
                       family_support=r.family_support, shortfall=bool(r.shortfall), month=int(r.month),
                       bnpl_purchases=r.bnpl_purchases, bnpl_new_count=int(r.bnpl_new_purchases),
                       bnpl_instalments=r.pay_bnpl, event_costs=r.event_shock_cost + r.event_minor_cost,
                       other_fees=r.late_fees, education_spending=r.spend_education)


def per_row_engine(t: dict, oof: pd.DataFrame) -> pd.DataFrame:
    """The app's health score and the advice that fires, for every O2 row, from months 1..t only."""
    th = load_thresholds()
    users = t["users"].set_index("user_id")
    want = set(zip(oof.user_id, oof.t))
    rows = []
    for u, g in t["monthly"].groupby("user_id"):
        recs = [record(r) for r in g.sort_values("month").itertuples()]
        states = compute_states(recs, th)                               # state i uses records 0..i only
        fest = users.loc[u, "festive_month"]
        for i, s in enumerate(states):
            month = i + 1
            if (u, month) not in want:
                continue
            win = recs[max(0, i - 2):i + 1]
            hs = health_score(s, th)
            ctx = Context(state=s, debt_payments=recs[i].debt_payments,
                          essentials_and_debts=sum(r.essential_spending + r.debt_payments for r in win) / len(win),
                          cash=recs[i].cash, bnpl_plans=(recs[i - 1].bnpl_new_count if i else 0) + recs[i].bnpl_new_count,
                          bnpl_monthly=recs[i].bnpl_instalments, festive_month=int(fest) == recs[i].month)
            rows.append({"user_id": u, "t": month, "health": hs.score, **{f"ind_{k}": v for k, v in hs.indicators.items()},
                         "rules": {a.rule.split("_")[0] for a in advise(ctx, th)}})
    return oof.merge(pd.DataFrame(rows), on=["user_id", "t"], how="left")


def health_check(df: pd.DataFrame) -> dict:
    """Risk = 100 - score (a low score should mean more risk). Parts missing for a row count as 100."""
    out = {"health score": pr_auc(df.y, 100 - df.health)}
    for part in ("spend", "savings", "debt", "bills"):
        col = f"ind_{part}"
        if col in df:
            out[f"part: {part}"] = pr_auc(df.y, 100 - df[col].fillna(100))
    out.update({"B0 base rates (O2)": pr_auc(df.y, df.B0), "logistic regression (O2)": pr_auc(df.y, df.lr)})
    tiers = df.assign(tier=pd.cut(df.health, [-1, 39.999, 79.999, 101], labels=["Vulnerable", "Coping", "Healthy"]))
    boot = bootstrap(df.assign(h=100 - df.health), ["lr", "h", "B0"], B, SEED)
    return {"pr_auc": out, "prevalence": df.y.mean(),
            "lr_minus_health": (out["logistic regression (O2)"] - out["health score"], *ci(boot[:, 0] - boot[:, 1], CFG["ci_level"])),
            "health_minus_b0": (out["health score"] - out["B0 base rates (O2)"], *ci(boot[:, 1] - boot[:, 2], CFG["ci_level"])),
            "by_tier": [(str(k), len(g), g.y.mean()) for k, g in tiers.groupby("tier", observed=True)]}


def advice_relevance(df: pd.DataFrame) -> list[dict]:
    """Rules that need the forecast (R10) or the impulsivity flag (R08) aren't evaluated here."""
    out = []
    for rule in sorted({r for s in df.rules for r in s}):
        fired = df.rules.apply(lambda s: rule in s)
        if fired.sum() and (~fired).sum():
            out.append({"rule": rule, "share": fired.mean(), "rate_fired": df.y[fired].mean(),
                        "rate_not": df.y[~fired].mean(), "ratio": df.y[fired].mean() / max(df.y[~fired].mean(), 1e-9)})
    return out


def driver_coverage(t: dict) -> dict:
    art = _load()
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    pipe = art["model"]
    z = pipe[0].transform(X[FEATURES].to_numpy(dtype=float))
    mass = dict(zip(FEATURES, np.abs(z * pipe[-1].coef_[0]).mean(axis=0)))
    actionable = {f: m for f, m in mass.items() if not f.startswith(NOT_ACTIONABLE)}
    covered = sum(m for f, m in actionable.items() if f in RULE_FOR)
    ranked = sorted(actionable.items(), key=lambda kv: -kv[1])
    return {"ranked": ranked, "coverage": covered / sum(actionable.values()),
            "demographic_share": sum(m for f, m in mass.items() if f.startswith(("type_", "age_"))) / sum(mass.values())}


# ---------------------------------------------------------------- 5 readability
def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1                                     # a number or symbol, read as one unit
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)


def flesch(text: str) -> tuple[float, float]:
    sentences = max(1, len(re.findall(r"[.!?](\s|$)", text)))
    words = text.split()
    syl = sum(syllables(w) for w in words)
    wps, spw = len(words) / sentences, syl / max(len(words), 1)
    return 206.835 - 1.015 * wps - 84.6 * spw, 0.39 * wps + 11.8 * spw - 15.59


def readability() -> list[dict]:
    sample = {**limits(load_thresholds()), "shortfalls": 1, "debt_payments": "RM400", "dsr_pct": "57%",
              "cushion_months": "0.5", "gap_to_first": "RM600", "gap_to_next": "RM3,000", "bnpl_plans": 2,
              "bnpl_monthly": "RM150", "risk_pct": "34%", "overspend_pct": "10%", "new_band": "Green"}
    out = []
    for rule, texts in _ADVICE.items():
        for key, text in texts.items():
            if key.startswith("text"):
                filled = text.format(**sample)
                out.append({"what": f"advice {rule.split('_')[0]}" + ("" if key == "text" else f" ({key[5:]})"),
                            "text": filled, **dict(zip(("ease", "grade"), flesch(filled)))})
    for f, w in REASON_WORDS.items():
        for side in ("high", "low"):
            if side in w:
                out.append({"what": f"reason {f} ({side})", "text": w[side] + ".",
                            **dict(zip(("ease", "grade"), flesch(w[side] + ".")))})
    out.append({"what": "forecast note (already Red)", "text": RED_NOTE, **dict(zip(("ease", "grade"), flesch(RED_NOTE)))})
    return out


# ---------------------------------------------------------------- report
def _p(x):
    return f"{x:.1%}"


def write(res: dict) -> str:
    L = ["# Exploratory checks (D-101)", "",
         "**Exploratory:** decided after the O2 results were seen (the model evaluation of 17 Oct 2026), so they "
         "describe the result but are **not** pre-registered evidence; nothing here changes the O2 result or the app. "
         "Medium noise, master seed, the same 6,646 rows as O2. Generated by `ml/exploratory.py`.", ""]
    L += ["## 1. Fairness across groups (logistic regression, the app's model)", ""]
    for by, title in (("employment_type", "type of work"), ("age_band", "age group")):
        L += [f"### By {title}", "", "| Group | Rows | Base rate | PR-AUC [95% CI] | × chance | Mean predicted | "
              "Recall | Precision |", "|---|---|---|---|---|---|---|---|"]
        for r in res["fairness"][by]:
            L.append(f"| {r['group']} | {r['rows']} | {_p(r['prevalence'])} | {r['pr_auc']:.3f} [{r['ci'][0]:.3f}, "
                     f"{r['ci'][1]:.3f}] | {r['lift']:.1f} | {_p(r['mean_pred'])} | {r['recall']:.2f} | {r['precision']:.2f} |")
        L += ["", "Reliability (calibrated probability, five equal-sized bins: predicted → observed):", ""]
        for r in res["fairness"][by]:
            L.append(f"- **{r['group']}**: " + "; ".join(f"{p:.0%} → {o:.0%}" for p, o, _ in r["reliability"]))
        L.append("")
    recalls = [r["recall"] for r in res["fairness"]["employment_type"]]
    L += [f"Gap in recall between types of work (an equal-opportunity check): {max(recalls) - min(recalls):.2f}.", ""]
    d = res["demographics"]
    L += ["## 2. The same model without age and type of work", "",
          f"Logistic regression with the medium run's C = {d['C']}, refitted in the same 5 folds, with and without "
          f"{', '.join(d['dropped'])}.", "",
          f"PR-AUC with them {d['point']['with_demo']:.3f}, without {d['point']['without']:.3f}: "
          f"Δ {d['delta']:+.3f} [{d['delta_ci'][0]:+.3f}, {d['delta_ci'][1]:+.3f}].", "",
          "| Type of work | With | Without |", "|---|---|---|"]
    L += [f"| {k} | {v['with_demo']:.3f} | {v['without']:.3f} |" for k, v in d["by_type"].items()]
    L += ["", "**But ranking isn't everything:** the follow-up calibration check (`FORECAST_V2_CHECK.md`, D-102) found that "
              "without type of work the model under-states gig workers' risk (12.1% predicted vs 16.6% observed), so the "
              "app keeps the model with these inputs."]
    h = res["health"]
    L += ["", "## 3. Does the health score rank who gets worse?", "",
          f"Base rate {_p(h['prevalence'])}. Risk = 100 − score.", "", "| Score | PR-AUC |", "|---|---|"]
    L += [f"| {k} | {v:.3f} |" for k, v in h["pr_auc"].items()]
    a, b = h["lr_minus_health"], h["health_minus_b0"]
    L += ["", f"Logistic regression − health score: {a[0]:+.3f} [{a[1]:+.3f}, {a[2]:+.3f}]; "
              f"health score − B0: {b[0]:+.3f} [{b[1]:+.3f}, {b[2]:+.3f}] (user-level bootstrap, 95%)."]
    L += ["", "| Health tier | Rows | Got worse |", "|---|---|---|"]
    L += [f"| {k} | {n} | {_p(r)} |" for k, n, r in h["by_tier"]]
    L += ["", "## 4. Advice", "", "### Does a rule fire for people who really get worse more often?", "",
          "(R08 and R10 need the impulsivity flag and the forecast, so they aren't evaluated here.)", "",
          "| Rule | Fires for | Got worse when it fires | When it doesn't | Ratio |", "|---|---|---|---|---|"]
    L += [f"| {r['rule']} | {_p(r['share'])} | {_p(r['rate_fired'])} | {_p(r['rate_not'])} | {r['ratio']:.1f}× |"
          for r in res["advice"]]
    c = res["coverage"]
    L += ["", "### Which of the forecast's drivers does some advice address?", "",
          f"Of the forecast's weight on things a user can act on (mean |SHAP| of everything except age, type of work "
          f"and the band indicators), **{_p(c['coverage'])}** sits on factors some advice rule addresses. Age and "
          f"type of work carry {_p(c['demographic_share'])} of the model's total weight.", "",
          "| Rank | Driver | Mean \\|SHAP\\| | Advice that addresses it |", "|---|---|---|---|"]
    L += [f"| {i} | {f} | {m:.3f} | {', '.join(RULE_FOR.get(f, ['-']))} |" for i, (f, m) in enumerate(c["ranked"][:12], 1)]
    rd = res["readability"]
    ease = [r["ease"] for r in rd]
    grade = [r["grade"] for r in rd]
    L += ["", "## 5. Readability (approximate)", "",
          f"{len(rd)} texts. Median Flesch reading ease **{median(ease):.0f}** (60 or more is plain English), "
          f"{sum(e >= 60 for e in ease)} of {len(rd)} at 60 or more; median grade level **{median(grade):.1f}**. "
          "The hardest five:", "", "| Text | Ease | Grade |", "|---|---|---|"]
    L += [f"| {r['what']} | {r['ease']:.0f} | {r['grade']:.1f} |" for r in sorted(rd, key=lambda r: r["ease"])[:5]]
    text = "\n".join(L) + "\n"
    OUT.write_text(text, encoding="utf-8")
    return text


def main() -> dict:
    import json
    t = tables()
    oof = oof_frame(t["users"])
    C = json.loads((RESULTS / f"medium_seed{SEED}" / "metrics.json").read_text(encoding="utf-8"))["chosen_params"]["lr"]["param"]
    engine_rows = per_row_engine(t, oof)
    res = {"fairness": fairness(oof), "demographics": without_demographics(t, C), "health": health_check(engine_rows),
           "advice": advice_relevance(engine_rows), "coverage": driver_coverage(t), "readability": readability()}
    print(write(res))
    return res


if __name__ == "__main__":
    main()
