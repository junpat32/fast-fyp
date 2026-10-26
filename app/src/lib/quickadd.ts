/**
 * Quicker logging on the Add screen (D-126): one sentence fills the form ("RM12 lunch", "salary 2800",
 * "petrol 50 yesterday", "shopee 89 atome"), debts on the list that aren't recorded yet this month are
 * one tap away, and so are recent entries. Each only fills the form: nothing is saved until the user
 * taps Save, as with typing it in. Pure TypeScript, tested by Node.
 *
 * Invariants
 *   QA1 the amount: one marked "RM" wins, else the last number ("99 speedmart 23.50" is RM23.50);
 *       "2.8k" is 2800; whole sen only, as the form allows
 *   QA2 the category: the longest word or phrase from shared/categories.json `words` found in the
 *       sentence, on either side; "paid", "gave", "bayar" make it money out, "got", "dapat", "terima"
 *       money in, and otherwise the side of the longer word decides
 *   QA3 the note keeps the words, without the amount, redacted as every note is (rule 11)
 *   QA4 a debt's bill is suggested only while it is unpaid this month (no entry in its category for its
 *       amount), not paid off, not RM0, and not taken off the salary (that money never reaches the
 *       account, so logging it would count it twice, api/money.py)
 */
import { debtName, paidOff, type DebtKind, type DebtRow } from './debts.ts';
import { parseAmount, redactNote, stepDay, type Categories, type Direction, type Form, type NewEntry, type PaidBy } from './entry.ts';

export type Quick = { patch: Partial<Form>; amount: boolean; category: string | null };

const MONEY = /(rm\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?(k)?(?![\w.])/gi;
const IN_VERBS = ['got', 'received', 'receive', 'dapat', 'terima', 'earned'];
const OUT_VERBS = ['gave', 'give', 'paid', 'pay', 'bayar', 'beli', 'bought', 'spent', 'sent', 'send'];
const BNPL = ['bnpl', 'atome', 'spaylater', 'paylater', 'pay later'];
const CARD = ['credit card', 'kad kredit', 'by card', 'card'];
const UNEXPECTED = ['unexpected', 'emergency', 'repair', 'rosak', 'saman'];
const YESTERDAY = ['yesterday', 'semalam'];

const norm = (text: string) => ` ${text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()} `;
const has = (n: string, phrase: string) => n.includes(` ${phrase} `);
const any = (n: string, phrases: string[]) => phrases.some((p) => has(n, p));

/** QA1: the amount in a sentence, as a decimal string, and the text it was written as. */
export function findAmount(text: string): { value: string; raw: string } | null {
  const all = [...text.matchAll(MONEY)];
  const pick = all.find((m) => m[1]) ?? all[all.length - 1];
  if (!pick) return null;
  let value = Number(pick[2].replace(/,/g, '')) + (pick[3] ? Number(`0.${pick[3]}`) : 0);
  if (pick[4]) value *= 1000;
  const parsed = parseAmount(value.toFixed(2));
  return parsed.ok ? { value: parsed.value, raw: pick[0] } : null;
}

/** QA2: the best category on each side (the longest word or phrase found). */
function bestCategory(n: string, cats: Categories, side: Direction): { key: string; len: number } | null {
  let best: { key: string; len: number } | null = null;
  for (const c of cats[side]) {
    for (const w of c.words ?? []) if (has(n, w) && (!best || w.length > best.len)) best = { key: c.key, len: w.length };
  }
  return best;
}

/** What one sentence fills in on the form (the rest stays as it was). */
export function parseQuick(text: string, cats: Categories, today: string): Quick {
  const amount = findAmount(text);
  const n = norm(text);
  const out = bestCategory(n, cats, 'out');
  const inc = bestCategory(n, cats, 'in');
  const direction: Direction = any(n, OUT_VERBS) ? 'out' : any(n, IN_VERBS) ? 'in'
    : inc && (!out || inc.len >= out.len) ? 'in' : 'out';
  const hit = direction === 'in' ? inc ?? { key: 'other_income', len: 0 } : out;
  const category = hit ? cats[direction].find((c) => c.key === hit.key) ?? null : null;
  const purchase = direction === 'out' && !!category && !category.debt_payment && !category.own_transfer;
  const patch: Partial<Form> = { direction, category: category?.key ?? '' };
  if (amount) patch.amount = amount.value;
  if (purchase) {
    const paidBy: PaidBy = any(n, BNPL) ? 'bnpl' : any(n, CARD) ? 'card' : 'now';
    patch.paidBy = paidBy;
    patch.unexpected = any(n, UNEXPECTED);
  }
  if (any(n, YESTERDAY)) patch.day = stepDay(today, -1, today);
  const note = redactNote((amount ? text.replace(amount.raw, ' ') : text).replace(/\s+/g, ' '));
  if (note) patch.note = note;
  return { patch, amount: !!amount, category: category?.label ?? null };
}

/** The entry category a debt's monthly payment goes in (every kind on the debts list has one). */
export function debtCategory(d: Pick<DebtRow, 'kind' | 'label'>): string {
  const byKind: Record<DebtKind, string> = {
    ptptn: 'ptptn', car: 'car_loan', housing: 'home_loan', personal: 'personal_loan', credit_card: 'credit_card',
    bnpl: 'bnpl_instalment', other: 'other_debt',
  };
  return d.kind === 'other' && /motor/i.test(d.label ?? '') ? 'motorbike_loan' : byKind[d.kind];
}

export type Bill = { id: string; name: string; category: string; amount: string };

/** QA4: the debts still to pay this month, in the order of the list. */
export function billsDue(debts: DebtRow[], month: Pick<NewEntry, 'category' | 'amount' | 'direction'>[], today: string): Bill[] {
  return debts
    .filter((d) => !paidOff(d, today) && d.monthly_payment > 0 && !d.deducted_from_salary)
    .map((d) => ({ id: d.id, name: debtName(d), category: debtCategory(d), amount: d.monthly_payment.toFixed(2) }))
    .filter((b) => !month.some((e) => e.direction === 'out' && e.category === b.category && Number(e.amount) === Number(b.amount)));
}

export type Repeat = { key: string; patch: Partial<Form> };

/** The most recent different entries (amount, category, way of paying), newest first: "same again". */
export function repeats(recent: (NewEntry & { created_at: string })[], n = 4): Repeat[] {
  const seen = new Set<string>();
  const out: Repeat[] = [];
  for (const e of [...recent].sort((a, b) => b.created_at.localeCompare(a.created_at))) {
    const key = `${e.direction}|${e.amount}|${e.category}|${e.is_bnpl}|${e.on_credit}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ key, patch: { direction: e.direction, amount: e.amount, category: e.category,
                             paidBy: e.is_bnpl ? 'bnpl' : e.on_credit ? 'card' : 'now', unexpected: false, note: e.note ?? '' } });
    if (out.length === n) break;
  }
  return out;
}
