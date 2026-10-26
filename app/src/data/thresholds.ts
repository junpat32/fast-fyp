// shared/thresholds.json, the one file both the Python engine and the app read (CLAUDE.md rule 5).
// Metro reaches it through metro.config.js (watchFolders).
import raw from '../../../shared/thresholds.json';

import type { Thresholds } from '@/lib/bands';

export const THRESHOLDS = raw as unknown as Thresholds & {
  advice: { cushion_first_goal_months: number; cushion_next_goal_months: number; forecast_elevated: number };
  health_score: { tiers: { healthy: number; coping: number } };
};
