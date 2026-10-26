import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  BASE_TONE, crispSize, paintSheet, portraitRects, sheetFrames, sheetLayout, suggestedTone, type Characters, type Rect6,
} from '../character.ts';
import type { Period } from '../timeOfDay.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const chars = read(join(ROOT, 'assets', 'isometric', 'characters.json')) as Characters;
const atlas = read(join(ROOT, 'assets', 'app', 'atlas', 'atlas.json')).pieces as Record<string, Rect6>;
type Case = {
  avatar: number; tone: number; glasses: boolean; period: Period; frame: string; head_dy: number; frame_glasses: boolean;
  frame_box: number[]; glasses_box: number[]; union: number[]; frame_rgba: string; glasses_rgba: string; expected: string;
};
const cases = (read(join(HERE, 'fixtures', 'character.json')) as { cases: Case[] }).cases;
const bytes = (b64: string) => new Uint8Array(Buffer.from(b64, 'base64'));

test('the skin swap and the glasses give exactly the kit\'s own pixels (palette.to_rgba with a tone)', () => {
  for (const c of cases) {
    const [fx0, fy0, fx1, fy1] = c.frame_box, [gx0, gy0, gx1, gy1] = c.glasses_box;
    const fw = fx1 - fx0, fh = fy1 - fy0, gw = gx1 - gx0, gh = gy1 - gy0;
    const W = Math.max(fw, gw), H = fh + 1 + gh;                   // a little atlas: the frame, the glasses below it
    const page = new Uint8Array(W * H * 4);
    const blit = (src: Uint8Array, w: number, h: number, y0: number) => {
      for (let j = 0; j < h; j++) page.set(src.subarray(j * w * 4, (j + 1) * w * 4), ((y0 + j) * W) * 4);
    };
    blit(bytes(c.frame_rgba), fw, fh, 0);
    blit(bytes(c.glasses_rgba), gw, gh, fh + 1);
    const name = chars.avatars[c.avatar - 1].name;
    const kit: Record<string, Rect6> = { [`${name}_${c.frame}`]: [0, 0, fw, fh, fx0, fy0], glasses_front: [0, fh + 1, gw, gh, gx0, gy0] };
    const one: Characters = { ...chars, avatars: chars.avatars.map((a, i) => (i === c.avatar - 1
      ? { ...a, frames: { [c.frame]: { head_dy: c.head_dy, glasses: c.frame_glasses, view: 'front' } } } : a)) };
    const look = { avatar: c.avatar, tone: c.tone, glasses: c.glasses };
    const frames = sheetFrames(look, one, kit);
    assert.equal(frames.length, 1);
    assert.deepEqual(frames[0].box, c.union, c.frame);
    const layout = sheetLayout(frames);
    const out = paintSheet(frames, layout, page, W, kit, look, c.period, one);
    const [x, y, w, h] = layout.rects[`${name}_${c.frame}`];
    const want = bytes(c.expected);
    for (let j = 0; j < h; j++) {
      const got = out.subarray(((y + j) * layout.width + x) * 4, ((y + j) * layout.width + x + w) * 4);
      assert.deepEqual([...got], [...want.subarray(j * w * 4, (j + 1) * w * 4)], `${c.frame} tone ${c.tone} row ${j}`);
    }
  }
});

test('a whole avatar fits one small sheet, frames apart; glasses only on front frames that take them', () => {
  for (let avatar = 1; avatar <= 6; avatar++) {
    const frames = sheetFrames({ avatar, tone: 1, glasses: true }, chars, atlas);
    assert.equal(frames.length, Object.keys(chars.avatars[avatar - 1].frames).length);
    assert.ok(frames.filter((f) => f.piece.includes('_sleep_') || f.piece.includes('_back_')).every((f) => !f.glasses));
    assert.ok(frames.filter((f) => f.piece.includes('_mood_')).every((f) => f.glasses));
    const layout = sheetLayout(frames);
    assert.ok(layout.width <= 512 && layout.height <= 512, `${layout.width} x ${layout.height}`);
    const rects = Object.values(layout.rects);
    for (const a of rects) for (const b of rects) {
      if (a === b) continue;
      const apart = a[0] + a[2] <= b[0] || b[0] + b[2] <= a[0] || a[1] + a[3] <= b[1] || b[1] + b[3] <= a[1];
      assert.ok(apart);
    }
  }
});

test('the base tone without glasses copies the art unchanged; each avatar starts in its suggested tone', () => {
  assert.equal(BASE_TONE, 3);
  assert.deepEqual(chars.avatars.map((_, i) => suggestedTone(i + 1, chars)), [3, 2, 1, 1, 5, 4]);
  assert.ok(chars.skin_tones.length === 6 && chars.skin_tones.every((t) => t.night.length === 3));
});

test('a portrait shows the head and shoulders, cut to the frame\'s own pixels, at a crisp whole-number scale', () => {
  const r: Rect6 = [100, 200, 27, 56, 26, 73];                     // avatar_03_mood_calm's place on a sheet
  assert.deepEqual(portraitRects(r), { src: [100, 200, 27, 41], dst: [10, 7, 27, 41] });
  assert.equal(portraitRects([0, 0, 5, 5, 0, 0]), null);           // nowhere near the box
  assert.equal(crispSize(104, 2.75), (6 * 48) / 2.75);             // 6 device pixels an art pixel
  assert.equal(crispSize(10, 1), 48);                              // never below one pixel each
});
