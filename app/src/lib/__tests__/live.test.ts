import assert from 'node:assert/strict';
import { test } from 'node:test';

import { dbError, DbError, supabaseDb, type Db, type Query } from '../../api/db.ts';
import {
  liveBudgets, liveCheckins, liveDebts, liveEntries, liveProfile, monthRange, readProfile,
} from '../../api/live.ts';
import type { NewCheckin } from '../checkin.ts';
import type { NewDebt } from '../debts.ts';
import type { NewEntry } from '../entry.ts';
import type { NewProfile } from '../onboarding.ts';

type Row = Record<string, unknown>;

/**
 * An in-memory stand-in for the user's own tables. `locked` rows are what Row Level Security hides from
 * a change after 48 hours: selects see them, updates and deletes don't (DBX1). Numbers come back as
 * numbers, as PostgREST sends numeric columns.
 */
function fakeDb(): Db & { tables: Record<string, Row[]>; locked: Set<string>; calls: string[] } {
  const tables: Record<string, Row[]> = {};
  const locked = new Set<string>();
  const calls: string[] = [];
  let next = 1;
  const t = (name: string) => (tables[name] ??= []);
  const matches = (r: Row, q: Query) =>
    Object.entries(q.eq ?? {}).every(([c, v]) => r[c] === v)
    && Object.entries(q.gte ?? {}).every(([c, v]) => String(r[c]) >= v)
    && Object.entries(q.lte ?? {}).every(([c, v]) => String(r[c]) <= v);
  const numeric = (row: object) => Object.fromEntries(Object.entries(row).map(([k, v]) =>
    [k, typeof v === 'string' && /^-?\d+\.\d+$/.test(v) ? Number(v) : v]));
  return {
    tables, locked, calls,
    async select(table, q = {}) {
      calls.push(`select ${table}`);
      const rows = t(table).filter((r) => matches(r, q));
      for (const [c, dir] of [...(q.order ?? [])].reverse()) {
        rows.sort((a, b) => (String(a[c]) < String(b[c]) ? -1 : String(a[c]) > String(b[c]) ? 1 : 0) * (dir === 'asc' ? 1 : -1));
      }
      return rows.map((r) => ({ ...r }));
    },
    async insert(table, row) {
      calls.push(`insert ${table}`);
      if (table === 'activity_days' && t(table).length > 0) throw new DbError('duplicate', 'That is already saved.');
      const r = { id: `r${next}`, created_at: `2026-07-0${Math.min(next, 9)}T04:00:00+00:00`, ...numeric(row) };
      next++;
      t(table).push(r);
      return { ...r };
    },
    async insertMany(table, rows) {
      calls.push(`insertMany ${table}`);
      const made = rows.map((row) => ({ id: `r${next++}`, created_at: '2026-07-01T04:00:00+00:00', ...numeric(row) }));
      t(table).push(...made);                                // one statement: all or none
      return made.map((r) => ({ ...r }));
    },
    async update(table, match, patch) {
      calls.push(`update ${table}`);
      const rows = t(table).filter((r) => matches(r, { eq: match }) && !locked.has(String(r.id)));
      for (const r of rows) Object.assign(r, numeric(patch));
      return rows.map((r) => ({ ...r }));
    },
    async remove(table, match) {
      calls.push(`remove ${table}`);
      const rows = t(table).filter((r) => matches(r, { eq: match }) && !locked.has(String(r.id)));
      tables[table] = t(table).filter((r) => !rows.includes(r));
      return rows;
    },
    async rpc(fn) {
      calls.push(`rpc ${fn}`);
      return null;
    },
  };
}

const entry = (over: Partial<NewEntry> = {}): NewEntry => ({
  occurred_on: '2026-07-15', direction: 'out', amount: '12.50', category: 'Food', is_essential: true, is_bnpl: false,
  on_credit: false, is_debt_payment: false, is_own_transfer: false, is_unexpected: false, note: null, source: 'typed', ...over,
});

test('a month runs from its first day to its last, leap years included', () => {
  assert.deepEqual(monthRange('2026-07-15'), ['2026-07-01', '2026-07-31']);
  assert.deepEqual(monthRange('2028-02-01'), ['2028-02-01', '2028-02-29']);
  assert.deepEqual(monthRange('2026-11-30'), ['2026-11-01', '2026-11-30']);
});

test('entries: the month\'s, newest first; the amount stays a decimal string; the phone sends when it saved (LV1, LV2)', async () => {
  const db = fakeDb();
  const store = liveEntries(db, () => new Date('2026-07-15T03:00:00Z'));
  assert.equal(store.local, false);
  const a = await store.add(entry());
  await store.add(entry({ occurred_on: '2026-07-20', amount: '1200.00', direction: 'in', category: 'Salary' }));
  await store.add(entry({ occurred_on: '2026-08-01' }));
  assert.equal(db.tables.transactions[0].client_logged_at, '2026-07-15T03:00:00.000Z');
  assert.equal(a.amount, '12.50');
  const july = await store.month('2026-07-01');
  assert.deepEqual(july.map((e) => [e.occurred_on, e.amount]), [['2026-07-20', '1200.00'], ['2026-07-15', '12.50']]);
  assert.ok(!('user_id' in july[0]) && !('client_logged_at' in july[0]));           // only the entry's own fields
});

