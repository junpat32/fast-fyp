/** Small formatting rules for the screens (pure; tested by Node). */
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December'];

/** "2026-06-01" -> "June 2026". */
export function monthName(iso: string): string {
  const [y, m] = iso.split('-').map(Number);
  if (!y || !m || m < 1 || m > 12) throw new Error(`not a month: ${iso}`);
  return `${MONTHS[m - 1]} ${y}`;
}

/** "2026-07-01" -> "1 July 2026". */
export function dayName(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) throw new Error(`not a date: ${iso}`);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** "2026-07-01" -> "1 Jul 2026" (the Money screen's header line). */
export function shortDay(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d || m < 1 || m > 12) throw new Error(`not a date: ${iso}`);
  return `${d} ${MONTHS[m - 1].slice(0, 3)} ${y}`;
}

/** A calibrated probability as "out of 100 people" (the study's question B4): 0.0845 -> 8. */
export function outOf100(p: number): number {
  return Math.round(p * 100);
}

/** Months of costs covered, one decimal, never below zero: 1.04 -> "1.0". */
export function monthsText(m: number): string {
  return Math.max(m, 0).toFixed(1);
}

export function rm(x: number): string {
  return `RM${Math.round(x).toLocaleString('en-MY')}`;
}
