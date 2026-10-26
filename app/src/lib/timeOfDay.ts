/**
 * Which set of art to show: morning, afternoon or night, from the art kit's own times
 * (assets/isometric/manifest.json "times", e.g. "06:00-11:59"; night wraps past midnight).
 * The times come in as data so the manifest stays the single source (rule 5). For a study persona,
 * "now" is the server's as_of date at the device's local time (docs/app_plan.md §6, step 9).
 */
export type Period = 'morning' | 'afternoon' | 'night';
type Range = { period: Period; from: number; to: number };   // minutes after midnight, inclusive

function minutes(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number);
  if (!Number.isInteger(h) || !Number.isInteger(m) || h < 0 || h > 23 || m < 0 || m > 59) {
    throw new Error(`not a time: ${hhmm}`);
  }
  return h * 60 + m;
}

export function parseTimes(times: Record<string, string>): Range[] {
  return Object.entries(times).map(([period, span]) => {
    const [from, to] = span.split('-');
    return { period: period as Period, from: minutes(from), to: minutes(to) };
  });
}

export function periodAt(hour: number, minute: number, times: Record<string, string>): Period {
  const t = hour * 60 + minute;
  for (const r of parseTimes(times)) {
    const inside = r.from <= r.to ? t >= r.from && t <= r.to : t >= r.from || t <= r.to;   // wraps midnight
    if (inside) return r.period;
  }
  throw new Error(`no period covers ${hour}:${minute}`);
}
