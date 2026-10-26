/**
 * Taps on the Home scene (D-114): which thing is under the finger, and the short card it opens.
 * Pure TypeScript, tested by Node.
 *
 * A tap is tested against each structure's opaque box (assets/app/piece_boxes.json), front to back,
 * so the piece drawn on top wins; pieces that open nothing (walls, beds, fences) let the tap through to
 * whatever is behind. A tap on no piece but on the plot's ground opens the garden card (study task 6,
 * B8: "what makes the garden grow"). Room objects open what room.json "interactive" names.
 */
import { DECOR_NAMES } from './extras.ts';
import { cellAt, type Point } from './iso.ts';
import { MAP_ORIGIN, type Draw, type SceneJson } from './scene.ts';

export type Target =
  | { kind: 'object'; opens: string; piece: string }
  | { kind: 'plant'; plant: string; stage: string; cell: [number, number] }
  | { kind: 'bed'; cell: [number, number] }                  // an empty spot in the bed: plant here (D-115)
  | { kind: 'character' }
  | { kind: 'tree' }                                         // the tree, or its empty spot at the top level (D-120)
  | { kind: 'animal'; piece: string }
  | { kind: 'decoration'; item: string; cell: [number, number] }   // a garden decoration: move it (D-120)
  | { kind: 'choices' }                                      // the points pill's "Spend a choice" (D-120)
  | { kind: 'garden'; cell: [number, number] };
export type Box = [number, number, number, number];

/** The plot inside the fence, [lo, hi] on both axes (none before the garden opens). */
export function plotBounds(scene: SceneJson): [number, number] | null {
  const fence = scene.structures.filter(([, , n]) => n.startsWith('fence_'));
  if (fence.length === 0) return null;
  const lo = Math.min(...fence.map(([gx, gy]) => Math.min(gx, gy)));
  const hi = Math.max(...fence.map(([gx, gy]) => Math.max(gx, gy))) - 1;
  return [lo, hi];
}

function boxOf(d: Draw, boxes: Record<string, Box>, widths: Record<string, number>): Box | null {
  const b = boxes[d.piece];
  if (!b || b[2] <= b[0]) return null;
  const [x0, y0, x1, y1] = d.flip ? [widths[d.piece] - b[2], b[1], widths[d.piece] - b[0], b[3]] : b;
  return [d.x + x0, d.y + y0, d.x + x1, d.y + y1];
}

function targetOf(d: Draw, ctx: HitContext, cellOf: (d: Draw) => [number, number]): Target | null {
  const n = d.piece;
  const key = Object.keys(ctx.interactive).find((k) => n.startsWith(k));
  if (key) return { kind: 'object', opens: ctx.interactive[key], piece: n };
  if (ctx.gardenDecor?.includes(n)) return { kind: 'decoration', item: n, cell: cellOf(d) };
  const plant = /^plant_([a-z]+(?:_[a-z]+)*?)_(seedling|young|full)(?:_droop)?$/.exec(n);
  if (plant) return { kind: 'plant', plant: plant[1], stage: plant[2], cell: cellOf(d) };
  if (n.startsWith('avatar_')) return { kind: 'character' };
  if (n.startsWith('tree_')) return { kind: 'tree' };
  if (n.startsWith('chicken_') || n === 'prop_chicken_coop') return { kind: 'animal', piece: n };
  return null;
}

export type HitContext = {
  cells: [number, number][];                     // each structure draw's back cell, in draw order
  boxes: Record<string, Box>;                    // opaque boxes on each piece's canvas (the atlas)
  widths: Record<string, number>;                // canvas widths (for mirrored pieces)
  interactive: Record<string, string>;           // room.json "interactive"
  plot: [number, number] | null;                 // plotBounds
  room: [number, number, number, number];        // the room's [x0, y0, w, d]
  bed: [number, number][];                       // GET /v1/game garden.bed
  plants: { cell: [number, number]; plant: string; stage: string }[];
  gardenDecor?: string[];                        // game.json decorations.garden: pieces that open their card
  treeSpot?: { cell: [number, number]; size: [number, number] } | null;   // the scene's tree spot (from G4)
};

/**
 * What a tap at `p` (in the 540 x 1200 view's art pixels) touches. The bed comes first, by cell: in a
 * full bed the plants' boxes overlap the cells behind them, and a plant belongs to its cell (a tap on
 * tall leaves above the bed still reaches the plant through its box).
 */
export function hitTest(p: Point, list: Draw[], ctx: HitContext): Target | null {
  const [gx, gy] = cellAt(p, MAP_ORIGIN);
  if (ctx.bed.some(([x, y]) => x === gx && y === gy)) {           // the bed: its plant, or plant here
    const plant = ctx.plants.find((q) => q.cell[0] === gx && q.cell[1] === gy);
    return plant ? { kind: 'plant', plant: plant.plant, stage: plant.stage, cell: [gx, gy] } : { kind: 'bed', cell: [gx, gy] };
  }
  const structs = list.filter((d) => d.layer === 'struct');
  const cellOf = (d: Draw) => ctx.cells[structs.indexOf(d)];
  for (let i = structs.length - 1; i >= 0; i--) {
    const b = boxOf(structs[i], ctx.boxes, ctx.widths);
    if (!b || p.x < b[0] || p.x >= b[2] || p.y < b[1] || p.y >= b[3]) continue;
    const t = targetOf(structs[i], ctx, cellOf);
    if (t) return t;
  }
  const spot = ctx.treeSpot;                                       // the tree's spot: the tree, or planting one
  if (spot && gx >= spot.cell[0] && gx < spot.cell[0] + spot.size[0] && gy >= spot.cell[1] && gy < spot.cell[1] + spot.size[1]) {
    return { kind: 'tree' };
  }
  const [x0, y0, w, d] = ctx.room;
  const inRoom = gx >= x0 && gx < x0 + w && gy >= y0 && gy < y0 + d;
  const plot = ctx.plot;
  if (plot && !inRoom && gx >= plot[0] && gx <= plot[1] && gy >= plot[0] && gy <= plot[1]) {
    return { kind: 'garden', cell: [gx, gy] };
  }
  return null;
}

