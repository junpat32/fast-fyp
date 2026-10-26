/**
 * The game's three badges (game_design §6, G-04; D-127) and how points are earned, in words built from
 * shared/game.json (rule 5), for the Home points panel and the More screen. Which badges the user has
 * always comes from the API (GET /v1/game); this only explains them.
 *
 * Guardrails (D-107): a badge, once earned, stays; nothing is compared with anyone else; "not yet" is
 * never a loss. Pure TypeScript, tested by Node against game.json and the persona samples.
 */
export type BadgeRules = {
  points: { checkin: number; verified: number; saved_low_rate: number; saved_low: number; saved_high_rate: number;
            saved_high: number; debt_low_rate: number; debt_low: number; debt_high_rate: number; debt_high: number;
            bills_on_time: number; cushion_kept: Record<string, number>; card_answered: number;
            milestones: Record<string, number> };
  badges: { cushion_builder_months: number; steady_saver_months_in_a_row: number; honest_tracker_streak_days: number };
  streak: { rest_days_per_week: number; milestone_points: Record<string, number> };
  choices: { points_per_choice: number };
};

export type Badge = { key: string; name: string; earned: boolean; how: string; now: string | null };

/** The badges in the order the panel shows them (engine/game.py awards these names). */
export const BADGE_KEYS = ['cushion_builder', 'steady_saver', 'honest_tracker'] as const;

const pct = (x: number) => `${Math.round(x * 100)}%`;
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
/** Rounded down, so 0.97 months never reads as "1 month" before it is. */
const months = (x: number) => plural(Math.floor(Math.max(x, 0) * 10) / 10, 'month');

/** Each badge: earned or not, what earns it, and how close the user is where the API says so. */
export function badgeList(game: { badges: string[]; game_cushion: number; streak: { current: number } },
                          rules: BadgeRules): Badge[] {
  const b = rules.badges;
  const has = new Set(game.badges);
  const cushion = b.cushion_builder_months;
  const days = b.honest_tracker_streak_days;
  const rest = rules.streak.rest_days_per_week;
  const list: Omit<Badge, 'earned'>[] = [
    { key: 'cushion_builder', name: 'Cushion Builder',
      how: `Have ${plural(cushion, 'month')} of costs saved.`,
      now: game.game_cushion >= cushion ? 'You have it saved: it counts once a check-in confirms it.'
        : `Now: ${months(game.game_cushion)} saved.` },
    { key: 'steady_saver', name: 'Steady Saver',
      how: `Set aside at least ${pct(rules.points.saved_low_rate)} of your income ${b.steady_saver_months_in_a_row} months in a row.`,
      now: null },
    { key: 'honest_tracker', name: 'Honest Tracker',
      how: `Log something, or tap "No spending today", ${days} days in a row (${plural(rest, 'rest day')} a week is fine).`,
      now: `Now: ${plural(game.streak.current, 'day')} in a row.` },
  ];
  return list.map((x) => (has.has(x.key) ? { ...x, earned: true, now: null } : { ...x, earned: false }));
}

/** How points are earned, one line each, every number from game.json. */
export function pointsGuide(rules: BadgeRules): string[] {
  const p = rules.points;
  const ms = Object.entries(p.milestones).sort((a, c) => Number(a[0]) - Number(c[0]));
  const kept = Object.entries(p.cushion_kept).sort((a, c) => Number(a[0]) - Number(c[0]));
  const streak = Object.entries(rules.streak.milestone_points).sort((a, c) => Number(a[0]) - Number(c[0]));
  const list = (xs: string[]) => (xs.length > 1 ? `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}` : xs[0]);
  return [
    `Monthly check-in: +${p.checkin}`,
    `The month adds up (what you logged explains your money): +${p.verified}`,
    `Set aside ${pct(p.saved_low_rate)} of your income in a month: +${p.saved_low}; ${pct(p.saved_high_rate)}: +${p.saved_high}`,
    `Debt paid down to a new low by ${pct(p.debt_low_rate)} of your income: +${p.debt_low}; ${pct(p.debt_high_rate)}: +${p.debt_high}`,
    `Bills paid on time: +${p.bills_on_time} a month`,
    `Costs saved, ${list(ms.map(([m]) => m))} months: ${list(ms.map(([, v]) => `+${v}`))}, once each`,
    `Keeping ${plural(Number(kept[0][0]), 'month')} saved: +${kept[0][1]} at each check-in` +
      kept.slice(1).map(([m, v]) => `; ${plural(Number(m), 'month')}: +${v}`).join(''),
    `Logging streak of ${list(streak.map(([d]) => d))} days: ${list(streak.map(([, v]) => `+${v}`))}, once each`,
    `This week's what-if card: +${p.card_answered}`,
    `Every ${rules.choices.points_per_choice} points: a choice of plant or decoration. Points are never taken away.`,
  ];
}
