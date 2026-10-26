import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  buildCheckin, canEditCheckin, CHECKIN_EDIT_HOURS, closes, formOf, lastDay, monthEnd, monthWord, myDate, nextOpens, openMonth,
  parseBalance, WINDOW_DAYS, type CheckinForm, type CheckinRow,
} from '../checkin.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));
const blank: CheckinForm = { cash: '', epfFleksibel: '', emergency: '', others: '', epfRetirement: '', debt: '', income: '',
                             bills: null, ranShort: null };

test('the window: a month\'s last day until 7 days after, never before sign-up (D-77)', () => {
  const joined = '2025-12-31';
  assert.equal(lastDay('2026-06-01'), '2026-06-30');
  assert.equal(lastDay('2024-02-01'), '2024-02-29');
  assert.equal(openMonth('2026-06-30', joined), '2026-06-01');       // the last day opens it
  assert.equal(openMonth('2026-07-01', joined), '2026-06-01');       // the study's start date: June is open
  assert.equal(openMonth('2026-07-07', joined), '2026-06-01');
  assert.equal(openMonth('2026-07-08', joined), null);               // closed
  assert.equal(openMonth('2026-07-15', joined), null);
  assert.equal(nextOpens('2026-07-15'), '2026-07-31');
  assert.equal(closes('2026-06-01'), '2026-07-07');
  assert.equal(openMonth('2026-01-03', '2026-01-02'), null, 'December was before sign-up');
  assert.equal(openMonth('2026-01-03', joined), '2025-12-01');       // signed up on 31 Dec: December counts
  assert.equal(monthWord('2026-06-01'), 'June');
});

test('balances to the sen as decimal strings; blank is zero except where an answer is needed', () => {
  assert.deepEqual(parseBalance('1,250.5', true), { ok: true, value: '1250.50' });
  assert.deepEqual(parseBalance('', false), { ok: true, value: '0.00' });
  assert.equal(parseBalance('', true).ok, false);
  assert.deepEqual(parseBalance('0', true), { ok: true, value: '0.00' });
  assert.equal(parseBalance('-3', false).ok, false);
});

test('the row the database expects, and everything to fix at once', () => {
  const r = buildCheckin({ ...blank, cash: '1250', debt: '594.48', epfFleksibel: '300', bills: true, ranShort: false }, '2026-06-01');
  assert.ok(r.ok);
  assert.deepEqual(r.row, {
    month: '2026-06-01', cash_bank_ewallet: '1250.00', epf_fleksibel: '300.00', others_emergency: '0.00', others: '0.00',
    epf_retirement: null, debt_total: '594.48', net_income: null, bills_paid_on_time: true, ran_short: false,
  });
  const bad = buildCheckin(blank, '2026-06-01');
  assert.ok(!bad.ok);
  assert.deepEqual(Object.keys(bad.errors).sort(), ['bills', 'cash', 'debt', 'ranShort']);
});

test('fix it for 48 hours, as the database allows check-ins (C3)', () => {
  const migration = readFileSync(join(ROOT, 'supabase', 'migrations', '20261014000000_init.sql'), 'utf-8');
  assert.match(migration, new RegExp(`"edit own rows for ${CHECKIN_EDIT_HOURS} hours" on public\\.monthly_checkins`));
  assert.match(migration, /interval '1 day'\)::date \+ 7/, 'the window is 7 days after the last day');
  const game = JSON.parse(readFileSync(join(ROOT, 'shared', 'game.json'), 'utf-8'));
  assert.equal(game.edit_window_hours, CHECKIN_EDIT_HOURS, 'game.json, the app and the database agree');
  assert.equal(game.checkin_grace_days, WINDOW_DAYS);
  const made = '2026-06-30T15:00:00+00:00';                          // the personas' June check-in
  assert.equal(canEditCheckin(made, new Date('2026-07-01T04:00:00Z')), true);    // the study date, noon
  assert.equal(canEditCheckin(made, new Date('2026-07-02T15:00:00Z')), false);
});

test('the month\'s end: today\'s balances minus what was logged after the month ended (D-77)', () => {
  const row = { cash_bank_ewallet: 3000, epf_fleksibel: 200, others_emergency: 100, debt_total: 5000,
                after_month_net: 2800, after_month_debt: 300 } as CheckinRow;
  assert.deepEqual(monthEnd(row), { counted: 500, owed: 4700 });      // July's salary came in after June ended
  assert.deepEqual(monthEnd({ ...row, after_month_net: 9999 }), { counted: 300, owed: 4700 }, 'never below zero');
});

test('sign-up is counted in Malaysian time, as the database does', () => {
  assert.equal(myDate('2025-12-31T16:30:00+00:00'), '2026-01-01');     // 00:30 on 1 January in KL
  assert.equal(openMonth('2026-01-03', myDate('2025-12-31T16:30:00+00:00')), null, 'December was before sign-up');
});

test('each persona: June is open on the study date, already checked in, and its form comes back as saved', () => {
  for (const s of samples) {
    const last = s.checkins.at(-1) as CheckinRow;
    assert.equal(openMonth(s.assess.as_of, myDate(s.profile.created_at)), '2026-06-01', s.persona.name);
    assert.equal(last.month, '2026-06-01');
    const again = buildCheckin(formOf(last), last.month);
    assert.ok(again.ok);
    assert.equal(Number(again.row.debt_total), last.debt_total);
    assert.equal(again.row.bills_paid_on_time, last.bills_paid_on_time);
  }
});
