/**
 * Where the Add screen's entries go (D-112). With Supabase this is public.transactions and
 * public.activity_days, as the user (RLS, rule 8); until the project exists, sample data mode keeps
 * them on the phone for the session, per persona, and says so. The screens only see this interface.
 */
import type { NewEntry } from '../lib/entry.ts';

export type Entry = NewEntry & { id: string; created_at: string };

export interface EntryStore {
  /** Entries dated in the month of `monthIso` ("2026-07-01"), newest day first, then newest added. */
  month(monthIso: string): Promise<Entry[]>;
  add(e: NewEntry): Promise<Entry>;
  update(id: string, e: NewEntry): Promise<Entry>;
  remove(id: string): Promise<void>;
  /** "No spending today" (activity_days.no_spend; the database dates it by the user's clock). */
  noSpend(day: string): Promise<void>;
  noSpendDays(monthIso: string): Promise<string[]>;
  /** True when entries live only on this phone (sample data mode). */
  readonly local: boolean;
}

/** In memory: sample data mode, and tests. `now` is the clock that dates each entry's arrival. */
export function memoryStore(now: () => Date = () => new Date()): EntryStore {
  const rows: Entry[] = [];
  const quiet = new Set<string>();
  let next = 1;
  const inMonth = (day: string, monthIso: string) => day.slice(0, 7) === monthIso.slice(0, 7);
  return {
    local: true,
    async month(monthIso) {
      return rows.filter((r) => inMonth(r.occurred_on, monthIso))
        .sort((a, b) => b.occurred_on.localeCompare(a.occurred_on) || b.created_at.localeCompare(a.created_at)
                        || Number(b.id) - Number(a.id));
    },
    async add(e) {
      const row = { ...e, id: String(next++), created_at: now().toISOString() };
      rows.push(row);
      return row;
    },
    async update(id, e) {
      const i = rows.findIndex((r) => r.id === id);
      if (i < 0) throw new Error('That entry no longer exists');
      rows[i] = { ...e, id, created_at: rows[i].created_at };     // the arrival time never changes
      return rows[i];
    },
    async remove(id) {
      const i = rows.findIndex((r) => r.id === id);
      if (i >= 0) rows.splice(i, 1);
    },
    async noSpend(day) {
      quiet.add(day);
    },
    async noSpendDays(monthIso) {
      return [...quiet].filter((d) => inMonth(d, monthIso)).sort();
    },
  };
}
