/**
 * The garden's rules on the phone (D-115): what planting and digging do, and what the Home cards
 * show about plants. With the real API the server replays every action (engine/game.py _apply, C4);
 * sample data mode, which can't save, applies the same rules here, with the engine's own messages.
 * Pure TypeScript, tested by Node.
 *
 * Plant (engine G-rules): the garden is open; the cell is in the bed and empty; the plant is known
 * and unlocked at the garden's plant tier; one waiting in the seed box goes in free, keeping its
 * growth, otherwise it costs one choice (every 200 points gives one). Dig: the plant goes to the seed
 * box with its growth. Stages: a seedling, young after 7 growing days, full grown after 21.
 */
export type GardenRules = {
  garden: {
    plants: Record<string, number>; plant_tier_at_qualifying_months: Record<string, number>;
    tree_from_garden_level: number; animals: string[]; max_animals_per_type: number;
  };
  decorations: { room: string[]; garden: string[] };
  growth: { young_after_growing_days: number; full_after_growing_days: number };
  choices: { points_per_choice: number };
};
export type PlantAction = { kind: 'plant'; cell: [number, number]; item: string } | { kind: 'dig'; cell: [number, number] };
/** Every action the game takes (POST /v1/game/actions): plants, and the Home extras (D-120). */
export type GameMove =
  | PlantAction
  | { kind: 'buy_tree' }
  | { kind: 'decorate' | 'move_decoration'; item: string; spot: string }
  | { kind: 'choose_animal' | 'add_animal'; item: string };
type Growing = { plant: string; growing_days: number };
export type GardenState = {
  garden: {
    open: boolean; level: number; qualifying_months: number; plant_tier: number; bed: [number, number][];
    animal_slots: number; animal_slots_used: number;
  };
  plants: { cell: [number, number]; plant: string; stage: string; growing_days: number }[];
  seed_box: string[];
  choices: { earned: number; used: number; available: number };
  tree: { stage: number } | null;
  decorations: Record<string, string>;
  animals: Record<string, number>;
};

export class GameRuleError extends Error {}

const same = (a: [number, number], b: [number, number]) => a[0] === b[0] && a[1] === b[1];

export function stageOf(days: number, rules: GardenRules): 'seedling' | 'young' | 'full' {
  if (days >= rules.growth.full_after_growing_days) return 'full';
  return days >= rules.growth.young_after_growing_days ? 'young' : 'seedling';
}

/**
 * The game after a list of actions, applied in order; a refused one throws. With `onRefused`, a
 * refused action is reported and skipped instead, as the server's replay does (strict=False, C4):
 * after time travel, an action made earlier may no longer fit the later garden. Every check comes
 * before any change, so a skipped action leaves nothing behind. The extras (D-120) follow
 * engine/game.py _apply too: the tree from the top garden level, decorations once each on a free
 * spot, the first animal free at an open animal place and more for a choice each.
 */
