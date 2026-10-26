/**
 * Words for the band card (docs/app_plan.md §3, the study's questions B1-B3), built from
 * shared/thresholds.json, the same file the Python engine reads (rule 5): nothing typed twice.
 * The band itself always comes from the API (GET /v1/assess); this only explains it.
 */
export type Band = 'GREEN' | 'YELLOW' | 'RED' | 'INSUFFICIENT_INCOME';
export type Thresholds = {
  dsr: { green_below: number; red_at_or_above: number; leave_red_below: number };
  improvement_confirm_months: number;
  insufficient_income_below_rm: number;
};

export const BAND_LABEL: Record<Band, string> = {
  GREEN: 'Green',
  YELLOW: 'Yellow',
  RED: 'Red',
  INSUFFICIENT_INCOME: 'Not enough income data',
};

const pct = (x: number) => `${Math.round(x * 100)}%`;

/** B2: "Debt payments take 59% of your income" (null when there's no band to explain). */
export function dsrLine(band: Band, dsr: number): string | null {
  return band === 'INSUFFICIENT_INCOME' ? null : `Debt payments take ${pct(dsr)} of your income`;
}

/** The band limits in one line, e.g. "Green below 30% · Yellow 30% to below 60% · Red 60% or more". */
export function limitsLine(t: Thresholds): string {
  const { green_below: g, red_at_or_above: r } = t.dsr;
  return `Green below ${pct(g)} · Yellow ${pct(g)} to below ${pct(r)} · Red ${pct(r)} or more`;
}

/** B3: how the band changes (D-49, D-05). */
export function changeRule(t: Thresholds): string {
  const k = t.improvement_confirm_months;
  return `A worse band shows at once; a better one after ${k} months in a row. ` +
    `Once Red, it stays Red until debt payments are below ${pct(t.dsr.leave_red_below)}.`;
}

/** Shown in place of a band (CLAUDE.md rule 5). */
export function noBandLine(t: Thresholds): string {
  return `No band yet: your typical monthly income is below RM${t.insufficient_income_below_rm}.`;
}
