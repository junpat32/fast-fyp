import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { adviceReward, checkinWindow, cushionProgress, gardenProgress, milestoneLine, monthStrip,
         progressLine, progressParts, type GameRules } from '../rewards.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const rules = JSON.parse(readFileSync(join(ROOT, 'shared', 'game.json'), 'utf-8')) as GameRules;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));

test('milestones and room levels come from game.json', () => {
  const { milestones, next } = cushionProgress({ game_cushion: 1.2, milestones: ['0.5', '1'] }, rules);
  assert.deepEqual(milestones.map((m) => [m.months, m.points, m.room, m.reached]),
                   [[0.5, 50, 2, true], [1, 100, 3, true], [2, 150, 4, false], [3, 200, 5, false]]);
  assert.equal(next?.months, 2);
  assert.equal(milestoneLine(next!), 'Next: 2 months of costs saved: your room grows to level 4 and +150 points.');
  assert.equal(cushionProgress({ game_cushion: 9, milestones: ['0.5', '1', '2', '3'] }, rules).next, null);
});

test('the one-row progress line keeps the points visible (D-109)', () => {
  assert.equal(progressLine({ room_level: 3, game_cushion: 1.2, milestones: ['0.5', '1'] }, rules),
               'Room 3 of 5 · next: 2 months saved → room 4, +150 pts');
  assert.equal(progressLine({ room_level: 1, game_cushion: 0.1, milestones: [] }, rules),
               'Room 1 of 5 · next: 0.5 months saved → room 2, +50 pts');
  assert.equal(progressLine({ room_level: 5, game_cushion: 4, milestones: ['0.5', '1', '2', '3'] }, rules),
               'Room 5 of 5 · every level unlocked');
  for (const s of samples) assert.match(progressLine(s.game, rules), /^Room \d of 5 · /, s.persona.name);
  assert.deepEqual(progressParts({ room_level: 3, game_cushion: 1.2, milestones: ['0.5', '1'] }, rules),
                   { room: 'Room 3 of 5', next: 'next: 2 months saved → room 4, +150 pts' });   // two lines (D-111)
});

test('every reward line quotes only numbers the game really gives', () => {
  const allowed = new Set<number>();
  const walk = (v: unknown): void => {
    if (typeof v === 'number') allowed.add(v);
    else if (v && typeof v === 'object') Object.values(v).forEach(walk);
  };
  walk(rules.points);
  for (const rule of ['R02', 'R05', 'R06', 'R11', 'R12']) {
    const line = adviceReward(`${rule}_x`, rules);
    assert.ok(line, rule);
    for (const n of (line!.match(/\+(\d+)/g) ?? []).map((s) => Number(s.slice(1)))) {
      assert.ok(allowed.has(n), `${rule} mentions +${n}, which isn't in game.json points`);
    }
  }
  assert.match(adviceReward('R11_spending_more_than_income', rules)!, /5% of your income .* \+60 points; 10% earns \+120/);
});

test('guardrail: no reward on debt, AKPK, band, forecast or festive advice', () => {
  for (const rule of ['R01_insufficient_income', 'R03_red_band', 'R04_near_red', 'R07_bnpl_load', 'R08_spending_swings',
                      'R09_festive_month', 'R10_forecast_elevated', 'R13_band_improving']) {
    assert.equal(adviceReward(rule, rules), null, rule);
  }
});

test('the garden: level and qualifying months to the next one', () => {
  assert.deepEqual(gardenProgress({ level: 2, qualifying_months: 3, open: true }, rules),
                   { level: 2, top: 4, open: true, next: { level: 3, needs: 1 } });
  assert.equal(gardenProgress({ level: 4, qualifying_months: 9, open: true }, rules).next, null);
});

test('the check-in opens on the month\'s last day for 7 days (D-77)', () => {
  assert.deepEqual(checkinWindow('2026-07-01', rules), { opens: '2026-07-31', closes: '2026-08-07' });
  assert.deepEqual(checkinWindow('2026-02-14', rules), { opens: '2026-02-28', closes: '2026-03-07' });
});

test('the month strip and the samples', () => {
  for (const s of samples) {
    const strip = monthStrip(s.game.months);
    assert.ok(strip.length > 0 && strip.length <= 6, s.persona.name);
    const p = cushionProgress(s.game, rules);
    assert.ok(p.fill >= 0 && p.fill <= 1);
  }
});
