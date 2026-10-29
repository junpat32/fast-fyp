import {
  Canvas, FilterMode, Group, MipmapMode, Path, Picture, Skia, type SkCanvas, type SkImage, type SkPicture,
  type Transforms3d,
} from '@shopify/react-native-skia';
import { useEffect, useMemo, useState } from 'react';
import { useDerivedValue, useSharedValue, withRepeat, withTiming, type DerivedValue, type SharedValue } from 'react-native-reanimated';

import { atlasPage } from '@/components/character/atlas';
import { characterSheet, type Sheet } from '@/components/character/sheet';
import { KIT_GEOM, KIT_RECT } from '@/data/art-index';
import { frameAt, idleLoop } from '@/lib/animate';
import type { Look } from '@/lib/character';
import { MAP_ORIGIN, VIEW_H, VIEW_W, type Draw } from '@/lib/scene';
import type { Period } from '@/lib/timeOfDay';

const inKit = (name: string) => (KIT_RECT[name]?.[2] ?? 0) > 0;
const TICK_MS = 100;                                              // the idle clock's step
type Art = { atlas: SkImage; sheet: Sheet | null };

/** One piece: a sub-rectangle of the atlas (its opaque pixels, at their place on the piece's canvas),
 * nearest-neighbour so the pixel art stays crisp at any size; a "|flip" piece is mirrored. The
 * character's frames come from its sheet instead: its skin tone and glasses (D-125). */
function drawPiece(c: SkCanvas, d: Draw, piece: string, art: Art) {
  const own = art.sheet?.rects[piece];
  const r = own ?? KIT_RECT[piece];
  const atlas = own ? art.sheet!.image : art.atlas;
  if (!r || r[2] === 0) return;
  const [x, y, w, h, ox, oy] = r;
  const src = Skia.XYWHRect(x, y, w, h);
  if (d.flip) {
    c.save();
    c.translate(d.x + KIT_GEOM[piece][2], d.y);                   // mirror across the canvas's width
    c.scale(-1, 1);
    c.drawImageRectOptions(atlas, src, Skia.XYWHRect(ox, oy, w, h), FilterMode.Nearest, MipmapMode.None);
    c.restore();
  } else {
    c.drawImageRectOptions(atlas, src, Skia.XYWHRect(d.x + ox, d.y + oy, w, h), FilterMode.Nearest, MipmapMode.None);
  }
}

function record(draw: (c: SkCanvas) => void): SkPicture {
  const rec = Skia.PictureRecorder();
  draw(rec.beginRecording(Skia.XYWHRect(0, 0, VIEW_W, VIEW_H)));
  return rec.finishRecordingAsPicture();
}

type Layer =
  | { kind: 'still'; picture: SkPicture }
  | { kind: 'idle'; pictures: SkPicture[]; ms: number[]; offset: number };

/**
 * The scene as layers in drawing order (D-116): runs of still pieces recorded once as one picture
 * each, and between them every piece that idles, as one small picture per frame of its loop. The
 * depth order is exactly the composed one (scene.ts); only the idling pieces change.
 */
function layers(list: Draw[], art: Art): Layer[] {
  const out: Layer[] = [];
  let run: Draw[] = [];
  let n = 0;
  const flush = () => {
    if (run.length) {
      const still = run;
      out.push({ kind: 'still', picture: record((c) => still.forEach((d) => drawPiece(c, d, d.piece, art))) });
    }
    run = [];
  };
  for (const d of list) {
    const loop = d.layer === 'struct' ? idleLoop(d.piece, inKit) : null;
    if (!loop) { run.push(d); continue; }
    flush();
    out.push({ kind: 'idle', pictures: loop.frames.map((f) => record((c) => drawPiece(c, d, f, art))), ms: loop.ms,
               offset: (n++) * 370 });                            // each one a little out of step
  }
  flush();
  return out;
}

function IdlePiece({ layer, tick }: { layer: Extract<Layer, { kind: 'idle' }>; tick: SharedValue<number> }) {
  const { pictures, ms, offset } = layer;
  const picture = useDerivedValue(() => pictures[frameAt(ms, tick.value + offset)]);
  return <Picture picture={picture} />;
}

/** Diamonds over cells (where a plant can go, D-115), in the view's art pixels. */
function diamonds(cells: [number, number][]) {
  const p = Skia.PathBuilder.Make();                         // Skia 2.14 (SDK 58): built, then frozen
  for (const [gx, gy] of cells) {
    const x = MAP_ORIGIN.x + (gx - gy) * 32;
    const y = MAP_ORIGIN.y + (gx + gy) * 16;
    p.moveTo(x + 32, y + 1).lineTo(x + 63, y + 16).lineTo(x + 32, y + 31).lineTo(x + 1, y + 16).close();
  }
  return p.detach();
}

/** The home scene (D-113): the 540 x 1200 view of the art previews in a width x height canvas, placed
 * by `transform` (pan and pinch, D-114: a shared value, so zooming redraws on the UI thread, sharp at
 * any size, without a React render). `highlight` cells glow gently (where a plant can go, D-115).
 * While `animate` (the Home tab is showing), the character and the chickens idle (D-116). The
 * character wears the user's skin tone and glasses (`look`, D-125). */
export default function HomeScene({ list, period, look, width, height, transform, highlight = [], animate = true }: {
  list: Draw[]; period: Period; look: Look; width: number; height: number; transform: DerivedValue<Transforms3d>;
  highlight?: [number, number][]; animate?: boolean;
}) {
  const [scene, setScene] = useState<Layer[] | null>(null);
  const glow = useSharedValue(0.35);
  const tick = useSharedValue(0);
  useEffect(() => {
    glow.value = withRepeat(withTiming(0.75, { duration: 900 }), -1, true);    // breathes, never random
  }, [glow]);
  useEffect(() => {                                       // the idle clock runs only while Home is showing
    if (!animate) return;
    const id = setInterval(() => { tick.value += TICK_MS; }, TICK_MS);
    return () => clearInterval(id);
  }, [animate, tick]);
  const { avatar, tone, glasses } = look;
  useEffect(() => {
    let alive = true;
    Promise.all([atlasPage(period), characterSheet({ avatar, tone, glasses }, period)]).then(([atlas, sheet]) => {
      if (alive && atlas) setScene(layers(list, { atlas, sheet }));
    });
    return () => { alive = false; };
  }, [list, period, avatar, tone, glasses]);
  const path = useMemo(() => (highlight.length ? diamonds(highlight) : null), [highlight]);
  return (
    <Canvas style={{ width, height }}>
      {scene && (
        <Group transform={transform}>
          {scene.map((l, i) => (l.kind === 'still'
            ? <Picture key={i} picture={l.picture} />
            : <IdlePiece key={i} layer={l} tick={tick} />))}
          {path && <Path path={path} color="#FFF1A8" opacity={glow} />}
          {path && <Path path={path} color="#FFFFFF" style="stroke" strokeWidth={1.5} />}
        </Group>
      )}
    </Canvas>
  );
}