export type CardGame = {
  room_level: number; game_cushion: number;
  garden: { open: boolean; level: number; qualifying_months: number };
  plants: { cell: [number, number]; plant: string; stage: string; growing_days: number }[];
  look: { mood: string; plants: string; coin_jar: number; savings_plant: number };
};
export type CardRules = {
  coin_jar_fills_at_cushion: number[];
  savings_plant_stages_at_saved_months: number[];
  garden: { level_at_qualifying_months: Record<string, number>; qualifying_cushion_months: number };
  choices: { points_per_choice: number };
};
export type Card = { title: string; lines: string[] };

const PLANT_NAMES: Record<string, string> = { serai: 'Serai (lemongrass)', pandan: 'Pandan', chilli: 'Chilli' };
const STAGES: Record<string, string> = { seedling: 'a seedling', young: 'growing', full: 'full grown' };
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
const months = (xs: number[]) => xs.map(String).join(', ').replace(/, ([^,]*)$/, ' and $1');

/** The short card a tap opens (the B8 sentence is the garden card's first line). */
export function cardFor(t: Target, g: CardGame, rules: CardRules, night: boolean): Card {
  switch (t.kind) {
    case 'object':
      if (t.opens === 'savings') {
        return { title: 'Coin jar', lines: [
          `It fills as your cushion grows: at ${months(rules.coin_jar_fills_at_cushion)} months of costs saved.`,
          `Now: ${g.look.coin_jar} of ${rules.coin_jar_fills_at_cushion.length} filled.`] };
      }
      if (t.opens === 'savings_history') {
        const steps = rules.savings_plant_stages_at_saved_months;
        return { title: 'Savings plant', lines: [
          'It grows with the months you put money aside: a new stage after ' +
          `${months(steps)} months of saving.`,
          `Now: stage ${g.look.savings_plant} of ${steps.length}.`] };
      }
      if (t.opens === 'budgets') {
        return { title: 'Budget board', lines: [
          'Your monthly budgets: a limit for anything you want to keep an eye on, and how much of it is left.'] };
      }
      return { title: 'Money helper', lines: [
        'Ask a question about your own numbers. An AI answers from a summary of your results, never your entries.'] };
    case 'plant': {
      const p = g.plants.find((x) => x.cell[0] === t.cell[0] && x.cell[1] === t.cell[1]);
      const lines = [`${STAGES[t.stage] ?? t.stage}${p ? `, growing for ${plural(p.growing_days, 'day')}` : ''}.`];
      if (g.look.plants !== 'normal') lines.push('Plants droop in a really hard month and perk up again after it.');
      return { title: PLANT_NAMES[t.plant] ?? t.plant, lines };
    }
    case 'character': {
      if (night) return { title: 'You', lines: ['Asleep. The room and garden wait for the morning.'] };
      const mood: Record<string, string> = {
        relaxed: 'Relaxed: your health score says Healthy.',
        calm: 'Calm: your health score says Coping.',
        focused: 'Focused and determined: your health score says Vulnerable. One step at a time.',
        concerned_hopeful: 'A hard month, but hopeful: your next step is on the Money tab.',
      };
      return { title: 'You', lines: [mood[g.look.mood] ?? 'Calm.'] };
    }
    case 'bed':
      return { title: 'Plant here', lines: ['Choose a plant for this spot. It grows with every day that isn\'t a really hard month.'] };
    case 'tree':
      return { title: 'Your tree', lines: ['It grows on every day that isn\'t a really hard month, like the plants, and stays for good.'] };
    case 'animal':
      return { title: 'Chickens', lines: ['They never get hungry or sick, and they never leave, whatever happens with money.'] };
    case 'decoration':
      return { title: DECOR_NAMES[t.item] ?? t.item, lines: ['Yours for good. Move it to another spot any time, for free.'] };
    case 'choices':
      return { title: 'Spend a choice', lines: [`Every ${rules.choices.points_per_choice} points gives a choice: something for ` +
        'your room or garden. Nothing has a price, and nothing is ever taken away.'] };
    case 'garden': {
      const sentence = 'Your garden grows when you meet your saving goal or keep a cushion, month after month.';
      if (!g.garden.open) return { title: 'Your garden', lines: ['Your garden opens after your first 3 check-ins.', sentence] };
      const levels = Object.entries(rules.garden.level_at_qualifying_months).map(([lv, m]) => [Number(lv), m] as const)
        .sort((a, b) => a[0] - b[0]);
      const top = levels[levels.length - 1][0];
      const next = levels.find(([lv]) => lv > g.garden.level);
      const lines = [sentence,
        `A month counts when you meet your goal or keep at least ${plural(rules.garden.qualifying_cushion_months, 'month')} of costs saved.`];
      lines.push(next ? `${plural(Math.max(next[1] - g.garden.qualifying_months, 0), 'more counted month')} to level ${next[0]}.`
        : 'Your garden is at its top level.');
      return { title: `Your garden · level ${g.garden.level} of ${top}`, lines };
    }
  }
}
