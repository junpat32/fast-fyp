import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { periodAt } from '../timeOfDay.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
const times = JSON.parse(readFileSync(join(ROOT, 'assets', 'isometric', 'manifest.json'), 'utf-8')).times;

test('the art kit says morning 06:00-11:59, afternoon 12:00-18:59, night 19:00-05:59', () => {
  assert.deepEqual(times, { morning: '06:00-11:59', afternoon: '12:00-18:59', night: '19:00-05:59' });
});

test('edges of each period', () => {
  const cases: [number, number, string][] = [
    [6, 0, 'morning'], [11, 59, 'morning'], [12, 0, 'afternoon'], [18, 59, 'afternoon'],
    [19, 0, 'night'], [23, 59, 'night'], [0, 0, 'night'], [5, 59, 'night'],
  ];
  for (const [h, m, want] of cases) assert.equal(periodAt(h, m, times), want, `${h}:${m}`);
});

test('every minute of the day has exactly one period', () => {
  for (let t = 0; t < 24 * 60; t++) assert.ok(periodAt(Math.floor(t / 60), t % 60, times));
});
