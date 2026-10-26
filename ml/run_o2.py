"""O2 experiment, exactly as pre-registered (docs/frozen/generator_spec_v1.0.md §11, §13).

    python -m ml.run_o2 --dev                  # debug on a separate development dataset (never reported)
    python -m ml.run_o2                        # the real run: medium (criterion), low, high, robustness
    python -m ml.run_o2 --skip-robustness

Order of work in the real run (the criterion is decided before anything else is looked at):
  1. integrity: the dataset's metadata must carry the frozen spec's SHA-256
  2. medium noise, master seed: nested CV, bootstrap, success criterion, leakage alarms
  3. low and high noise: same pipeline (reported, not pass/fail)
  4. robustness: 20 seeds x 3 noise levels with the medium run's hyperparameters (D-44)
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import GroupKFold

from generator.run import FROZEN_SPEC, ROOT, generate, sha256
from ml.baselines import B0, B2Markov, b1_score
from ml.evaluate import bootstrap, ci, pairwise, pr_auc, secondary, single_feature_pr_auc
from ml.features import FEATURES, build_features, check_no_lookahead
from ml.models import f1_threshold, fit_fixed, grid_of, tune_and_fit

BASELINES, MODELS, ORACLE = ["B0", "B1", "B2"], ["lr", "rf", "xgb"], "oracle"
SIMPLICITY = ["lr", "rf", "xgb"]              # model choice for the app: simplest first
PROBABILISTIC = {"B0", "B2", "lr", "rf", "xgb", "oracle"}


def load_tables(folder: Path) -> dict:
    return {k: pd.read_parquet(folder / f"{k}.parquet")
            for k in ("users", "monthly", "flags", "labels", "latent")}


def _inner_oof_baseline(kind, X, y, groups, band_w, cush_w, folds):
    oof = np.zeros(len(y))
    for tr, va in GroupKFold(folds).split(X, y, groups):
        if kind == "B0":
            oof[va] = B0().fit(X.iloc[tr], y[tr]).predict(X.iloc[va])
        else:
            oof[va] = B2Markov().fit(band_w, cush_w, np.unique(groups[tr])).predict(X.iloc[va])
    return oof


def run_experiment(tables: dict, cfg: dict, fixed: dict | None = None, with_oracle: bool = True):
    """Nested CV over all contenders. Returns (out-of-fold frame, per-fold info, feature frame)."""
    from sklearn.isotonic import IsotonicRegression
    X = build_features(tables["monthly"], tables["users"], tables["flags"], tables["labels"])
    y, groups = X.y.to_numpy(), X.user_id.to_numpy()
    Xm = X[FEATURES].to_numpy(dtype=float)
    if with_oracle:
        lat = tables["latent"].set_index("user_id")[cfg["oracle_traits"]]
        Xo = np.hstack([Xm, lat.loc[groups].to_numpy(dtype=float)])
    mo = tables["monthly"]
    band_w = mo.pivot(index="user_id", columns="month", values="band")
    cush_w = mo.pivot(index="user_id", columns="month", values="cushion_months")
    b1_all = b1_score(X)

    oof = X[["user_id", "t", "y", "employment_type", "band_t", "worsened", "shortfall_t1_t3"]].copy()
    names = BASELINES + MODELS + ([ORACLE] if with_oracle else [])
    for c in names:
        oof[c], oof[c + "_cal"], oof[c + "_label"] = np.nan, np.nan, -1
    folds = []
    for k, (tr, te) in enumerate(GroupKFold(cfg["outer_folds"]).split(Xm, y, groups)):
        info = {"fold": k}
        # ---- baselines ----
        for c in ("B0", "B2"):
            if c == "B0":
                pred = B0().fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
            else:
                pred = B2Markov().fit(band_w, cush_w, np.unique(groups[tr])).predict(X.iloc[te])
            oof.loc[oof.index[te], c] = pred
            if fixed is None:
                inner = _inner_oof_baseline(c, X.iloc[tr], y[tr], groups[tr], band_w, cush_w, cfg["inner_folds"])
                th = f1_threshold(y[tr], inner)
                iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(inner, y[tr])
                oof.loc[oof.index[te], c + "_cal"] = iso.predict(pred)
                oof.loc[oof.index[te], c + "_label"] = (pred >= th).astype(int)
        oof.loc[oof.index[te], "B1"] = b1_all[te]
        if fixed is None:     # B1 has no fitting, so its threshold is chosen on the training rows directly
            th = f1_threshold(y[tr], b1_all[tr])
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(b1_all[tr], y[tr])
            oof.loc[oof.index[te], "B1_cal"] = iso.predict(b1_all[te])
            oof.loc[oof.index[te], "B1_label"] = (b1_all[te] >= th).astype(int)
        # ---- models ----
        for c in MODELS + ([ORACLE] if with_oracle else []):
            XX = Xo if c == ORACLE else Xm
            if fixed is None:
                res = tune_and_fit(c, cfg, XX[tr], y[tr], groups[tr])
                pred = res["model"].predict_proba(XX[te])[:, 1]
                oof.loc[oof.index[te], c + "_cal"] = res["iso"].predict(pred)
                oof.loc[oof.index[te], c + "_label"] = (pred >= res["threshold"]).astype(int)
                info[c] = {"param": res["param"], "n_rounds": res["n_rounds"],
                           "inner_pr_auc": res["inner_pr_auc"], "threshold": res["threshold"]}
            else:
                model = fit_fixed(c, cfg, fixed[c]["param"], fixed[c]["n_rounds"], XX[tr], y[tr])
                pred = model.predict_proba(XX[te])[:, 1]
            oof.loc[oof.index[te], c] = pred
        folds.append(info)
    return oof, folds, X


def chosen_params(folds: list[dict], cfg: dict) -> dict:
    """Most frequent setting across outer folds (ties -> simpler, i.e. earlier in the grid);
    XGBoost: median best iteration (D-44)."""
    out = {}
    for c in MODELS + [ORACLE]:
        if c not in folds[0]:
            continue
        params = [f[c]["param"] for f in folds]
        grid = grid_of(c, cfg)
        counts = Counter(params)
        top = max(counts.values())
        param = next(g for g in grid if counts.get(g, 0) == top)
        rounds = [f[c]["n_rounds"] for f in folds if f[c]["n_rounds"] is not None]
        out[c] = {"param": param, "n_rounds": int(np.median(rounds)) if rounds else None}
    return out


def evaluate_main(oof: pd.DataFrame, X: pd.DataFrame, folds: list, cfg: dict, B: int, seed: int) -> dict:
    names = [c for c in BASELINES + MODELS + [ORACLE] if c in oof]
    y = oof.y.to_numpy()
    point = {c: pr_auc(y, oof[c]) for c in names}
    best_ml = max(MODELS, key=lambda c: point[c])
    best_base = max(BASELINES, key=lambda c: point[c])
    boot = bootstrap(oof, names, B, seed)
    cis = {c: ci(boot[:, i], cfg["ci_level"]) for i, c in enumerate(names)}
    d = boot[:, names.index(best_ml)] - boot[:, names.index(best_base)]
    d_lo, d_hi = ci(d, cfg["ci_level"])
    lo_best = cis[best_ml][0]
    app_model = next(c for c in SIMPLICITY if cis[c][1] >= lo_best)
    sec = {c: secondary(y, oof[c].to_numpy(), oof[c + "_label"].to_numpy(), oof[c + "_cal"].to_numpy(),
                        c in PROBABILISTIC) for c in names}
    pos = oof[oof.y == 1]
    comp = {"band_only": int((pos.worsened & ~pos.shortfall_t1_t3).sum()),
            "shortfall_only": int((~pos.worsened & pos.shortfall_t1_t3).sum()),
            "both": int((pos.worsened & pos.shortfall_t1_t3).sum())}
    by_band = oof.groupby("band_t").y.agg(["count", "mean"]).round(4).to_dict("index")
    by_type = {typ: {c: pr_auc(g.y, g[c]) for c in names} for typ, g in oof.groupby("employment_type")}
    return {"n_rows": int(len(oof)), "n_users": int(oof.user_id.nunique()), "prevalence": float(y.mean()),
            "point": point, "ci": cis, "best_ml": best_ml, "best_baseline": best_base,
            "delta": point[best_ml] - point[best_base], "delta_ci": [d_lo, d_hi],
            "criterion_pass": bool(d_lo > 0), "app_model": app_model,
            "pairwise": pairwise(boot, point, names, cfg["ci_level"]), "secondary": sec,
            "components": comp, "by_start_band": by_band, "pr_auc_by_type": by_type,
            "chosen_params": chosen_params(folds, cfg), "folds": folds}


def leakage_alarms(oof, X, tables, cfg, params, seed) -> dict:
    lk = cfg["leakage"]
    y, groups = X.y.to_numpy(), X.user_id.to_numpy()
    over = {c: pr_auc(y, oof[c]) for c in BASELINES + MODELS if pr_auc(y, oof[c]) > lk["max_model_pr_auc"]}
    rng = np.random.default_rng(seed)
    y_shuf = rng.permutation(y)
    shuffled = {}
    Xm = X[FEATURES].to_numpy(dtype=float)
    for c in MODELS:
        pred = np.zeros(len(y))
        for tr, te in GroupKFold(cfg["outer_folds"]).split(Xm, y_shuf, groups):
            m = fit_fixed(c, cfg, params[c]["param"], params[c]["n_rounds"], Xm[tr], y_shuf[tr])
            pred[te] = m.predict_proba(Xm[te])[:, 1]
        shuffled[c] = pr_auc(y_shuf, pred)
    prev = float(y_shuf.mean())
    single = single_feature_pr_auc(X, y, groups, FEATURES, cfg["outer_folds"])
    ts_ok = check_no_lookahead(tables["monthly"], tables["users"], tables["flags"])
    alarms = {
        "any_model_over_0.95": over,
        "shuffled_pr_auc": shuffled, "shuffled_prevalence": prev,
        "shuffled_outside_tolerance": {c: v for c, v in shuffled.items() if abs(v - prev) > lk["shuffled_tolerance"]},
        "single_feature_max": max(single.items(), key=lambda kv: kv[1]),
        "single_feature_over_0.90": {f: v for f, v in single.items() if v > lk["max_single_feature_pr_auc"]},
        "feature_timestamp_test_pass": ts_ok,
    }
    alarms["any_alarm"] = bool(over or alarms["shuffled_outside_tolerance"]
                               or alarms["single_feature_over_0.90"] or not ts_ok)
    return alarms


def robustness_seeds(master: int, n: int) -> list[int]:
    """Spec §15: the robustness seeds come from SeedSequence(master).spawn(n)."""
    return [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(master).spawn(n)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "ml" / "o2_config.yaml"))
    ap.add_argument("--dev", action="store_true", help="debug on a separate development dataset")
    ap.add_argument("--skip-robustness", action="store_true")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
    from ml import report
    t0 = time.time()

    if a.dev:
        out = ROOT / cfg["results_dir"] / "dev"
        gcfg["n_users"] = cfg["dev"]["n_users"]
        runs = [("medium", cfg["dev"]["seed"], generate(gcfg, "medium", cfg["dev"]["seed"], with_transactions=False))]
        B, rob_seeds, rob_levels = cfg["dev"]["bootstrap_resamples"], robustness_seeds(cfg["dev"]["seed"], 1), ["medium"]
    else:
        out = ROOT / cfg["results_dir"]
        runs = []
        for nz in cfg["noise_levels"]:
            folder = ROOT / cfg["data_dir"] / f"{nz}_seed{cfg['master_seed']}"
            meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            if meta["spec_sha256"] != sha256(FROZEN_SPEC):
                raise SystemExit(f"Integrity check failed: {folder} was not generated from the frozen spec")
            runs.append((nz, cfg["master_seed"], load_tables(folder)))
        B, rob_seeds, rob_levels = cfg["bootstrap_resamples"], robustness_seeds(cfg["master_seed"], cfg["robustness_seeds"]), cfg["noise_levels"]
    out.mkdir(parents=True, exist_ok=True)

    results, params = {}, None
    for nz, seed, tables in runs:
        print(f"[{time.time() - t0:6.0f}s] main run: {nz}, seed {seed}")
        oof, folds, X = run_experiment(tables, cfg)
        res = evaluate_main(oof, X, folds, cfg, B, seed)
        if nz == "medium":
            params = res["chosen_params"]
            res["leakage"] = leakage_alarms(oof, X, tables, cfg, params, seed)
        folder = out / f"{nz}_seed{seed}"
        folder.mkdir(parents=True, exist_ok=True)
        oof.to_parquet(folder / "oof.parquet", index=False)
        (folder / "metrics.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
        report.reliability_plot(oof, res["best_ml"], folder / "reliability.png", f"{nz} noise")
        if nz == "medium":
            report.shap_outputs(tables, X, cfg, res, folder)
        results[nz] = res
        print(f"           best ML {res['best_ml']} {res['point'][res['best_ml']]:.3f} vs best baseline "
              f"{res['best_baseline']} {res['point'][res['best_baseline']]:.3f}; "
              f"delta CI [{res['delta_ci'][0]:+.3f}, {res['delta_ci'][1]:+.3f}]")

    rob = []
    if not a.skip_robustness:
        gcfg_r = dict(gcfg)
        for nz in rob_levels:
            for s in rob_seeds:
                tables = generate(gcfg_r, nz, s, with_transactions=False)
                oof, _, X = run_experiment(tables, cfg, fixed=params, with_oracle=False)
                y = oof.y.to_numpy()
                pt = {c: pr_auc(y, oof[c]) for c in BASELINES + MODELS}
                bm, bb = max(MODELS, key=pt.get), max(BASELINES, key=pt.get)
                rob.append({"noise": nz, "seed": s, "prevalence": float(y.mean()), **pt,
                            "best_ml": bm, "best_baseline": bb, "delta": pt[bm] - pt[bb]})
                print(f"[{time.time() - t0:6.0f}s] robustness {nz} seed {s}: delta {pt[bm] - pt[bb]:+.3f}")
        pd.DataFrame(rob).to_csv(out / "robustness.csv", index=False)

    report.write_report(results, rob, cfg, out, dev=a.dev, elapsed=time.time() - t0)
    print(f"done in {time.time() - t0:.0f}s -> {out / 'O2_REPORT.md'}")


if __name__ == "__main__":
    main()
