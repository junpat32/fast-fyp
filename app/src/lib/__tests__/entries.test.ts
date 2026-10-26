import assert from 'node:assert/strict';
import { test } from 'node:test';

import { memoryStore } from '../../api/entries.ts';
import type { NewEntry } from '../entry.ts';

const lunch = (day: string, amount = '12.00'): NewEntry => ({
  occurred_on: day, direction: 'out', amount, category: 'eating_out', is_essential: false, is_bnpl: false,
  on_credit: false, is_debt_payment: false, is_own_transfer: false, is_unexpected: false, note: null, source: 'typed',
});

test('the month\'s entries, newest first, and only that month', async () => {
  let t = Date.parse('2026-07-01T04:00:00Z');
  const s = memoryStore(() => new Date((t += 1000)));
  await s.add(lunch('2026-06-30'));
  await s.add(lunch('2026-07-01', '5.00'));
  await s.add(lunch('2026-07-01', '7.00'));
  const july = await s.month('2026-07-01');
  assert.deepEqual(july.map((e) => e.amount), ['7.00', '5.00']);
  assert.equal((await s.month('2026-06-01')).length, 1);
  assert.equal(s.local, true);
});

test('task 7: fix a typo, keeping when the entry arrived; or delete it', async () => {
  const s = memoryStore(() => new Date('2026-07-01T04:00:00Z'));
  const e = await s.add(lunch('2026-07-01', '21.00'));
  const fixed = await s.update(e.id, lunch('2026-07-01', '12.00'));
  assert.equal(fixed.amount, '12.00');
  assert.equal(fixed.created_at, e.created_at);
  await s.remove(e.id);
  assert.equal((await s.month('2026-07-01')).length, 0);
  await assert.rejects(s.update(e.id, lunch('2026-07-01')));
});

test('"No spending today" is kept per day', async () => {
  const s = memoryStore();
  await s.noSpend('2026-07-01');
  await s.noSpend('2026-07-01');
  assert.deepEqual(await s.noSpendDays('2026-07-01'), ['2026-07-01']);
  assert.deepEqual(await s.noSpendDays('2026-06-01'), []);
});
