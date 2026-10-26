/**
 * The Home extras (D-120; game_design §4 rule 5, §8): room and garden decorations, the tree and the
 * animals. Each costs one choice, except the first animal at an animal place, which is free (the
 * engine's ChooseAnimal); nothing has a price and nothing is random (D-107). This module says what each
 * option needs or is still waiting for, and where a garden decoration can go. Pure TypeScript, tested
 * by Node.
 *
 * Spots (the kit's scenes.decor_spots, K2): a garden decoration's spot is its back cell, "gx,gy". Its
 * whole footprint (the manifest's cells: w along gx, d along gy) must lie on the scene's
 * decor_free_cells (free lawn on screen, never the paths, the bed, an animal home or the tree's spot)
 * and on no other decoration. The scene lists those cells nearest the garden door first, so the first
 * fits are the nearest. The app offers up to 3 that don't overlap, so each glowing spot is one clear
 * choice. A room decoration has a fixed place (room.json), so its spot is just "room:<item>".
 */
export type C2 = [number, number];

export type ExtrasRules = {
  decorations: { room: string[]; garden: string[] };
  garden: {
    tree_from_garden_level: number; animals: string[]; max_animals_per_type: number;
    animal_slots_at_qualifying_months: number[]; level_at_qualifying_months: Record<string, number>;
    opens_after_check_ins: number;
  };
  growth: { tree_stages: number; tree_stage_growing_days: number };
};

export type ExtrasGame = {
  choices: { available: number };
  garden: { open: boolean; level: number; qualifying_months: number; animal_slots: number; animal_slots_used: number };
  tree: { stage: number } | null;
  decorations: Record<string, string>;
  animals: Record<string, number>;
};

export const DECOR_NAMES: Record<string, string> = {
  dining_set: 'Dining set', storage_cabinet: 'Storage cabinet', curtains_sage: 'Sage curtains',
  curtains_peach: 'Peach curtains', curtains_blue: 'Blue curtains', rug_green: 'Green rug',
  rug_terracotta: 'Terracotta rug', rug_blue: 'Blue rug', wall_art_kampung: 'Kampung picture',
  wall_art_flowers: 'Flower picture', desk_plant: 'Desk plant',
  bench: 'Bench', bench_improved: 'Comfy bench', garden_lamp: 'Garden lamp', lantern: 'Lantern',
  bird_bath: 'Bird bath', decorative_stones: 'Garden stones', garden_arch: 'Garden arch',
  outdoor_table: 'Outdoor table', outdoor_chair: 'Outdoor chair', mailbox: 'Letterbox', bicycle_rack: 'Bicycle rack',
  fountain: 'Fountain',
};
const REPLACES = ['curtains', 'rug'];                      // one of these shows at a time (scenes.DECOR_REPLACES)

export const roomSpot = (item: string) => `room:${item}`;
export const gardenSpot = ([gx, gy]: C2) => `${gx},${gy}`;

/** A garden decoration's back cell from its spot, or null for a room spot. */
export function spotCell(spot: string): C2 | null {
  const m = /^(-?\d+),(-?\d+)$/.exec(spot);
  return m ? [Number(m[1]), Number(m[2])] : null;
}

export function footprint([gx, gy]: C2, [w, d]: C2): C2[] {
  const out: C2[] = [];
  for (let i = 0; i < w; i++) for (let j = 0; j < d; j++) out.push([gx + i, gy + j]);
  return out;
}

const key = ([gx, gy]: C2) => `${gx},${gy}`;

/** The cells the placed garden decorations cover, except `moving` (the one being moved). */
export function usedCells(decorations: Record<string, string>, sizes: Record<string, C2>, moving?: string): C2[] {
  return Object.entries(decorations).flatMap(([item, spot]) => {
    const cell = spotCell(spot);
    return cell && item !== moving ? footprint(cell, sizes[item] ?? [1, 1]) : [];
  });
}

/** Every back cell where a decoration of `size` fits, nearest the garden door first (decor_spots). */
export function decorSpots(free: C2[], size: C2, used: C2[]): C2[] {
  const open = new Set(free.map(key));
  for (const c of used) open.delete(key(c));
  return free.filter((c) => footprint(c, size).every((x) => open.has(key(x))));
}

/** Up to `n` of those that don't overlap one another: the glowing spots to choose from. */
export function offeredSpots(free: C2[], size: C2, used: C2[], n = 3): C2[] {
  const out: C2[] = [];
  const taken = new Set<string>();
  for (const c of decorSpots(free, size, used)) {
    const cells = footprint(c, size).map(key);
    if (cells.some((x) => taken.has(x))) continue;
    cells.forEach((x) => taken.add(x));
    out.push(c);
    if (out.length === n) break;
  }
  return out;
}

/** The offered spot whose footprint holds a tapped cell. */
export function spotAt(cell: C2, spots: C2[], size: C2): C2 | null {
  return spots.find((s) => footprint(s, size).some(([x, y]) => x === cell[0] && y === cell[1])) ?? null;
}

export type RoomOption = { item: string; owned: boolean; hides: string | null };   // hides: the one it would replace

/** The room decorations in the game's order; a curtain or rug hides the one showing (the last chosen). */
export function roomOptions(g: ExtrasGame, rules: ExtrasRules): RoomOption[] {
  const owned = Object.keys(g.decorations).filter((d) => rules.decorations.room.includes(d));
  return rules.decorations.room.map((item) => {
    const kind = REPLACES.find((k) => item.startsWith(k));
    const showing = kind ? owned.filter((d) => d.startsWith(kind)).at(-1) ?? null : null;
    return { item, owned: owned.includes(item), hides: showing && showing !== item ? showing : null };
  });
}

export type Status =
  | { kind: 'locked'; months: number | null }   // counted months still to go; null: when the garden opens
  | { kind: 'ready'; free: boolean }
  | { kind: 'have'; count: number; max: number; stage?: number; stages?: number };

const toGo = (at: number, g: ExtrasGame) => Math.max(at - g.garden.qualifying_months, 0);

/** The tree: from the top garden level, one choice, then it grows through its stages. */
export function treeStatus(g: ExtrasGame, rules: ExtrasRules): Status {
  if (g.tree) return { kind: 'have', count: 1, max: 1, stage: g.tree.stage, stages: rules.growth.tree_stages };
  const level = rules.garden.tree_from_garden_level;
  if (!g.garden.open) return { kind: 'locked', months: null };
  if (g.garden.level < level) return { kind: 'locked', months: toGo(rules.garden.level_at_qualifying_months[String(level)], g) };
  return { kind: 'ready', free: false };
}

/** An animal: chosen free at an open animal place, then more of it for a choice each, up to the most. */
export function animalStatus(g: ExtrasGame, rules: ExtrasRules, animal: string): Status {
  const max = rules.garden.max_animals_per_type;
  const count = g.animals[animal] ?? 0;
  if (count > 0) return { kind: 'have', count, max };
  if (!g.garden.open) return { kind: 'locked', months: null };
  if (g.garden.animal_slots_used < g.garden.animal_slots) return { kind: 'ready', free: true };
  const next = rules.garden.animal_slots_at_qualifying_months.find((m) => m > g.garden.qualifying_months);
  return { kind: 'locked', months: next === undefined ? null : toGo(next, g) };
}
