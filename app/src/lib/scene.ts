/**
 * The home scene (D-113): which kit pieces to draw, where, and in what order. A port of
 * tools/asset_generation/scenes.py home_scene (from the kit's scene and room JSON, D-88) and of the
 * view the art previews use (preview.phone_scene: a 540 x 1200 view with the room's back corner at
 * (270, 330)), kept equal to them by a fixture made in Python (tools/app_fixtures.py, scene.test.ts).
 *
 * Order: every visible cell's ground tile; the rugs; the neighbourhood (behind the plot); then the
 * home's structures (walls, fences, beds, the animals' homes, furniture, plants, extras), sorted by
 * front cell plus a layer and then by depthSort, so a piece wholly behind another is drawn first.
 * Pure TypeScript: tested by Node.
 * Cost: O(cells) ground + O(n^2) depthSort, n up to ~200 structures.
 */
import { depthSort } from './depthSort.ts';
import type { Point } from './iso.ts';

export const VIEW_W = 540;                       // preview.py PHONE: art pixels, shown at 2x on a 1080 px phone
export const VIEW_H = 1200;
export const ROOM_TOP: Point = { x: 270, y: 330 };          // preview.py ROOM_TOP: cell (0, 0)'s top vertex
export const MAP_ORIGIN: Point = { x: ROOM_TOP.x - 32, y: ROOM_TOP.y };

type C2 = [number, number];
type CellPiece = [number, number, string];
export type SceneJson = {
  level: number;
  room: [number, number, number, number];
  animal_homes: Record<string, { piece: string; cell: C2; size: C2; sleep_cell: C2 }>;
  tree: { cell: C2; size: C2 } | null;
  decor_free_cells: C2[];
  default_ground: string;
  ground: CellPiece[];
  background: CellPiece[];
  structures: CellPiece[];
  bed_growth?: { step: number; cells: C2[]; loop: C2[]; edging: CellPiece[] }[];
};
export type Furniture = [number, number, string, C2, number | 'floor'];
export type RoomJson = {
  floor: Record<string, string>;
  kitchen_floor: { piece: string; cells: C2[] };
  levels: Record<string, { label: string; furniture: Furniture[] }>;
  decorations: Record<string, { replaces: string | null; from_room_level: Record<string, Furniture[]> }>;
  interactive: Record<string, string>;
};
/** Mirrors home_scene's arguments: room_state, plants {cell: piece}, extras [(cell, piece, size, layer)]. */
export type SceneInput = {
  bedSteps?: number;
  animals?: string[] | null;
  room?: { level: number; jar?: number; plant?: number; droop?: boolean; decor?: string[] } | null;
  plants?: CellPiece[];
  extras?: [number, number, string, C2, number][];
};
export type Placed = { gx: number; gy: number; name: string; w: number; d: number };
export type Composed = {
  ground: Map<string, string>; defaultGround: string; decals: Placed[]; background: Placed[]; structs: Placed[];
};

const key = (gx: number, gy: number) => `${gx},${gy}`;
const base = (name: string) => name.split('|')[0];

/** The pieces of the home for one game state, in drawing order (scenes.home_scene). */
export function composeScene(scene: SceneJson, room: RoomJson, input: SceneInput): Composed {
  const ground = new Map(scene.ground.map(([gx, gy, n]) => [key(gx, gy), n]));
  let structures = scene.structures;
  const growth = scene.bed_growth ?? [];
  const steps = Math.min(input.bedSteps ?? 0, growth.length);
  if (steps > 0) {                               // the bed's monthly growth at G4 (scene JSON "draw")
    for (const g of growth.slice(0, steps)) for (const [gx, gy] of g.cells) ground.set(key(gx, gy), 'garden_soil_improved');
    for (const [gx, gy] of growth[steps - 1].loop) ground.set(key(gx, gy), 'path_nice_paved');
    structures = [...structures.filter(([, , n]) => !n.startsWith('garden_border_')), ...growth[steps - 1].edging];
  }
  const st = input.room ?? null;
  if (st) {                                      // the room's floor at its level, the kitchen tiles kept
    const [x0, y0, w, d] = scene.room;
    const kitchen = new Set(room.kitchen_floor.cells.map(([gx, gy]) => key(gx, gy)));
    for (let gx = x0; gx < x0 + w; gx++) {
      for (let gy = y0; gy < y0 + d; gy++) {
        ground.set(key(gx, gy), kitchen.has(key(gx, gy)) ? room.kitchen_floor.piece : room.floor[String(st.level)]);
      }
    }
  }

  // insertion order as home_scene builds it: the room's walls, the garden's structures, the animals'
  // homes, furniture, plants, extras (ties in the sort below keep this order)
  const walls = structures.filter(([, , n]) => n.startsWith('wall_'));
  const garden = structures.filter(([, , n]) => !n.startsWith('wall_'));
  type Item = Placed & { k: number };
  const items: Item[] = [];
  const add = (gx: number, gy: number, name: string, w = 1, d = 1, layer = 0) =>
    items.push({ gx, gy, name, w, d, k: gx + gy + w + d - 2 + layer });
  for (const [gx, gy, n] of [...walls, ...garden]) add(gx, gy, n, 1, 1, n.startsWith('wall_cutaway') ? 0.5 : 0);
  const animals = input.animals ?? (scene.level >= 2 ? ['chickens'] : []);
  for (const a of animals) {
    const h = scene.animal_homes[a];
    if (h) add(h.cell[0], h.cell[1], h.piece, h.size[0], h.size[1]);
  }
  const decals: Placed[] = [];
  if (st) {
    for (const [gx, gy, name, [w, d], layer] of roomFurniture(room, st)) {
      if (layer === 'floor') decals.push({ gx, gy, name, w, d });
      else add(gx, gy, name, w, d, layer);
    }
  }
  for (const [gx, gy, name] of input.plants ?? []) add(gx, gy, name);
  for (const [gx, gy, name, [w, d], layer] of input.extras ?? []) add(gx, gy, name, w, d, layer);
  const sorted = items.map((it, i) => ({ it, i })).sort((a, b) => a.it.k - b.it.k || a.i - b.i).map(({ it }) => it);
  const structs = depthSort(sorted).map(({ gx, gy, name, w, d }) => ({ gx, gy, name, w, d }));
  return {
    ground, defaultGround: scene.default_ground, decals,
    background: scene.background.map(([gx, gy, name]) => ({ gx, gy, name, w: 1, d: 1 })),
    structs,
  };
}

