/**
 * The live stores (D-145): the same interfaces as the sample data stores (entries.ts, checkins.ts,
 * lists.ts, profile.ts), over the user's own Supabase rows. Screens don't know which they have.
 *
 * Invariants
 *   LV1  amounts go up as decimal strings and are never rounded on the phone (rule 9); they come back
 *        as numbers, except an entry's amount, which the Add screen keeps as a decimal string
 *   LV2  the database dates arrivals (created_at, a persona's study date, a "No spending today" day);
 *        the phone sends only when it saved the row (client_logged_at), which the database checks
 *   LV3  a change that matches no row is refused with the reason the user can act on: entries and
 *        check-ins can be changed for 48 hours (C3); the database's own rule sentences pass through
 *   LV4  sign-up is safe to retry: an existing profile is not inserted again, and the debts go in one
 *        statement (all or none) only while the account has none, so a retry never doubles or drops one
 */
import type { CheckinRow, NewCheckin } from '../lib/checkin.ts';
import type { BudgetRow, NewBudget } from '../lib/budgets.ts';
import type { Look } from '../lib/character.ts';
import type { DebtRow, NewDebt } from '../lib/debts.ts';
import type { NewEntry } from '../lib/entry.ts';
import type { NewProfile } from '../lib/onboarding.ts';
import type { CheckinStore } from './checkins.ts';
import { DbError, type Db } from './db.ts';
import type { Entry, EntryStore } from './entries.ts';
import type { BudgetStore, DebtStore } from './lists.ts';
import type { ProfileStore } from './profile.ts';

type Row = Record<string, unknown>;
const num = (v: unknown) => Number(v);
const numOrNull = (v: unknown) => (v === null || v === undefined ? null : Number(v));
const str = (v: unknown) => String(v);

/** "2026-07-15" -> ["2026-07-01", "2026-07-31"]. */
export function monthRange(monthIso: string): [string, string] {
  const [y, m] = monthIso.slice(0, 7).split('-').map(Number);
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const mm = String(m).padStart(2, '0');
  return [`${y}-${mm}-01`, `${y}-${mm}-${String(last).padStart(2, '0')}`];
}

const ENTRY_WINDOW = 'Entries can be changed for 48 hours after you add them.';

function entryOf(r: Row): Entry {
  return {
    id: str(r.id), created_at: str(r.created_at), occurred_on: str(r.occurred_on),
    direction: r.direction as Entry['direction'], amount: num(r.amount).toFixed(2), category: str(r.category),
    is_essential: !!r.is_essential, is_bnpl: !!r.is_bnpl, on_credit: !!r.on_credit, is_debt_payment: !!r.is_debt_payment,
    is_own_transfer: !!r.is_own_transfer, is_unexpected: !!r.is_unexpected,
    note: r.note === null || r.note === undefined ? null : str(r.note), source: 'typed',
  };
}

export function liveEntries(db: Db, clock: () => Date = () => new Date()): EntryStore {
  return {
    local: false,
    async month(monthIso) {
      const [first, last] = monthRange(monthIso);
      const rows = await db.select('transactions', {
        gte: { occurred_on: first }, lte: { occurred_on: last },
        order: [['occurred_on', 'desc'], ['created_at', 'desc'], ['id', 'desc']],
      });
      return rows.map(entryOf);
    },
    async add(e: NewEntry) {
      return entryOf(await db.insert('transactions', { ...e, client_logged_at: clock().toISOString() }));
    },
    async update(id, e) {
      const rows = await db.update('transactions', { id }, e);
      if (rows.length === 0) throw new DbError('denied', ENTRY_WINDOW);
      return entryOf(rows[0]);
    },
    async remove(id) {
      const rows = await db.remove('transactions', { id });
      if (rows.length === 0) throw new DbError('denied', ENTRY_WINDOW);
    },
    async noSpend() {
      try {
        await db.insert('activity_days', { client_logged_at: clock().toISOString() });   // the database dates it
      } catch (e) {
        if (!(e instanceof DbError && e.problem === 'duplicate')) throw e;                 // already marked today
      }
    },
    async noSpendDays(monthIso) {
      const [first, last] = monthRange(monthIso);
      const rows = await db.select('activity_days', { eq: { no_spend: true }, gte: { day: first }, lte: { day: last },
                                                      order: [['day', 'asc']] });
      return rows.map((r) => str(r.day));
    },
  };
}

