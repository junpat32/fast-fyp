import type { ComponentProps } from 'react';

import CharacterPortrait from './portrait';

/** On the phone, Skia is built into Expo Go: draw the portrait straight away (web: portrait-host.web.tsx). */
export function PortraitHost(props: ComponentProps<typeof CharacterPortrait>) {
  return <CharacterPortrait {...props} />;
}
