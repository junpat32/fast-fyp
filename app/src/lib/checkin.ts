/**
 * The monthly check-in (game_design §2, §3a; D-75, D-77; D-118): which month is open, what the form
 * becomes in public.monthly_checkins, and what the month looks like at its end. Pure TypeScript,
 * tested by Node. The database is the judge (check_checkin_window, freeze_logged_sums, the 48-hour
 * edit policy); these rules let the screen say the same thing before it asks.
 *
 *   window   a month's check-in opens on its last day and closes 7 days later, for months since sign-up
 *   values   today's balances in the money sections and what is owed today; the server adds what was
 *            logged after the month ended, so the game uses the month's END (D-77)
 *   money    decimal strings from keyboard to database, never floats (rule 9)
 */
export type CheckinRow = {
  month: string; created_at: string;
  cash_bank_ewallet: number; epf_fleksibel: number; others_emergency: number; others: number;
  epf_retirement: number | null; debt_total: number; net_income: number | null;
  bills_paid_on_time: boolean; ran_short: boolean;
  after_month_net: number; after_month_debt: number;           // set by the server (D-77)
};
export type CheckinForm = {
  cash: string; epfFleksibel: string; emergency: string; others: string; epfRetirement: string;
  debt: string; income: string; bills: boolean | null; ranShort: boolean | null;
};
export type NewCheckin = {
  month: string; cash_bank_ewallet: string; epf_fleksibel: string; others_emergency: string; others: string;
  epf_retirement: string | null; debt_total: string; net_income: string | null;
  bills_paid_on_time: boolean; ran_short: boolean;
};
export type CheckinErrors = Partial<Record<keyof CheckinForm, string>>;

export const CHECKIN_EDIT_HOURS = 48;                 // the database's policy (C3); tested against it
export const WINDOW_DAYS = 7;                         // check_checkin_window (D-77)
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December'];

const utc = (day: string) => Date.parse(`${day}T00:00:00Z`);
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);
const firstOf = (day: string) => `${day.slice(0, 7)}-01`;

/** A timestamp's day in Malaysia (UTC+8), as the database counts days ("at time zone 'Asia/Kuala_Lumpur'"). */
export function myDate(timestamp: string): string {
  return iso(Date.parse(timestamp) + 8 * 3_600_000);
}

/** "2026-06-01" -> "2026-06-30". */
export function lastDay(month: string): string {
  const [y, m] = month.split('-').map(Number);
  return iso(Date.UTC(y, m, 0));
}

function previousMonth(month: string): string {
  const [y, m] = month.split('-').map(Number);
  return iso(Date.UTC(m === 1 ? y - 1 : y, m === 1 ? 11 : m - 2, 1));
}

/** The month whose check-in is open today (its last day to 7 days after), not before sign-up; or null. */
export function openMonth(today: string, signedUp: string): string | null {
  const joined = firstOf(signedUp);
  const prev = previousMonth(firstOf(today));
  const prevClose = iso(utc(lastDay(prev)) + WINDOW_DAYS * 86_400_000);
  if (today <= prevClose && prev >= joined) return prev;
  const here = firstOf(today);
  return today === lastDay(here) && here >= joined ? here : null;
}

/** When the next check-in opens: this month's last day. */
export function nextOpens(today: string): string {
  return lastDay(firstOf(today));
}

/** The last day of a month's window. */
export function closes(month: string): string {
  return iso(utc(lastDay(month)) + WINDOW_DAYS * 86_400_000);
}

export function monthWord(month: string): string {
  return MONTHS[Number(month.slice(5, 7)) - 1];
}

/** A balance: "", "0" and up to the sen; blank means zero unless the field is required. */
export function parseBalance(text: string, required: boolean): { ok: true; value: string } | { ok: false; error: string } {
  const t = text.replace(/^\s*RM\s*/i, '').replace(/[\s,]/g, '');
  if (t === '') return required ? { ok: false, error: 'Type an amount (0 if none)' } : { ok: true, value: '0.00' };
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(t);
  if (!m) return { ok: false, error: 'Use numbers only, like 1250.50' };
  if (Number(m[1]) > 99_999_999) return { ok: false, error: 'Check the amount' };
  return { ok: true, value: `${BigInt(m[1])}.${(m[2] ?? '').padEnd(2, '0')}` };
}

/** The row to save for `month`, or what to fix. */
export function buildCheckin(form: CheckinForm, month: string): { ok: true; row: NewCheckin } | { ok: false; errors: CheckinErrors } {
  const errors: CheckinErrors = {};
  const field = (k: keyof CheckinForm, text: string, required: boolean) => {
    const r = parseBalance(text, required);
    if (!r.ok) errors[k] = r.error;
    return r.ok ? r.value : '0.00';
  };
  const cash = field('cash', form.cash, true);
  const debt = field('debt', form.debt, true);
  const epf = field('epfFleksibel', form.epfFleksibel, false);
  const emergency = field('emergency', form.emergency, false);
  const others = field('others', form.others, false);
  const retirement = form.epfRetirement.trim() === '' ? null : field('epfRetirement', form.epfRetirement, false);
  const income = form.income.trim() === '' ? null : field('income', form.income, false);
  if (form.bills === null) errors.bills = 'Choose yes or no';
  if (form.ranShort === null) errors.ranShort = 'Choose yes or no';
  if (Object.keys(errors).length) return { ok: false, errors };
  return {
    ok: true,
    row: { month, cash_bank_ewallet: cash, epf_fleksibel: epf, others_emergency: emergency, others,
           epf_retirement: retirement, debt_total: debt, net_income: income,
           bills_paid_on_time: form.bills!, ran_short: form.ranShort! },
  };
}

/** A saved check-in back in the form (to fix it within 48 hours). */
export function formOf(row: CheckinRow): CheckinForm {
  const s = (n: number | null) => (n === null ? '' : String(n));
  return { cash: s(row.cash_bank_ewallet), epfFleksibel: s(row.epf_fleksibel), emergency: s(row.others_emergency),
           others: s(row.others), epfRetirement: s(row.epf_retirement), debt: s(row.debt_total), income: s(row.net_income),
           bills: row.bills_paid_on_time, ranShort: row.ran_short };
}

export function canEditCheckin(createdAt: string, now: Date): boolean {
  return now.getTime() - Date.parse(createdAt) < CHECKIN_EDIT_HOURS * 3_600_000;
}

/** The money as at the month's end, as the game counts it (api/money.py, D-77): counted money is
 * cash, bank and e-wallets minus what came in net after the month ended, plus EPF Fleksibel and
 * emergency savings; what is owed, minus what was added since. */
export function monthEnd(row: CheckinRow): { counted: number; owed: number } {
  return {
    counted: Math.max(0, row.cash_bank_ewallet - row.after_month_net) + row.epf_fleksibel + row.others_emergency,
    owed: Math.max(0, row.debt_total - row.after_month_debt),
  };
}
