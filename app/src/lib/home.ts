/**
 * From GET /v1/game to the home scene's input (D-113): which garden and room, the plants, the tree,
 * decorations, animals and the character, for the time of day. The scene itself is composed by
 * scene.ts exactly as the art previews compose it. Pure TypeScript, tested by Node.
 *
 * App conventions (the API stores them as given): a garden decoration's spot is its back cell "gx,gy"
 * (one of the scene's decor_free_cells); a room decoration's spot is "room:<item>", since room
 * decorations have fixed places (room.json) and the engine only needs spots to differ.
 */
import type { SceneInput, SceneJson } from './scene.ts';
import type { Period } from './timeOfDay.ts';

export type GameLike = {
  room_level: number;
  garden: { open: boolean; level: number; bed_step: number };
  plants: { cell: [number, number]; plant: string; stage: string }[];
  tree: { stage: number } | null;
  decorations: Record<string, string>;
  animals: Record<string, number>;
  look: { mood: string; plants: string; coin_jar: number; savings_plant: number };
};
export type Lists = {
  roomDecor: string[];                                      // shared/game.json decorations.room
  gardenDecor: string[];                                    // shared/game.json decorations.garden
  pieces: Record<string, [number, number, number, number, number, number]>;   // KIT_GEOM
};

export const STAND_CELL: [number, number] = [4, 4];        // where the character stands by day (the previews)
export const BED_CELL: [number, number] = [0, 0];          // the bed's cell: asleep there at night

export function gardenLevel(g: GameLike): number {
  return g.garden.open ? g.garden.level : 0;
}

const droops = (g: GameLike) => g.look.plants !== 'normal';                // 'droop' or 'rest' (D-73)
const MOODS = ['relaxed', 'calm', 'focused', 'concerned_hopeful', 'celebrating'];

/** The tree's piece at a stage: tree_<stage>_<name>[_droop], the name read from the kit. */
export function treePiece(stage: number, droop: boolean, lists: Lists): string | null {
  const name = Object.keys(lists.pieces).find((n) => n.startsWith(`tree_${stage}_`) && !n.endsWith('_droop'));
  return name ? `${name}${droop ? '_droop' : ''}` : null;
}

/** The scene's home for an animal: the engine says "chicken" (game.json animals), the kit "chickens". */
export function animalHome(animal: string, scene: SceneJson): string | null {
  return [animal, `${animal}s`].find((k) => scene.animal_homes[k]) ?? null;
}

export function homeInput(g: GameLike, scene: SceneJson, period: Period, avatar: number, lists: Lists): SceneInput {
  const droop = droops(g);
  const extras: NonNullable<SceneInput['extras']> = [];
  if (g.tree && scene.tree) {
    const piece = treePiece(g.tree.stage, droop, lists);
    if (piece) extras.push([scene.tree.cell[0], scene.tree.cell[1], piece, scene.tree.size, 0]);
  }
  for (const [item, spot] of Object.entries(g.decorations)) {
    const m = /^(-?\d+),(-?\d+)$/.exec(spot);
    const geo = lists.pieces[item];
    if (lists.gardenDecor.includes(item) && m && geo) extras.push([Number(m[1]), Number(m[2]), item, [geo[4], geo[5]], 0]);
  }
  const night = period === 'night';
  if (night) {                                    // asleep in bed (characters.json "draw"), 19:00-05:59
    const bed = g.room_level >= 2 ? 'bed' : 'mattress';
    extras.push([BED_CELL[0], BED_CELL[1], `avatar_0${avatar}_sleep_${bed}_1`, [1, 2], 0.35]);
  } else {
    const mood = MOODS.includes(g.look.mood) ? g.look.mood : 'calm';
    extras.push([STAND_CELL[0], STAND_CELL[1], `avatar_0${avatar}_mood_${mood}`, [1, 1], 0.3]);
  }
  const homes: string[] = [];
  for (const [animal, count] of Object.entries(g.animals)) {   // chickens round their coop; asleep at night
    const home = animalHome(animal, scene);
    if (!home || count < 1) continue;
    homes.push(home);
    const [sx, sy] = scene.animal_homes[home].sleep_cell;
    for (let i = 0; i < count; i++) {
      const frame = night ? 'sleep_0' : i % 2 ? 'peck_0' : 'idle_0';
      extras.push([sx + i, sy, `${animal}_${frame}${i % 2 ? '|flip' : ''}`, [1, 1], 0.3]);
    }
  }
  return {
    bedSteps: g.garden.bed_step,
    animals: homes,
    room: {
      level: g.room_level, jar: g.look.coin_jar, plant: g.look.savings_plant, droop,
      decor: Object.keys(g.decorations).filter((d) => lists.roomDecor.includes(d)),     // in the order chosen
    },
    plants: g.plants.map((p): [number, number, string] => [p.cell[0], p.cell[1], `plant_${p.plant}_${p.stage}${droop ? '_droop' : ''}`]),
    extras,
  };
}
