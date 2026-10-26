// shared/game.json, the game's single source (CLAUDE.md rule 5), also read by engine/game.py.
import raw from '../../../shared/game.json';

import type { BadgeRules } from '@/lib/badges';
import type { GameRules } from '@/lib/rewards';

export const GAME_RULES = raw as unknown as GameRules & BadgeRules;
