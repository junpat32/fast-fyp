/**
 * The Add screen's rules (D-112): what a typed entry becomes in public.transactions. Categories and
 * their essential flag come from shared/categories.json, the list the personas' data uses, so the
 * engine reads a typed entry exactly like the synthetic data (rule 5). Money stays a decimal string
 * from the keyboard to the database, never a float (rule 9). Pure TypeScript, tested by Node.
 */
export type Category = {
  key: string; label: string; group?: string; essential?: boolean; debt_payment?: boolean; own_transfer?: boolean;
  words?: string[];                                   // what the quick-add box matches (D-126)
};
export type Categories = { groups: Record<string, string>; out: Category[]; in: Category[] };
export type Direction = 'out' | 'in';
export type PaidBy = 'now' | 'card' | 'bnpl';
export type Form = {
  direction: Direction; amount: string; category: string; paidBy: PaidBy; unexpected: boolean; day: string; note: string;
};
export type NewEntry = {
  occurred_on: string; direction: Direction; amount: string; category: string;
  is_essential: boolean; is_bnpl: boolean; on_credit: boolean; is_debt_payment: boolean;
  is_own_transfer: boolean; is_unexpected: boolean; note: string | null; source: 'typed';
};
export type Errors = Partial<Record<'amount' | 'category' | 'day', string>>;

export const MAX_AMOUNT_CENTS = 100_000_000;     // RM1,000,000: a typo guard, far below numeric(12,2)
export const EDIT_HOURS = 48;                    // the database's policy (supabase/migrations, C3); tested
export const NOTE_MAX = 120;                     // transactions.note check

/** "12", "12.5", "RM 1,200.50" -> "12.00", "12.50", "1200.50"; whole sen only, more than zero. */
export function parseAmount(text: string): { ok: true; value: string } | { ok: false; error: string } {
  const t = text.replace(/^\s*RM\s*/i, '').replace(/[\s,]/g, '');
  if (t === '') return { ok: false, error: 'Type an amount' };
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(t);
  if (!m) return { ok: false, error: 'Use numbers only, like 12.50' };
  const cents = BigInt(m[1]) * 100n + BigInt((m[2] ?? '').padEnd(2, '0'));
  if (cents === 0n) return { ok: false, error: 'The amount must be more than RM0' };
  if (cents > BigInt(MAX_AMOUNT_CENTS)) return { ok: false, error: "That's over RM1,000,000: check the amount" };
  return { ok: true, value: centsText(cents) };
}

function centsText(cents: bigint): string {
  const s = cents.toString().padStart(3, '0');
  return `${s.slice(0, -2)}.${s.slice(-2)}`;
}

/** Sum of decimal strings without floating point: "12.50" + "0.10" -> "12.60". */
export function sumAmounts(amounts: string[]): string {
  let total = 0n;
  for (const a of amounts) {
    const [whole, frac = ''] = a.split('.');
    total += BigInt(whole) * 100n + BigInt(frac.padEnd(2, '0').slice(0, 2));
  }
  return centsText(total);
}

/** "1200.50" -> "RM1,200.50" (en-MY grouping). */
export function rmText(amount: string): string {
  const [whole, frac] = amount.split('.');
  return `RM${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${frac}`;
}

/**
 * Rule 11: sensitive text is removed on the phone before upload. A typed note shouldn't hold any,
 * but a pasted one might: TAC/OTP lines are dropped, IC numbers removed, and account or card numbers
 * (8+ digits, spaces or dashes allowed) masked to the last 4.
 */
export function redactNote(text: string): string {
  const kept = text.split(/\r?\n/).filter((l) => !/\b(TAC|OTP)\b/i.test(l)).join(' ');
  return kept
    .replace(/\b\d{6}-?\d{2}-?\d{4}\b/g, '[IC removed]')
    .replace(/\b\d(?:[ -]?\d){7,}\b/g, (run) => `••••${run.replace(/\D/g, '').slice(-4)}`)
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, NOTE_MAX);
}

const DAY_MS = 86_400_000;
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);
const utc = (day: string) => Date.parse(`${day}T00:00:00Z`);

/** The earliest day the form offers: the 1st of the previous month (older entries are rare and
 * would land in months already checked in). */
export function earliestDay(today: string): string {
  const [y, m] = today.split('-').map(Number);
  return iso(Date.UTC(m === 1 ? y - 1 : y, m === 1 ? 11 : m - 2, 1));
}

/** One day earlier or later, kept between earliestDay and today. */
export function stepDay(day: string, by: -1 | 1, today: string): string {
  const next = iso(utc(day) + by * DAY_MS);
  return next > today ? today : next < earliestDay(today) ? earliestDay(today) : next;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-06-28" -> "28 Jun". */
export function dayShort(day: string): string {
  const [, m, d] = day.split('-').map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}

/** "Today, 1 Jul" / "Yesterday, 30 Jun" / "28 Jun". */
export function dayLabel(day: string, today: string): string {
  const short = dayShort(day);
  if (day === today) return `Today, ${short}`;
  if (day === iso(utc(today) - DAY_MS)) return `Yesterday, ${short}`;
  return short;
}

/** The row to insert, or what to fix. The category decides the kind: a debt payment or a move
 * between one's own pockets carries none of a purchase's flags; money in carries none at all. */
export function buildEntry(form: Form, cats: Categories, today: string):
    { ok: true; entry: NewEntry } | { ok: false; errors: Errors } {
  const errors: Errors = {};
  const amount = parseAmount(form.amount);
  if (!amount.ok) errors.amount = amount.error;
  const cat = cats[form.direction].find((c) => c.key === form.category);
  if (!cat) errors.category = 'Choose a category';
  if (form.day > today) errors.day = "The day can't be after today";
  else if (form.day < earliestDay(today)) errors.day = 'Choose a day this month or last month';
  if (!amount.ok || !cat || errors.day) return { ok: false, errors };
  const purchase = form.direction === 'out' && !cat.debt_payment && !cat.own_transfer;
  const note = redactNote(form.note);
  return {
    ok: true,
    entry: {
      occurred_on: form.day, direction: form.direction, amount: amount.value, category: cat.key,
      is_essential: purchase && Boolean(cat.essential),
      is_bnpl: purchase && form.paidBy === 'bnpl',
      on_credit: purchase && form.paidBy === 'card',
      is_debt_payment: form.direction === 'out' && Boolean(cat.debt_payment),
      is_own_transfer: Boolean(cat.own_transfer),
      is_unexpected: purchase && form.unexpected,
      note: note === '' ? null : note,
      source: 'typed',
    },
  };
}

/** Which extra questions the form shows for a category: how it was paid, and "unexpected". */
export function asksPurchaseQuestions(direction: Direction, category: Category | undefined): boolean {
  return direction === 'out' && !!category && !category.debt_payment && !category.own_transfer;
}

/** Entries can be edited or deleted for EDIT_HOURS after they arrive, by the user's clock. */
export function canEdit(createdAt: string, now: Date): boolean {
  return now.getTime() - Date.parse(createdAt) < EDIT_HOURS * 3_600_000;
}

/** Money out and in for a list of entries; moves between one's own pockets are neither. */
export function monthTotals(entries: Pick<NewEntry, 'direction' | 'amount' | 'is_own_transfer'>[]): { out: string; in: string } {
  const real = entries.filter((e) => !e.is_own_transfer);
  return { out: sumAmounts(real.filter((e) => e.direction === 'out').map((e) => e.amount)),
           in: sumAmounts(real.filter((e) => e.direction === 'in').map((e) => e.amount)) };
}
