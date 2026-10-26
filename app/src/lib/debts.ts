/**
 * The debts list (docs/app_plan.md §3; D-121): what the user owes, each with its monthly payment. The
 * payments are the debt commitments in the DSR (CLAUDE.md rule 6: monthly debt payments ÷ net
 * monthly income; api/money.py), so this list moves the band. A payment taken from salary (potongan
 * gaji) is added back to income there, since the take-home pay already had it removed. Pure
 * TypeScript, tested by Node.
 *
 * Invariants
 *   DB1  the database's own rules (public.debts): its seven kinds, a label of at most 40 characters,
 *        amounts of at least zero as decimal strings (rule 9), never floats on the way in
 *   DB2  a label is redacted on the phone before it is saved (rule 11): no IC numbers, card or account
 *        numbers only by their last 4 digits
 *   DB3  a paid-off debt keeps its row with an end date (ends_on), so months before it still count it
 *        (api/money.py _active); deleting is for one added by mistake
 *   DB4  BNPL here is only for plans from before the user started: a BNPL buy logged on the Add screen
 *        is counted from the purchase (a third of it for 3 months), and listing it too would count it twice
 *   DB5  the interest rate is optional (D-144): typed as a yearly percentage, saved as a fraction with 4
 *        decimals as a string ("18" -> "0.1800"), null when left empty; FAST never fills one in
 */
import { parseAmount, redactNote, sumAmounts } from './entry.ts';

export type DebtKind = 'ptptn' | 'car' | 'housing' | 'personal' | 'credit_card' | 'bnpl' | 'other';
export const DEBT_KINDS: { kind: DebtKind; label: string; hint: string }[] = [
  { kind: 'ptptn', label: 'PTPTN', hint: 'Your study loan. Not paying yet? Put 0 for the monthly payment.' },
  { kind: 'car', label: 'Car loan', hint: 'Hire purchase: the monthly instalment and what is left to pay.' },
  { kind: 'housing', label: 'Home loan', hint: 'The monthly instalment and what is left to pay.' },
  { kind: 'personal', label: 'Personal loan', hint: 'From a bank or a koperasi.' },
  { kind: 'credit_card', label: 'Credit card', hint: 'What you pay each month (at least the minimum) and the balance owed.' },
  { kind: 'bnpl', label: 'Buy Now Pay Later', hint: 'Only plans from before you started using FAST: a BNPL buy you log on Add is counted for you.' },
  { kind: 'other', label: 'Other', hint: 'A motorbike loan, money owed to family, anything else you pay back monthly.' },
];
export const LABEL_MAX = 40;                              // debts.label check
const FROM_SALARY: DebtKind[] = ['ptptn', 'personal', 'housing', 'other'];

export type DebtRow = {
  id: string; kind: DebtKind; label: string | null; monthly_payment: number; outstanding: number;
  deducted_from_salary: boolean; starts_on: string | null; ends_on: string | null; created_at: string;
  annual_rate?: number | null;                            // the database always sends it; personas' seeds may not
};
export type NewDebt = {
  kind: DebtKind; label: string | null; monthly_payment: string; outstanding: string; deducted_from_salary: boolean;
  annual_rate: string | null;
};
export type DebtForm = { kind: DebtKind | ''; label: string; monthly: string; owed: string; fromSalary: boolean; rate: string };
export type DebtErrors = Partial<Record<'kind' | 'monthly' | 'owed' | 'rate', string>>;

export const blankDebt = (): DebtForm => ({ kind: '', label: '', monthly: '', owed: '', fromSalary: false, rate: '' });
export const kindLabel = (kind: DebtKind) => DEBT_KINDS.find((k) => k.kind === kind)?.label ?? kind;
export const debtName = (d: Pick<DebtRow, 'kind' | 'label'>) => d.label || kindLabel(d.kind);
/** Kinds that can come straight off a salary (potongan gaji); a card or BNPL never does. */
export const asksFromSalary = (kind: DebtKind | '') => kind !== '' && FROM_SALARY.includes(kind);