test('entries past their 48 hours can\'t be changed or deleted, and the user is told why (LV3)', async () => {
  const db = fakeDb();
  const store = liveEntries(db);
  const a = await store.add(entry());
  db.locked.add(a.id);
  await assert.rejects(store.update(a.id, entry({ amount: '13.00' })), /48 hours/);
  await assert.rejects(store.remove(a.id), /48 hours/);
  db.locked.clear();
  assert.equal((await store.update(a.id, entry({ amount: '13.00' }))).amount, '13.00');
  await store.remove(a.id);
  assert.equal((await store.month('2026-07-01')).length, 0);
});

test('"No spending today" twice is fine; the database dates it (LV2)', async () => {
  const db = fakeDb();
  const store = liveEntries(db);
  await store.noSpend('2026-07-15');
  await store.noSpend('2026-07-15');
  assert.deepEqual(Object.keys(db.tables.activity_days[0]).filter((k) => k !== 'id' && k !== 'created_at'), ['client_logged_at']);
  db.tables.activity_days[0].day = '2026-07-15';
  db.tables.activity_days[0].no_spend = true;
  assert.deepEqual(await store.noSpendDays('2026-07-01'), ['2026-07-15']);
});

const checkin = (over: Partial<NewCheckin> = {}): NewCheckin => ({
  month: '2026-07-01', cash_bank_ewallet: '1250.00', epf_fleksibel: '0.00', others_emergency: '300.00', others: '0.00',
  epf_retirement: null, debt_total: '14500.00', net_income: '2800.00', bills_paid_on_time: true, ran_short: false, ...over,
});

test('a check-in: the first save adds the month, a second fixes it, and the month itself never changes', async () => {
  const db = fakeDb();
  const store = liveCheckins(db);
  const first = await store.save(checkin());
  assert.equal(first.cash_bank_ewallet, 1250);
  assert.equal(first.epf_retirement, null);
  const fixed = await store.save(checkin({ cash_bank_ewallet: '1300.00' }));
  assert.equal(fixed.cash_bank_ewallet, 1300);
  assert.equal(db.tables.monthly_checkins.length, 1);
  assert.deepEqual(db.calls.filter((c) => c.endsWith('monthly_checkins')),
                   ['select monthly_checkins', 'insert monthly_checkins', 'select monthly_checkins', 'update monthly_checkins']);
  db.locked.add(String(db.tables.monthly_checkins[0].id));
  await assert.rejects(store.save(checkin({ cash_bank_ewallet: '1.00' })), /48 hours/);
  assert.deepEqual((await store.list()).map((r) => r.month), ['2026-07-01']);
});

const debt = (over: Partial<NewDebt> = {}): NewDebt => ({
  kind: 'ptptn', label: null, monthly_payment: '150.00', outstanding: '14500.00', deducted_from_salary: false, annual_rate: '0.0100',
  ...over,
});

test('debts: add, change, pay off and delete; the rate comes back as a number (D-144)', async () => {
  const db = fakeDb();
  const store = liveDebts(db);
  const d = await store.add(debt());
  assert.equal(d.annual_rate, 0.01);
  assert.equal(d.monthly_payment, 150);
  assert.equal((await store.update(d.id, debt({ monthly_payment: '160.00' }))).monthly_payment, 160);
  assert.equal((await store.payOff(d.id, '2026-09-01')).ends_on, '2026-09-01');
  await store.remove(d.id);
  assert.deepEqual(await store.list(), []);
  await assert.rejects(store.update('nope', debt()), /no longer exists/);
});

test('a budget per category: setting it again changes it (BU1)', async () => {
  const db = fakeDb();
  const store = liveBudgets(db);
  await store.set({ category: 'Food', monthly_limit: '600.00' });
  await store.set({ category: 'Food', monthly_limit: '650.00' });
  await store.set({ category: 'Transport', monthly_limit: '200.00' });
  assert.deepEqual((await store.list()).map((b) => [b.category, b.monthly_limit]), [['Food', 650], ['Transport', 200]]);
  await store.remove('Food');
  assert.deepEqual((await store.list()).map((b) => b.category), ['Transport']);
});

const profile: NewProfile = {
  employment_type: 'employee', birth_year: 2002, lives_with_parents: false, family_support: true, festive_month: 3,
  vehicle: 'motorcycle', typical_monthly_costs: '1900.00', declared_income: '2800.00', onboarding_counted_money: '1250.00',
  onboarding_other_money: '0.00', onboarding_debt: '14860.00', savings_goal_monthly: '200.00', savings_goal_share: null,
  avatar: 3, skin_tone: null, glasses: false,
};

