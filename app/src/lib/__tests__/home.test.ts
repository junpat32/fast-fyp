import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { gardenLevel, homeInput, treePiece, type GameLike, type Lists } from '../home.ts';
import { composeScene, draws, type RoomJson, type SceneJson } from '../scene.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const KIT = join(ROOT, 'assets', 'isometric');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const manifest = read(join(KIT, 'manifest.json'));
const game = read(join(ROOT, 'shared', 'game.json'));
const room = read(join(KIT, 'scenes', 'room.json')) as RoomJson;
const pieces: Lists['pieces'] = Object.fromEntries(manifest.pieces.map(
  (p: { name: string; footprint_origin: number[]; canvas: number[]; cells: number[] }) =>
    [p.name, [...p.footprint_origin, ...p.canvas, ...p.cells]]));
const lists: Lists = { roomDecor: game.decorations.room, gardenDecor: game.decorations.garden, pieces };
const scene = (lv: number) => read(join(KIT, 'scenes', `home_g${lv}.json`)) as SceneJson;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json')).map((f) => read(join(SAMPLES, f)));

test('each persona\'s home: every piece it draws exists in the kit', () => {
  for (const s of samples) {
    const g = s.game as GameLike;
    for (const period of ['morning', 'afternoon', 'night'] as const) {
      const sc = scene(gardenLevel(g));
      const out = draws(composeScene(sc, room, homeInput(g, sc, period, 5, lists)), Object.fromEntries(
        Object.entries(pieces).map(([n, v]) => [n, [v[0], v[1], v[2], v[3]]])));
      const missing = out.filter((d) => !pieces[d.piece]).map((d) => d.piece);
      assert.deepEqual(missing, [], `${s.persona.name} ${period}`);
    }
  }
});

test('Aina at the start: her room, her three plants, standing by day and asleep at night', () => {
  const aina = samples.find((s) => s.persona.name === 'Aina').game as GameLike;
  const day = homeInput(aina, scene(1), 'afternoon', 5, lists);
  assert.equal(day.room?.level, 2);
  assert.deepEqual(day.plants?.map((p) => p[2]).sort(), ['plant_chilli_full', 'plant_pandan_full', 'plant_serai_full']);
  assert.deepEqual(day.extras, [[4, 4, 'avatar_05_mood_focused', [1, 1], 0.3]]);
  const night = homeInput(aina, scene(1), 'night', 5, lists);
  assert.deepEqual(night.extras, [[0, 0, 'avatar_05_sleep_bed_1', [1, 2], 0.35]]);     // room 2 has the bed
});

test('drooping plants, the tree, decorations and chickens', () => {
  const g: GameLike = {
    room_level: 1, garden: { open: true, level: 4, bed_step: 2 },
    plants: [{ cell: [6, 8], plant: 'serai', stage: 'young' }], tree: { stage: 3 },
    decorations: { curtains_peach: 'room:curtains_peach', bench: '3,9', rug_blue: 'room:rug_blue' },
    animals: { chicken: 2 }, look: { mood: 'concerned_hopeful', plants: 'droop', coin_jar: 1, savings_plant: 2 },
  };
  const input = homeInput(g, scene(4), 'morning', 2, lists);
  assert.deepEqual(input.plants, [[6, 8, 'plant_serai_young_droop']]);
  assert.equal(input.room?.droop, true);
  assert.deepEqual(input.room?.decor, ['curtains_peach', 'rug_blue']);
  assert.deepEqual(input.animals, ['chickens']);                     // the API's "chicken" lives in the kit's "chickens" coop
  assert.deepEqual(game.garden.animals, ['chicken']);                // what the API sends (game.json)
  const names = input.extras!.map((e) => e[2]);
  assert.ok(names.includes('tree_3_young_droop'));
  assert.ok(names.includes('bench'));
  assert.ok(names.includes('avatar_02_mood_concerned_hopeful'));
  assert.ok(names.includes('chicken_idle_0') && names.includes('chicken_peck_0|flip'));
  assert.equal(homeInput(g, scene(4), 'night', 2, lists).extras!.find((e) => String(e[2]).startsWith('avatar'))![2],
               'avatar_02_sleep_mattress_1');                                  // room 1: the mattress
  assert.equal(treePiece(0, false, lists), 'tree_0_mound');
});

test('before the garden opens the home is the room alone (G0)', () => {
  assert.equal(gardenLevel({ garden: { open: false, level: 1, bed_step: 0 } } as GameLike), 0);
});
