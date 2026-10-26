import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { orderViolations, overlapOnScreen } from '../depthSort.ts';
import {
  composeScene, draws, roomFurniture, visibleCells, type Geometry, type RoomJson, type SceneInput, type SceneJson,
} from '../scene.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const KIT = join(HERE, '..', '..', '..', '..', 'assets', 'isometric');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const fixture = read(join(HERE, 'fixtures', 'home_scene.json'));
const room = read(join(KIT, 'scenes', 'room.json')) as RoomJson;
const geom: Geometry = Object.fromEntries(read(join(KIT, 'manifest.json')).pieces.map(
  (p: { name: string; footprint_origin: [number, number]; canvas: [number, number] }) =>
    [p.name, [...p.footprint_origin, ...p.canvas]]));

type Triple = [string, number, number];
type Case = {
  name: string;
  input: { level: number; bed_steps: number; animals: string[] | null; room_state: SceneInput['room'];
           plants: SceneInput['plants']; extras: SceneInput['extras'] };
  boxes: [number, number, number, number][];
  draws: Record<'ground' | 'decals' | 'background' | 'structs', Triple[]>;
};

for (const c of fixture.cases as Case[]) {
  test(`the home scene as the art previews draw it: ${c.name}`, () => {
    const scene = read(join(KIT, 'scenes', `home_g${c.input.level}.json`)) as SceneJson;
    const composed = composeScene(scene, room, {
      bedSteps: c.input.bed_steps, animals: c.input.animals, room: c.input.room_state,
      plants: c.input.plants, extras: c.input.extras,
    });
    const out = draws(composed, geom);
    const by = (layer: string) => out.filter((d) => d.layer === layer).map((d): Triple => [d.name, d.x, d.y]);
    assert.deepEqual(by('ground'), c.draws.ground, 'ground tiles');
    assert.deepEqual(by('decal'), c.draws.decals, 'rugs');
    assert.deepEqual(by('background'), c.draws.background, 'neighbourhood');

    // structures: the same pieces at the same places, and every pair that overlaps on screen drawn in
    // the same order as Python (pairs that never overlap may come either way: the screen is the same)
    const ours = by('struct').map((t) => t.join(' '));
    const theirs = c.draws.structs.map((t) => t.join(' '));
    assert.deepEqual([...ours].sort(), [...theirs].sort(), 'the same structures');
    assert.deepEqual(orderViolations(composed.structs), [], 'nothing wholly behind another is drawn after it');
    const at = new Map(ours.map((s, i) => [s, i]));
    const box = (i: number) => ({ gx: c.boxes[i][0], gy: c.boxes[i][1], w: c.boxes[i][2], d: c.boxes[i][3] });
    let pairs = 0;
    for (let i = 0; i < theirs.length; i++) {
      for (let j = i + 1; j < theirs.length; j++) {
        if (theirs[i] === theirs[j] || !overlapOnScreen(box(i), box(j))) continue;
        pairs += 1;
        assert.ok(at.get(theirs[i])! < at.get(theirs[j])!, `${theirs[i]} must be drawn before ${theirs[j]}`);
      }
    }
    assert.ok(pairs > 0);
  });
}

test('every visible cell of the 540 x 1200 view gets one ground tile', () => {
  const cells = visibleCells();
  assert.equal(cells.length, fixture.cases[0].draws.ground.length);
  assert.equal(new Set(cells.map((x) => x.join(','))).size, cells.length);
});

test('room furniture: level pieces, decorations in the order chosen, the jar and plant filled in', () => {
  const names = roomFurniture(room, { level: 3, jar: 2, plant: 1, droop: true, decor: ['curtains_sage', 'curtains_blue'] })
    .map((x) => x[2]);
  assert.ok(names.includes('savings_plant_1_droop'));
  assert.ok(names.some((n) => n.startsWith('coin_jar_') && n.endsWith('_2')));
  assert.ok(names.some((n) => n.startsWith('curtains_blue_')));
  assert.ok(!names.some((n) => n.startsWith('curtains_sage_')), 'the later curtains replace the earlier');
  assert.ok(!names.some((n) => n.includes('{')), 'no placeholder left');
});
