import assert from 'node:assert/strict';
import { test } from 'node:test';

import { dayName, monthName, monthsText, outOf100, shortDay } from '../format.ts';

test('months and days in words', () => {
  assert.equal(monthName('2026-06-01'), 'June 2026');
  assert.equal(dayName('2026-07-01'), '1 July 2026');
  assert.equal(shortDay('2026-07-01'), '1 Jul 2026');
  assert.equal(shortDay('2026-12-31'), '31 Dec 2026');
  assert.throws(() => monthName('2026-13-01'));
  assert.throws(() => shortDay('2026-13-01'));
});

test('a probability as people out of 100 (B4)', () => {
  assert.equal(outOf100(0.0845), 8);
  assert.equal(outOf100(0.6789), 68);
  assert.equal(outOf100(0.02), 2);
});

test('months covered, one decimal, never negative', () => {
  assert.equal(monthsText(1.04), '1.0');
  assert.equal(monthsText(-0.3), '0.0');
});
