/**
 * Which debt to pay off first (WP-14c, D-144): the avalanche (highest interest rate first) against the
 * snowball (smallest balance first). A port of compare_debt_plans in sim/monte_carlo.py, kept equal to it
 * by a fixture (tools/app_fixtures.py -> __tests__/fixtures/debt_plans.json, D-104). It uses only the
 * rates the user typed: with any rate missing there is no comparison (FAST never guesses a rate).
 * Pure TypeScript, tested by Node.
 *
 * Invariants
 *   DP1  the monthly budget is fixed: every minimum payment plus the extra; a cleared debt's minimum
 *        rolls into the others
 *   DP2  each month, interest is the yearly rate / 12 on the balance, before that month's payments
 *   DP3  a comparison needs at least two open debts with something left to pay, and a rate for each
 *   DP4  ties: avalanche by (rate high, balance low, list order); snowball by (balance low, rate high,
 *        list order); the same keys as the Python
 *
 * Pseudo-code (per method)
 *   budget = sum of minimums + extra
 *   each month, up to 360: add interest; pay each debt its minimum (or what is left of it) from the
 *   budget; give what remains to the debts in the method's order; stop when every balance is cleared
 *
 * Cost: O(M x D log D) per method; M <= 360 months, D debts.
 *
 * Trace (card 18% RM1,000, minimum RM50; PTPTN 1% RM600, minimum RM50; extra RM100, so RM200 a month):
 *   avalanche  month  interest (card, PTPTN)  balances after payments
 *              1      15.00, 0.50             865.00, 550.50   (the extra RM100 goes to the card)
 *              2      12.97, 0.46             727.98, 500.96
 *   both clear in 9 months; interest RM64.46 (avalanche) against RM93.91 (snowball pays PTPTN first)
 */
import type { DebtRow } from './debts.ts';
import { debtName, paidOff } from './debts.ts';

export type Plan = { outstanding: number; monthly_payment: number; annual_rate: number };
export type Comparison = {
  avalanche_months: number | null; snowball_months: number | null;     // null: not cleared within maxMonths
  avalanche_interest: number; snowball_interest: number;
};

const CLEARED = 0.005;

function run(debts: Plan[], budget: number, method: 'avalanche' | 'snowball', maxMonths: number): [number | null, number] {
  let balances = debts.map((d) => d.outstanding);
  let interestTotal = 0;
  const allCleared = () => balances.every((x) => x <= CLEARED);
  for (let month = 1; month <= maxMonths; month++) {
    if (allCleared()) return [month - 1, interestTotal];
    const interest = balances.map((b, i) => b * debts[i].annual_rate / 12);
    interestTotal += interest.reduce((a, b) => a + b, 0);
    balances = balances.map((b, i) => b + interest[i]);
    let left = budget;
    debts.forEach((d, i) => {
      const paid = Math.min(left, balances[i], d.monthly_payment);
      balances[i] -= paid;
      left -= paid;
    });
    const key = (i: number) => (method === 'avalanche'
      ? [-debts[i].annual_rate, balances[i], i] : [balances[i], -debts[i].annual_rate, i]);
    const order = debts.map((_, i) => i).sort((x, y) => {
      const [a, b] = [key(x), key(y)];
      for (let j = 0; j < a.length; j++) if (a[j] !== b[j]) return a[j] - b[j];
      return 0;
    });
    for (const i of order) {
      const paid = Math.min(left, balances[i]);
      balances[i] -= paid;
      left -= paid;
    }
    if (allCleared()) return [month, interestTotal];
  }
  return [null, interestTotal];
}

/** compare_debt_plans: the same budget paid out two ways (DP1, DP2, DP4). */
export function comparePlans(debts: Plan[], extra: number, maxMonths = 360): Comparison {
  const bad = (x: number) => !Number.isFinite(x) || x < 0;
  if (debts.length === 0 || bad(extra) || maxMonths < 1
      || debts.some((d) => bad(d.outstanding) || bad(d.monthly_payment) || bad(d.annual_rate))) {
    throw new Error('Valid debts, nonnegative extra and positive horizon required');
  }
  const budget = debts.reduce((a, d) => a + d.monthly_payment, 0) + extra;
  const [aMonths, aInterest] = run(debts, budget, 'avalanche', maxMonths);
  const [sMonths, sInterest] = run(debts, budget, 'snowball', maxMonths);
  return { avalanche_months: aMonths, snowball_months: sMonths, avalanche_interest: aInterest, snowball_interest: sInterest };
}

export type PlanInputs =
  | { ok: true; plans: Plan[] }
  | { ok: false; reason: 'too_few' }
  | { ok: false; reason: 'rates'; missing: string[] };

/** The open debts with something left to pay, ready to compare, or why not (DP3). */
export function planInputs(debts: DebtRow[], today: string): PlanInputs {
  const open = debts.filter((d) => !paidOff(d, today) && d.outstanding > 0);
  if (open.length < 2) return { ok: false, reason: 'too_few' };
  const missing = open.filter((d) => d.annual_rate === null || d.annual_rate === undefined).map(debtName);
  if (missing.length > 0) return { ok: false, reason: 'rates', missing };
  return { ok: true, plans: open.map((d) => ({ outstanding: d.outstanding, monthly_payment: d.monthly_payment,
                                               annual_rate: d.annual_rate as number })) };
}
