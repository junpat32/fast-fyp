/**
 * The Money screen's "Your progress" section (D-107): how the user's money connects to the game.
 * Every number comes from shared/game.json (rule 5), and only rewards the game really gives appear.
 *
 * Guardrails (D-107, Patrick's "safe?" check):
 *   - no reward line on debt, AKPK, band or forecast advice (R01, R03, R04, R07, R08, R09, R10, R13):
 *     someone in difficulty needs help, not points
 *   - nothing random, nothing compared with others, nothing taken away
 * Pure TypeScript, tested by Node against game.json and the persona samples.
 */
export type GameRules = {
  points: { checkin: number; verified: number; bills_on_time: number; saved_low_rate: number; saved_low: number;
            saved_high_rate: number; saved_high: number; cushion_kept: Record<string, number>; milestones: Record<string, number> };
  room_level_at_cushion: Record<string, number>;
  checkin_grace_days: number;
  garden: { level_at_qualifying_months: Record<string, number>; qualifying_cushion_months: number };
};

export type Milestone = { months: number; points: number; room: number | null; reached: boolean };

const pct = (x: number) => `${Math.round(x * 100)}%`;
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

/** The cushion milestones (0.5, 1, 2, 3 months), which are reached, and the next one (A). */
export function cushionProgress(game: { game_cushion: number; milestones: string[] }, rules: GameRules) {
  const roomAt = new Map(Object.entries(rules.room_level_at_cushion).map(([lv, m]) => [m, Number(lv)]));
  const milestones: Milestone[] = Object.entries(rules.points.milestones)
    .map(([m, points]) => ({ months: Number(m), points, room: roomAt.get(Number(m)) ?? null,
                             reached: game.milestones.some((x) => Number(x) === Number(m)) }))
    .sort((a, b) => a.months - b.months);
  const top = milestones[milestones.length - 1].months;
  return { milestones, next: milestones.find((m) => !m.reached) ?? null,
           fill: Math.min(Math.max(game.game_cushion, 0) / top, 1) };
}

/** What the next milestone unlocks, in words. */
export function milestoneLine(m: Milestone): string {
  const room = m.room ? `your room grows to level ${m.room} and ` : '';
  return `Next: ${plural(m.months, 'month')} of costs saved: ${room}+${m.points} points.`;
}

/** The Money screen's progress row (D-109, D-111): the room now, and what the next milestone brings.
 * Points stay in it, so the core flow's last step ("→ points") shows without a tap. */
export function progressParts(game: { room_level: number; game_cushion: number; milestones: string[] },
                              rules: GameRules): { room: string; next: string } {
  const top = Math.max(...Object.keys(rules.room_level_at_cushion).map(Number));
  const next = cushionProgress(game, rules).next;
  const room = `Room ${game.room_level} of ${top}`;
  if (!next) return { room, next: 'every level unlocked' };
  return { room, next: `next: ${plural(next.months, 'month')} saved → ${next.room ? `room ${next.room}, ` : ''}+${next.points} pts` };
}

/** The same in one line (for screen readers). */
export function progressLine(game: { room_level: number; game_cushion: number; milestones: string[] },
                             rules: GameRules): string {
  const { room, next } = progressParts(game, rules);
  return `${room} · ${next}`;
}

/** The game's real reward for following an advice item (B), or null when there is none or it
 * would be wrong to show one (the guardrails above). */
export function adviceReward(rule: string, rules: GameRules): string | null {
  const id = rule.split('_')[0];
  const p = rules.points;
  const kept3 = p.cushion_kept['3'];
  switch (id) {
    case 'R02':
      return `In the game: bills paid on time earn +${p.bills_on_time} points at each monthly check-in.`;
    case 'R05': {
      const one = rules.points.milestones['1'];
      return `In the game: reaching 1 month of costs saved grows your room and earns +${one} points.`;
    }
    case 'R06':
      return `In the game: 3 months saved takes your room to its top level (+${p.milestones['3']} points), ` +
        `and keeping it earns +${kept3} points every month.`;
    case 'R11':
      return `In the game: setting aside ${pct(p.saved_low_rate)} of your income in a month earns ` +
        `+${p.saved_low} points; ${pct(p.saved_high_rate)} earns +${p.saved_high}.`;
    case 'R12':
      return `In the game: keeping 3 months saved earns +${kept3} points every month.`;
    default:
      return null;                                   // debt, AKPK, band, forecast and festive advice: none
  }
}

/** The garden's level and how many qualifying months the next one needs (C). */
export function gardenProgress(garden: { level: number; qualifying_months: number; open: boolean }, rules: GameRules) {
  const levels = Object.entries(rules.garden.level_at_qualifying_months)
    .map(([lv, m]) => ({ level: Number(lv), months: m })).sort((a, b) => a.level - b.level);
  const next = levels.find((l) => l.level > garden.level) ?? null;
  return { level: garden.level, top: levels[levels.length - 1].level, open: garden.open,
           next: next ? { level: next.level, needs: Math.max(next.months - garden.qualifying_months, 0) } : null };
}

/** When this month's check-in opens and closes (D-77): its last day, until checkin_grace_days after. */
export function checkinWindow(asOf: string, rules: GameRules): { opens: string; closes: string } {
  const [y, m] = asOf.split('-').map(Number);
  const last = new Date(Date.UTC(y, m, 0));                 // day 0 of next month = this month's last day
  const close = new Date(last.getTime() + rules.checkin_grace_days * 86_400_000);
  return { opens: last.toISOString().slice(0, 10), closes: close.toISOString().slice(0, 10) };
}

/** The last n months for the strip: checked and verified, and counted for the garden (C). */
export function monthStrip(months: { month: string; verified: boolean; goal_met: boolean; qualifying: boolean }[],
                           n = 6) {
  return months.slice(-n).map((x) => ({ month: x.month, verified: x.verified, garden: x.qualifying || x.goal_met }));
}
