import { WithSkiaWeb } from '@shopify/react-native-skia/lib/module/web';
import type { ComponentProps } from 'react';
import { View } from 'react-native';

import type CharacterPortrait from './portrait';

/** In the browser, Skia needs CanvasKit first (as the Home scene, scene-host.web.tsx): load it, then
 * the portrait; meanwhile an empty square of the same size keeps the layout still. The web build's
 * server render (app.json web.output "server") gets only the square: CanvasKit there looked for
 * C:\canvaskit.wasm and stopped Metro when the More screen, which shows a portrait at once, was opened
 * by its address. */
export function PortraitHost(props: ComponentProps<typeof CharacterPortrait>) {
  const blank = <View style={{ width: props.size, height: props.size }} />;
  if (typeof window === 'undefined') return blank;
  return (
    <WithSkiaWeb getComponent={() => import('./portrait')} componentProps={props}
                 opts={{ locateFile: (file: string) => `/${file}` }} fallback={blank} />
  );
}
