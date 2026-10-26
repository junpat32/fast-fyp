import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { memoryCheckins } from '../../api/checkins.ts';
import { memoryStore } from '../../api/entries.ts';
import type { CheckinRow, NewCheckin } from '../checkin.ts';
import { canEdit } from '../entry.ts';
import { applyActions, freeBedCells, GameRuleError, type GardenRules, type GardenState } from '../garden.ts';
import { canGoBack, canGoOn, shiftMonth, stepDate, studyDates, type StudyClock } from '../study.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const rules = read(join(HERE, '..', '..', '..', '..', 'shared', 'game.json')) as GardenRules;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const TRAVEL = join(HERE, '..', '..', 'data', 'travel');
const files = readdirSync(SAMPLES).filter((f) => f.endsWith('.json')).sort();
const start = files.map((f) => read(join(SAMPLES, f)));
const later = files.map((f) => read(join(TRAVEL, f)).dates as Record<string, { checkins: CheckinRow[]; game: GardenState }>);
const clock = (date: string): StudyClock => ({ date, first: '2026-07-01', last: '2027-01-01' });

test('a month on or back, across the new year', () => {
  assert.equal(shiftMonth('2026-07-01', 1), '2026-08-01');
  assert.equal(shiftMonth('2026-12-01', 1), '2027-01-01');
  assert.equal(shiftMonth('2027-01-01', -1), '2026-12-01');
  assert.equal(shiftMonth('2026-07-15', 0), '2026-07-01');              // always the first of a month
  assert.throws(() => shiftMonth('July', 1));
});

test('time travel stays in the study range, as the API clamps it', () => {
  assert.equal(stepDate(clock('2026-07-01'), 'next'), '2026-08-01');
  assert.equal(stepDate(clock('2026-07-01'), 'previous'), '2026-07-01');  // already at the start
  assert.equal(stepDate(clock('2027-01-01'), 'next'), '2027-01-01');      // already at the end
  assert.equal(stepDate(clock('2026-10-01'), 'first'), '2026-07-01');
  assert.equal(stepDate(clock('2026-10-01'), 'last'), '2027-01-01');
  assert.ok(!canGoBack(clock('2026-07-01')) && canGoOn(clock('2026-07-01')));
  assert.ok(canGoBack(clock('2027-01-01')) && !canGoOn(clock('2027-01-01')));
});

test('every date the bar can reach has sample data (D-119)', () => {
  for (let i = 0; i < start.length; i++) {
    const s = start[i].study;
    const dates = studyDates(s);
    assert.equal(dates.length, 7);
    assert.equal(dates[0], s.study_date);
    assert.deepEqual(dates.slice(1), Object.keys(later[i]));
    let d = s.first;                                      // pressing › six times walks the same dates
    for (const want of dates.slice(1)) assert.equal((d = stepDate({ ...s, date: d }, 'next')), want);
  }
});

test('after time travel, an earlier plant that no longer fits is skipped, as the replay does', () => {
  const jasonJan = later[1]['2027-01-01'].game;
  const [free] = freeBedCells(jasonJan);
  const taken = jasonJan.plants[0].cell;
  const actions = [{ kind: 'plant' as const, cell: taken, item: 'pandan' }, { kind: 'plant' as const, cell: free, item: 'pandan' }];
  assert.throws(() => applyActions(jasonJan, actions, rules), GameRuleError);    // strict: the first one stops it
  const skipped: string[] = [];
  const after = applyActions(jasonJan, actions, rules, (_, e) => skipped.push(e.message));
  assert.deepEqual(skipped, ['something is already growing there']);
  assert.equal(after.plants.length, jasonJan.plants.length + 1);                // the one that fits went in
  assert.equal(after.choices.available, jasonJan.choices.available - 1);       // and only it cost a choice
});

const fix = (month: string, cash: string): NewCheckin => ({
  month, cash_bank_ewallet: cash, epf_fleksibel: '0', others_emergency: '0', others: '0', epf_retirement: null,
  debt_total: '0', net_income: null, bills_paid_on_time: true, ran_short: false,
});

test('check-ins follow the persona\'s date, and the session\'s own stay', async () => {
  const aina: Record<string, CheckinRow[]> = {
    '2026-07-01': start[0].checkins, ...Object.fromEntries(Object.entries(later[0]).map(([d, x]) => [d, x.checkins])) };
  let date = '2026-07-01';
  const store = memoryCheckins(() => aina[date], () => new Date(`${date}T04:00:00Z`));
  assert.equal((await store.list()).at(-1)!.month, '2026-06-01');              // June is the latest on 1 July
  const june = await store.save(fix('2026-06-01', '120'));                     // fixed within its 48 hours
  assert.equal(june.created_at, aina[date].at(-1)!.created_at);                // a fix keeps when it was made
  date = '2026-08-01';
  const list = await store.list();
  assert.equal(list.at(-1)!.month, '2026-07-01');                              // the persona's July appears
  assert.equal(list.find((r) => r.month === '2026-06-01')!.cash_bank_ewallet, 120);   // the fix is still there
  date = '2026-07-01';
  assert.equal((await store.list()).at(-1)!.month, '2026-06-01');              // back again: July hides again
});

test('a new check-in shows from the month after its own, dated on the persona\'s clock', async () => {
  let date = '2026-09-01';
  const store = memoryCheckins(() => [], () => new Date(`${date}T04:00:00Z`));
  const aug = await store.save(fix('2026-08-01', '50'));
  assert.equal(aug.created_at, '2026-09-01T04:00:00.000Z');
  assert.equal((await store.list()).length, 1);
  date = '2026-08-01';
  assert.equal((await store.list()).length, 0);                                // August isn't over yet then
});

test('task 7\'s entry is dated on the persona\'s clock, so its 48-hour fix window follows time travel', async () => {
  let date = '2026-07-01';
  const now = () => new Date(`${date}T04:00:00Z`);
  const store = memoryStore(now);
  const e = await store.add({ occurred_on: date, direction: 'out', amount: '12.00', category: 'eating_out',
    is_essential: false, is_bnpl: false, on_credit: false, is_debt_payment: false, is_own_transfer: false,
    is_unexpected: false, note: null, source: 'typed' });
  assert.ok(canEdit(e.created_at, now()));
  date = '2026-08-01';
  assert.ok(!canEdit(e.created_at, now()));                                     // a month later: closed
  assert.equal((await store.month(date)).length, 0);                           // and not in August's list
});