export function applyActions<G extends GardenState>(game: G, actions: GameMove[], rules: GardenRules,
                                                    onRefused?: (a: GameMove, e: GameRuleError) => void): G {
  const plants = game.plants.map((p) => ({ ...p }));
  const box: Growing[] = game.seed_box.map((plant) => ({ plant, growing_days: 0 }));   // the server keeps their days
  const choices = { ...game.choices };
  const garden = { ...game.garden };
  const decorations = { ...game.decorations };
  const animals = { ...game.animals };
  let tree = game.tree;
  for (const a of actions) {
    try {
      apply(a);
    } catch (e) {
      if (!(onRefused && e instanceof GameRuleError)) throw e;
      onRefused(a, e);
    }
  }
  return { ...game, plants, seed_box: box.map((b) => b.plant), choices, garden, decorations, animals, tree };

  function spend() {
    if (choices.available < 1) {
      throw new GameRuleError(`no choice available yet: every ${rules.choices.points_per_choice} points gives one`);
    }
    choices.used += 1;
    choices.available -= 1;
  }

  function apply(a: GameMove) {
    const g = rules.garden;
    if (a.kind === 'buy_tree') {
      if (garden.level < g.tree_from_garden_level || !garden.open) throw new GameRuleError('the tree needs the bigger garden (G4)');
      if (tree) throw new GameRuleError('the garden already has its tree');
      spend();
      tree = { stage: 0 };
      return;
    }
    if (a.kind === 'decorate' || a.kind === 'move_decoration') {
      const taken = Object.entries(decorations).some(([item, spot]) => spot === a.spot && item !== a.item);
      if (a.kind === 'move_decoration') {
        if (!(a.item in decorations)) throw new GameRuleError("you don't have that decoration");
        if (taken) throw new GameRuleError('that spot is taken');
        decorations[a.item] = a.spot;
        return;
      }
      if (![...rules.decorations.room, ...rules.decorations.garden].includes(a.item)) {
        throw new GameRuleError(`unknown decoration: ${a.item}`);
      }
      if (rules.decorations.garden.includes(a.item) && !garden.open) throw new GameRuleError("the garden isn't open yet");
      if (a.item in decorations) throw new GameRuleError('you already have that one');
      if (taken) throw new GameRuleError('that spot is taken');
      spend();
      decorations[a.item] = a.spot;
      return;
    }
    if (a.kind === 'choose_animal') {
      if (!g.animals.includes(a.item)) throw new GameRuleError(`unknown animal: ${a.item}`);
      if (garden.animal_slots_used >= garden.animal_slots) throw new GameRuleError('no animal slot open yet');
      if (a.item in animals) throw new GameRuleError('you already have that animal; add another with a choice');
      animals[a.item] = 1;
      garden.animal_slots_used += 1;
      return;
    }
    if (a.kind === 'add_animal') {
      if (!(a.item in animals)) throw new GameRuleError('choose this animal at an animal slot first');
      if (animals[a.item] >= g.max_animals_per_type) throw new GameRuleError(`at most ${g.max_animals_per_type} of each animal`);
      spend();
      animals[a.item] += 1;
      return;
    }
    if (a.kind === 'plant') {
      if (!game.garden.open) throw new GameRuleError("the garden isn't open yet");
      if (!game.garden.bed.some((c) => same(c, a.cell))) throw new GameRuleError('plants go in the flower bed');
      if (plants.some((p) => same(p.cell, a.cell))) throw new GameRuleError('something is already growing there');
      const tier = rules.garden.plants[a.item];
      if (tier === undefined) throw new GameRuleError(`unknown plant: ${a.item}`);
      if (tier > game.garden.plant_tier) throw new GameRuleError('that plant unlocks with more months of keeping your buffer');
      const i = box.findIndex((b) => b.plant === a.item);
      let days = 0;
      if (i >= 0) days = box.splice(i, 1)[0].growing_days;
      else spend();
      plants.push({ cell: a.cell, plant: a.item, stage: stageOf(days, rules), growing_days: days });
    } else if (a.kind === 'dig') {
      const i = plants.findIndex((p) => same(p.cell, a.cell));
      if (i < 0) throw new GameRuleError('nothing planted there');
      const [p] = plants.splice(i, 1);
      box.push({ plant: p.plant, growing_days: p.growing_days });
    }
  }
}

/** Points still needed for the next choice (engine: choices earned = points // 200 + free ones). */
export function pointsToNextChoice(points: number, rules: GardenRules): number {
  const per = rules.choices.points_per_choice;
  return per - (points % per);
}

/** Bed cells with nothing growing: where a plant can go. */
export function freeBedCells(game: GardenState): [number, number][] {
  return game.garden.bed.filter((c) => !game.plants.some((p) => same(p.cell, c)));
}

export type PlantOption = {
  plant: string; tier: number; unlocked: boolean; free: boolean; unlockInMonths: number;
};

/** The seed picker: every plant in the game's order, what it costs, or how far away it is. */
export function plantOptions(game: GardenState, rules: GardenRules): PlantOption[] {
  return Object.entries(rules.garden.plants).map(([plant, tier]) => {
    const at = rules.garden.plant_tier_at_qualifying_months[String(tier)] ?? 0;
    return { plant, tier, unlocked: tier <= game.garden.plant_tier, free: game.seed_box.includes(plant),
             unlockInMonths: Math.max(at - game.garden.qualifying_months, 0) };
  });
}

/** Where a plant is on its way to full grown: "Young in 3 growing days", or "Full grown". */
export function growthLine(days: number, rules: GardenRules): string {
  const { young_after_growing_days: young, full_after_growing_days: full } = rules.growth;
  const left = (n: number) => `${n} growing ${n === 1 ? 'day' : 'days'}`;
  if (days >= full) return 'Full grown';
  if (days >= young) return `Full grown in ${left(full - days)}`;
  return `Young in ${left(young - days)}, full grown in ${left(full - days)}`;
}

export const PLANT_NAMES: Record<string, string> = {
  serai: 'Serai (lemongrass)', pandan: 'Pandan', chilli: 'Chilli', bunga_raya: 'Bunga raya',
  bougainvillea: 'Bougainvillea', ixora: 'Ixora (jejarum)', orchid: 'Orchid', frangipani: 'Frangipani (kemboja)',
  torch_ginger: 'Torch ginger (kantan)', jade_vine: 'Jade vine',
};
