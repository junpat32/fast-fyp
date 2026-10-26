"""Fresh D-80 audit fixed in DECISIONS.md before results were viewed.

Two synthetic populations of 200 users, medium noise, independent seeds
49001/49002, six observed months, six-month horizon, 1000 paths each.
Only the terminal P10-P90 result and month-1/3 checks are inspected. This
audit is descriptive; no parameters are adapted to its users.
"""
import json
from pathlib import Path
from sim.investigate_monte_carlo import world


def main():
    results = {str(seed): world(seed, 'full', 6, 1000, n_users=200)
               for seed in (49001, 49002)}
    path = Path(__file__).resolve().parent / 'results/monte_carlo_v2_audit.json'
    path.write_text(json.dumps(results, indent=2), encoding='utf-8')
    for seed, metrics in results.items():
        print(seed, metrics['all_h6'], flush=True)


if __name__ == '__main__':
    main()
