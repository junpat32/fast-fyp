import type { ComponentProps } from 'react';

import HomeScene from './home-scene';

/** On the phone, Skia is built into Expo Go: draw the scene straight away (web: scene-host.web.tsx). */
export function SceneHost(props: ComponentProps<typeof HomeScene>) {
  return <HomeScene {...props} />;
}
