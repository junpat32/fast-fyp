/**
 * The isometric grid of the art kit (assets/isometric/manifest.json "grid", D-57): every cell is a
 * 64 x 32 px diamond. A piece whose back cell is (gx, gy) is drawn at
 *     mapOrigin + ((gx - gy) * 32, (gx + gy) * 16) - footprintOrigin
 * Taps go the other way (cellAt). Pure functions, no React Native: tested by Node (src/lib/__tests__).
 *
 * Inverse, from the diamond's centre: for cell (gx, gy) the centre sits at tile + (32, 16), so with
 *     a = (x - 32) / 32 = gx - gy   and   b = (y - 16) / 16 = gx + gy
 * gx = (a + b) / 2 and gy = (b - a) / 2; any point inside the diamond rounds to that cell.
 */
export const CELL_W = 64;
export const CELL_H = 32;

export type Point = { x: number; y: number };
export type Cell = [number, number];

const ZERO: Point = { x: 0, y: 0 };

/** Top-left corner of cell (gx, gy)'s 64 x 32 tile, relative to the map origin. */
export function tileOrigin(gx: number, gy: number, mapOrigin: Point = ZERO): Point {
  return { x: mapOrigin.x + (gx - gy) * (CELL_W / 2), y: mapOrigin.y + (gx + gy) * (CELL_H / 2) };
}

/** Where to draw a piece's image: its back cell's tile minus the piece's footprint origin (manifest). */
export function piecePosition(gx: number, gy: number, footprintOrigin: [number, number], mapOrigin: Point = ZERO): Point {
  const t = tileOrigin(gx, gy, mapOrigin);
  return { x: t.x - footprintOrigin[0], y: t.y - footprintOrigin[1] };
}

/** The cell under a screen point (a tap), relative to the same map origin. */
export function cellAt(p: Point, mapOrigin: Point = ZERO): Cell {
  const a = (p.x - mapOrigin.x - CELL_W / 2) / (CELL_W / 2);
  const b = (p.y - mapOrigin.y - CELL_H / 2) / (CELL_H / 2);
  return [round((a + b) / 2), round((b - a) / 2)];
}

/** Math.round gives -0 for values in (-0.5, 0); a cell coordinate must be a plain 0 there. */
function round(v: number): number {
  return Math.round(v) + 0;
}
