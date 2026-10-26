import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { comparePlans, planInputs, type Comparison, type Plan } from '../debt-plan.ts';
import type { DebtRow } from '../debts.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(HERE, 'fixtures', 'debt_plans.json'), 'utf-8')) as {
  cases: { name: string; extra: number; debts: Plan[]; expected: Comparison }[];
};

test('the app compares debts exactly as compare_debt_plans does (D-104, D-144)', () => {
  assert.ok(fixture.cases.length >= 8);
  for (const c of fixture.cases) {
    const got = comparePlans(c.debts, c.extra);
    assert.equal(got.avalanche_months, c.expected.avalanche_months, c.name);
    assert.equal(got.snowball_months, c.expected.snowball_months, c.name);
    assert.ok(Math.abs(got.avalanche_interest - c.expected.avalanche_interest) < 1e-4, c.name);
    assert.ok(Math.abs(got.snowball_interest - c.expected.snowball_interest) < 1e-4, c.name);
  }
});

test('the docstring trace: the extra goes to the card first, which saves interest', () => {
  const r = comparePlans([{ outstanding: 1000, monthly_payment: 50, annual_rate: 0.18 },
                          { outstanding: 600, monthly_payment: 50, annual_rate: 0.01 }], 100);
  assert.equal(r.avalanche_months, 9);
  assert.equal(r.snowball_months, 9);
  assert.equal(r.avalanche_interest.toFixed(2), '64.46');
  assert.equal(r.snowball_interest.toFixed(2), '93.91');
});

test('bad input is refused, as in Python', () => {
  assert.throws(() => comparePlans([], 0));
  assert.throws(() => comparePlans([{ outstanding: 100, monthly_payment: 10, annual_rate: 0.1 }], -1));
  assert.throws(() => comparePlans([{ outstanding: 100, monthly_payment: 10, annual_rate: -0.1 }], 0));
  assert.throws(() => comparePlans([{ outstanding: Number.NaN, monthly_payment: 10, annual_rate: 0.1 }], 0));
});

const row = (over: Partial<DebtRow>): DebtRow => ({
  id: '1', kind: 'credit_card', label: null, monthly_payment: 150, outstanding: 3000, deducted_from_salary: false,
  starts_on: null, ends_on: null, created_at: '2025-12-31T16:30:00+00:00', annual_rate: 0.18, ...over,
});

test('a comparison needs two open debts with something left, and a rate for each (DP3)', () => {
  const ptptn = row({ id: '2', kind: 'ptptn', annual_rate: 0.01, outstanding: 12000 });
  assert.deepEqual(planInputs([row({})], '2026-08-01'), { ok: false, reason: 'too_few' });
  assert.deepEqual(planInputs([row({}), row({ id: '3', outstanding: 0 })], '2026-08-01'), { ok: false, reason: 'too_few' });
  assert.deepEqual(planInputs([row({}), row({ id: '3', ends_on: '2026-07-01' })], '2026-08-01'), { ok: false, reason: 'too_few' });
  const car = row({ id: '4', kind: 'car', annual_rate: null });
  const atome = row({ id: '5', kind: 'bnpl', label: 'Atome' });
  delete atome.annual_rate;                                       // a persona's seed row has no rate field
  assert.deepEqual(planInputs([row({}), car, atome], '2026-08-01'), { ok: false, reason: 'rates', missing: ['Car loan', 'Atome'] });
  const ok = planInputs([row({}), ptptn], '2026-08-01');
  assert.ok(ok.ok);
  assert.deepEqual(ok.plans, [{ outstanding: 3000, monthly_payment: 150, annual_rate: 0.18 },
                              { outstanding: 12000, monthly_payment: 150, annual_rate: 0.01 }]);
});