test('sign-up saves the profile, then its debts, and is safe to retry (LV4)', async () => {
  const db = fakeDb();
  const store = liveProfile(db, 'u1');
  assert.equal(await readProfile(db, 'u1'), null);
  const insert = db.insert.bind(db);
  db.insert = async (table, row) => insert(table, table === 'profiles' ? { ...row, user_id: 'u1' } : row);
  const insertMany = db.insertMany.bind(db);
  let failOnce = true;
  db.insertMany = async (table, rows) => {                   // the connection drops while the debts are saved
    if (failOnce) { failOnce = false; throw new DbError('network', 'No connection'); }
    return insertMany(table, rows);
  };
  const debts = [debt(), debt({ kind: 'bnpl', monthly_payment: '120.00', outstanding: '360.00', annual_rate: null })];
  await assert.rejects(store.create(profile, debts), /No connection/);
  assert.equal(db.tables.profiles.length, 1);
  assert.equal((db.tables.debts ?? []).length, 0);           // none of them, never half
  await store.create(profile, debts);                        // the retry
  assert.equal(db.tables.profiles.length, 1);
  assert.equal(db.tables.debts.length, 2);
  await store.create(profile, debts);                        // a third tap adds nothing
  assert.equal(db.tables.debts.length, 2);
  const p = await readProfile(db, 'u1');
  assert.deepEqual(p && [p.declared_income, p.avatar, p.skin_tone, p.glasses], [2800, 3, null, false]);
  await store.saveLook({ avatar: 5, tone: 2, glasses: true });
  const q = await readProfile(db, 'u1');
  assert.deepEqual(q && [q.avatar, q.skin_tone, q.glasses], [5, 2, true]);
});

// ------------------------------------------------------------------ the supabase-js adapter

type Result = { data: unknown; error: { message: string; code?: string } | null };
function fakeClient(result: Result | (() => never)) {
  const log: string[] = [];
  const builder: Record<string, unknown> = {};
  for (const m of ['select', 'insert', 'update', 'delete', 'eq', 'gte', 'lte', 'order', 'single']) {
    builder[m] = (...args: unknown[]) => { log.push(`${m}(${args.map((a) => JSON.stringify(a)).join(',')})`); return builder; };
  }
  builder.then = (ok: (r: Result) => unknown, bad: (e: unknown) => unknown) => {
    try {
      return Promise.resolve(typeof result === 'function' ? result() : result).then(ok, bad);
    } catch (e) {
      return Promise.reject(e).then(ok, bad);
    }
  };
  const client = {
    from: (table: string) => { log.push(`from(${table})`); return builder; },
    rpc: (fn: string) => { log.push(`rpc(${fn})`); return builder; },
  };
  return { client: client as never, log };
}

test('the adapter builds the query the store asked for', async () => {
  const { client, log } = fakeClient({ data: [{ id: 'a' }], error: null });
  const db = supabaseDb(client);
  assert.deepEqual(await db.select('transactions', { eq: { direction: 'out' }, gte: { occurred_on: '2026-07-01' },
                                                      lte: { occurred_on: '2026-07-31' }, order: [['occurred_on', 'desc']] }), [{ id: 'a' }]);
  assert.deepEqual(log, ['from(transactions)', 'select("*")', 'eq("direction","out")', 'gte("occurred_on","2026-07-01")',
                         'lte("occurred_on","2026-07-31")', 'order("occurred_on",{"ascending":false})']);
  log.length = 0;
  await db.update('debts', { id: 'x' }, { ends_on: '2026-09-01' });
  assert.deepEqual(log, ['from(debts)', 'update({"ends_on":"2026-09-01"})', 'eq("id","x")', 'select()']);
  log.length = 0;
  await db.insert('debts', { kind: 'car' });
  assert.deepEqual(log, ['from(debts)', 'insert({"kind":"car"})', 'select()', 'single()']);
  log.length = 0;
  await db.insertMany('debts', [{ kind: 'car' }, { kind: 'bnpl' }]);
  assert.deepEqual(log, ['from(debts)', 'insert([{"kind":"car"},{"kind":"bnpl"}])', 'select()']);   // one statement
  log.length = 0;
  assert.deepEqual(await db.insertMany('debts', []), []);
  assert.deepEqual(log, []);
});

test('database failures reach the user as sentences (DBX2)', async () => {
  const rule = supabaseDb(fakeClient({ data: null, error: { code: 'P0001', message: 'a month can be checked in from its last day until a week after it' } }).client);
  await assert.rejects(rule.insert('monthly_checkins', {}), /^Error: A month can be checked in from its last day until a week after it\.$/);
  const dup = supabaseDb(fakeClient({ data: null, error: { code: '23505', message: 'duplicate key value' } }).client);
  await assert.rejects(dup.insert('activity_days', {}), (e: unknown) => e instanceof DbError && e.problem === 'duplicate');
  const offline = supabaseDb(fakeClient(() => { throw new TypeError('Network request failed'); }).client);
  await assert.rejects(offline.select('debts'), /No connection/);
  assert.equal(dbError({ code: '42501', message: 'new row violates row-level security policy' }).problem, 'denied');
  assert.equal(dbError({ code: '23514', message: 'violates check constraint' }).problem, 'invalid');
});
