"""One-at-a-time sensitivity analysis (T-25; frozen spec §16, a Should; Patrick X1, D-88).

    python -m ml.run_sensitivity --list            # the variants, nothing run
    python -m ml.run_sensitivity --dev             # a quick check (200 users, 2 variants, ~1 minute)
    python -m ml.run_sensitivity                   # the full run (68 datasets; roughly 15-30 minutes)
    python -m ml.run_sensitivity --only shock_scale job_loss      # chosen assumptions only
    python -m ml.run_sensitivity --resume          # skip variants already in sensitivity.csv

What it does: every assumption in the register (spec §16) is moved, one at a time, to the low and
the high end of the range the spec says it is tested across, with everything else at its default.
For each setting the data are regenerated (medium noise, master seed; no transaction table, which is
drawn last and changes nothing else) and the O2 pipeline is rerun with the medium run's
hyperparameters, reused rather than re-tuned, exactly as in the robustness run (D-44). A "default"
row repeats the same with no change, so every variant is compared like with like.

Invariants
  V1  report only: nothing here touches the pre-registered criterion, the frozen spec or the O2
      results; the main result is still ml/results/O2_REPORT.md
  V2  one change per variant, on a deep copy of generator/config.yaml (the file is never written)
  V3  the seed, noise level, users and hyperparameters are the same in every variant
  V4  written row by row, so a stopped run keeps what it finished (--resume continues it)
Cost: one generation + one 5-fold fit per variant (no tuning, no bootstrap).

Output: ml/results/sensitivity.csv (one row per variant) and ml/results/SENSITIVITY.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from engine.bands import INSUFFICIENT, NAMES
from generator.run import ROOT, generate
from ml.evaluate import pr_auc
from ml.run_o2 import BASELINES, MODELS, run_experiment

RESULTS = ROOT / "ml" / "results"


# ---------------------------------------------------------------- the variants (spec §16)
def _get(cfg: dict, path: str):
    for k in path.split("."):
        cfg = cfg[k]
    return cfg


def _set(cfg: dict, path: str, value) -> None:
    *head, last = path.split(".")
    for k in head:
        cfg = cfg[k]
    cfg[last] = value


def setting(**paths) -> Callable[[dict], None]:
    """Set config paths (dots for nesting) to values: setting(**{"shocks.k": 0.5})."""
    def apply(cfg):
        for path, value in paths.items():
            _set(cfg, path, value)
    return apply


def scaled(factor: float, *paths: str) -> Callable[[dict], None]:
    """Multiply numbers (or each number in a [low, high] range) at config paths."""
    def apply(cfg):
        for path in paths:
            v = _get(cfg, path)
            _set(cfg, path, [x * factor for x in v] if isinstance(v, list) else v * factor)
    return apply


def shifted(delta: float, *paths: str) -> Callable[[dict], None]:
    def apply(cfg):
        for path in paths:
            _set(cfg, path, round(_get(cfg, path) + delta, 6))
    return apply


def cushion_shifted_down(cfg) -> None:
    """Spec §16: every starting-cushion bucket one level lower (own cash only): each bucket's share
    moves to the bucket below, the lowest keeps its own too, the top one is left empty."""
    b = cfg["cushion_buckets"]
    shares = [b[0][0] + b[1][0]] + [b[i + 1][0] for i in range(1, len(b) - 1)] + [0.0]
    cfg["cushion_buckets"] = [[s, lo, hi] for s, (_, lo, hi) in zip(shares, b)]


def cushion_cap(months: float) -> Callable[[dict], None]:
    def apply(cfg):
        cfg["cushion_buckets"][-1][2] = months
    return apply


@dataclass(frozen=True)
class Variant:
    key: str              # the assumption (several variants share it)
    assumption: str       # its row in the spec's register
    setting: str          # what this variant changes it to
    apply: Callable[[dict], None]
    insufficient_rm: float | None = None    # the band rule's insufficient-income threshold, if changed


V = Variant
VARIANTS = [
    V("wage_spread", "Wage spread σ_log (C-02; default 0.35)", "0.25", setting(**{"income.employee_sigma_log": 0.25})),
    V("wage_spread", "Wage spread σ_log (C-02; default 0.35)", "0.60", setting(**{"income.employee_sigma_log": 0.60})),
    V("employment_mix", "Employment mix (C-22; default 70/15/15)", "65/30/5 (gig-heavy)",
      setting(**{"population.employment_mix": {"employee": 0.65, "gig": 0.30, "student": 0.05}})),
    V("employment_mix", "Employment mix (C-22; default 70/15/15)", "80/10/10",
      setting(**{"population.employment_mix": {"employee": 0.80, "gig": 0.10, "student": 0.10}})),
    V("gig_median", "Gig median income (C-18; default RM2,500)", "RM2,000 (-20%)", setting(**{"income.gig_median": 2000})),
    V("gig_median", "Gig median income (C-18; default RM2,500)", "RM3,000 (+20%)", setting(**{"income.gig_median": 3000})),
    V("gig_cv", "Gig month-to-month CV (C-18; default 0.15-0.35)", "0.10-0.30",
      setting(**{"income.sigma_inc.gig": [0.10, 0.30]})),
    V("gig_cv", "Gig month-to-month CV (C-18; default 0.15-0.35)", "0.25-0.45",
      setting(**{"income.sigma_inc.gig": [0.25, 0.45]})),
    V("consumption", "Consumption ratio (C-23; default U(0.75, 1.00))", "U(0.70, 0.95)",
      setting(**{"spending.consumption_ratio": [0.70, 0.95]})),
    V("consumption", "Consumption ratio (C-23; default U(0.75, 1.00))", "U(0.80, 1.05)",
      setting(**{"spending.consumption_ratio": [0.80, 1.05]})),
    V("job_loss", "Job loss probability (C-25)", "x0.5", scaled(0.5, "income.job_loss.p_young", "income.job_loss.p_older")),
    V("job_loss", "Job loss probability (C-25)", "x1.5", scaled(1.5, "income.job_loss.p_young", "income.job_loss.p_older")),
    V("gig_spread", "Gig income spread σ_log (C-18; default 0.70)", "0.50", setting(**{"income.gig_sigma_log": 0.50})),
    V("gig_spread", "Gig income spread σ_log (C-18; default 0.70)", "0.90", setting(**{"income.gig_sigma_log": 0.90})),
    V("festive", "Festive multiplier (C-19; default x1.2-1.4)", "x1.1-1.3", setting(**{"spending.festive.multiplier": [1.1, 1.3]})),
    V("festive", "Festive multiplier (C-19; default x1.2-1.4)", "x1.4-1.6", setting(**{"spending.festive.multiplier": [1.4, 1.6]})),
    V("shock_scale", "Shock scale k (C-20; default 1.0)", "0.5", setting(**{"shocks.k": 0.5})),
    V("shock_scale", "Shock scale k (C-20; default 1.0)", "1.7", setting(**{"shocks.k": 1.7})),
    V("semester", "Student semester multiplier (C-26; default x1.15)", "x1.05", setting(**{"spending.semester.multiplier": 1.05})),
    V("semester", "Student semester multiplier (C-26; default x1.15)", "x1.30", setting(**{"spending.semester.multiplier": 1.30})),
    V("bnpl_share", "BNPL user share (C-12; default 32%)", "20%", setting(**{"debt.bnpl.user_share": 0.20})),
    V("bnpl_share", "BNPL user share (C-12; default 32%)", "45%", setting(**{"debt.bnpl.user_share": 0.45})),
    V("bnpl_rate", "BNPL purchases a month (C-12; default 2.7)", "1.5", setting(**{"debt.bnpl.purchases_per_month": 1.5})),
    V("bnpl_rate", "BNPL purchases a month (C-12; default 2.7)", "4.0", setting(**{"debt.bnpl.purchases_per_month": 4.0})),
    V("pl_holding", "Personal loan holding (C-32; default 0.07)", "0.03", setting(**{"debt.personal_loan.p": 0.03})),
    V("pl_holding", "Personal loan holding (C-32; default 0.07)", "0.15", setting(**{"debt.personal_loan.p": 0.15})),
    V("pl_payment", "Personal loan instalment (C-32; default RM200-800)", "-30%", scaled(0.7, "debt.personal_loan.payment")),
    V("pl_payment", "Personal loan instalment (C-32; default RM200-800)", "+30%", scaled(1.3, "debt.personal_loan.payment")),
    V("family_holding", "Family support holding (C-33; default 0.17, a Findex lower bound)", "0.35",
      setting(**{"debt.family_support.p": 0.35})),
    V("family_amount", "Family support amount (C-33; default RM100-500)", "-50%", scaled(0.5, "debt.family_support.amount")),
    V("family_amount", "Family support amount (C-33; default RM100-500)", "+50%", scaled(1.5, "debt.family_support.amount")),
    V("parents_share", "Living with parents (C-34; default 0.6 aged 18-24 / 0.3 aged 25-35)", "-0.2 (0.4 / 0.1)",
      shifted(-0.2, "spending.living_with_parents.p_18_24", "spending.living_with_parents.p_25_35")),
    V("parents_share", "Living with parents (C-34; default 0.6 aged 18-24 / 0.3 aged 25-35)", "+0.2 (0.8 / 0.5)",
      shifted(0.2, "spending.living_with_parents.p_18_24", "spending.living_with_parents.p_25_35")),
    V("parents_housing", "Housing cost living with parents (C-34; default x0.4)", "x0.2",
      setting(**{"spending.living_with_parents.housing_factor": 0.2})),
    V("parents_housing", "Housing cost living with parents (C-34; default x0.4)", "x0.6",
      setting(**{"spending.living_with_parents.housing_factor": 0.6})),
    V("vehicle_payment", "Vehicle loan payments (C-17)", "-30%",
      scaled(0.7, "debt.vehicle_loan.car_payment", "debt.vehicle_loan.motorbike_payment")),
    V("vehicle_payment", "Vehicle loan payments (C-17)", "+30%",
      scaled(1.3, "debt.vehicle_loan.car_payment", "debt.vehicle_loan.motorbike_payment")),
    V("vehicle_own_employee", "Vehicle ownership, employees (C-29; household proxy 0.90 / 0.75)", "both x0.6",
      scaled(0.6, "debt.vehicles.employee.car", "debt.vehicles.employee.motorbike")),
    V("vehicle_own_student", "Car ownership, students (C-29; default 0.32)", "0.15", setting(**{"debt.vehicles.student.car": 0.15})),
    V("vehicle_own_student", "Car ownership, students (C-29; default 0.32)", "0.45", setting(**{"debt.vehicles.student.car": 0.45})),
    V("vehicle_loan", "Vehicle loan given ownership (C-17; default 0.5)", "0.3", setting(**{"debt.vehicle_loan.p": 0.3})),
    V("vehicle_loan", "Vehicle loan given ownership (C-17; default 0.5)", "0.7", setting(**{"debt.vehicle_loan.p": 0.7})),
    V("pay_rise", "Pay rise probability (C-25; default 1 in 12 a month)", "x0.5", scaled(0.5, "income.pay_rise.p")),
    V("pay_rise", "Pay rise probability (C-25; default 1 in 12 a month)", "x2", scaled(2.0, "income.pay_rise.p")),
    V("gig_slow", "Gig slow-month probability (C-25; default 8%)", "x0.5", scaled(0.5, "income.gig_slow.p")),
    V("gig_slow", "Gig slow-month probability (C-25; default 8%)", "x2", scaled(2.0, "income.gig_slow.p")),
    V("rho_imp_dis", "Trait correlation impulsivity-discipline (§3a; default -0.4)", "-0.2 (weaker)",
      setting(**{"traits.rho_imp_dis": -0.2})),
    V("rho_imp_dis", "Trait correlation impulsivity-discipline (§3a; default -0.4)", "-0.6 (stronger)",
      setting(**{"traits.rho_imp_dis": -0.6})),
    V("rho_imp_ovc", "Trait correlation impulsivity-overconfidence (§3a; default 0.3)", "0.1",
      setting(**{"traits.rho_imp_ovc": 0.1})),
    V("rho_imp_ovc", "Trait correlation impulsivity-overconfidence (§3a; default 0.3)", "0.5",
      setting(**{"traits.rho_imp_ovc": 0.5})),
    V("insufficient", "Insufficient-income threshold (default RM300)", "RM200", setting(), insufficient_rm=200),
    V("insufficient", "Insufficient-income threshold (default RM300)", "RM500", setting(), insufficient_rm=500),
    V("cushion_shift", "Starting cushion mapping (C-21; Findex buckets)", "every bucket one level down (own cash only)",
      cushion_shifted_down),
    V("cushion_cap", "Starting cushion top cap (C-21; default 6 months)", "4 months", cushion_cap(4.0)),
    V("cushion_cap", "Starting cushion top cap (C-21; default 6 months)", "9 months", cushion_cap(9.0)),
    V("card_holding", "Credit card holding (C-27; default 0.15)", "0.10", setting(**{"debt.credit_card.share_of_workers": 0.10})),
    V("card_holding", "Credit card holding (C-27; default 0.15)", "0.25", setting(**{"debt.credit_card.share_of_workers": 0.25})),
    V("card_limit", "Credit limit (C-28; default 2 x gross income)", "3 x above RM3,000 a month (no BNM cap there)",
      setting(**{"debt.credit_card.limit_multiple_high": 3, "debt.credit_card.high_income_gross": 3000})),
    V("budget_rule", "Budget rule (default 0.95 x median of the previous 3 months)", "0.90",
      setting(**{"spending.budget_factor": 0.90})),
    V("budget_rule", "Budget rule (default 0.95 x median of the previous 3 months)", "1.00",
      setting(**{"spending.budget_factor": 1.00})),
    V("correction_months", "Correction duration (default 3 months)", "1 month", setting(**{"behaviour.correction_months": 1})),
    V("correction_kappa", "Correction size κ (default U(0.10, 0.25))", "U(0.05, 0.15)",
      setting(**{"behaviour.correction_kappa": [0.05, 0.15]})),
    V("goal_stickiness", "Goal stickiness probability (default = overconfidence)", "half",
      setting(**{"behaviour.goal_stickiness_scale": 0.5})),
    V("goal_stickiness", "Goal stickiness probability (default = overconfidence)", "off",
      setting(**{"behaviour.goal_stickiness_scale": 0.0})),
    V("card_start_balance", "Starting card balance, non-payers (C-30; default U(10%, 60%) of the limit)", "U(0%, 30%)",
      setting(**{"debt.credit_card.start_balance_share": [0.0, 0.30]})),
    V("card_start_balance", "Starting card balance, non-payers (C-30; default U(10%, 60%) of the limit)", "U(30%, 90%)",
      setting(**{"debt.credit_card.start_balance_share": [0.30, 0.90]})),
    V("car_tenure", "Car loan tenure (C-31; default 9 years)", "7 years", setting(**{"debt.vehicle_loan.car_tenure_months": 84})),
]
DEFAULT = Variant("default", "All assumptions at their defaults", "-", setting())
# rows of the register the spec itself says are not varied (§16), listed in the report
NOT_VARIED = ["Life-event frequencies, individually (stated limitation; the shock scale k varies them together)",
              "Festive and semester months stacking (allowed; not varied)"]


@contextmanager
def insufficient_threshold(rm: float | None):
    """The generator's band rule is pinned to the frozen thresholds (generator/bands.py); for one
    variant only its insufficient-income threshold is swapped, and always put back afterwards."""
    import generator.bands as gb
    old = gb.SPEC_V1
    if rm is not None:
        gb.SPEC_V1 = {**old, "insufficient_income_below_rm": rm}
    try:
        yield
    finally:
        gb.SPEC_V1 = old


def variant_config(base: dict, v: Variant) -> dict:
    cfg = copy.deepcopy(base)
    v.apply(cfg)
    return cfg


# ---------------------------------------------------------------- running
def run_variant(base_cfg: dict, o2: dict, params: dict, v: Variant, seed: int) -> dict:
    with insufficient_threshold(v.insufficient_rm):
        tables = generate(variant_config(base_cfg, v), "medium", seed, with_transactions=False)
    oof, _, _ = run_experiment(tables, o2, fixed=params, with_oracle=False)
    y = oof.y.to_numpy()
    pt = {c: pr_auc(y, oof[c]) for c in BASELINES + MODELS}
    best_ml, best_base = max(MODELS, key=pt.get), max(BASELINES, key=pt.get)
    monthly = tables["monthly"]
    return {"key": v.key, "assumption": v.assumption, "setting": v.setting, "rows": int(len(y)),
            "prevalence": round(float(y.mean()), 4), **{c: round(pt[c], 4) for c in BASELINES + MODELS},
            "best_ml": best_ml, "best_baseline": best_base, "delta": round(pt[best_ml] - pt[best_base], 4),
            "red_share": round(float((monthly.band == "RED").mean()), 4),
            "insufficient_share": round(float((monthly.band == NAMES[INSUFFICIENT]).mean()), 4)}   # "INSUFFICIENT_INCOME"


def write_report(rows: pd.DataFrame, out: Path, params: dict, n_users: int, elapsed: float) -> str:
    base = rows[rows.key == "default"].iloc[0]
    var = rows[rows.key != "default"].copy()
    var["change"] = (var.delta - base.delta).round(4)
    positive = int((var.delta > 0).sum())
    order = var.reindex(var.change.abs().sort_values(ascending=False).index)
    lines = ["# Sensitivity analysis (one at a time; T-25, frozen spec §16)", "",
             f"Reported only (V1): the pre-registered O2 result is `ml/results/O2_REPORT.md`. {len(var)} settings, "
             f"each changing one assumption to an end of its tested range; {n_users} synthetic users, medium noise, "
             f"master seed, the medium run's hyperparameters reused (D-44): {json.dumps(params)}. "
             f"Run time {elapsed / 60:.1f} min.", "",
             f"**Default** (no change, same pipeline): label rate {base.prevalence:.1%}; best ML {base.best_ml} "
             f"{base[base.best_ml]:.3f} vs best baseline {base.best_baseline} {base[base.best_baseline]:.3f}; "
             f"ΔPR-AUC {base.delta:+.3f}.", "",
             f"**ML beats the best baseline (Δ > 0) in {positive} of {len(var)} settings.** "
             f"Smallest Δ: {var.delta.min():+.3f} ({var.loc[var.delta.idxmin(), 'assumption']}: "
             f"{var.loc[var.delta.idxmin(), 'setting']}). Label rate from {var.prevalence.min():.1%} to "
             f"{var.prevalence.max():.1%}.", "",
             "Sorted by how much Δ moves against the default run:", "",
             "| Assumption | Setting | Label rate | Best ML | Best baseline | ΔPR-AUC | Change vs default | Red rows |",
             "|---|---|---|---|---|---|---|---|"]
    for _, r in order.iterrows():
        lines.append(f"| {r.assumption} | {r.setting} | {r.prevalence:.1%} | {r.best_ml} {r[r.best_ml]:.3f} | "
                     f"{r.best_baseline} {r[r.best_baseline]:.3f} | {r.delta:+.3f} | {r.change:+.3f} | {r.red_share:.1%} |")
    lines += ["", "**Not varied** (as the spec states):", ""] + [f"- {x}" for x in NOT_VARIED]
    lines += ["", "How to read it: a setting that moves Δ a lot is one whose real value matters for the O2 "
              "conclusion, so its calibration source (docs/calibration_table.md) deserves the most care in the "
              "report. A change in the label rate shows how much the assumption changes how often things get "
              "worse, independently of the models."]
    text = "\n".join(lines) + "\n"
    (out / "SENSITIVITY.md").write_text(text, encoding="utf-8")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="One-at-a-time sensitivity analysis (spec §16)")
    ap.add_argument("--list", action="store_true", help="print the variants and exit")
    ap.add_argument("--dev", action="store_true", help="a quick check: 200 users, 2 variants")
    ap.add_argument("--only", nargs="*", help="assumption keys to run (see --list)")
    ap.add_argument("--resume", action="store_true", help="skip variants already in sensitivity.csv")
    a = ap.parse_args(argv)
    if a.list:
        for v in VARIANTS:
            print(f"{v.key:22s} {v.setting:45s} {v.assumption}")
        print(f"{len(VARIANTS)} variants + the default run")
        return
    o2 = yaml.safe_load((ROOT / "ml" / "o2_config.yaml").read_text(encoding="utf-8"))
    gcfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
    metrics = RESULTS / f"medium_seed{o2['master_seed']}" / "metrics.json"
    if not metrics.exists():
        raise SystemExit(f"{metrics} is missing: run `python -m ml.run_o2` first (its hyperparameters are reused)")
    params = json.loads(metrics.read_text(encoding="utf-8"))["chosen_params"]
    out = RESULTS / ("dev_sensitivity" if a.dev else "")
    out.mkdir(parents=True, exist_ok=True)
    variants = [v for v in VARIANTS if not a.only or v.key in a.only]
    if a.dev:
        gcfg["n_users"] = 200
        variants = [v for v in VARIANTS if v.key == "shock_scale"]
    csv = out / "sensitivity.csv"
    done = pd.read_csv(csv) if a.resume and csv.exists() else pd.DataFrame()
    seen = set(zip(done.get("key", []), done.get("setting", [])))
    t0 = time.time()
    rows = done.to_dict("records")
    for v in [DEFAULT] + variants:
        if (v.key, v.setting) in seen:
            continue
        rows.append(run_variant(gcfg, o2, params, v, o2["master_seed"]))
        pd.DataFrame(rows).to_csv(csv, index=False)                    # V4: saved as it goes
        r = rows[-1]
        print(f"[{time.time() - t0:6.0f}s] {v.key:22s} {v.setting:30s} label rate {r['prevalence']:.1%}  "
              f"delta {r['delta']:+.3f}")
    write_report(pd.DataFrame(rows), out, params, gcfg["n_users"], time.time() - t0)
    print(f"done in {time.time() - t0:.0f}s -> {out / 'SENSITIVITY.md'}")


if __name__ == "__main__":
    main()
