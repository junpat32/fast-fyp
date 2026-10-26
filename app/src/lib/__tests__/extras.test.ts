import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  animalStatus, decorSpots, footprint, offeredSpots, roomOptions, spotAt, treeStatus, usedCells, type C2, type ExtrasGame,
  type ExtrasRules,
} from '../extras.ts';
import { applyActions, GameRuleError, type GameMove, type GardenRules, type GardenState } from '../garden.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const rules = read(join(ROOT, 'shared', 'game.json')) as ExtrasRules & GardenRules;
const free = (lv: number) => read(join(ROOT, 'assets', 'isometric', 'scenes', `home_g${lv}.json`)).decor_free_cells as C2[];
const fixture = read(join(HERE, 'fixtures', 'decor_spots.json')) as {
  cases: { level: number; size: C2; used: C2[]; expected: C2[] }[] };

test('a garden decoration fits where the kit says, nearest the garden door first (decor_spots)', () => {
  for (const c of fixture.cases) {
    assert.deepEqual(decorSpots(free(c.level), c.size, c.used), c.expected, `G${c.level} ${c.size} used ${c.used.length}`);
  }
});

test('the glowing spots: at most 3, each a fit, none overlapping another', () => {
  for (const c of fixture.cases) {
    const spots = offeredSpots(free(c.level), c.size, c.used);
    assert.ok(spots.length >= 1 && spots.length <= 3);
    assert.deepEqual(spots[0], c.expected[0]);                                 // the nearest always comes first
    const cells = spots.flatMap((s) => footprint(s, c.size).map(String));
    assert.equal(new Set(cells).size, cells.length);
    assert.ok(spots.every((s) => c.expected.some((e) => e[0] === s[0] && e[1] === s[1])));
  }
});

test('placed decorations take their whole footprint; a moving one frees its own', () => {
  const sizes: Record<string, C2> = { bench: [1, 2], fountain: [2, 2] };
  const deco = { bench: '3,9', fountain: '12,13', curtains_peach: 'room:curtains_peach' };
  assert.deepEqual(usedCells(deco, sizes).map(String), ['3,9', '3,10', '12,13', '12,14', '13,13', '13,14']);
  assert.deepEqual(usedCells(deco, sizes, 'bench').map(String), ['12,13', '12,14', '13,13', '13,14']);
  assert.deepEqual(spotAt([3, 10], [[3, 9], [7, 5]], [1, 2]), [3, 9]);          // the back cell or the one in front
  assert.equal(spotAt([5, 5], [[3, 9]], [1, 2]), null);
});

const base: ExtrasGame & GardenState = {
  choices: { earned: 3, used: 0, available: 3 },
  garden: { open: true, level: 2, qualifying_months: 2, plant_tier: 1, bed: [], animal_slots: 1, animal_slots_used: 0 },
  plants: [], seed_box: [], tree: null, decorations: {}, animals: {},
};

test('room decorations: one of each; a curtain or rug shows instead of the one before', () => {
  const g = { ...base, decorations: { curtains_peach: 'room:curtains_peach', dining_set: 'room:dining_set' } };
  const opts = Object.fromEntries(roomOptions(g, rules).map((o) => [o.item, o]));
  assert.equal(opts.curtains_peach.owned, true);
  assert.equal(opts.curtains_blue.hides, 'curtains_peach');
  assert.equal(opts.curtains_peach.hides, null);
  assert.equal(opts.rug_blue.hides, null);                                     // no rug yet
  assert.equal(roomOptions(g, rules).length, rules.decorations.room.length);
});

test('the tree waits for the top garden level, counted in months; then it grows through 7 stages', () => {
  assert.deepEqual(treeStatus({ ...base, garden: { ...base.garden, open: false } }, rules), { kind: 'locked', months: null });
  assert.deepEqual(treeStatus(base, rules), { kind: 'locked', months: 4 });        // level 4 comes at 6 counted months
  assert.deepEqual(treeStatus({ ...base, garden: { ...base.garden, level: 4, qualifying_months: 6 } }, rules), { kind: 'ready', free: false });
  assert.deepEqual(treeStatus({ ...base, tree: { stage: 2 } }, rules), { kind: 'have', count: 1, max: 1, stage: 2, stages: 7 });
});

test('chickens: free at an open animal place, then up to 4, and the next place counted in months', () => {
  assert.deepEqual(animalStatus(base, rules, 'chicken'), { kind: 'ready', free: true });
  assert.deepEqual(animalStatus({ ...base, animals: { chicken: 2 } }, rules, 'chicken'), { kind: 'have', count: 2, max: 4 });
  const early = { ...base, garden: { ...base.garden, qualifying_months: 1, animal_slots: 0 } };
  assert.deepEqual(animalStatus(early, rules, 'chicken'), { kind: 'locked', months: 1 });
  assert.deepEqual(animalStatus({ ...base, garden: { ...base.garden, open: false } }, rules, 'chicken'), { kind: 'locked', months: null });
});

const refused = (g: GardenState, a: GameMove, message: string) =>
  assert.throws(() => applyActions(g, [a], rules), (e: Error) => e instanceof GameRuleError && e.message === message);

test('the extras on the phone follow the engine: costs, limits and its own refusals', () => {
  const after = applyActions(base, [
    { kind: 'decorate', item: 'bench', spot: '3,9' },
    { kind: 'decorate', item: 'curtains_sage', spot: 'room:curtains_sage' },
    { kind: 'choose_animal', item: 'chicken' },                                 // free: an animal place was open
    { kind: 'add_animal', item: 'chicken' },
    { kind: 'move_decoration', item: 'bench', spot: '4,9' },                   // moving is free
  ], rules);
  assert.deepEqual(after.decorations, { bench: '4,9', curtains_sage: 'room:curtains_sage' });
  assert.deepEqual(after.animals, { chicken: 2 });
  assert.equal(after.choices.available, 0);                                    // bench, curtains, a second chicken
  assert.equal(after.garden.animal_slots_used, 1);
  refused(after, { kind: 'decorate', item: 'lantern', spot: '7,5' }, 'no choice available yet: every 200 points gives one');
  refused(base, { kind: 'buy_tree' }, 'the tree needs the bigger garden (G4)');
  refused({ ...base, decorations: { bench: '3,9' } }, { kind: 'decorate', item: 'lantern', spot: '3,9' }, 'that spot is taken');
  refused({ ...base, decorations: { bench: '3,9' } }, { kind: 'decorate', item: 'bench', spot: '7,5' }, 'you already have that one');
  refused({ ...base, garden: { ...base.garden, open: false } }, { kind: 'decorate', item: 'bench', spot: '3,9' }, "the garden isn't open yet");
  refused(base, { kind: 'move_decoration', item: 'bench', spot: '3,9' }, "you don't have that decoration");
  refused(base, { kind: 'add_animal', item: 'chicken' }, 'choose this animal at an animal slot first');
  refused({ ...base, animals: { chicken: 4 } }, { kind: 'add_animal', item: 'chicken' }, 'at most 4 of each animal');
  refused({ ...base, garden: { ...base.garden, animal_slots: 0 } }, { kind: 'choose_animal', item: 'chicken' }, 'no animal slot open yet');
  const tree = applyActions({ ...base, garden: { ...base.garden, level: 4 } }, [{ kind: 'buy_tree' }], rules);
  assert.deepEqual(tree.tree, { stage: 0 });
  assert.equal(tree.choices.available, 2);
  refused(tree, { kind: 'buy_tree' }, 'the garden already has its tree');
});
