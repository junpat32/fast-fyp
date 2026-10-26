import { AlphaType, ColorType, loadData, Skia, type SkImage } from '@shopify/react-native-skia';

import { ATLAS } from '@/data/art-index';
import type { Period } from '@/lib/timeOfDay';

const pages = new Map<Period, Promise<SkImage | null>>();         // one atlas page per time of day, decoded once
let pixels: { period: Period; data: Promise<{ data: Uint8Array; width: number } | null> } | null = null;

/** The art kit's atlas page for a time of day (D-114). */
export function atlasPage(period: Period): Promise<SkImage | null> {
  if (!pages.has(period)) {
    pages.set(period, loadData(ATLAS[period], (d) => Skia.Image.MakeImageFromEncoded(d)).catch(() => null));
  }
  return pages.get(period)!;
}

/** The page's pixels (RGBA), for making a character sheet (D-125); only the latest time of day is kept
 * (about 5 MB). */
export function atlasPixels(period: Period): Promise<{ data: Uint8Array; width: number } | null> {
  if (pixels?.period !== period) {
    pixels = {
      period,
      data: atlasPage(period).then((img) => {
        if (!img) return null;
        const width = img.width(), height = img.height();
        const data = img.readPixels(0, 0, { width, height, colorType: ColorType.RGBA_8888, alphaType: AlphaType.Unpremul });
        return data instanceof Uint8Array ? { data, width } : null;
      }).catch(() => null),
    };
  }
  return pixels.data;
}
