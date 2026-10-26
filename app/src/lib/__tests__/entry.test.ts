import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  asksPurchaseQuestions, buildEntry, canEdit, dayLabel, dayShort, earliestDay, EDIT_HOURS, monthTotals, parseAmount, redactNote,
  rmText, stepDay, sumAmounts, type Categories, type Form,
} from '../entry.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
const cats = JSON.parse(readFileSync(join(ROOT, 'shared', 'categories.json'), 'utf-8')) as Categories;
const TODAY = '2026-07-01';
const form = (over: Partial<Form> = {}): Form => ({
  direction: 'out', amount: '12', category: 'eating_out', paidBy: 'now', unexpected: false, day: TODAY, note: '', ...over,
});

test('amounts: decimal strings to the sen, never floats (rule 9)', () => {
  assert.deepEqual(parseAmount('12'), { ok: true, value: '12.00' });
  assert.deepEqual(parseAmount('12.5'), { ok: true, value: '12.50' });
  assert.deepEqual(parseAmount('RM 1,200.05'), { ok: true, value: '1200.05' });
  assert.deepEqual(parseAmount('0.1'), { ok: true, value: '0.10' });
  for (const bad of ['', '0', '0.00', '-5', '12.345', '1.2.3', 'abc', '1000000.01']) assert.equal(parseAmount(bad).ok, false, bad);
  assert.equal(parseAmount('1000000').ok, true);
  assert.equal(sumAmounts(['0.10', '0.20', '12.50']), '12.80');          // 0.1 + 0.2 without float error
  assert.equal(rmText('1200.50'), 'RM1,200.50');
  assert.equal(rmText('12.00'), 'RM12.00');
});

test('task 7: "RM12 on lunch today" becomes the row the engine expects', () => {
  const r = buildEntry(form(), cats, TODAY);
  assert.ok(r.ok);
  assert.deepEqual(r.entry, {
    occurred_on: TODAY, direction: 'out', amount: '12.00', category: 'eating_out', is_essential: false, is_bnpl: false,
    on_credit: false, is_debt_payment: false, is_own_transfer: false, is_unexpected: false, note: null, source: 'typed',
  });
});

test('the category decides the flags (D-28 essentials; debt payments; own transfers)', () => {
  const groceries = buildEntry(form({ category: 'food_home', paidBy: 'card' }), cats, TODAY);
  assert.ok(groceries.ok && groceries.entry.is_essential && groceries.entry.on_credit);
  const bnpl = buildEntry(form({ category: 'shopping', paidBy: 'bnpl', unexpected: true }), cats, TODAY);
  assert.ok(bnpl.ok && bnpl.entry.is_bnpl && !bnpl.entry.on_credit && bnpl.entry.is_unexpected);
  // a debt payment is never a purchase on credit, unexpected or essential, whatever the form says
  const loan = buildEntry(form({ category: 'ptptn', paidBy: 'bnpl', unexpected: true }), cats, TODAY);
  assert.ok(loan.ok);
  assert.deepEqual([loan.entry.is_debt_payment, loan.entry.is_bnpl, loan.entry.on_credit, loan.entry.is_unexpected,
                    loan.entry.is_essential], [true, false, false, false, false]);
  const move = buildEntry(form({ category: 'own_transfer', paidBy: 'card' }), cats, TODAY);
  assert.ok(move.ok && move.entry.is_own_transfer && !move.entry.on_credit && !move.entry.is_debt_payment);
  const pay = buildEntry(form({ direction: 'in', category: 'salary', paidBy: 'bnpl', unexpected: true }), cats, TODAY);
  assert.ok(pay.ok);
  assert.deepEqual([pay.entry.is_bnpl, pay.entry.on_credit, pay.entry.is_unexpected, pay.entry.is_essential], [false, false, false, false]);
  assert.equal(asksPurchaseQuestions('out', cats.out.find((c) => c.key === 'ptptn')), false);
  assert.equal(asksPurchaseQuestions('out', cats.out.find((c) => c.key === 'eating_out')), true);
  assert.equal(asksPurchaseQuestions('in', cats.in[0]), false);
});

test('what to fix, all at once', () => {
  const r = buildEntry(form({ amount: '', category: 'nope', day: '2026-07-02' }), cats, TODAY);
  assert.ok(!r.ok);
  assert.deepEqual(Object.keys(r.errors).sort(), ['amount', 'category', 'day']);
  assert.equal(buildEntry(form({ direction: 'in', category: 'eating_out' }), cats, TODAY).ok, false);   // wrong side
});

test('days: this month and last, never after today', () => {
  assert.equal(earliestDay(TODAY), '2026-06-01');
  assert.equal(earliestDay('2026-01-15'), '2025-12-01');
  assert.equal(stepDay(TODAY, 1, TODAY), TODAY);
  assert.equal(stepDay(TODAY, -1, TODAY), '2026-06-30');
  assert.equal(stepDay('2026-06-01', -1, TODAY), '2026-06-01');
  assert.equal(dayLabel(TODAY, TODAY), 'Today, 1 Jul');
  assert.equal(dayLabel('2026-06-30', TODAY), 'Yesterday, 30 Jun');
  assert.equal(dayLabel('2026-06-28', TODAY), '28 Jun');
  assert.equal(dayShort(TODAY), '1 Jul');
  assert.equal(buildEntry(form({ day: '2026-05-31' }), cats, TODAY).ok, false);
});

test('rule 11: notes lose TAC/OTP lines, IC numbers and long account numbers', () => {
  assert.equal(redactNote('lunch with Ali'), 'lunch with Ali');
  assert.equal(redactNote('Your TAC is 123456\nlunch'), 'lunch');
  assert.equal(redactNote('IC 990101-14-5678 form'), 'IC [IC removed] form');
  assert.equal(redactNote('to acct 1234 5678 9012'), 'to acct ••••9012');
  assert.equal(redactNote('x'.repeat(200)).length, 120);
  const r = buildEntry(form({ note: '  OTP 4321 ' }), cats, TODAY);
  assert.ok(r.ok && r.entry.note === null);
});

test('edit or delete for 48 hours, as the database allows (C3)', () => {
  const migration = readFileSync(join(ROOT, 'supabase', 'migrations', '20261014000000_init.sql'), 'utf-8');
  assert.match(migration, new RegExp(`"edit own rows for ${EDIT_HOURS} hours" on public\\.transactions`));
  assert.match(migration, new RegExp(`"delete own rows for ${EDIT_HOURS} hours" on public\\.transactions`));
  const at = '2026-07-01T04:00:00.000Z';
  assert.equal(canEdit(at, new Date('2026-07-03T03:59:00Z')), true);
  assert.equal(canEdit(at, new Date('2026-07-03T04:00:00Z')), false);
});

test('month totals leave out moves between own pockets', () => {
  assert.deepEqual(monthTotals([
    { direction: 'out', amount: '12.00', is_own_transfer: false },
    { direction: 'out', amount: '500.00', is_own_transfer: true },
    { direction: 'in', amount: '2800.00', is_own_transfer: false },
  ]), { out: '12.00', in: '2800.00' });
});
