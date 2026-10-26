# generator/: FAST synthetic data generator

Implements `docs/generator_spec.md` **v1.0** (frozen 2026-10-12; reference copy and SHA-256
in `docs/frozen/` and `docs/DECISIONS.md`). Every parameter is in `config.yaml`, with its
calibration ID (`docs/calibration_table.md`).

## Run

```bash
.venv\Scripts\python -m generator.run --noise medium            # master seed from config
.venv\Scripts\python -m generator.checks                        # sanity checks S1-S14
.venv\Scripts\python -m pytest -q                               # tests
```

Output: `data/synthetic/<noise>_seed<seed>/` with `users`, `monthly`, `transactions`, `flags`,
`labels` (observable), `latent`, `latent_monthly` (hidden: oracle and audits only),
`metadata.json` (spec version, frozen-spec SHA-256, config SHA-256, seed, row counts) and
`checks_report.json`. About 12 s and 7–8 MB per dataset on the development laptop.

## Modules

| File | Role | Spec |
|---|---|---|
| `bands.py` | DSR bands + hysteresis; thresholds from `shared/thresholds.json` | §6 |
| `population.py` | Who each user is: type, age, traits (Gaussian copula), income, vehicles, debts, household, card, BNPL, spending base, starting cash | §3a, §4–§6, §8 |
| `simulate.py` | Monthly engine, all users at once (numpy) | §3, §5–§9, §12 |
| `flags.py` | Impulsivity, overconfidence, delayed correction | §9 |
| `labels.py` | 3-month deterioration label | §11 (frozen) |
| `transactions.py` | Transaction log, generic merchant labels | §10 |
| `run.py` | Orchestration, output files, metadata | §10, §15 |
| `checks.py` | Sanity checks S1–S14 | §14 (frozen) |

**Randomness:** one `numpy.random.Generator` per component (population, income, spending,
BNPL, shocks, hidden, behaviour, transactions), spawned from `SeedSequence(seed)`. The same
seed gives byte-identical files (tested), and extra draws in one component never shift another.

## Implementation choices the spec left open

Each one is a reasoned interpretation. None touches the frozen §11–14 rules.

| Choice | Why |
|---|---|
| Spending never falls below **30% of net income**, even when debts exceed income | The formula `c × disposable income` gives zero or negative spending when debts exceed income; people still eat. Such users then run deficits, as in reality |
| "Total spending" in **saved** = cash-paid spending (BNPL purchases enter through their instalments) | Counting both the BNPL purchase and its instalments would double-count. Budgets and overruns still use full consumption (cash + BNPL) |
| **PTPTN** instalment = loan × (1 + 1% × tenure years) ÷ tenure months → RM138–319 | Derived from C-14's loan sizes and tenure bands; consistent with C-14's RM100–300 |
| **Arrears** = the unpaid part of that month's debt payments | Spec says "unpaid commitments become arrears" |
| **Card tier** from a missed-payment counter (0 → 15%, 1–2 → 17%, 3+ → 18%); starts at 0 for full payers, 1 otherwise | C-15 tiers by payment record; D-38 starting tiers |
| **Overconfidence** scored for months 4–11 | It needs targets based on real saving history (month 1 is the RM50 floor) and the next month's target |
| **Nulls by design**: budget in month 1, savings rate when income is 0, unscorable flags, labels excluded for insufficient income | These values are undefined, not missing; stored as nulls rather than invented numbers. All money columns are finite, at 2 dp (G3) |
| Transactions: monthly counts per category, Dirichlet α = 2, 40 generic merchants per category, source mix 60/30/10 (manual/notification/OCR) | Implementation assumptions (`config.yaml` → `transactions`); they don't affect the monthly figures |
| Hidden cost is **never** written as a transaction | It represents unlogged spending (§12) |

## Realism notes

- **Job loss** (D-47): about 23.5% of employees lose their job at some point in the year;
  spell lengths follow DOSM LFS 2025, and steady-state unemployment matches DOSM. The spell
  distribution comes from a stock snapshot of the unemployed, which slightly over-represents
  long spells.
- **Flag validity** (S14): impulsivity ×16.5 passes; overconfidence ×1.97 and delayed
  correction ×1.71 don't, so in the app they are ML features only, never shown to users.
