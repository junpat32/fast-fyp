/**
 * What the FAST API sends (api/main.py), as TypeScript types. They mirror the JSON the Python
 * endpoints build; app/src/data/samples/*.json are real responses for the four study personas
 * (tools/app_fixtures.py), and src/lib/__tests__/api.test.ts checks every sample against validate.ts.
 * Pure types, no React Native.
 */
import type { Band } from '../lib/bands.ts';
import type { CheckinRow } from '../lib/checkin.ts';
import type { DebtRow } from '../lib/debts.ts';

export type Reason = {
  feature: string;
  label: string;
  value: number;
  contribution: number;
  direction: 'raises' | 'lowers';
  text: string;                 // the plain words shown to the user (D-92)
};

export type Forecast = {
  probability: number;          // calibrated, 0.02-0.98 (P7)
  base_rate: number;
  version: string;
  reasons: Reason[];
  note: string | null;          // P6: type of work and age also matter
  red_note: string | null;      // W3: already Red, so only running short counts
};

export type Advice = {
  rule: string;
  priority: number;
  title: string;
  short: string;                // the one-line, action-first version shown first (D-108)
  text: string;                 // the full text, behind "Read more"
};

export type Health = {
  score: number | null;
  tier: 'Healthy' | 'Coping' | 'Vulnerable' | null;
  indicators: Partial<Record<'spend' | 'savings' | 'debt' | 'bills', number>>;
};

/** GET /v1/assess: the latest complete month (assessed_month), from the user's own rows (A2). */
export type AssessResponse = {
  month: number;
  band: Band;
  raw_band_this_month: Band;
  insufficient_income: boolean;
  dsr: number;
  dti: number;
  cushion_months: number;
  health: Health;
  forecast: Forecast | null;
  forecast_note: string | null; // why there's no forecast (e.g. income too low to judge)
  flags: Record<string, boolean>;
  advice: Advice[];
  as_of: string;                // the user's today (a persona's study date)
  assessed_month: string;       // first day of the month assessed, e.g. "2026-06-01"
  months: { month: string; source: 'check-in' | 'estimated' | 'this month so far' }[];
};

/** GET /v1/future: the Future Self (D-79, D-81). The app doesn't show shortfall_probability (D-100). */
export type FutureResponse =
  | { available: false; reason: string; label: string; as_of: string }
  | {
      available: true;
      label: string;            // "if recent habits continue"
      based_on_months: number;
      months: { month: number; p10: number; p50: number; p90: number }[];
      shortfall_probability: number;
      cash_flow_at_risk: number;
      expected_shortfall: number;
      median_path_room_level: number;
      median_path_final_cushion: number;
      as_of: string;
    };

/** GET /v1/game: the whole game, replayed from the user's facts (D-76). */
export type GameResponse = {
  as_of: string;
  points: number;
  points_pending: number;
  points_by_tier: Record<string, number>;
  choices: { earned: number; used: number; available: number };
  streak: { current: number; best: number };
  badges: string[];
  milestones: string[];
  room_level: number;
  garden: {
    open: boolean; level: number; qualifying_months: number; bed_step: number; bed: [number, number][];
    plant_tier: number; animal_slots: number; animal_slots_used: number;
  };
  plants: { cell: [number, number]; plant: string; stage: string; growing_days: number }[];
  seed_box: string[];
  tree: { stage: number } | null;
  decorations: Record<string, string>;
  animals: Record<string, number>;      // how many of each chosen animal (engine/game.py)
  // decorations: item -> spot; app convention (lib/home.ts): "gx,gy" in the garden, "room:<item>" indoors
  look: { mood: string; plants: string; suggest_akpk: boolean; coin_jar: number; savings_plant: number };
  game_cushion: number;
  months: { month: string; verified: boolean; saving: number; progress: number; goal: number;
            goal_met: boolean; cushion: number; qualifying: boolean }[];
  ledger: { day: string; kind: string; points: number; ref: string | null; pending: boolean }[];
  skipped: { what: string; day: string | null; why: string }[];
};

/** GET /v1/card (G-08, D-117): this week's life-event card; POST /v1/card answers it. */
export type CardAnswer = 'use_savings' | 'cut_spending' | 'set_goal' | 'not_this_week';
export type CardResponse = {
  week: string;                         // its Monday
  event_id: string;
  title: string;
  text: string;
  cost_low: number;                     // RM, the usual range
  cost_high: number;
  coverage: 'covered' | 'partly' | 'not_yet';
  coverage_text: string;
  responses: { id: CardAnswer; label: string; after: string }[];   // "after": the card's kind reply
  points: number;                       // the game's card points (once a week; none for "not this week")
  answer: CardAnswer | null;
};

/** GET /v1/study (A4, D-90): only personas get the time-travel bar. */
export type StudyResponse = { persona: false } | { persona: true; study_date: string; first: string; last: string };

/** POST /v1/assistant (D-92). */
export type AssistantReply = {
  answer: string;
  kind: 'answer' | 'refused_product' | 'refused_scope' | 'crisis' | 'fallback';
  by: 'model' | 'fast';
  grounded: boolean;
  as_of: string;
  assessed_month: string;
  shared_with_assistant: unknown | null;
};

/** What one persona's screens read on one study date (app/src/data/travel holds the later dates, D-119). */
export type SampleDay = {
  assess: AssessResponse;
  game: GameResponse;
  future: FutureResponse;
  card: CardResponse;
  checkins: CheckinRow[];                 // read from Supabase by the app itself (D-118)
  helper_facts: unknown;                  // what POST /v1/assistant would give the AI that day (D-123)
};

/** One persona's sample responses on its start date (app/src/data/samples). */
export type SampleBundle = SampleDay & {
  persona: { key: string; name: string; story: string };
  study: StudyResponse;
  profile: { created_at: string; declared_income: number; avatar: number | null; skin_tone: number | null; glasses: boolean };
  debts: Omit<DebtRow, 'id'>[];           // the debts list, read from Supabase by the app itself (D-121)
};
