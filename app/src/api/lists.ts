/**
 * Where the debts list and the budgets go (D-121). With Supabase these are public.debts and
 * public.budgets, read and written as the user (RLS, rule 8; the API reads debts for the band, so a
 * change there moves it). Until the project exists, sample data mode keeps them on the phone for the
 * session, per persona, seeded with the persona's own debts, and says so. The screens only see these
 * interfaces.
 */
import { myDate } from '../lib/checkin.ts';
import type { BudgetRow, NewBudget } from '../lib/budgets.ts';
import type { DebtRow, NewDebt } from '../lib/debts.ts';

export interface DebtStore {
  /** Every debt the user has told FAST about by now, paid off ones included, oldest first. */
  list(): Promise<DebtRow[]>;
  add(d: NewDebt): Promise<DebtRow>;
  update(id: string, d: NewDebt): Promise<DebtRow>;
  /** Paid off on `day`: the row stays, with its end date, so earlier months still count it (DB3). */
  payOff(id: string, day: string): Promise<DebtRow>;
  /** For one added by mistake. */
  remove(id: string): Promise<void>;
  readonly local: boolean;
}

export interface BudgetStore {
  list(): Promise<BudgetRow[]>;
  /** A category's limit: new, or a change to the one it has (one per category, BU1). */
  set(b: NewBudget): Promise<BudgetRow>;
  remove(category: string): Promise<void>;
  readonly local: boolean;
}

const num = (s: string) => Number(s);
const rate = (s: string | null) => (s === null ? null : Number(s));
const today = (now: () => Date) => myDate(now().toISOString());

/** In memory, seeded with the persona's own debts. `now` is the user's clock (a persona's study date
 * at noon), so a debt added or paid off later is not there yet when time travel goes back. */
export function memoryDebts(seed: Omit<DebtRow, 'id'>[], now: () => Date): DebtStore {
  const rows: DebtRow[] = seed.map((d, i) => ({ ...d, id: `seed-${i + 1}` }));
  let next = 1;
  const find = (id: string) => {
    const i = rows.findIndex((r) => r.id === id);
    if (i < 0) throw new Error('That debt no longer exists');
    return i;
  };
  return {
    local: true,
    async list() {
      const day = today(now);
      return rows.filter((r) => myDate(r.created_at) <= day)
        .map((r) => (r.ends_on && r.ends_on > day ? { ...r, ends_on: null } : r))   // paid off later: not yet
        .sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id));
    },
    async add(d) {
      const row: DebtRow = { ...d, id: `new-${next++}`, monthly_payment: num(d.monthly_payment), outstanding: num(d.outstanding),
                             annual_rate: rate(d.annual_rate), starts_on: null, ends_on: null, created_at: now().toISOString() };
      rows.push(row);
      return row;
    },
    async update(id, d) {
      const i = find(id);
      rows[i] = { ...rows[i], ...d, monthly_payment: num(d.monthly_payment), outstanding: num(d.outstanding),
                  annual_rate: rate(d.annual_rate) };
      return rows[i];
    },
    async payOff(id, day) {
      const i = find(id);
      rows[i] = { ...rows[i], ends_on: day };
      return rows[i];
    },
    async remove(id) {
      rows.splice(find(id), 1);
    },
  };
}

export function memoryBudgets(): BudgetStore {
  const rows: BudgetRow[] = [];
  let next = 1;
  return {
    local: true,
    async list() {
      return [...rows];
    },
    async set(b) {
      const i = rows.findIndex((r) => r.category === b.category);
      const row: BudgetRow = { id: i >= 0 ? rows[i].id : `b-${next++}`, category: b.category, monthly_limit: num(b.monthly_limit) };
      if (i >= 0) rows[i] = row;
      else rows.push(row);
      return row;
    },
    async remove(category) {
      const i = rows.findIndex((r) => r.category === category);
      if (i >= 0) rows.splice(i, 1);
    },
  };
}
