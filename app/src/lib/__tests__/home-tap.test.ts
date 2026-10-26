import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { gardenLevel, homeInput, type GameLike, type Lists } from '../home.ts';
import { cardFor, hitTest, plotBounds, type Box, type CardGame, type CardRules } from '../home-tap.ts';
import { MAP_ORIGIN, composeScene, draws, type RoomJson, type SceneJson } from '../scene.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const KIT = join(ROOT, 'assets', 'isometric');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const manifest = read(join(KIT, 'manifest.json'));
const rules = read(join(ROOT, 'shared', 'game.json'));
const room = read(join(KIT, 'scenes', 'room.json')) as RoomJson;
const boxes: Record<string, Box> = Object.fromEntries(Object.entries(read(join(ROOT, 'assets', 'app', 'atlas', 'atlas.json')).pieces as
  Record<string, number[]>).map(([n, [, , w, h, ox, oy]]) => [n, [ox, oy, ox + w, oy + h] as Box]));
type P = { name: string; footprint_origin: number[]; canvas: number[]; cells: number[] };
const pieces: Lists['pieces'] = Object.fromEntries(manifest.pieces.map((p: P) => [p.name, [...p.footprint_origin, ...p.canvas, ...p.cells]]));
const geom = Object.fromEntries(Object.entries(pieces).map(([n, v]) => [n, [v[0], v[1], v[2], v[3]] as [number, number, number, number]]));
const widths = Object.fromEntries(Object.entries(pieces).map(([n, v]) => [n, v[2]]));
const lists: Lists = { roomDecor: rules.decorations.room, gardenDecor: rules.decorations.garden, pieces };
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const aina = readdirSync(SAMPLES).map((f) => read(join(SAMPLES, f))).find((s) => s.persona.name === 'Aina').game as GameLike & CardGame;

function scene(g: GameLike, period: 'afternoon' | 'night' = 'afternoon') {
  const sc = read(join(KIT, 'scenes', `home_g${gardenLevel(g)}.json`)) as SceneJson;
  const composed = composeScene(sc, room, homeInput(g, sc, period, 5, lists));
  const list = draws(composed, geom);
  const cells = composed.structs.map((s): [number, number] => [s.gx, s.gy]);
  const tap = (x: number, y: number) => hitTest({ x, y }, list, {
    cells, boxes, widths, interactive: room.interactive, plot: plotBounds(sc), room: sc.room,
    bed: (g as unknown as { garden: { bed: [number, number][] } }).garden.bed, plants: g.plants,
    gardenDecor: lists.gardenDecor, treeSpot: sc.tree });
  return { list, tap };
}
/** The centre of a drawn piece's opaque box (where a finger would land). */
function centre(list: ReturnType<typeof draws>, prefix: string) {
  const d = list.find((x) => x.layer === 'struct' && x.piece.startsWith(prefix))!;
  const b = boxes[d.piece];
  return [d.x + (b[0] + b[2]) / 2, d.y + (b[1] + b[3]) / 2] as const;
}

test('a tap on each room object opens what room.json names', () => {
  const { list, tap } = scene(aina);
  assert.deepEqual(tap(...centre(list, 'savings_plant_')), { kind: 'object', opens: 'savings_history', piece: 'savings_plant_1' });
  assert.equal((tap(...centre(list, 'coin_jar_')) as { opens: string }).opens, 'savings');
  assert.equal((tap(...centre(list, 'budget_board_')) as { opens: string }).opens, 'budgets');
  assert.equal((tap(...centre(list, 'crate_shelf')) as { opens: string }).opens, 'assistant');
  assert.deepEqual(tap(...centre(list, 'avatar_')), { kind: 'character' });
});

test('a tap on a plant names it; on the plot\'s ground, the garden; on the room floor or outside, nothing', () => {
  const { list, tap } = scene(aina);
  assert.deepEqual(tap(...centre(list, 'plant_serai')), { kind: 'plant', plant: 'serai', stage: 'full', cell: [6, 8] });
  const cell = (gx: number, gy: number) => [MAP_ORIGIN.x + (gx - gy) * 32 + 32, MAP_ORIGIN.y + (gx + gy) * 16 + 16] as const;
  assert.deepEqual(tap(...cell(9, 2)), { kind: 'garden', cell: [9, 2] });               // lawn inside the fence
  assert.equal(tap(...cell(3, 5)), null);                                              // the room's floor
  assert.equal(tap(...cell(-6, 3)), null);                                             // the street, outside
});

