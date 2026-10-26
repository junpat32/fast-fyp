/**
 * The Future screen's words and numbers (D-110), from GET /v1/future: six months of possible cushions
 * (P10 to P90, in months of costs) "if recent habits continue" (D-81), never called a validated
 * prediction interval; no percentage on this screen (D-100). Moods come from the game's never-sad set
 * (D-12). Pure TypeScript, tested by Node.
 */
import { monthsText } from './format.ts';

export type Mood = 'relaxed' | 'calm' | 'focused' | 'concerned_hopeful' | 'celebrating';
export type FutureMonth = { month: number; p10: number; p50: number; p90: number };
type Goals = { advice: { cushion_first_goal_months: number; cushion_next_goal_months: number } };

const MOODS: Mood[] = ['relaxed', 'calm', 'focused', 'concerned_hopeful', 'celebrating'];
const SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** A calendar month number (the simulation's months are calendar months) as "Jul". */
export function monthShort(m: number): string {
  if (!Number.isInteger(m) || m < 1 || m > 12) throw new Error(`not a month: ${m}`);
  return SHORT[m - 1];
}

/** "You now": the engine's own mood (GET /v1/game look.mood), or calm for anything unknown. */
export function moodNow(mood: string): Mood {
  return (MOODS as string[]).includes(mood) ? (mood as Mood) : 'calm';
}

/**
 * "You in 6 months": where the middle path ends. Celebrating at the 3-month goal, relaxed at the
 * first goal, otherwise focused (the game's "determined" face, D-12). Never concerned: that face is
 * kept for a really bad month now (D-73), not for a future that hasn't happened.
 */
export function futureMood(medianFinal: number, t: Goals): Mood {
  if (medianFinal >= t.advice.cushion_next_goal_months) return 'celebrating';
  if (medianFinal >= t.advice.cushion_first_goal_months) return 'relaxed';
  return 'focused';
}

/** B6: the range at the end of the six months, e.g. "between 0.3 and 2.5 months of costs". */
export function rangeLine(months: FutureMonth[]): string {
  const last = months[months.length - 1];
  const [lo, hi] = [monthsText(last.p10), monthsText(last.p90)];
  return lo === hi ? `about ${lo} months of costs` : `between ${lo} and ${hi} months of costs`;
}

/** The number under the future self, above "months saved": "0.3–2.5". */
export function rangeShort(months: FutureMonth[]): string {
  const last = months[months.length - 1];
  const [lo, hi] = [monthsText(last.p10), monthsText(last.p90)];
  return lo === hi ? `about ${lo}` : `${lo}–${hi}`;
}

/** The chart's top: the highest value drawn, at least the first goal, rounded up to a half month. */
export function chartTop(months: FutureMonth[], now: number, t: Goals): number {
  const top = Math.max(...months.map((m) => m.p90), now, t.advice.cushion_first_goal_months);
  return Math.ceil(top * 2) / 2;
}

/**
 * The app's sprites come pre-enlarged nearest-neighbour (app_sprites.py, D-111), because React Native
 * scales images smoothly and blurs pixel art. Shown at one image pixel per screen pixel they stay
 * crisp; that size in dp is px / pixelRatio, kept within [min, max] dp on unusual screens.
 */
export function spriteDp(px: number, pixelRatio: number, min: number, max: number): number {
  return Math.min(Math.max(px / pixelRatio, min), max);
}
