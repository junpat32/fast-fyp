"""Read-only model investigation: writes diagnostic results, never changes forecast settings.

Run python -m sim.investigate_monte_carlo. Fixed design before inspecting results:
same forecast origin (month 6), 3/6 observations, horizons 1/3/6, 500/2000 paths;
three independent full-world seeds; single-seed world ablations. Ablations are
diagnostics only, not substitute acceptance data. No O2 evaluation is executed.
"""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import yaml
from scipy.stats import t
from generator.run import generate
from engine.state import MonthRecord
from sim.monte_carlo import FutureProfile, GameSnapshot, simulate_future

ROOT = Path(__file__).resolve().parents[1]


def summarize(rows):
    a = np.asarray(rows)
    lo, med, hi, truth = a.T
    return dict(n=len(a), coverage=float(np.mean((lo <= truth) & (truth <= hi))),
                below=float(np.mean(truth < lo)), above=float(np.mean(truth > hi)),
                mean_width=float(np.mean(hi-lo)), median_error=float(np.median(med-truth)))


def world(seed, variant, n_history=6, paths=2000, n_users=120):
    cfg = yaml.safe_load((ROOT / 'generator/config.yaml').read_text(encoding='utf-8'))
    cfg['n_users'] = n_users
    if variant in ('no_hidden', 'combined'):
        cfg['noise_levels']['medium']['hidden_cost_share'] = 0
    if variant in ('no_regimes', 'combined'):
        cfg['income']['job_loss']['p_young'] = 0
        cfg['income']['job_loss']['p_older'] = 0
        cfg['income']['pay_rise']['p'] = 0
        cfg['income']['gig_slow']['p'] = 0
    if variant in ('no_clustering', 'combined'):
        cfg['shocks']['clustering'] = 1
    data = generate(cfg, 'medium', seed, with_transactions=False)
    grouped = data['monthly'].groupby('user_id')
    scores = {}
    for u in data['users'].itertuples():
        rows = list(grouped.get_group(u.user_id).sort_values('month').itertuples())
        hist = [MonthRecord(net_income=r.net_income, debt_payments=r.commitments_total,
                            outstanding_debt=r.outstanding_debt, cash=r.cash,
                            essential_spending=r.spend_essential, total_spending=r.spend_total,
                            family_support=r.family_support, month=int(r.month),
                            bnpl_purchases=r.bnpl_purchases, bnpl_instalments=r.pay_bnpl,
                            education_spending=r.spend_education, other_fees=r.late_fees,
                            event_costs=r.event_shock_cost+r.event_minor_cost)
                for r in rows[6-n_history:6]]
        p = FutureProfile(u.employment_type, int(u.festive_month), bool(u.has_car), bool(u.has_motorbike))
        g = GameSnapshot(hist[-1].cash, 0, max(1, np.mean([
            r.essential_spending+r.debt_payments for r in hist[-3:]])), 1)
        forecast = simulate_future(hist, p, g, seed=50000+int(u.user_id), paths=paths)
        for h in (1,3,6):
            q = forecast.cushion[h-1]
            actual = rows[5+h].cash / max(1, np.mean([
                r.spend_essential+r.commitments_total for r in rows[3+h:6+h]]))
            for kind in ('all', u.employment_type):
                scores.setdefault(f'{kind}_h{h}', []).append((q.p10,q.p50,q.p90,actual))
    return {k:summarize(v) for k,v in scores.items()}


def iid_experiment():
    # Isolate estimation uncertainty: iid N(0,1), no shocks/calendar/debts/regimes.
    # Predict a six-month sum with a plain empirical bootstrap vs a normal-theory
    # Student-t predictive interval allowing unknown mean and variance (NIST).
    rng = np.random.default_rng(2026101401)
    results = []
    for n in (3,6,12,24,60):
        hits = corrected = 0
        widths = []
        for _ in range(1000):
            history = rng.normal(size=n)
            truth = rng.normal(size=6).sum()
            sums = history[rng.integers(n, size=(2000,6))].sum(axis=1)
            lo, hi = np.percentile(sums, [10,90])
            hits += lo <= truth <= hi
            half = t.ppf(.9,n-1)*history.std(ddof=1)*np.sqrt(6+36/n)
            center = 6*history.mean()
            corrected += center-half <= truth <= center+half
            widths.append(hi-lo)
        results.append(dict(history=n, trials=1000, bootstrap_coverage=hits/1000,
                            predictive_t_coverage=corrected/1000, mean_bootstrap_width=float(np.mean(widths))))
    return results


def main():
    result = {'iid_experiment': iid_experiment(), 'worlds': {}}
    jobs = [(20261015,'full',3,2000),(20261015,'full',6,500),
            (20261015,'full',6,2000),(31001,'full',6,2000),(31002,'full',6,2000)]
    jobs += [(20261015,v,6,2000) for v in ('no_hidden','no_regimes','no_clustering','combined')]
    for seed,v,n,p in jobs:
        key = f'{seed}_{v}_history{n}_paths{p}'
        result['worlds'][key] = world(seed,v,n,p)
        print(key, result['worlds'][key]['all_h6'], flush=True)
    path = ROOT / 'sim/results/monte_carlo_investigation.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['iid_experiment'], indent=2), flush=True)


if __name__ == '__main__':
    main()
