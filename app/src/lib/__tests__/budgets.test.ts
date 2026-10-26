import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { budgetCategories, budgetLine, buildBudget, spentByCategory } from '../budgets.ts';
import type { Categories, NewEntry } from '../entry.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const cats = JSON.parse(readFileSync(join(ROOT, 'shared', 'categories.json'), 'utf-8')) as Categories;
const SQL = readFileSync(join(ROOT, 'supabase', 'migrations', '20261014000000_init.sql'), 'utf-8');

test('budgets are for spending categories only, not debt payments or own transfers (BU2)', () => {
  const keys = budgetCategories(cats).map((c) => c.key);
  assert.ok(keys.includes('food_home') && keys.includes('eating_out') && keys.includes('family'));
  assert.ok(!keys.includes('ptptn') && !keys.includes('bnpl_instalment') && !keys.includes('own_transfer'));
});

const out = (category: string, amount: string, extra: Partial<NewEntry> = {}) =>
  ({ direction: 'out' as const, amount, category, is_own_transfer: false, ...extra });

test('this month\'s spending per category, in whole sen (BU3)', () => {
  const spent = spentByCategory([out('eating_out', '12.10'), out('eating_out', '0.20'), out('food_home', '45.00'),
    { ...out('salary', '2800.00'), direction: 'in' }, out('own_transfer', '100.00', { is_own_transfer: true })]);
  assert.deepEqual(spent, { eating_out: '12.30', food_home: '45.00' });
});

test('how a budget stands: the bar, what is left, how far over', () => {
  assert.deepEqual(budgetLine(300, '120.00'), { share: 0.4, left: '180.00', over: null });
  assert.deepEqual(budgetLine(300, '300.00'), { share: 1, left: '0.00', over: null });
  assert.deepEqual(budgetLine(300, '320.50'), { share: 1, left: null, over: '20.50' });
  assert.deepEqual(budgetLine(0.3, '0.10'), { share: 1 / 3, left: '0.20', over: null });
});

test('a new budget: a spending category without one yet, a limit above zero (BU1)', () => {
  assert.ok(/monthly_limit numeric\(12,2\) not null check \(monthly_limit > 0\)/.test(SQL));
  assert.ok(/unique \(user_id, category\)/.test(/create table public\.budgets \(([\s\S]*?)\n\);/.exec(SQL)![1]));
  assert.deepEqual(buildBudget('eating_out', 'RM 300', [], cats), { ok: true, budget: { category: 'eating_out', monthly_limit: '300.00' } });
  const taken = buildBudget('eating_out', '300', ['eating_out'], cats);
  assert.ok(!taken.ok && taken.errors.category);
  const debt = buildBudget('ptptn', '300', [], cats);
  assert.ok(!debt.ok && debt.errors.category);
  const zero = buildBudget('food_home', '0', [], cats);
  assert.ok(!zero.ok && zero.errors.limit);
});
