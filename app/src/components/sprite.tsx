import { Image, PixelRatio, View } from 'react-native';

import { PortraitHost } from '@/components/character/portrait-host';
import { SPRITE_SIZE, SPRITES, TIMES } from '@/data/art-index';
import type { Look } from '@/lib/character';
import type { Mood } from '@/lib/future';
import { spriteDp } from '@/lib/future';
import { periodAt, type Period } from '@/lib/timeOfDay';

/** One of the app sprites (assets/app/sprites, D-111) in the art for the phone's time of day (D-52),
 * or a set one (`period`), at one image pixel per screen pixel so the pixel art stays crisp. */
export function Sprite({ name, min, max, label = '', period }: {
  name: string; min: number; max: number; label?: string; period?: Period;
}) {
  const art = SPRITES[name];
  if (!art) return null;
  const [w, h] = SPRITE_SIZE[name];
  const ratio = PixelRatio.get();
  const height = spriteDp(h, ratio, min, max);
  const now = new Date();
  return (
    <Image source={art[period ?? periodAt(now.getHours(), now.getMinutes(), TIMES)]}
           style={{ width: (w * height) / h, height }} resizeMode="stretch" accessibilityLabel={label} />
  );
}

/** Head and shoulders of the user's character in a mood (the Future screen, the Home character card):
 * drawn from the character sheet, so it has their skin tone and glasses (D-125), in the phone's time of
 * day; the sign-up's picker shows daylight (`period`), so skin and clothes look as they are. */
export function Portrait({ look, mood, label, period, size = 104 }: {
  look: Look; mood: Mood; label: string; period?: Period; size?: number;
}) {
  const now = new Date();
  return (
    <View accessible accessibilityRole="image" accessibilityLabel={label}>
      <PortraitHost look={look} mood={mood} size={size} period={period ?? periodAt(now.getHours(), now.getMinutes(), TIMES)} />
    </View>
  );
}

/** The savings plant at a stage 0-4 (the same plant as on the Home screen). */
export function PlantIcon({ stage, max = 44, label = '' }: { stage: number; max?: number; label?: string }) {
  const s = Math.min(Math.max(Math.round(stage), 0), 4);
  return <Sprite name={`plant_${s}`} min={Math.min(18, max)} max={max} label={label} />;
}
