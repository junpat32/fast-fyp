/**
 * Budgets (docs/app_plan.md §3; D-121): a monthly limit for a spending category the user wants to keep
 * an eye on, and this month's spending against it. Budgets are for the user's own awareness only:
 * they never earn or cost points (D-11; game_design.md, the budget streak: a reward for "staying within
 * budget" would reward not logging). Pure TypeScript, tested by Node.
 *
 * Invariants
 *   BU1  the database's rules (public.budgets): one limit per category, more than zero, a decimal
 *        string on the way in (rule 9)
 *   BU2  only spending categories: debt payments are on the debts list, and a move between the
 *        user's own pockets is not spending
 *   BU3  sums in whole sen (sumAmounts), so RM0.10 + RM0.20 is exactly RM0.30
 */
import { parseAmount, sumAmounts, type Categories, type Category, type NewEntry } from './entry.ts';

export type BudgetRow = { id: string; category: string; monthly_limit: number };
export type NewBudget = { category: string; monthly_limit: string };

/** The categories a budget can be set for (BU2), in the Add screen's order. */
export function budgetCategories(cats: Categories): Category[] {
  return cats.out.filter((c) => !c.debt_payment && !c.own_transfer);
}

/** This month's money out per category, as decimal strings (BU3). */
export function spentByCategory(entries: Pick<NewEntry, 'direction' | 'amount' | 'category' | 'is_own_transfer'>[]): Record<string, string> {
  const by: Record<string, string[]> = {};
  for (const e of entries) {
    if (e.direction !== 'out' || e.is_own_transfer) continue;
    (by[e.category] ??= []).push(e.amount);
  }
  return Object.fromEntries(Object.entries(by).map(([c, xs]) => [c, sumAmounts(xs)]));
}

const sen = (amount: string) => {
  const [whole, frac = ''] = amount.split('.');
  return Number(whole) * 100 + Number((frac + '00').slice(0, 2));
};
const ringgit = (cents: number) => `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;

/** How a budget stands: the share used (0 to 1 for the bar), and what is left or how far over. */
export function budgetLine(limit: number, spent: string): { share: number; left: string | null; over: string | null } {
  const l = Math.round(limit * 100);
  const s = sen(spent);
  return { share: l > 0 ? Math.min(s / l, 1) : 1, left: s <= l ? ringgit(l - s) : null, over: s > l ? ringgit(s - l) : null };
}

export function buildBudget(category: string, limit: string, taken: string[], cats: Categories):
    { ok: true; budget: NewBudget } | { ok: false; errors: Partial<Record<'category' | 'limit', string>> } {
  const errors: Partial<Record<'category' | 'limit', string>> = {};
  if (!budgetCategories(cats).some((c) => c.key === category)) errors.category = 'Choose a category';
  else if (taken.includes(category)) errors.category = 'That category already has a budget: tap it in the list to change it';
  const l = parseAmount(limit);
  if (!l.ok) errors.limit = limit.trim() === '' ? 'Type a monthly limit' : l.error;
  if (Object.keys(errors).length > 0 || !l.ok) return { ok: false, errors };
  return { ok: true, budget: { category, monthly_limit: l.value } };
}