test('tap-to-plant: an empty bed cell offers a plant; a planted cell, even below the plant, opens the plant', () => {
  const { tap } = scene(aina);
  const cell = (gx: number, gy: number) => [MAP_ORIGIN.x + (gx - gy) * 32 + 32, MAP_ORIGIN.y + (gx + gy) * 16 + 24] as const;
  const bed = (aina as unknown as { garden: { bed: [number, number][] } }).garden.bed;
  const empty = bed.find(([x, y]) => !aina.plants.some((p) => p.cell[0] === x && p.cell[1] === y))!;
  assert.deepEqual(tap(...cell(empty[0], empty[1])), { kind: 'bed', cell: empty });
  assert.deepEqual(tap(...cell(6, 8)), { kind: 'plant', plant: 'serai', stage: 'full', cell: [6, 8] });
  assert.equal(cardFor({ kind: 'bed', cell: empty }, aina, rules, false).title, 'Plant here');
});

test('the extras: a garden decoration opens its card (to move it); the tree\'s whole spot opens the tree (D-120)', () => {
  const g = { ...aina, garden: { ...aina.garden, level: 4 }, decorations: { bench: '7,5', curtains_blue: 'room:curtains_blue' },
              tree: { stage: 0 } } as GameLike & CardGame;
  const { list, tap } = scene(g);
  assert.deepEqual(tap(...centre(list, 'bench')), { kind: 'decoration', item: 'bench', cell: [7, 5] });
  const cell = (gx: number, gy: number) => [MAP_ORIGIN.x + (gx - gy) * 32 + 32, MAP_ORIGIN.y + (gx + gy) * 16 + 16] as const;
  for (const [gx, gy] of [[12, 9], [13, 10]]) assert.deepEqual(tap(...cell(gx, gy)), { kind: 'tree' });   // a 7 px mound, a 2 x 2 spot
  assert.deepEqual(scene({ ...g, tree: null }).tap(...cell(12, 9)), { kind: 'tree' });                 // no tree yet: plant one
  assert.match(cardFor({ kind: 'choices' }, g, rules, false).lines[0], /^Every 200 points gives a choice/);
});

test('the plot is inside the fence; before the garden opens there is none', () => {
  const sc = (lv: number) => read(join(KIT, 'scenes', `home_g${lv}.json`)) as SceneJson;
  assert.equal(plotBounds(sc(0)), null);
  const [lo, hi] = plotBounds(sc(1))!;
  assert.ok(lo < 0 && hi > 6);
  assert.ok(plotBounds(sc(4))![1] > hi);                                               // the plot grows
});

test('B8: the garden card says what makes the garden grow, from game.json', () => {
  const c = cardFor({ kind: 'garden', cell: [9, 2] }, aina, rules as CardRules, false);
  assert.equal(c.lines[0], 'Your garden grows when you meet your saving goal or keep a cushion, month after month.');
  assert.match(c.title, /^Your garden · level 1 of 4$/);
  assert.match(c.lines[2], /more counted months? to level 2\.$/);
  const closed = cardFor({ kind: 'garden', cell: [0, 0] }, { ...aina, garden: { ...aina.garden, open: false } }, rules, false);
  assert.match(closed.lines[0], /opens after your first 3 check-ins/);
});

test('object cards quote the game\'s own numbers; the character follows the mood and sleeps at night', () => {
  const jar = cardFor({ kind: 'object', opens: 'savings', piece: 'coin_jar_desk_0' }, aina, rules, false);
  assert.match(jar.lines[0], /at 0\.5, 1, 2 and 3 months/);
  const plant = cardFor({ kind: 'object', opens: 'savings_history', piece: 'savings_plant_1' }, aina, rules, false);
  assert.match(plant.lines[0], /after 1, 2, 3 and 6 months/);
  assert.equal(plant.lines[1], 'Now: stage 1 of 4.');
  assert.match(cardFor({ kind: 'character' }, aina, rules, false).lines[0], /^Focused and determined/);
  assert.match(cardFor({ kind: 'character' }, aina, rules, true).lines[0], /^Asleep/);
  assert.match(cardFor({ kind: 'plant', plant: 'serai', stage: 'full', cell: [6, 8] }, aina, rules, false).lines[0],
               /^full grown, growing for 91 days\.$/);
});
