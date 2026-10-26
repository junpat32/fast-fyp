/**
 * A few words under the Money screen's tiles (D-109), so the status reads at a glance without
 * opening ⓘ: is "8 in 100" high, is "0.6 months" enough? Every limit comes from shared/thresholds.json
 * (rule 5) and is compared the way engine/rules.py compares it, so a verdict never disagrees with the
 * advice beside it. Pure TypeScript, tested by Node.
 */
import { outOf100 } from './format.ts';

export type Tone = 'good' | 'watch' | 'bad' | 'neutral';
export type Verdict = { text: string; tone: Tone };
export type VerdictLimits = {
  advice: { forecast_elevated: number; cushion_first_goal_months: number; cushion_next_goal_months: number };
};

const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

/**
 * "high" at the limit that triggers R10 ("a tight month may be ahead"); otherwise compared with the
 * average shown under ⓘ, on the same rounded numbers the screen prints. None for a user already in
 * Red: their forecast counts running short only, so the average is not like for like (W3).
 */
export function forecastVerdict(f: { probability: number; base_rate: number; red_note: string | null },
                                t: VerdictLimits): Verdict | null {
  if (f.probability >= t.advice.forecast_elevated) return { text: 'high', tone: 'bad' };
  if (f.red_note) return null;
  const p = outOf100(f.probability);
  const avg = outOf100(f.base_rate);
  if (p === avg) return { text: 'about average', tone: 'neutral' };
  return p > avg ? { text: 'above average', tone: 'watch' } : { text: 'below average', tone: 'good' };
}

/** Where the cushion stands against its goals: the same tests that choose R05 and R06. */
export function cushionVerdict(months: number, t: VerdictLimits): Verdict {
  const { cushion_first_goal_months: first, cushion_next_goal_months: next } = t.advice;
  if (months < first) return { text: `goal: ${plural(first, 'month')}`, tone: 'neutral' };
  if (months < next) return { text: '✓ first goal', tone: 'good' };
  return { text: `✓ ${next}-month goal`, tone: 'good' };
}
