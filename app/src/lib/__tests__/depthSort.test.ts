import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { depthSort, orderViolations, type Box } from '../depthSort.ts';

type Item = Box & { name: string };
const here = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(here, 'fixtures', 'depth_sort.json'), 'utf-8')) as {
  cases: { name: string; items: Item[]; expected: number[] }[];
};

for (const c of fixture.cases) {
  test(`same order as Python's depth_sort: ${c.name}`, () => {
    const got = depthSort(c.items).map((it) => c.items.indexOf(it));
    assert.deepEqual(got, c.expected);
    assert.ok(c.expected.some((j, i) => i !== j), 'the fixture must make depthSort reorder something');
  });

  test(`no piece wholly behind another is drawn after it: ${c.name}`, () => {
    assert.equal(orderViolations(depthSort(c.items)).length, 0);
  });
}

test('the sofa and the coffee table (D-88)', () => {
  const sofa = { gx: 2, gy: 3, w: 1, d: 2, name: 'sofa' };      // 1 x 2, front cell (2, 4)
  const table = { gx: 3, gy: 3, w: 1, d: 1, name: 'coffee_table' };
  assert.deepEqual(depthSort([table, sofa]).map((p) => p.name), ['sofa', 'coffee_table']);
  assert.equal(orderViolations([table, sofa]).length, 1);
});

test('pieces that never overlap on screen keep their order', () => {
  const a = { gx: 0, gy: 5, w: 1, d: 1 };
  const b = { gx: 5, gy: 0, w: 1, d: 1 };
  assert.deepEqual(depthSort([b, a]), [b, a]);
});
