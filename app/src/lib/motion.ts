/**
 * The screens' motion (D-154): how long a tap's dimming, a number's count, a bar's growth and a "Read
 * more" opening take, and the easing they share. Short (under 0.7 s) so nothing waits on an animation;
 * when the phone's "Remove animations" is on, everything shows at its end at once (Reanimated's
 * withTiming does this itself; useCountUp asks useReducedMotion). Pure TypeScript, tested by Node.
 */
export const MOTION = {
  pressedOpacity: 0.55,   // how far a tapped thing dims
  pressMs: 60,            // dims fast, so even a quick tap shows
  releaseMs: 180,         // and fades back
  countMs: 700,           // a number counting up to its value
  growMs: 600,            // a bar growing to its length
  growStepMs: 40,         // each bar in a row starts this much after the one before
  revealMs: 220,          // details opening or closing
} as const;

/** Fast at first, settling at the end: 0 -> 0, 1 -> 1 (Reanimated's Easing.out(Easing.cubic)). */
export function easeOut(p: number): number {
  const q = Math.min(Math.max(p, 0), 1);
  return 1 - (1 - q) ** 3;
}

/** A counting number's value `elapsed` ms into a count from `from` to `to` lasting `ms`. */
export function countAt(from: number, to: number, elapsed: number, ms: number): number {
  if (ms <= 0 || elapsed >= ms) return to;
  return from + (to - from) * easeOut(elapsed / ms);
}
