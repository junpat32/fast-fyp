import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import type { DebtRow } from '../debts.ts';
import { buildEntry, type Categories, type Form, type NewEntry } from '../entry.ts';
import { billsDue, debtCategory, findAmount, parseQuick, repeats } from '../quickadd.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const cats = JSON.parse(readFileSync(join(HERE, '..', '..', '..', '..', 'shared', 'categories.json'), 'utf-8')) as Categories;
const TODAY = '2026-07-15';
const blank: Form = { direction: 'out', amount: '', category: '', paidBy: 'now', unexpected: false, day: TODAY, note: '' };
const fill = (text: string) => ({ ...blank, ...parseQuick(text, cats, TODAY).patch });

test('the amount: "RM" wins, else the last number; commas, sen and "k" (QA1)', () => {
  assert.equal(findAmount('RM12 lunch')!.value, '12.00');
  assert.equal(findAmount('99 speedmart 23.50')!.value, '23.50');
  assert.equal(findAmount('2 nasi lemak rm 9.80 total 3')!.value, '9.80');
  assert.equal(findAmount('rent 1.2k')!.value, '1200.00');
  assert.equal(findAmount('laptop RM2,499.90')!.value, '2499.90');
  assert.equal(findAmount('nasi lemak'), null);
  assert.equal(findAmount('lunch 0'), null);                                    // the form takes more than zero
});

test('everyday sentences fill the form the way a person would (QA2)', () => {
  const cases: [string, Partial<Form>][] = [
    ['RM12 lunch', { direction: 'out', amount: '12.00', category: 'eating_out', paidBy: 'now', note: 'lunch' }],
    ['salary 2800', { direction: 'in', amount: '2800.00', category: 'salary' }],
    ['petrol 50 yesterday', { category: 'transport', amount: '50.00', day: '2026-07-14' }],
    ['shopee 89.90 atome', { category: 'shopping', paidBy: 'bnpl' }],
    ['baju 120 credit card', { category: 'clothing', paidBy: 'card' }],
    ['99 speedmart 23.50', { category: 'food_home', amount: '23.50' }],
    ['got RM50 from mum', { direction: 'in', category: 'other_income', amount: '50.00' }],
    ['gave duit raya 50 to adik', { direction: 'out', category: 'family' }],
    ['paid ptptn 150', { direction: 'out', category: 'ptptn', amount: '150.00' }],
    ['makan semalam 8.50', { category: 'eating_out', day: '2026-07-14' }],
    ['elaun 300', { direction: 'in', category: 'allowance' }],
    ['phone repair 180', { category: 'communication', unexpected: true }],
  ];
  for (const [text, want] of cases) {
    const got = fill(text);
    for (const [k, v] of Object.entries(want)) assert.equal(got[k as keyof Form], v, `${text}: ${k}`);
  }
});

test('a filled form is one Save away: it passes the same checks as one typed in', () => {
  for (const text of ['RM12 lunch', 'salary 2800', 'paid ptptn 150', 'shopee 89.90 atome']) {
    assert.ok(buildEntry(fill(text), cats, TODAY).ok, text);
  }
});

test('what it can\'t tell, it leaves for the person: no amount, no category', () => {
  const q = parseQuick('nasi lemak', cats, TODAY);
  assert.equal(q.amount, false);
  assert.equal(q.category, 'Eating out');
  const unknown = parseQuick('mystery thing 20', cats, TODAY);
  assert.equal(unknown.category, null);
  assert.equal(unknown.patch.category, '');
  assert.equal(unknown.patch.amount, '20.00');
});

test('the note keeps the words, without the amount, redacted (QA3)', () => {
  assert.equal(fill('lunch at mamak RM12').note, 'lunch at mamak');
  assert.equal(fill('RM50 to 990101-14-5678').note, 'to [IC removed]');
});

const debt = (over: Partial<DebtRow>): DebtRow => ({
  id: '1', kind: 'car', label: null, monthly_payment: 480.78, outstanding: 35000, deducted_from_salary: false,
  starts_on: null, ends_on: null, created_at: '2026-01-01T00:00:00Z', ...over,
});
const paid = (category: string, amount: string): NewEntry => ({
  occurred_on: '2026-07-03', direction: 'out', amount, category, is_essential: false, is_bnpl: false, on_credit: false,
  is_debt_payment: true, is_own_transfer: false, is_unexpected: false, note: null, source: 'typed',
});

test('every kind of debt has a category to log its payment in', () => {
  assert.equal(debtCategory({ kind: 'housing', label: null }), 'home_loan');
  assert.equal(debtCategory({ kind: 'other', label: 'Motorbike loan' }), 'motorbike_loan');
  assert.equal(debtCategory({ kind: 'other', label: 'Owe my sister' }), 'other_debt');
  const keys = new Set(cats.out.filter((c) => c.debt_payment).map((c) => c.key));
  for (const kind of ['ptptn', 'car', 'housing', 'personal', 'credit_card', 'bnpl', 'other'] as const) {
    assert.ok(keys.has(debtCategory({ kind, label: null })), kind);
  }
});

test('bills still to pay this month: not yet logged, not paid off, not RM0, not off the salary (QA4)', () => {
  const debts = [
    debt({ id: 'car' }),
    debt({ id: 'ptptn', kind: 'ptptn', monthly_payment: 150, deducted_from_salary: true }),
    debt({ id: 'bnpl', kind: 'bnpl', monthly_payment: 120 }),
    debt({ id: 'old', kind: 'personal', monthly_payment: 200, ends_on: '2026-07-01' }),
    debt({ id: 'study', kind: 'ptptn', monthly_payment: 0 }),
  ];
  const due = billsDue(debts, [paid('car_loan', '480.78')], TODAY);
  assert.deepEqual(due, [{ id: 'bnpl', name: 'Buy Now Pay Later', category: 'bnpl_instalment', amount: '120.00' }]);
  assert.equal(billsDue(debts, [], TODAY).length, 2);                            // the car is due again next month
});

test('"same again": the latest different entries, newest first', () => {
  const at = (amount: string, category: string, created_at: string, extra: Partial<NewEntry> = {}) =>
    ({ ...paid(category, amount), is_debt_payment: false, created_at, ...extra });
  const list = [at('12.00', 'eating_out', '2026-07-01T04:00:00Z'), at('12.00', 'eating_out', '2026-07-03T04:00:00Z'),
                at('50.00', 'transport', '2026-07-02T04:00:00Z'), at('89.90', 'shopping', '2026-07-04T04:00:00Z', { is_bnpl: true })];
  const r = repeats(list, 3);
  assert.deepEqual(r.map((x) => [x.patch.amount, x.patch.category]), [['89.90', 'shopping'], ['12.00', 'eating_out'], ['50.00', 'transport']]);
  assert.equal(r[0].patch.paidBy, 'bnpl');
});