/** An amount of at least zero, as a decimal string: "0", "480.78", "RM 1,200" -> "0.00", "480.78", "1200.00". */
export function parseMoney(text: string): { ok: true; value: string } | { ok: false; error: string } {
  if (/^\s*(RM\s*)?0+(\.0{1,2})?\s*$/i.test(text)) return { ok: true, value: '0.00' };
  return parseAmount(text);
}

/**
 * A yearly rate typed as a percentage, saved as a fraction (DB5): "" -> null, "18" or "18%" -> "0.1800",
 * "3.25" -> "0.0325". At most 2 decimals, 0 to 100; worked out in whole basis points, never floats.
 */
export function parseRate(text: string): { ok: true; value: string | null } | { ok: false; error: string } {
  const s = text.trim();
  if (s === '') return { ok: true, value: null };
  const m = /^(\d{1,3})(?:\.(\d{1,2}))?\s*%?$/.exec(s);
  const bp = m ? Number(m[1]) * 100 + Number((m[2] ?? '').padEnd(2, '0')) : NaN;
  if (!m || bp > 10000) return { ok: false, error: 'Type a yearly rate from 0 to 100, e.g. 18 or 3.5' };
  return { ok: true, value: `${Math.floor(bp / 10000)}.${String(bp % 10000).padStart(4, '0')}` };
}

/** A saved rate back as the percentage the user typed: 0.18 -> "18", 0.0325 -> "3.25", null -> "". */
export function rateText(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return '';
  const bp = Math.round(rate * 10000);
  return bp % 100 === 0 ? String(bp / 100) : `${Math.floor(bp / 100)}.${String(bp % 100).padStart(2, '0').replace(/0$/, '')}`;
}

export function buildDebt(form: DebtForm): { ok: true; debt: NewDebt } | { ok: false; errors: DebtErrors } {
  const errors: DebtErrors = {};
  if (form.kind === '') errors.kind = 'Choose what kind of debt it is';
  const monthly = parseMoney(form.monthly);
  if (!monthly.ok) errors.monthly = form.monthly.trim() === '' ? 'Type the monthly payment (0 if none yet)' : monthly.error;
  const owed = parseMoney(form.owed);
  if (!owed.ok) errors.owed = form.owed.trim() === '' ? 'Type what is left to pay' : owed.error;
  if (monthly.ok && owed.ok && monthly.value === '0.00' && owed.value === '0.00') {
    errors.owed = 'A debt needs a monthly payment or something left to pay';
  }
  const rate = parseRate(form.rate);
  if (!rate.ok) errors.rate = rate.error;
  if (Object.keys(errors).length > 0 || form.kind === '' || !monthly.ok || !owed.ok || !rate.ok) return { ok: false, errors };
  const label = redactNote(form.label.trim()).slice(0, LABEL_MAX).trim();
  return { ok: true, debt: {
    kind: form.kind, label: label === '' || label === kindLabel(form.kind) ? null : label,
    monthly_payment: monthly.value, outstanding: owed.value,
    deducted_from_salary: asksFromSalary(form.kind) && form.fromSalary,
    annual_rate: rate.value,
  } };
}

/** A saved debt back in the form (amounts as typed decimals, never rounded to whole ringgit). */
export function formOf(d: DebtRow): DebtForm {
  return { kind: d.kind, label: d.label ?? '', monthly: d.monthly_payment.toFixed(2), owed: d.outstanding.toFixed(2),
           fromSalary: d.deducted_from_salary, rate: rateText(d.annual_rate) };
}

/** Paid off by `today` (DB3): it stays on record but is no longer a monthly payment. */
export const paidOff = (d: Pick<DebtRow, 'ends_on'>, today: string) => d.ends_on !== null && d.ends_on <= today;

/** What the list adds up to: the monthly payments and what is left to pay, as decimal strings. */
export function debtTotals(debts: Pick<DebtRow, 'monthly_payment' | 'outstanding'>[]): { monthly: string; owed: string } {
  return { monthly: sumAmounts(debts.map((d) => d.monthly_payment.toFixed(2))),
           owed: sumAmounts(debts.map((d) => d.outstanding.toFixed(2))) };
}
