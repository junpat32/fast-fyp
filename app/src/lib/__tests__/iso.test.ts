import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { CELL_H, CELL_W, cellAt, piecePosition, tileOrigin } from '../iso.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
const manifest = JSON.parse(readFileSync(join(ROOT, 'assets', 'isometric', 'manifest.json'), 'utf-8'));

test('the grid matches the art kit', () => {
  assert.deepEqual(manifest.grid.cell, [CELL_W, CELL_H]);
});

test('placement follows the manifest formula', () => {
  assert.deepEqual(tileOrigin(0, 0), { x: 0, y: 0 });
  assert.deepEqual(tileOrigin(3, 1), { x: 64, y: 64 });                 // ((3-1)*32, (3+1)*16)
  assert.deepEqual(piecePosition(3, 1, [10, 40], { x: 100, y: 5 }), { x: 154, y: 29 });
});

test('a tap anywhere inside a cell finds that cell', () => {
  for (let gx = -3; gx <= 12; gx++) {
    for (let gy = -3; gy <= 12; gy++) {
      const t = tileOrigin(gx, gy, { x: 7, y: 9 });
      const centre = { x: t.x + 32, y: t.y + 16 };
      for (const [dx, dy] of [[0, 0], [20, 0], [-20, 0], [0, 10], [0, -10], [10, 5]]) {
        assert.deepEqual(cellAt({ x: centre.x + dx, y: centre.y + dy }, { x: 7, y: 9 }), [gx, gy]);
      }
    }
  }
});
