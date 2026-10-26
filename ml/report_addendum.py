"""O2 report addendum (D-98): the items the frozen spec (v1.0 §11, §13) says are always reported but
that the 2026-10-12 report showed only for medium noise, or not at all. **No model is re-run**: every
number is read from that run's saved files (`<noise>_seed*/metrics.json`, the label tables), and the
original `O2_REPORT.md` is left exactly as generated. The Monte Carlo comparator is added once
`python -m ml.mc_comparator` has been run.

    .venv\\Scripts\\python -m ml.report_addendum      # -> ml/results/O2_ADDENDUM.md (seconds)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from .report import LABEL, breakdown_lines, by_type_table, secondary_table

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "ml" / "results"
DATA = ROOT / "data" / "synthetic"
FROZEN = ROOT / "docs" / "frozen" / "generator_spec_v1.0.md"
SEED = 20261009
NOISE = ("medium", "low", "high")
OUT = RESULTS / "O2_ADDENDUM.md"

# spec §13 "Always reported" (and §11's exclusion count), with where each one is
CHECKLIST = [
    ("All models × all noise levels (PR-AUC with CIs)", "O2_REPORT.md: PR-AUC table"),
    ("Confusion matrices", "O2_REPORT.md (medium); this addendum §2 (all levels)"),
    ("Brier scores, raw and after isotonic calibration", "O2_REPORT.md (medium); this addendum §2 (all levels)"),
    ("Reliability plots", "`<noise>_seed*/reliability.png`, all three levels (raw and calibrated curves)"),
    ("SHAP global summary + 3 persona explanations", "`medium_seed*/shap_summary.png`, `shap_personas.md`"),
    ("Every failure", "O2_REPORT.md: leakage alarms (none); run log: no errors; this addendum §1 (exclusions)"),
    ("Label prevalence", "O2_REPORT.md, per noise level"),
    ("Positives by component (band only / shortfall only / both)", "O2_REPORT.md (medium); this addendum §3 (all levels)"),
    ("Positives by starting band", "O2_REPORT.md (medium); this addendum §3 (all levels)"),
    ("PR-AUC per employment type", "O2_REPORT.md (medium); this addendum §4 (all levels)"),
    ("Rows excluded by the label rule, counted (§11)", "this addendum §1"),
    ("Effect size (ΔPR-AUC point estimate) with the verdict", "O2_REPORT.md: success criterion"),
    ("All pairwise differences", "O2_REPORT.md: pairwise table (medium, the criterion's level)"),
    ("Robustness: 20 seeds × 3 levels, median Δ, share Δ > 0", "O2_REPORT.md: robustness"),
    ("Comparator (Should): app Monte Carlo P(shortfall)", "this addendum §5"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_metrics() -> dict:
    return {nz: json.loads((RESULTS / f"{nz}_seed{SEED}" / "metrics.json").read_text(encoding="utf-8")) for nz in NOISE}


def exclusions() -> dict:
    out = {}
    for nz in NOISE:
        lab = pd.read_parquet(DATA / f"{nz}_seed{SEED}" / "labels.parquet")
        reasons = lab.exclusion_reason[lab.exclusion_reason != ""].value_counts().to_dict()
        out[nz] = {"rows": int(len(lab)), "excluded": int(sum(reasons.values())), "reasons": reasons}
    return out


def comparator_section() -> list[str]:
    path = RESULTS / "mc_comparator.json"
    if not path.exists():
        return ["**Not run yet.** `python -m ml.mc_comparator` scores the app's Monte Carlo P(shortfall in 3 months) "
                "on the same 6,646 medium-noise rows (about 35 minutes on the laptop; Patrick runs it). Its design "
                "was fixed before any run (the script's docstring, D-98). Then run this script again."]
    r = json.loads(path.read_text(encoding="utf-8"))
    L = [f"Scored on {r['rows']} rows from {r['users']} users (medium noise, master seed); "
         f"{r['minutes']} minutes. Design fixed before the run: `ml/mc_comparator.py` (D-98). "
         "Reported only; not part of the O2 criterion.\n",
         "| Target | Monte Carlo | Logistic regression | B0 base rates | MC − LR | MC − B0 |", "|---|---|---|---|---|---|"]
    for target, name in (("label", "O2 label (band worse or shortfall)"), ("shortfall_part", "shortfall part only")):
        t = r[target]
        cell = {c: f"{t['point'][c]:.3f} [{t['ci'][c][0]:.3f}, {t['ci'][c][1]:.3f}]" for c in ("mc", "lr", "B0")}
        d1, d2 = t["mc_minus_lr"], t["mc_minus_b0"]
        L.append(f"| {name} (prevalence {t['prevalence']:.1%}) | {cell['mc']} | {cell['lr']} | {cell['B0']} | "
                 f"{d1[0]:+.3f} [{d1[1]:+.3f}, {d1[2]:+.3f}] | {d2[0]:+.3f} [{d2[1]:+.3f}, {d2[2]:+.3f}] |")
    lab = r["label"]["mc_minus_lr"]
    held = lab[2] < 0                                   # the pre-stated expectation: MC below the model
    L += ["", f"**The expectation stated before the run** (the Monte Carlo ranks below the model) "
              f"**{'held' if held else 'did not hold'}**: "
              + ("its PR-AUC is lower and the interval excludes 0." if held else
                 "the difference from logistic regression has an interval that includes 0, so the two are "
                 "statistically tied on the O2 label. Possible reasons, for the discussion: the simulation models "
                 "directly the mechanism behind most positives (cash running out); it uses up to 6 past months where "
                 "the model's features use 3 (both look only backwards); and in synthetic data a person's future months "
                 "resemble their past ones by construction, which favours a method that resamples the past.")]
    return L


def render(metrics: dict, excl: dict, frozen_sha: str, report_sha: str) -> str:
    match = "matches" if frozen_sha == report_sha else "**DOES NOT MATCH**"
    L = ["# O2 report addendum (pre-registered reporting items, spec v1.0 §11 and §13)", "",
         "Generated by `ml/report_addendum.py` (D-98) from the saved files of the **2026-10-12 run**; no model was "
         "re-run and `O2_REPORT.md` is unchanged. It adds the items the frozen spec says are always reported but "
         "the report showed only for medium noise, or not at all.", "",
         f"Frozen spec SHA-256 today: `{frozen_sha}` ({match} the one printed in `O2_REPORT.md` and recorded in "
         "`docs/DECISIONS.md`).", "",
         "## Checklist: where each pre-registered item is reported", "",
         "| Item (spec §13 \"Always reported\", §11) | Where |", "|---|---|"]
    L += [f"| {item} | {where} |" for item, where in CHECKLIST]
    L += ["", "## 1. Rows excluded by the label rule (§11)", "",
          "Rows where the band at t or t+3 is \"insufficient income\" are excluded from the label.", "",
          "| Noise | Label rows | Excluded | Share | Reason |", "|---|---|---|---|---|"]
    for nz, e in excl.items():
        why = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in e["reasons"].items()) or "-"
        L.append(f"| {nz} | {e['rows']} | {e['excluded']} | {e['excluded'] / e['rows']:.1%} | {why} |")
    for i, (title, fn) in enumerate((("Secondary metrics", secondary_table), ("Label breakdown", breakdown_lines),
                                     ("PR-AUC by employment type", by_type_table)), start=2):
        L += ["", f"## {i}. {title}, every noise level", ""]
        for nz in NOISE:
            L += [f"### {nz}" + (" (the criterion's level; as in O2_REPORT.md)" if nz == "medium" else ""), ""]
            L += fn(metrics[nz]) + [""]
    L += ["## 5. Comparator: the app's Monte Carlo P(shortfall in 3 months)", ""] + comparator_section()
    L += ["", "## Notes", "",
          "- **B0 and B2 have identical confusion matrices at every noise level.** This is expected, not an error: both "
          "baselines score a row only by its state (band × cushion bucket, 9 states), so at the threshold that "
          "maximises F1 they flag the same states, and their 0/1 predictions coincide (checked: identical on all "
          f"{b0_b2_rows()} medium-noise rows). Their rankings differ, which is why their PR-AUCs differ.",
          "- `O2_REPORT.md` says the comparator was not available because T-15 was not built; T-15 has since been built "
          "and accepted as an illustrative scenario (D-79, D-81), and the comparator is §5 above. The report itself is "
          "kept as generated, as the record of the pre-registered run."]
    return "\n".join(L) + "\n"


def b0_b2_rows() -> str:
    oof = pd.read_parquet(RESULTS / f"medium_seed{SEED}" / "oof.parquet")
    if not (oof.B0_label == oof.B2_label).all():
        raise AssertionError("B0 and B2 predictions differ: update the note")
    return f"{len(oof):,}"


def main() -> str:
    report = (RESULTS / "O2_REPORT.md").read_text(encoding="utf-8")
    printed = re.search(r"frozen spec SHA-256 `([0-9a-f]{64})`", report).group(1)
    text = render(load_metrics(), exclusions(), sha256(FROZEN), printed)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return text


if __name__ == "__main__":
    main()
