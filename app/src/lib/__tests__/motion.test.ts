import assert from 'node:assert/strict';
import { test } from 'node:test';

import { countAt, easeOut, MOTION } from '../motion.ts';

test('the easing starts at 0, ends at 1, never goes back and stays inside 0-1 (D-154)', () => {
  assert.equal(easeOut(0), 0);
  assert.equal(easeOut(1), 1);
  assert.equal(easeOut(-1), 0);
  assert.equal(easeOut(2), 1);
  let last = 0;
  for (let i = 1; i <= 100; i++) {
    const v = easeOut(i / 100);
    assert.ok(v >= last && v <= 1, `step ${i}`);
    last = v;
  }
  assert.ok(easeOut(0.5) > 0.5, 'fast at first');
});

test('a count lands exactly on its value, up or down, and from where it was', () => {
  assert.equal(countAt(0, 68, 0, 700), 0);
  assert.equal(countAt(0, 68, 700, 700), 68);
  assert.equal(countAt(0, 68, 5000, 700), 68, 'after the end it stays put');
  assert.equal(countAt(30, 12, 700, 700), 12, 'counting down');
  const mid = countAt(30, 12, 350, 700);
  assert.ok(mid < 30 && mid > 12);
  assert.equal(countAt(0, 1.4, 100, 0), 1.4, 'no time: the value at once');
});

test('every motion is short, so nobody waits on one', () => {
  for (const [name, v] of Object.entries(MOTION)) {
    if (name.endsWith('Ms')) assert.ok(v > 0 && v <= 700, name);
  }
  assert.ok(MOTION.pressedOpacity >= 0.4 && MOTION.pressedOpacity < 1);
});
