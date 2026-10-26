/**
 * The few database calls the live stores make (D-145), behind a small interface so the stores can be
 * tested in Node with an in-memory fake, and one adapter over supabase-js for the app. Every call runs
 * as the signed-in user: Row Level Security limits it to the user's own rows (rule 8), and the
 * database's triggers set arrival times, the persona clock and the check-in sums (C3, D-77).
 *
 * Invariants
 *   DBX1  a write that matches no row is an error, never silent: Row Level Security hides rows the
 *         user may no longer change (the 48-hour edit window), so "nothing changed" means "not allowed"
 *   DBX2  the database's own sentences (raise exception in a trigger) reach the user as they are;
 *         other failures become plain sentences, never codes
 */
import type { SupabaseClient } from '@supabase/supabase-js';

type Value = string | number | boolean | null;
export type Query = {
  eq?: Record<string, Value>;
  gte?: Record<string, string>;
  lte?: Record<string, string>;
  order?: [string, 'asc' | 'desc'][];
};

export interface Db {
  select(table: string, q?: Query): Promise<Record<string, unknown>[]>;
  insert(table: string, row: object): Promise<Record<string, unknown>>;
  /** Several rows in one statement: all saved, or none. */
  insertMany(table: string, rows: object[]): Promise<Record<string, unknown>[]>;
  update(table: string, match: Record<string, Value>, patch: object): Promise<Record<string, unknown>[]>;
  remove(table: string, match: Record<string, Value>): Promise<Record<string, unknown>[]>;
  rpc(fn: string, args?: object): Promise<unknown>;
}

export type DbProblem = 'duplicate' | 'denied' | 'rule' | 'invalid' | 'network' | 'other';
export class DbError extends Error {
  problem: DbProblem;
  constructor(problem: DbProblem, message: string) {
    super(message);
    this.problem = problem;
  }
}

/** A PostgREST or network failure as a DbError with a readable message (DBX2). */
export function dbError(e: { message?: string; code?: string } | null | undefined): DbError {
  const message = e?.message ?? 'something went wrong';
  const code = e?.code ?? '';
  if (/network request failed|failed to fetch|fetch failed|load failed/i.test(message)) {
    return new DbError('network', 'No connection: check your internet and try again.');
  }
  if (code === '23505') return new DbError('duplicate', 'That is already saved.');
  if (code === '42501') return new DbError('denied', 'FAST could not save that for this account.');
  if (code === 'P0001') return new DbError('rule', message.charAt(0).toUpperCase() + message.slice(1).replace(/\.?$/, '.'));
  if (code.startsWith('22') || code.startsWith('23')) return new DbError('invalid', 'One of those values is not allowed.');
  return new DbError('other', `FAST could not reach your data (${message}).`);
}

/** The interface over supabase-js. */
export function supabaseDb(client: SupabaseClient): Db {
  const run = async <T>(p: PromiseLike<{ data: T | null; error: { message: string; code?: string } | null }>): Promise<T> => {
    let res: { data: T | null; error: { message: string; code?: string } | null };
    try {
      res = await p;
    } catch (e) {
      throw dbError({ message: e instanceof Error ? e.message : String(e) });
    }
    if (res.error) throw dbError(res.error);
    return res.data as T;
  };
  const matching = <B extends { eq: (c: string, v: Value) => B }>(b: B, match: Record<string, Value>) =>
    Object.entries(match).reduce((q, [c, v]) => q.eq(c, v), b);
  return {
    async select(table, q = {}) {
      let b = client.from(table).select('*');
      for (const [c, v] of Object.entries(q.eq ?? {})) b = b.eq(c, v);
      for (const [c, v] of Object.entries(q.gte ?? {})) b = b.gte(c, v);
      for (const [c, v] of Object.entries(q.lte ?? {})) b = b.lte(c, v);
      for (const [c, dir] of q.order ?? []) b = b.order(c, { ascending: dir === 'asc' });
      return (await run(b)) ?? [];
    },
    async insert(table, row) {
      return run(client.from(table).insert(row).select().single());
    },
    async insertMany(table, rows) {
      if (rows.length === 0) return [];
      return (await run(client.from(table).insert(rows).select())) ?? [];
    },
    async update(table, match, patch) {
      return (await run(matching(client.from(table).update(patch), match).select())) ?? [];
    },
    async remove(table, match) {
      return (await run(matching(client.from(table).delete(), match).select())) ?? [];
    },
    async rpc(fn, args) {
      return run(client.rpc(fn, args));
    },
  };
}
