/**
 * The study's time travel (A4, D-90, D-119): a persona's date moves a month at a time between its first
 * and last study date (1 Jul 2026 to 1 Jan 2027), exactly as POST /v1/study/time-travel does
 * (api/main.py _shift_month, then clamped to the range). Pure TypeScript, tested by Node.
 *
 * Invariants: a step never leaves [first, last]; every date is the first of a month; "next" from the
 * last date and "previous" from the first stay put (the buttons are disabled there).
 */
export type TravelStep = 'next' | 'previous' | 'first' | 'last';
export type StudyClock = { date: string; first: string; last: string };   // ISO dates

/** The first of the month k months after (k < 0: before) the month of `iso`. */
export function shiftMonth(iso: string, k: number): string {
  const [y, m] = iso.split('-').map(Number);
  if (!y || !m || m < 1 || m > 12) throw new Error(`not a date: ${iso}`);
  const n = y * 12 + (m - 1) + k;
  const year = Math.floor(n / 12);
  return `${year}-${String(n - year * 12 + 1).padStart(2, '0')}-01`;
}

/** Where a step lands: a month on or back, or either end of the range; never outside it. */
export function stepDate(c: StudyClock, step: TravelStep): string {
  const target = step === 'first' ? c.first : step === 'last' ? c.last : shiftMonth(c.date, step === 'next' ? 1 : -1);
  return target < c.first ? c.first : target > c.last ? c.last : target;
}

export const canGoBack = (c: StudyClock) => c.date > c.first;
export const canGoOn = (c: StudyClock) => c.date < c.last;

/** Every date time travel can reach, in order (the first of each month from first to last). */
export function studyDates(c: Pick<StudyClock, 'first' | 'last'>): string[] {
  const out: string[] = [];
  for (let d = c.first; d <= c.last; d = shiftMonth(d, 1)) out.push(d);
  return out;
}
