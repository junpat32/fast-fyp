import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  applyActions, freeBedCells, GameRuleError, growthLine, plantOptions, pointsToNextChoice, stageOf, type GardenRules,
  type GardenState,
} from '../garden.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const rules = read(join(ROOT, 'shared', 'game.json')) as GardenRules;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const byName = Object.fromEntries(readdirSync(SAMPLES).map((f) => read(join(SAMPLES, f))).map((s) => [s.persona.name, s.game]));
const aina = byName.Aina as GardenState;              // garden 1, a 2 x 2 bed with 3 plants, no choice left
const jason = byName.Jason as GardenState;            // garden 2, a 2 x 3 bed with 4 plants, 8 choices

const refused = (g: GardenState, a: Parameters<typeof applyActions>[1], message: string) =>
  assert.throws(() => applyActions(g, a, rules), (e: Error) => e instanceof GameRuleError && e.message === message);

test('tap-to-plant: a free bed cell, an unlocked plant, one choice spent', () => {
  const [cell] = freeBedCells(jason);
  const after = applyActions(jason, [{ kind: 'plant', cell, item: 'pandan' }], rules);
  assert.equal(after.plants.length, jason.plants.length + 1);
  assert.deepEqual(after.plants.at(-1), { cell, plant: 'pandan', stage: 'seedling', growing_days: 0 });
  assert.equal(after.choices.available, jason.choices.available - 1);
  assert.equal(after.choices.used, jason.choices.used + 1);
  assert.equal(jason.plants.length, 4, 'the original game is unchanged');
});

test('the engine\'s refusals, word for word', () => {
  const [free] = freeBedCells(jason);
  refused(jason, [{ kind: 'plant', cell: [0, 0], item: 'serai' }], 'plants go in the flower bed');
  refused(jason, [{ kind: 'plant', cell: jason.plants[0].cell, item: 'serai' }], 'something is already growing there');
  refused(jason, [{ kind: 'plant', cell: free, item: 'cactus' }], 'unknown plant: cactus');
  refused(jason, [{ kind: 'plant', cell: free, item: 'orchid' }], 'that plant unlocks with more months of keeping your buffer');
  refused(aina, [{ kind: 'plant', cell: freeBedCells(aina)[0], item: 'serai' }], 'no choice available yet: every 200 points gives one');
  refused({ ...jason, garden: { ...jason.garden, open: false } }, [{ kind: 'plant', cell: free, item: 'serai' }], "the garden isn't open yet");
  refused(jason, [{ kind: 'dig', cell: free }], 'nothing planted there');
});

test('dig up: into the seed box with its growth; planting it again is free and keeps the growth', () => {
  const chilli = aina.plants.find((p) => p.plant === 'chilli')!;
  const dug = applyActions(aina, [{ kind: 'dig', cell: chilli.cell }], rules);
  assert.deepEqual(dug.seed_box, ['chilli']);
  assert.equal(dug.plants.length, 2);
  const back = applyActions(aina, [{ kind: 'dig', cell: chilli.cell }, { kind: 'plant', cell: chilli.cell, item: 'chilli' }], rules);
  assert.deepEqual(back.seed_box, []);
  assert.equal(back.choices.available, aina.choices.available, 'free from the seed box');
  assert.equal(back.plants.at(-1)!.growing_days, chilli.growing_days);
  assert.equal(back.plants.at(-1)!.stage, chilli.stage);
});

test('points to the next choice: every 200 points gives one', () => {
  assert.equal(pointsToNextChoice(575, rules), 25);
  assert.equal(pointsToNextChoice(600, rules), 200);
  assert.equal(pointsToNextChoice(0, rules), 200);
});

test('stages and the growth line follow game.json (young after 7, full after 21 growing days)', () => {
  assert.deepEqual([0, 6, 7, 20, 21].map((d) => stageOf(d, rules)), ['seedling', 'seedling', 'young', 'young', 'full']);
  assert.equal(growthLine(0, rules), 'Young in 7 growing days, full grown in 21 growing days');
  assert.equal(growthLine(20, rules), 'Full grown in 1 growing day');
  assert.equal(growthLine(30, rules), 'Full grown');
});

test('the seed picker: tier 1 open for everyone, the rest a number of counted months away', () => {
  const opts = plantOptions(jason, rules);
  assert.deepEqual(opts.filter((o) => o.unlocked).map((o) => o.plant), ['serai', 'pandan', 'chilli']);
  const orchid = opts.find((o) => o.plant === 'orchid')!;
  assert.equal(orchid.unlocked, false);
  assert.equal(orchid.unlockInMonths, 12 - jason.garden.qualifying_months);
  assert.equal(opts.find((o) => o.plant === 'pandan')!.free, false);
});
