import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { frameAt, idleLoop } from '../animate.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
const manifest = JSON.parse(readFileSync(join(ROOT, 'assets', 'isometric', 'manifest.json'), 'utf-8'));
const pieces = new Map<string, { canvas: number[]; footprint_origin: number[] }>(
  manifest.pieces.map((p: { name: string; canvas: number[]; footprint_origin: number[] }) => [p.name, p]));
const has = (n: string) => pieces.has(n);

test('every avatar in every mood breathes and blinks, in the same mood (D-116)', () => {
  for (let a = 1; a <= 6; a++) {
    for (const mood of ['relaxed', 'calm', 'focused', 'concerned_hopeful', 'celebrating']) {
      const loop = idleLoop(`avatar_0${a}_mood_${mood}`, has);
      assert.ok(loop, `avatar ${a} ${mood}`);
      assert.ok(loop.frames.every((f) => f.startsWith(`avatar_0${a}_mood_${mood}`)), 'the expression never changes');
      assert.ok(loop.frames.some((f) => f.endsWith('_blink')) && loop.frames.some((f) => f.endsWith('_breathe')));
    }
  }
});

test('asleep, chickens; and pieces without frames stand still', () => {
  assert.deepEqual(idleLoop('avatar_03_sleep_bed_1', has)?.frames,
                   ['avatar_03_sleep_bed_0', 'avatar_03_sleep_bed_1', 'avatar_03_sleep_bed_2', 'avatar_03_sleep_bed_3']);
  assert.equal(idleLoop('avatar_03_sleep_mattress_2', has)?.frames.length, 4);
  assert.deepEqual(idleLoop('chicken_peck_0', has)?.frames.slice(-1), ['chicken_idle_0']);
  assert.equal(idleLoop('chicken_sleep_0', has)?.frames.length, 8);
  assert.equal(idleLoop('sofa', has), null);
  assert.equal(idleLoop('avatar_03_mood_calm_blink', has), null, 'a frame of a loop is not a loop itself');
  assert.equal(idleLoop('avatar_03_mood_calm', () => false), null, 'no frames in the kit: no loop');
});

test('a loop\'s frames share their canvas and footprint, so the piece never jumps', () => {
  for (const base of ['avatar_05_mood_focused', 'avatar_02_sleep_bed_0', 'avatar_06_sleep_mattress_1', 'chicken_peck_0',
                      'chicken_idle_0', 'chicken_sleep_0']) {
    const loop = idleLoop(base, has)!;
    const first = pieces.get(loop.frames[0])!;
    for (const f of loop.frames) {
      assert.deepEqual(pieces.get(f)!.canvas, first.canvas, f);
      assert.deepEqual(pieces.get(f)!.footprint_origin, first.footprint_origin, f);
    }
  }
});

test('frameAt walks the schedule and wraps', () => {
  const ms = [600, 600, 150];
  assert.deepEqual([0, 599, 600, 1199, 1200, 1349, 1350, -1].map((t) => frameAt(ms, t)), [0, 0, 1, 1, 2, 2, 0, 2]);
});
