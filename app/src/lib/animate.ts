/**
 * The Home scene's idle animation (D-116): which kit frames a piece cycles through, and which frame
 * shows at a time. Only the kit's own frames, on fixed schedules: nothing random. Pure TypeScript,
 * tested by Node; frameAt also runs on the UI thread (a worklet).
 *
 *   the character by day   its mood, breathing in and out, and a blink every few breaths
 *   the character at night asleep: the bed's or mattress's 4 frames (breathing, the "z")
 *   chickens               idling, pecking, or asleep; each one a little out of step with the others
 */
export type Loop = { frames: string[]; ms: number[] };

const DAY = [['', 600], ['_breathe', 600], ['', 600], ['_breathe', 600], ['', 300], ['_blink', 150], ['', 450]] as const;

function range(prefix: string, n: number, has: (name: string) => boolean): string[] {
  return Array.from({ length: n }, (_, k) => `${prefix}_${k}`).filter(has);
}

/** The loop for a piece, or null when it stands still (or the kit lacks its frames). */
export function idleLoop(piece: string, has: (name: string) => boolean): Loop | null {
  const mood = /^avatar_0\d_mood_[a-z_]+$/.test(piece) && !/_(breathe|blink)$/.test(piece);
  if (mood) {
    const frames = DAY.map(([s]) => `${piece}${s}`);
    return frames.every(has) ? { frames, ms: DAY.map(([, ms]) => ms) } : null;
  }
  const sleep = /^(avatar_0\d_sleep_(?:bed|mattress))_\d$/.exec(piece);
  if (sleep) {
    const frames = range(sleep[1], 4, has);
    return frames.length > 1 ? { frames, ms: frames.map(() => 700) } : null;
  }
  if (/^chicken_peck_\d$/.test(piece)) {
    const pecks = range('chicken_peck', 4, has);
    if (pecks.length < 2 || !has('chicken_idle_0')) return null;
    return { frames: [...pecks, 'chicken_idle_0'], ms: [...pecks.map(() => 160), 1100] };
  }
  if (/^chicken_idle_\d$/.test(piece)) {
    const idle = range('chicken_idle', 2, has);
    return idle.length > 1 ? { frames: idle, ms: [1400, 500] } : null;
  }
  if (/^chicken_sleep_\d$/.test(piece)) {
    const frames = range('chicken_sleep', 8, has);
    return frames.length > 1 ? { frames, ms: frames.map(() => 450) } : null;
  }
  return null;
}

/** Which frame shows at time t (ms) in a loop that started at 0. */
export function frameAt(ms: number[], t: number): number {
  'worklet';
  let total = 0;
  for (let i = 0; i < ms.length; i++) total += ms[i];
  let at = ((t % total) + total) % total;
  for (let i = 0; i < ms.length; i++) {
    if (at < ms[i]) return i;
    at -= ms[i];
  }
  return 0;
}
