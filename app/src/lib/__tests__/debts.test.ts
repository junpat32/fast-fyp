import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  asksFromSalary, blankDebt, buildDebt, DEBT_KINDS, debtName, debtTotals, formOf, LABEL_MAX, paidOff, parseMoney, parseRate,
  rateText, type DebtRow,
} from '../debts.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const SQL = readFileSync(join(HERE, '..', '..', '..', '..', 'supabase', 'migrations', '20261014000000_init.sql'), 'utf-8');
const table = /create table public\.debts \(([\s\S]*?)\n\);/.exec(SQL)![1];

test('the kinds and the label limit are the database\'s own (DB1)', () => {
  const kinds = /kind in \(([^)]*)\)/.exec(table)![1].match(/'([a-z_]+)'/g)!.map((k) => k.slice(1, -1));
  assert.deepEqual(DEBT_KINDS.map((k) => k.kind), kinds);
  assert.equal(Number(/char_length\(label\) <= (\d+)/.exec(table)![1]), LABEL_MAX);
});

test('amounts of zero or more, as decimal strings', () => {
  assert.deepEqual(parseMoney('0'), { ok: true, value: '0.00' });
  assert.deepEqual(parseMoney('RM 0.0'), { ok: true, value: '0.00' });
  assert.deepEqual(parseMoney('480.78'), { ok: true, value: '480.78' });
  assert.deepEqual(parseMoney('RM1,200'), { ok: true, value: '1200.00' });
  assert.equal(parseMoney('-5').ok, false);
  assert.equal(parseMoney('12.345').ok, false);
});

test('a debt from the form: kind and amounts needed, a PTPTN not repaid yet is fine', () => {
  const errors = buildDebt(blankDebt());
  assert.ok(!errors.ok && errors.errors.kind && errors.errors.monthly && errors.errors.owed);
  const ptptn = buildDebt({ kind: 'ptptn', label: '', monthly: '0', owed: '18,500', fromSalary: false, rate: '' });
  assert.deepEqual(ptptn, { ok: true, debt: { kind: 'ptptn', label: null, monthly_payment: '0.00', outstanding: '18500.00',
                                             deducted_from_salary: false, annual_rate: null } });
  const nothing = buildDebt({ kind: 'other', label: '', monthly: '0', owed: '0', fromSalary: false, rate: '' });
  assert.ok(!nothing.ok && nothing.errors.owed);
});

test('the label is redacted before it is saved and kept to 40 characters (DB2)', () => {
  const r = buildDebt({ kind: 'credit_card', label: 'Maybank card 4111 1111 1111 1234', monthly: '150', owed: '2300', fromSalary: false, rate: '' });
  assert.ok(r.ok && r.debt.label === 'Maybank card ••••1234');
  const ic = buildDebt({ kind: 'personal', label: 'Loan for 990101-14-5678', monthly: '200', owed: '5000', fromSalary: true, rate: '' });
  assert.ok(ic.ok && ic.debt.label === 'Loan for [IC removed]');
  const long = buildDebt({ kind: 'other', label: 'x'.repeat(60), monthly: '10', owed: '0', fromSalary: false, rate: '' });
  assert.ok(long.ok && long.debt.label!.length === LABEL_MAX);
  const same = buildDebt({ kind: 'car', label: 'Car loan', monthly: '480', owed: '35000', fromSalary: false, rate: '' });
  assert.ok(same.ok && same.debt.label === null);                                  // the kind's own name: no label
});

test('only loans can come off a salary; a card or BNPL never does', () => {
  assert.deepEqual(DEBT_KINDS.filter((k) => asksFromSalary(k.kind)).map((k) => k.kind), ['ptptn', 'housing', 'personal', 'other']);
  const card = buildDebt({ kind: 'credit_card', label: '', monthly: '100', owed: '900', fromSalary: true, rate: '' });
  assert.ok(card.ok && card.debt.deducted_from_salary === false);
});

test('an interest rate is optional, typed as a percentage and saved as a fraction (DB5)', () => {
  assert.deepEqual(parseRate(''), { ok: true, value: null });
  assert.deepEqual(parseRate('18'), { ok: true, value: '0.1800' });
  assert.deepEqual(parseRate(' 18 % '), { ok: true, value: '0.1800' });
  assert.deepEqual(parseRate('3.25'), { ok: true, value: '0.0325' });
  assert.deepEqual(parseRate('3.5'), { ok: true, value: '0.0350' });
  assert.deepEqual(parseRate('0'), { ok: true, value: '0.0000' });
  assert.deepEqual(parseRate('100'), { ok: true, value: '1.0000' });
  for (const bad of ['101', '-1', '3.255', 'abc', '.5', '18 a year']) assert.equal(parseRate(bad).ok, false, bad);
  for (const [rate, text] of [[0.18, '18'], [0.0325, '3.25'], [0.035, '3.5'], [0.0305, '3.05'], [1, '100'], [null, '']] as const) {
    assert.equal(rateText(rate), text);
  }
  const card = buildDebt({ kind: 'credit_card', label: '', monthly: '150', owed: '3000', fromSalary: false, rate: '18' });
  assert.ok(card.ok && card.debt.annual_rate === '0.1800');
  const bad = buildDebt({ kind: 'credit_card', label: '', monthly: '150', owed: '3000', fromSalary: false, rate: '180' });
  assert.ok(!bad.ok && bad.errors.rate);
});

test('the rate column is the database\'s own: optional, a fraction from 0 to 1 (DB5)', () => {
  assert.match(table, /annual_rate numeric\(5,4\) check \(annual_rate is null or annual_rate between 0 and 1\)/);
});

const row = (over: Partial<DebtRow>): DebtRow => ({
  id: '1', kind: 'car', label: null, monthly_payment: 480.78, outstanding: 35096.73, deducted_from_salary: false,
  starts_on: null, ends_on: null, created_at: '2025-12-31T16:30:00+00:00', ...over,
});

test('the list: names, totals in whole sen, back to the form, paid off from its end date (DB3)', () => {
  const car = row({});
  const bike = row({ id: '2', kind: 'other', label: 'Motorbike loan', monthly_payment: 276.06, outstanding: 14907.43 });
  assert.equal(debtName(car), 'Car loan');
  assert.equal(debtName(bike), 'Motorbike loan');
  assert.deepEqual(debtTotals([car, bike]), { monthly: '756.84', owed: '50004.16' });
  assert.deepEqual(debtTotals([row({ monthly_payment: 0.1, outstanding: 0.2 }), row({ monthly_payment: 0.2, outstanding: 0.1 })]),
                   { monthly: '0.30', owed: '0.30' });
  assert.deepEqual(formOf(bike), { kind: 'other', label: 'Motorbike loan', monthly: '276.06', owed: '14907.43', fromSalary: false, rate: '' });
  assert.equal(formOf(row({ annual_rate: 0.035 })).rate, '3.5');
  assert.equal(paidOff(car, '2026-08-01'), false);
  assert.equal(paidOff(row({ ends_on: '2026-08-01' }), '2026-08-01'), true);
  assert.equal(paidOff(row({ ends_on: '2026-09-01' }), '2026-08-01'), false);     // seen from before it was paid off
});
