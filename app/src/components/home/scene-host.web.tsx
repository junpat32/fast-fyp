import { WithSkiaWeb } from '@shopify/react-native-skia/lib/module/web';
import type { ComponentProps } from 'react';
import { ActivityIndicator } from 'react-native';

import type HomeScene from './home-scene';

/** In the browser (the web build Claude checks screens with), Skia needs CanvasKit first: load
 * public/canvaskit.wasm, then import the scene (scripts/sync-art copies the file from node_modules). */
export function SceneHost(props: ComponentProps<typeof HomeScene>) {
  return (
    <WithSkiaWeb getComponent={() => import('./home-scene')} componentProps={props}
                 opts={{ locateFile: (file: string) => `/${file}` }} fallback={<ActivityIndicator />} />
  );
}
