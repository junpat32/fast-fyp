import { Canvas, FilterMode, MipmapMode, Picture, Skia } from '@shopify/react-native-skia';
import { useEffect, useMemo, useState } from 'react';
import { PixelRatio, View } from 'react-native';

import { crispSize, portraitRects, type Look } from '@/lib/character';
import type { Mood } from '@/lib/future';
import type { Period } from '@/lib/timeOfDay';

import { characterSheet, type Sheet } from './sheet';

/**
 * Head and shoulders of the user's character in a mood (the Future screen's two selves, the Home
 * character card, the sign-up's picker): the mood frame from the character sheet, so it shows the
 * chosen skin tone and glasses (D-125), cut to the kit's portrait box and drawn nearest-neighbour at a
 * whole number of device pixels per art pixel, so it stays crisp.
 */
export default function CharacterPortrait({ look, mood, period, size }: { look: Look; mood: Mood; period: Period; size: number }) {
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const { avatar, tone, glasses } = look;
  useEffect(() => {
    let alive = true;
    characterSheet({ avatar, tone, glasses }, period).then((s) => { if (alive) setSheet(s); });
    return () => { alive = false; };
  }, [avatar, tone, glasses, period]);
  const dp = crispSize(size, PixelRatio.get());
  const picture = useMemo(() => {
    const r = sheet?.rects[`avatar_0${avatar}_mood_${mood}`];
    const cut = r && portraitRects(r);
    if (!sheet || !cut) return null;
    const k = dp / 48;
    const rec = Skia.PictureRecorder();
    const c = rec.beginRecording(Skia.XYWHRect(0, 0, dp, dp));
    c.drawImageRectOptions(sheet.image, Skia.XYWHRect(...cut.src),
                           Skia.XYWHRect(cut.dst[0] * k, cut.dst[1] * k, cut.dst[2] * k, cut.dst[3] * k),
                           FilterMode.Nearest, MipmapMode.None);
    return rec.finishRecordingAsPicture();
  }, [sheet, avatar, mood, dp]);
  return (
    <View style={{ width: dp, height: dp }}>
      {picture && <Canvas style={{ width: dp, height: dp }}><Picture picture={picture} /></Canvas>}
    </View>
  );
}
