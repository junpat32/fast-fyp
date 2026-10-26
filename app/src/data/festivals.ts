// shared/festivals.json: the festivals sign-up asks about and their dates (D-124, rule 5). Metro reaches
// it through metro.config.js (watchFolders).
import raw from '../../../shared/festivals.json';

import type { Festivals } from '@/lib/onboarding';

export const FESTIVALS = raw as unknown as Festivals;
