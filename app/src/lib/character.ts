/**
 * The user's character (decision A1; D-125): the art kit draws every avatar once, in the base skin tone
 * (tone 3) and without glasses. The app makes a small sheet of the chosen avatar's frames in the chosen
 * tone, with glasses painted onto each front frame at its head height (characters.json), and draws the
 * character from that sheet everywhere: the Home scene, its idle loops and the portraits. Pure
 * TypeScript, tested by Node against the kit's own recolouring (palette.to_rgba with a tone).
 *
 * Invariants
 *   CH1 an exact swap: a pixel changes only if it is exactly one of the base tone's three skin colours
 *       for that time of day; no other colour in the character art equals them (checked in Python)
 *   CH2 glasses go only on frames whose `glasses` is true, moved up by that frame's head_dy
 *   CH3 nothing else changes: outline, hair, clothes and transparency are copied as they are
 * Cost: O(pixels of one avatar's frames), about 60k, once per look and time of day.
 */
import type { Period } from './timeOfDay.ts';

export type Rect6 = [number, number, number, number, number, number];   // atlas x, y, w, h; canvas ox, oy
export type Look = { avatar: number; tone: number; glasses: boolean };   // avatar 1-6, tone 1-6 (profiles)
export type Characters = {
  avatars: { name: string; suggested_tone: number;
             frames: Record<string, { head_dy: number; glasses: boolean; view: string }> }[];
  skin_tones: Record<Period, string[]>[];
  glasses: { piece: string };
};

export const BASE_TONE = 3;                    // the kit's own skin (palette.py: tone 3 is the base palette's)
export const TONES = 6;

/** The tone an avatar is shown in until the user picks one (characters.json counts tones from 0). */
export const suggestedTone = (avatar: number, ch: Characters) => ch.avatars[avatar - 1].suggested_tone + 1;

export type SheetFrame = { piece: string; box: [number, number, number, number]; headDy: number; glasses: boolean };
export type SheetLayout = { width: number; height: number; rects: Record<string, Rect6> };

/** The chosen avatar's frames in the kit, each with the part of its canvas the sheet keeps: its opaque
 * pixels, and the glasses' when it wears them (canvas coordinates x0, y0, x1, y1). */
export function sheetFrames(look: Look, ch: Characters, kit: Record<string, Rect6>): SheetFrame[] {
  const avatar = ch.avatars[look.avatar - 1];
  const g = kit[ch.glasses.piece];
  const out: SheetFrame[] = [];
  for (const [frame, f] of Object.entries(avatar.frames)) {
    const piece = `${avatar.name}_${frame}`;
    const r = kit[piece];
    if (!r || r[2] === 0) continue;
    const glasses = look.glasses && f.glasses && !!g && g[2] > 0;
    const box: [number, number, number, number] = [r[4], r[5], r[4] + r[2], r[5] + r[3]];
    if (glasses) {
      box[0] = Math.min(box[0], g[4]); box[1] = Math.min(box[1], g[5] - f.head_dy);
      box[2] = Math.max(box[2], g[4] + g[2]); box[3] = Math.max(box[3], g[5] + g[3] - f.head_dy);
    }
    out.push({ piece, box, headDy: f.head_dy, glasses });
  }
  return out;
}

/** Where each frame goes on the sheet: rows left to right, a clear pixel between frames. */
export function sheetLayout(frames: SheetFrame[], width = 512): SheetLayout {
  const rects: Record<string, Rect6> = {};
  let x = 0, y = 0, row = 0;
  for (const f of frames) {
    const w = f.box[2] - f.box[0], h = f.box[3] - f.box[1];
    if (x + w > width) { x = 0; y += row + 1; row = 0; }
    rects[f.piece] = [x, y, w, h, f.box[0], f.box[1]];
    x += w + 1;
    row = Math.max(row, h);
  }
  return { width, height: y + row, rects };
}

const rgb = (hex: string): [number, number, number] =>
  [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];

/** The sheet's pixels (RGBA): each frame copied from the atlas page's pixels (`atlas`, `atlasWidth`
 * wide), its skin swapped to the look's tone (CH1), and the glasses painted on where they go (CH2). */
export function paintSheet(frames: SheetFrame[], layout: SheetLayout, atlas: Uint8Array, atlasWidth: number,
                           kit: Record<string, Rect6>, look: Look, period: Period, ch: Characters): Uint8Array {
  const out = new Uint8Array(layout.width * layout.height * 4);
  const from = ch.skin_tones[BASE_TONE - 1][period].map(rgb);
  const to = ch.skin_tones[look.tone - 1][period].map(rgb);
  const swap = look.tone !== BASE_TONE;
  const put = (sx: number, sy: number, dx: number, dy: number, skin: boolean) => {
    const s = (sy * atlasWidth + sx) * 4, d = (dy * layout.width + dx) * 4;
    const a = atlas[s + 3];
    if (a === 0) return;
    let r = atlas[s], gg = atlas[s + 1], b = atlas[s + 2];
    if (skin && swap && a === 255) {
      const k = from.findIndex(([fr, fg, fb]) => fr === r && fg === gg && fb === b);
      if (k >= 0) [r, gg, b] = to[k];
    }
    out[d] = r; out[d + 1] = gg; out[d + 2] = b; out[d + 3] = a;
  };
  const g = kit[ch.glasses.piece];
  for (const f of frames) {
    const [x, y, w, h, ox, oy] = kit[f.piece];
    const [dx, dy, , , dox, doy] = layout.rects[f.piece];
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) put(x + i, y + j, dx + ox + i - dox, dy + oy + j - doy, true);
    if (!f.glasses) continue;
    const [gx, gy, gw, gh, gox, goy] = g;                          // CH2: up by the frame's head_dy
    for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) put(gx + i, gy + j, dx + gox + i - dox, dy + goy - f.headDy + j - doy, false);
  }
  return out;
}

/** The part of a frame a portrait shows (the kit's PORTRAIT_BOX: hair, face and shoulders, 48 x 48 art
 * pixels), as source and destination rectangles: the sheet holds only the frame's own pixels, so the
 * box is cut to them, and the rest of the portrait stays clear. */
export const PORTRAIT_BOX: [number, number, number, number] = [16, 66, 64, 114];
export function portraitRects(r: Rect6, box = PORTRAIT_BOX): { src: [number, number, number, number]; dst: [number, number, number, number] } | null {
  const [x, y, w, h, ox, oy] = r;
  const x0 = Math.max(box[0], ox), y0 = Math.max(box[1], oy), x1 = Math.min(box[2], ox + w), y1 = Math.min(box[3], oy + h);
  if (x1 <= x0 || y1 <= y0) return null;
  return { src: [x + x0 - ox, y + y0 - oy, x1 - x0, y1 - y0], dst: [x0 - box[0], y0 - box[1], x1 - x0, y1 - y0] };
}

/** A whole-number scale for crisp pixels: the portrait's art pixels at k device pixels each, nearest the
 * wanted size in dp; returns the size in dp. */
export function crispSize(wantDp: number, pixelRatio: number, artPx = PORTRAIT_BOX[2] - PORTRAIT_BOX[0]): number {
  const k = Math.max(1, Math.round((wantDp * pixelRatio) / artPx));
  return (k * artPx) / pixelRatio;
}
