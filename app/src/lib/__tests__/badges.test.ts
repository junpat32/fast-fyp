import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { BADGE_KEYS, badgeList, pointsGuide, type BadgeRules } from '../badges.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const rules = JSON.parse(readFileSync(join(ROOT, 'shared', 'game.json'), 'utf-8')) as BadgeRules;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));

test('the three badges are the ones game.json sets and the engine awards', () => {
  const fromRules = Object.keys(rules.badges).map((k) => k.split('_months')[0].split('_streak')[0]);
  assert.deepEqual([...BADGE_KEYS].sort(), fromRules.sort());
  for (const s of samples) for (const b of s.game.badges) assert.ok((BADGE_KEYS as readonly string[]).includes(b), b);
});

test('what earns each badge comes from game.json', () => {
  const list = badgeList({ badges: [], game_cushion: 0.97, streak: { current: 12 } }, rules);
  assert.deepEqual(list.map((b) => [b.key, b.earned]), BADGE_KEYS.map((k) => [k, false]));
  assert.equal(list[0].how, 'Have 1 month of costs saved.');
  assert.equal(list[0].now, 'Now: 0.9 months saved.');                     // rounded down: never "1 month" early
  assert.equal(list[1].how, 'Set aside at least 5% of your income 3 months in a row.');
  assert.equal(list[1].now, null);
  assert.equal(list[2].how, 'Log something, or tap "No spending today", 30 days in a row (1 rest day a week is fine).');
  assert.equal(list[2].now, 'Now: 12 days in a row.');
});

test('a cushion saved but not yet confirmed says so, and an earned badge shows no progress', () => {
  const [cushion] = badgeList({ badges: [], game_cushion: 1.2, streak: { current: 0 } }, rules);
  assert.equal(cushion.now, 'You have it saved: it counts once a check-in confirms it.');
  const earned = badgeList({ badges: ['honest_tracker'], game_cushion: 0, streak: { current: 1 } }, rules);
  assert.deepEqual(earned.map((b) => b.earned), [false, false, true]);
  assert.equal(earned[2].now, null);
  assert.equal(badgeList({ badges: [], game_cushion: -0.2, streak: { current: 1 } }, rules)[0].now, 'Now: 0 months saved.');
});

test('each persona shows its own badges', () => {
  const earned = samples.map((s) => badgeList(s.game, rules).filter((b) => b.earned).map((b) => b.key).sort());
  assert.deepEqual(earned, samples.map((s) => [...s.game.badges].sort()));
});

test('the points guide uses every number from game.json', () => {
  const g = pointsGuide(rules).join('\n');
  assert.match(g, /Monthly check-in: \+20/);
  assert.match(g, /Set aside 5% of your income in a month: \+60; 10%: \+120/);
  assert.match(g, /new low by 5% of your income: \+80; 10%: \+160/);
  assert.match(g, /Costs saved, 0\.5, 1, 2 and 3 months: \+50, \+100, \+150 and \+200, once each/);
  assert.match(g, /Keeping 1 month saved: \+40 at each check-in; 3 months: \+80/);
  assert.match(g, /Logging streak of 7, 30 and 100 days: \+20, \+40 and \+60, once each/);
  assert.match(g, /Every 200 points: a choice/);
  assert.match(g, /never taken away/);
});
