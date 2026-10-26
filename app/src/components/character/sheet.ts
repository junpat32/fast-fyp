import { AlphaType, ColorType, Skia, type SkImage } from '@shopify/react-native-skia';

import { KIT_RECT } from '@/data/art-index';
import { CHARACTERS } from '@/data/kit';
import { paintSheet, sheetFrames, sheetLayout, type Look, type Rect6 } from '@/lib/character';
import type { Period } from '@/lib/timeOfDay';

import { atlasPixels } from './atlas';

export type Sheet = { image: SkImage; rects: Record<string, Rect6> };
const sheets = new Map<string, Promise<Sheet | null>>();

/**
 * The chosen avatar's frames in the chosen skin tone, with glasses where they go (A1, D-125; the
 * pixels come from lib/character.ts, tested against the kit's own recolouring), as a Skia image with
 * each frame's place on it. Made once per look and time of day and kept.
 */
export function characterSheet(look: Look, period: Period): Promise<Sheet | null> {
  const key = `${look.avatar}:${look.tone}:${look.glasses}:${period}`;
  if (!sheets.has(key)) {
    sheets.set(key, atlasPixels(period).then((px) => {
      if (!px) return null;
      const frames = sheetFrames(look, CHARACTERS, KIT_RECT);
      const layout = sheetLayout(frames);
      const bytes = paintSheet(frames, layout, px.data, px.width, KIT_RECT, look, period, CHARACTERS);
      const image = Skia.Image.MakeImage(
        { width: layout.width, height: Math.max(layout.height, 1), colorType: ColorType.RGBA_8888, alphaType: AlphaType.Unpremul },
        Skia.Data.fromBytes(bytes), layout.width * 4);
      return image ? { image, rects: layout.rects } : null;
    }).catch(() => null));
  }
  return sheets.get(key)!;
}