function checkinOf(r: Row): CheckinRow {
  return {
    month: str(r.month), created_at: str(r.created_at),
    cash_bank_ewallet: num(r.cash_bank_ewallet), epf_fleksibel: num(r.epf_fleksibel),
    others_emergency: num(r.others_emergency), others: num(r.others), epf_retirement: numOrNull(r.epf_retirement),
    debt_total: num(r.debt_total), net_income: numOrNull(r.net_income),
    bills_paid_on_time: !!r.bills_paid_on_time, ran_short: !!r.ran_short,
    after_month_net: num(r.after_month_net), after_month_debt: num(r.after_month_debt),
  };
}

export function liveCheckins(db: Db): CheckinStore {
  return {
    local: false,
    async list() {
      return (await db.select('monthly_checkins', { order: [['month', 'asc']] })).map(checkinOf);
    },
    async save(r: NewCheckin) {
      const old = await db.select('monthly_checkins', { eq: { month: r.month } });
      if (old.length === 0) return checkinOf(await db.insert('monthly_checkins', r));
      const { month: _month, ...values } = r;                        // the month itself never changes
      const rows = await db.update('monthly_checkins', { month: r.month }, values);
      if (rows.length === 0) throw new DbError('denied', 'A check-in can be changed for 48 hours after you make it.');
      return checkinOf(rows[0]);
    },
  };
}

function debtOf(r: Row): DebtRow {
  return {
    id: str(r.id), kind: r.kind as DebtRow['kind'], label: r.label === null || r.label === undefined ? null : str(r.label),
    monthly_payment: num(r.monthly_payment), outstanding: num(r.outstanding), deducted_from_salary: !!r.deducted_from_salary,
    annual_rate: numOrNull(r.annual_rate), starts_on: (r.starts_on as string | null) ?? null,
    ends_on: (r.ends_on as string | null) ?? null, created_at: str(r.created_at),
  };
}

async function one(rows: Promise<Row[]>, gone = 'That debt no longer exists'): Promise<Row> {
  const r = await rows;
  if (r.length === 0) throw new DbError('denied', gone);
  return r[0];
}

export function liveDebts(db: Db): DebtStore {
  return {
    local: false,
    async list() {
      return (await db.select('debts', { order: [['created_at', 'asc'], ['id', 'asc']] })).map(debtOf);
    },
    async add(d: NewDebt) {
      return debtOf(await db.insert('debts', d));
    },
    async update(id, d) {
      return debtOf(await one(db.update('debts', { id }, d)));
    },
    async payOff(id, day) {
      return debtOf(await one(db.update('debts', { id }, { ends_on: day })));
    },
    async remove(id) {
      await one(db.remove('debts', { id }));
    },
  };
}

export function liveBudgets(db: Db): BudgetStore {
  const budgetOf = (r: Row): BudgetRow => ({ id: str(r.id), category: str(r.category), monthly_limit: num(r.monthly_limit) });
  return {
    local: false,
    async list() {
      return (await db.select('budgets', { order: [['category', 'asc']] })).map(budgetOf);
    },
    async set(b: NewBudget) {
      const rows = await db.update('budgets', { category: b.category }, { monthly_limit: b.monthly_limit });
      return budgetOf(rows[0] ?? await db.insert('budgets', b));         // one per category (BU1)
    },
    async remove(category) {
      await db.remove('budgets', { category });
    },
  };
}

export type ProfileFacts = { created_at: string; declared_income: number; avatar: number | null; skin_tone: number | null;
                             glasses: boolean };

/** The signed-in user's profile, or null before sign-up is finished. */
export async function readProfile(db: Db, userId: string): Promise<ProfileFacts | null> {
  const [r] = await db.select('profiles', { eq: { user_id: userId } });
  if (!r) return null;
  return { created_at: str(r.created_at), declared_income: num(r.declared_income), avatar: numOrNull(r.avatar),
           skin_tone: numOrNull(r.skin_tone), glasses: !!r.glasses };
}

export function liveProfile(db: Db, userId: string): ProfileStore {
  return {
    local: false,
    async create(profile: NewProfile, debts: NewDebt[]) {
      if (!(await readProfile(db, userId))) await db.insert('profiles', profile);          // LV4
      if ((await db.select('debts')).length === 0) await db.insertMany('debts', debts);
    },
    async saveLook(look: Look) {
      await one(db.update('profiles', { user_id: userId }, { avatar: look.avatar, skin_tone: look.tone, glasses: look.glasses }),
                'Finish setting up FAST first');
    },
  };
}
