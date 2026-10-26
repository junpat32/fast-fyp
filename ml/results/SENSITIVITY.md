# Sensitivity analysis (one at a time; T-25, frozen spec §16)

Reported only (V1): the pre-registered O2 result is `ml/results/O2_REPORT.md`. 67 settings, each changing one assumption to an end of its tested range; 1000 synthetic users, medium noise, master seed, the medium run's hyperparameters reused (D-44): {"lr": {"param": 0.1, "n_rounds": null}, "rf": {"param": 4, "n_rounds": null}, "xgb": {"param": 3, "n_rounds": 22}, "oracle": {"param": 3, "n_rounds": 16}}. Run time 6.7 min.

**Default** (no change, same pipeline): label rate 12.0%; best ML xgb 0.473 vs best baseline B0 0.284; ΔPR-AUC +0.189.

**ML beats the best baseline (Δ > 0) in 67 of 67 settings.** Smallest Δ: +0.147 (Shock scale k (C-20; default 1.0): 1.7). Label rate from 7.8% to 21.0%.

Sorted by how much Δ moves against the default run:

| Assumption | Setting | Label rate | Best ML | Best baseline | ΔPR-AUC | Change vs default | Red rows |
|---|---|---|---|---|---|---|---|
| Shock scale k (C-20; default 1.0) | 1.7 | 21.0% | rf 0.610 | B0 0.462 | +0.147 | -0.042 | 5.1% |
| BNPL purchases a month (C-12; default 2.7) | 1.5 | 11.2% | xgb 0.451 | B0 0.298 | +0.153 | -0.036 | 4.7% |
| Insufficient-income threshold (default RM300) | RM500 | 11.1% | rf 0.416 | B0 0.262 | +0.153 | -0.036 | 5.1% |
| Consumption ratio (C-23; default U(0.75, 1.00)) | U(0.70, 0.95) | 9.9% | xgb 0.412 | B0 0.256 | +0.156 | -0.033 | 5.0% |
| Employment mix (C-22; default 70/15/15) | 65/30/5 (gig-heavy) | 12.7% | rf 0.490 | B0 0.333 | +0.157 | -0.033 | 5.8% |
| Living with parents (C-34; default 0.6 aged 18-24 / 0.3 aged 25-35) | +0.2 (0.8 / 0.5) | 11.0% | rf 0.433 | B0 0.275 | +0.157 | -0.032 | 5.2% |
| Wage spread σ_log (C-02; default 0.35) | 0.25 | 12.5% | rf 0.444 | B0 0.284 | +0.160 | -0.029 | 4.4% |
| Gig median income (C-18; default RM2,500) | RM2,000 (-20%) | 13.1% | rf 0.484 | B0 0.321 | +0.163 | -0.026 | 5.6% |
| Vehicle loan given ownership (C-17; default 0.5) | 0.7 | 13.0% | xgb 0.494 | B0 0.332 | +0.163 | -0.026 | 8.9% |
| Trait correlation impulsivity-discipline (§3a; default -0.4) | -0.2 (weaker) | 12.0% | xgb 0.448 | B0 0.282 | +0.166 | -0.023 | 5.2% |
| Trait correlation impulsivity-discipline (§3a; default -0.4) | -0.6 (stronger) | 12.0% | xgb 0.458 | B0 0.291 | +0.167 | -0.022 | 5.2% |
| Gig slow-month probability (C-25; default 8%) | x0.5 | 11.8% | xgb 0.451 | B0 0.284 | +0.167 | -0.022 | 5.2% |
| Vehicle loan payments (C-17) | -30% | 11.1% | xgb 0.443 | B0 0.275 | +0.167 | -0.022 | 1.9% |
| BNPL purchases a month (C-12; default 2.7) | 4.0 | 12.2% | rf 0.447 | B0 0.279 | +0.168 | -0.021 | 5.7% |
| Wage spread σ_log (C-02; default 0.35) | 0.60 | 12.6% | xgb 0.491 | B0 0.321 | +0.170 | -0.019 | 6.5% |
| Gig slow-month probability (C-25; default 8%) | x2 | 12.7% | rf 0.478 | B0 0.307 | +0.170 | -0.019 | 5.3% |
| Gig income spread σ_log (C-18; default 0.70) | 0.50 | 11.6% | rf 0.434 | B0 0.263 | +0.171 | -0.018 | 4.9% |
| BNPL user share (C-12; default 32%) | 45% | 12.3% | xgb 0.465 | B0 0.293 | +0.172 | -0.017 | 5.7% |
| Family support holding (C-33; default 0.17, a Findex lower bound) | 0.35 | 13.2% | rf 0.505 | B0 0.333 | +0.172 | -0.017 | 5.1% |
| Personal loan instalment (C-32; default RM200-800) | +30% | 11.9% | xgb 0.476 | B0 0.301 | +0.174 | -0.015 | 5.4% |
| Festive multiplier (C-19; default x1.2-1.4) | x1.1-1.3 | 11.9% | xgb 0.459 | B0 0.285 | +0.174 | -0.015 | 5.2% |
| Family support amount (C-33; default RM100-500) | +50% | 12.3% | xgb 0.477 | B0 0.302 | +0.175 | -0.014 | 5.1% |
| Personal loan holding (C-32; default 0.07) | 0.15 | 12.7% | rf 0.491 | B0 0.316 | +0.175 | -0.014 | 6.5% |
| Housing cost living with parents (C-34; default x0.4) | x0.6 | 13.2% | xgb 0.478 | B0 0.303 | +0.175 | -0.014 | 5.2% |
| Credit card holding (C-27; default 0.15) | 0.10 | 13.4% | xgb 0.502 | B0 0.327 | +0.175 | -0.014 | 5.1% |
| Housing cost living with parents (C-34; default x0.4) | x0.2 | 11.5% | xgb 0.459 | B0 0.284 | +0.175 | -0.014 | 5.2% |
| Job loss probability (C-25) | x1.5 | 12.8% | xgb 0.473 | B0 0.298 | +0.175 | -0.014 | 5.1% |
| Shock scale k (C-20; default 1.0) | 0.5 | 7.8% | rf 0.379 | B0 0.178 | +0.201 | +0.012 | 5.2% |
| Vehicle loan payments (C-17) | +30% | 12.9% | rf 0.534 | B0 0.333 | +0.201 | +0.012 | 10.1% |
| Pay rise probability (C-25; default 1 in 12 a month) | x2 | 11.3% | xgb 0.460 | B0 0.282 | +0.178 | -0.011 | 4.9% |
| Vehicle ownership, employees (C-29; household proxy 0.90 / 0.75) | both x0.6 | 10.6% | xgb 0.439 | B0 0.260 | +0.179 | -0.010 | 2.3% |
| Student semester multiplier (C-26; default x1.15) | x1.30 | 12.2% | xgb 0.486 | B0 0.288 | +0.199 | +0.010 | 5.2% |
| Pay rise probability (C-25; default 1 in 12 a month) | x0.5 | 12.3% | xgb 0.474 | B0 0.294 | +0.179 | -0.009 | 5.3% |
| Car ownership, students (C-29; default 0.32) | 0.15 | 11.7% | xgb 0.458 | B0 0.278 | +0.180 | -0.009 | 5.2% |
| Consumption ratio (C-23; default U(0.75, 1.00)) | U(0.80, 1.05) | 15.5% | xgb 0.522 | B0 0.341 | +0.181 | -0.008 | 5.2% |
| Starting cushion mapping (C-21; Findex buckets) | every bucket one level down (own cash only) | 17.1% | rf 0.536 | B0 0.355 | +0.181 | -0.008 | 5.2% |
| Job loss probability (C-25) | x0.5 | 11.5% | xgb 0.449 | B0 0.268 | +0.181 | -0.008 | 5.3% |
| Starting cushion top cap (C-21; default 6 months) | 4 months | 12.9% | xgb 0.477 | B0 0.296 | +0.181 | -0.008 | 5.2% |
| BNPL user share (C-12; default 32%) | 20% | 11.2% | xgb 0.473 | B0 0.278 | +0.196 | +0.007 | 4.6% |
| Student semester multiplier (C-26; default x1.15) | x1.05 | 11.9% | xgb 0.468 | B0 0.285 | +0.182 | -0.006 | 5.2% |
| Insufficient-income threshold (default RM300) | RM200 | 12.0% | xgb 0.465 | B0 0.282 | +0.183 | -0.006 | 5.2% |
| Festive multiplier (C-19; default x1.2-1.4) | x1.4-1.6 | 12.3% | xgb 0.466 | B0 0.283 | +0.183 | -0.006 | 5.2% |
| Personal loan holding (C-32; default 0.07) | 0.03 | 11.7% | xgb 0.467 | B0 0.284 | +0.183 | -0.006 | 4.6% |
| Starting card balance, non-payers (C-30; default U(10%, 60%) of the limit) | U(0%, 30%) | 12.0% | xgb 0.471 | B0 0.287 | +0.183 | -0.005 | 5.2% |
| Starting cushion top cap (C-21; default 6 months) | 9 months | 11.4% | xgb 0.467 | B0 0.283 | +0.184 | -0.005 | 5.2% |
| Car ownership, students (C-29; default 0.32) | 0.45 | 12.0% | xgb 0.468 | B0 0.284 | +0.184 | -0.005 | 5.2% |
| Personal loan instalment (C-32; default RM200-800) | -30% | 11.7% | xgb 0.462 | B0 0.278 | +0.184 | -0.004 | 5.0% |
| Gig month-to-month CV (C-18; default 0.15-0.35) | 0.10-0.30 | 11.4% | xgb 0.465 | B0 0.280 | +0.185 | -0.004 | 5.1% |
| Correction duration (default 3 months) | 1 month | 13.0% | xgb 0.494 | B0 0.302 | +0.193 | +0.004 | 5.2% |
| Credit card holding (C-27; default 0.15) | 0.25 | 13.4% | xgb 0.520 | B0 0.328 | +0.193 | +0.004 | 5.2% |
| Living with parents (C-34; default 0.6 aged 18-24 / 0.3 aged 25-35) | -0.2 (0.4 / 0.1) | 13.1% | xgb 0.500 | B0 0.314 | +0.186 | -0.003 | 5.2% |
| Vehicle loan given ownership (C-17; default 0.5) | 0.3 | 11.2% | rf 0.452 | B0 0.266 | +0.186 | -0.003 | 2.7% |
| Budget rule (default 0.95 x median of the previous 3 months) | 1.00 | 12.0% | xgb 0.471 | B0 0.284 | +0.187 | -0.002 | 5.2% |
| Credit limit (C-28; default 2 x gross income) | 3 x above RM3,000 a month (no BNM cap there) | 12.0% | xgb 0.469 | B0 0.282 | +0.187 | -0.002 | 5.2% |
| Gig month-to-month CV (C-18; default 0.15-0.35) | 0.25-0.45 | 13.0% | xgb 0.494 | B0 0.303 | +0.191 | +0.002 | 5.3% |
| Gig income spread σ_log (C-18; default 0.70) | 0.90 | 12.3% | xgb 0.480 | B0 0.293 | +0.187 | -0.002 | 5.5% |
| Car loan tenure (C-31; default 9 years) | 7 years | 12.0% | xgb 0.475 | B0 0.284 | +0.190 | +0.001 | 5.2% |
| Correction size κ (default U(0.10, 0.25)) | U(0.05, 0.15) | 13.2% | xgb 0.496 | B0 0.308 | +0.188 | -0.001 | 5.2% |
| Starting card balance, non-payers (C-30; default U(10%, 60%) of the limit) | U(30%, 90%) | 12.0% | xgb 0.470 | B0 0.282 | +0.188 | -0.001 | 5.2% |
| Budget rule (default 0.95 x median of the previous 3 months) | 0.90 | 12.0% | xgb 0.473 | B0 0.284 | +0.188 | -0.001 | 5.2% |
| Employment mix (C-22; default 70/15/15) | 80/10/10 | 12.2% | rf 0.503 | B0 0.314 | +0.189 | +0.000 | 5.5% |
| Gig median income (C-18; default RM2,500) | RM3,000 (+20%) | 11.1% | xgb 0.454 | B0 0.265 | +0.189 | +0.000 | 4.8% |
| Family support amount (C-33; default RM100-500) | -50% | 11.8% | xgb 0.471 | B0 0.282 | +0.189 | +0.000 | 5.2% |
| Trait correlation impulsivity-overconfidence (§3a; default 0.3) | 0.5 | 12.0% | xgb 0.473 | B0 0.284 | +0.189 | +0.000 | 5.2% |
| Trait correlation impulsivity-overconfidence (§3a; default 0.3) | 0.1 | 12.0% | xgb 0.473 | B0 0.284 | +0.189 | +0.000 | 5.2% |
| Goal stickiness probability (default = overconfidence) | half | 12.0% | xgb 0.473 | B0 0.284 | +0.189 | +0.000 | 5.2% |
| Goal stickiness probability (default = overconfidence) | off | 12.0% | xgb 0.473 | B0 0.284 | +0.189 | +0.000 | 5.2% |

**Not varied** (as the spec states):

- Life-event frequencies, individually (stated limitation; the shock scale k varies them together)
- Festive and semester months stacking (allowed; not varied)

How to read it: a setting that moves Δ a lot is one whose real value matters for the O2 conclusion, so its calibration source (docs/calibration_table.md) deserves the most care in the report. A change in the label rate shows how much the assumption changes how often things get worse, independently of the models.
