"""Package the forecast model for the app (T-06 follow-up, feeds T-13).

    python -m ml.package

Uses exactly the model the pre-registered rule chose (O2 report: "simplest model whose CI
overlaps the best") with its chosen setting, read from the O2 metrics; nothing is re-tuned.
Calibration: isotonic regression fitted on out-of-fold predictions (GroupKFold by user), then
the model is refit on all rows. Output: ml/artifacts/forecast_v1.joblib + forecast_v1.json.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import joblib
import numpy as np
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import GroupKFold

from generator.run import FROZEN_SPEC, ROOT, sha256
from ml.features import FEATURES, build_features
from ml.models import fit_fixed
from ml.run_o2 import load_tables

VERSION = "forecast_v1"


def main():
    cfg = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
    data = ROOT / cfg["data_dir"] / f"medium_seed{cfg['master_seed']}"
    meta = json.loads((data / "metadata.json").read_text(encoding="utf-8"))
    if meta["spec_sha256"] != sha256(FROZEN_SPEC):
        raise SystemExit("dataset was not generated from the frozen spec")
    o2 = json.loads((ROOT / cfg["results_dir"] / f"medium_seed{cfg['master_seed']}" / "metrics.json")
                    .read_text(encoding="utf-8"))
    name = o2["app_model"]
    params = o2["chosen_params"][name]

    t = load_tables(data)
    X = build_features(t["monthly"], t["users"], t["flags"], t["labels"])
    Xm, y, groups = X[FEATURES].to_numpy(dtype=float), X.y.to_numpy(), X.user_id.to_numpy()

    oof = np.zeros(len(y))
    for tr, te in GroupKFold(cfg["outer_folds"]).split(Xm, y, groups):
        m = fit_fixed(name, cfg, params["param"], params["n_rounds"], Xm[tr], y[tr])
        oof[te] = m.predict_proba(Xm[te])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(oof, y)
    model = fit_fixed(name, cfg, params["param"], params["n_rounds"], Xm, y)

    out = ROOT / "ml" / "artifacts"
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "calibrator": iso, "features": FEATURES, "version": VERSION},
                out / f"{VERSION}.joblib")
    card = {
        "version": VERSION, "model": name, "setting": params, "features": FEATURES,
        "trained_on": {"dataset": str(data.relative_to(ROOT)), "rows": int(len(y)), "users": int(len(set(groups))),
                       "prevalence": float(y.mean()), "data_metadata": meta},
        "frozen_spec_sha256": sha256(FROZEN_SPEC),
        "chosen_by": "pre-registered rule: simplest model whose PR-AUC CI overlaps the best (O2 report)",
        "o2_pr_auc": {"point": o2["point"][name], "ci": o2["ci"][name]},
        "packaging_check": {"oof_pr_auc_fixed_setting": float(average_precision_score(y, oof)),
                            "oof_brier_raw": float(brier_score_loss(y, oof)),
                            "oof_brier_calibrated": float(brier_score_loss(y, iso.predict(oof)))},
        "calibration": "isotonic on out-of-fold predictions (GroupKFold by user), then refit on all rows",
        "intended_use": "Demo and persona user study only; trained on synthetic data (CLAUDE.md rule 12). "
                        "Not validated on real users.",
        "created": dt.date.today().isoformat(),
    }
    (out / f"{VERSION}.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    pc = card["packaging_check"]
    print(f"packaged {name} ({params}) -> {out / VERSION}.joblib")
    print(f"OOF PR-AUC with the fixed setting {pc['oof_pr_auc_fixed_setting']:.3f} "
          f"(O2: {o2['point'][name]:.3f}); Brier raw {pc['oof_brier_raw']:.4f} -> calibrated {pc['oof_brier_calibrated']:.4f}")


if __name__ == "__main__":
    main()