/** The room's furniture at its level with the chosen decorations, the coin jar and the savings plant
 * filled in (scenes.room_furniture; room.json "draw"). */
export function roomFurniture(room: RoomJson, st: NonNullable<SceneInput['room']>): Furniture[] {
  let out = [...room.levels[String(st.level)].furniture];
  for (const name of st.decor ?? []) {
    const deco = room.decorations[name];
    if (!deco) continue;
    if (deco.replaces) out = out.filter((f) => !f[2].startsWith(deco.replaces!));
    const levels = Object.keys(deco.from_room_level).map(Number).filter((lv) => lv <= st.level);
    if (levels.length) out = out.concat(deco.from_room_level[String(Math.max(...levels))]);
  }
  const plant = `${st.plant ?? 0}${st.droop ? '_droop' : ''}`;
  return out.map(([gx, gy, n, s, layer]) =>
    [gx, gy, n.replace('{jar}', String(st.jar ?? 0)).replace('{plant}', plant), s, layer]);
}

/** Every cell with any part of its tile inside the view, in the previews' order (phone_scene). */
export function visibleCells(): C2[] {
  const { x: ox, y: oy } = MAP_ORIGIN;
  const out: C2[] = [];
  for (let s = Math.floor((-oy - 32) / 16); s <= Math.ceil((VIEW_H - oy) / 16); s++) {
    for (let t = Math.floor((-ox - 64) / 32); t <= Math.ceil((VIEW_W - ox) / 32); t++) {
      if ((((s + t) % 2) + 2) % 2 === 0) out.push([Math.floor((s + t) / 2), Math.floor((s - t) / 2)]);
    }
  }
  return out;
}

/** footprint origin and canvas of a kit piece: [fx, fy, width, height] (manifest.json). */
export type Geometry = Record<string, [number, number, number, number]>;
export type Draw = { name: string; piece: string; flip: boolean; x: number; y: number; layer: 'ground' | 'decal' | 'background' | 'struct' };

/** Where each image goes in the 540 x 1200 view (top-left corner); a "|flip" piece is mirrored, so
 * its footprint origin moves to w - x - 64 (preview.Kit.get). */
export function draws(c: Composed, geom: Geometry): Draw[] {
  const at = (gx: number, gy: number, name: string, layer: Draw['layer']): Draw => {
    const piece = base(name);
    const flip = name.endsWith('|flip');
    const [fx0, fy, w] = geom[piece] ?? [0, 0, 64];
    const fx = flip ? w - fx0 - 64 : fx0;
    return { name, piece, flip, layer, x: MAP_ORIGIN.x + (gx - gy) * 32 - fx, y: MAP_ORIGIN.y + (gx + gy) * 16 - fy };
  };
  return [
    ...visibleCells().map(([gx, gy]) => at(gx, gy, c.ground.get(key(gx, gy)) ?? c.defaultGround, 'ground')),
    ...c.decals.map((p) => at(p.gx, p.gy, p.name, 'decal')),
    ...c.background.map((p) => at(p.gx, p.gy, p.name, 'background')),
    ...c.structs.map((p) => at(p.gx, p.gy, p.name, 'struct')),
  ];
}
