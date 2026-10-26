# Sensitivity analysis (one at a time; T-25, frozen spec §16)

Reported only (V1): the pre-registered O2 result is `ml/results/O2_REPORT.md`. 2 settings, each changing one assumption to an end of its tested range; 200 synthetic users, medium noise, master seed, the medium run's hyperparameters reused (D-44): {"lr": {"param": 0.1, "n_rounds": null}, "rf": {"param": 4, "n_rounds": null}, "xgb": {"param": 3, "n_rounds": 22}, "oracle": {"param": 3, "n_rounds": 16}}. Run time 4.7 min.

**Default** (no change, same pipeline): label rate 13.6%; best ML rf 0.621 vs best baseline B2 0.389; ΔPR-AUC +0.231.

**ML beats the best baseline (Δ > 0) in 2 of 2 settings.** Smallest Δ: +0.171 (Shock scale k (C-20; default 1.0): 0.5). Label rate from 8.4% to 20.7%.

Sorted by how much Δ moves against the default run:

| Assumption | Setting | Label rate | Best ML | Best baseline | ΔPR-AUC | Change vs default | Red rows |
|---|---|---|---|---|---|---|---|
| Shock scale k (C-20; default 1.0) | 0.5 | 8.4% | rf 0.464 | B1 0.293 | +0.171 | -0.060 | 7.2% |
| Shock scale k (C-20; default 1.0) | 1.7 | 20.7% | rf 0.681 | B0 0.477 | +0.205 | -0.026 | 7.2% |

**Not varied** (as the spec states):

- Life-event frequencies, individually (stated limitation; the shock scale k varies them together)
- Festive and semester months stacking (allowed; not varied)

How to read it: a setting that moves Δ a lot is one whose real value matters for the O2 conclusion, so its calibration source (docs/calibration_table.md) deserves the most care in the report. A change in the label rate shows how much the assumption changes how often things get worse, independently of the models.
