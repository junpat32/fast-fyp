import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { chartTop, futureMood, monthShort, moodNow, rangeLine, rangeShort, spriteDp } from '../future.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const t = JSON.parse(readFileSync(join(ROOT, 'shared', 'thresholds.json'), 'utf-8'));
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));
const months = (lo: number, mid: number, hi: number) =>
  [7, 8, 9, 10, 11, 12].map((m) => ({ month: m, p10: lo, p50: mid, p90: hi }));

test('calendar months in short', () => {
  assert.equal(monthShort(7), 'Jul');
  assert.equal(monthShort(12), 'Dec');
  assert.throws(() => monthShort(13));
});

test('the future self is never concerned, whatever the range (D-12)', () => {
  assert.equal(futureMood(0, t), 'focused');
  assert.equal(futureMood(0.99, t), 'focused');
  assert.equal(futureMood(1, t), 'relaxed');
  assert.equal(futureMood(3, t), 'celebrating');
  for (const m of [-1, 0, 0.5, 1, 2, 3, 10]) assert.notEqual(futureMood(m, t), 'concerned_hopeful');
});

test('the mood now is the engine\'s, with calm for anything unknown', () => {
  assert.equal(moodNow('concerned_hopeful'), 'concerned_hopeful');
  assert.equal(moodNow('sad'), 'calm');
});

test('B6: the range at the end of the six months, in words', () => {
  assert.equal(rangeLine(months(0.27, 1.37, 2.52)), 'between 0.3 and 2.5 months of costs');
  assert.equal(rangeShort(months(0.27, 1.37, 2.52)), '0.3–2.5');
  assert.equal(rangeShort(months(0, 0, 0.01)), 'about 0.0');
  assert.equal(rangeLine(months(0, 0, 0.01)), 'about 0.0 months of costs');
  assert.doesNotMatch(rangeLine(months(0.1, 0.5, 2)), /%/);   // no percentage on this screen (D-100)
});

test('the chart reaches the highest value and the first goal', () => {
  assert.equal(chartTop(months(0, 0, 0.4), 0, t), 1);       // the goal line always shows
  assert.equal(chartTop(months(0.3, 1.4, 2.52), 1.2, t), 3);
  assert.equal(chartTop(months(0.3, 1.4, 1.6), 1.9, t), 2);  // "now" counts too
});

test('sprites at one image pixel per screen pixel, within limits', () => {
  assert.equal(spriteDp(288, 2.75, 88, 128), 288 / 2.75);    // Patrick's Redmi: about 105 dp, crisp
  assert.equal(spriteDp(288, 1.5, 88, 128), 128);            // a low-density screen: capped
  assert.equal(spriteDp(288, 4, 88, 128), 88);               // a very dense one: not too small
});

test('each persona\'s future: six months, a range in words, a never-sad future mood', () => {
  for (const s of samples) {
    const f = s.future;
    assert.equal(f.available, true, s.persona.name);
    assert.equal(f.months.length, 6);
    assert.match(rangeLine(f.months), /^(between \d+\.\d and \d+\.\d|about \d+\.\d) months of costs$/);
    assert.notEqual(futureMood(f.median_path_final_cushion, t), 'concerned_hopeful');
    for (const m of f.months) assert.ok(m.p10 <= m.p50 && m.p50 <= m.p90, `${s.persona.name} ${m.month}`);
  }
});
