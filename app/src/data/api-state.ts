import { createContext, useContext } from 'react';

import type { CheckinStore } from '@/api/checkins';
import type { FastApi } from '@/api/client';
import type { EntryStore } from '@/api/entries';
import type { BudgetStore, DebtStore } from '@/api/lists';
import type { ProfileStore } from '@/api/profile';
import type { StudyResponse } from '@/api/types';
import { CHARACTERS } from '@/data/kit';
import { suggestedTone, type Look } from '@/lib/character';
import type { StudyClock, TravelStep } from '@/lib/study';

/**
 * What the screens read (D-106, D-145), the same in sample data mode (api-context.tsx) and live
 * (live-provider.tsx). A study persona has its own date (A4, D-90): `study` holds it for the study bar,
 * `now` is noon on it (the database's study_now), and `travel` moves it a month at a time (D-119);
 * every screen then reloads, as after any write.
 */
export type Account = {
  email: string | null;
  signOut: () => Promise<void>;                                   // also "Switch account" in the study bar (D-94)
  deleteAccount: () => Promise<string | null>;                    // delete_my_account() (S-2): a refusal, or null
};

export type ApiState = {
  api: FastApi;
  entries: EntryStore;                                            // the Add screen's entries (D-112)
  checkins: CheckinStore;                                         // the monthly check-ins (D-118)
  debts: DebtStore;                                               // the debts list (D-121)
  budgets: BudgetStore;                                           // the budgets (D-121)
  signUp: ProfileStore;                                           // where sign-up saves (D-124)
  profile: { created_at: string; declared_income: number } | null;   // sign-up day, declared income
  look: Look;                                                     // the character: avatar, skin tone, glasses (D-124, D-125)
  setLook: (look: Look) => Promise<string | null>;               // a new character (More, D-127): a refusal, or null
  now: () => Date;                                                // the user's clock: a persona's study date at noon
  study: StudyClock | null;                                       // a persona's date and range; null for everyone else
  travel: (step: TravelStep) => Promise<string | null>;           // time travel: a readable refusal, or null
  sample: { key: string; name: string; story: string } | null;   // null = real data
  samples: { key: string; name: string }[];
  chooseSample: (key: string) => void;
  version: number;                                                // goes up after every write
  changed: () => void;                                            // screens reload what they show
  account: Account | null;                                        // null in sample data mode
  needsSignUp: boolean;                                           // signed in, no profile yet: only the sign-up steps
};

export const ApiContext = createContext<ApiState | null>(null);

export function useApi(): ApiState {
  const v = useContext(ApiContext);
  if (!v) throw new Error('useApi must be used inside ApiProvider');
  return v;
}

export const noonOn = (date: string) => new Date(`${date}T04:00:00Z`);   // study_now: noon in KL (D-90)

/** The character a profile describes; a missing tone is the avatar's suggested one (D-125). */
export function lookOf(p: { avatar: number | null; skin_tone: number | null; glasses: boolean }): Look {
  const avatar = p.avatar ?? 1;
  return { avatar, tone: p.skin_tone ?? suggestedTone(avatar, CHARACTERS), glasses: !!p.glasses };
}

/** A persona's clock from the API's study answer (GET /v1/study, POST /v1/study/time-travel). */
export const clockOf = (s: StudyResponse): StudyClock | null =>
  (s.persona ? { date: s.study_date, first: s.first, last: s.last } : null);

export const messageOf = (e: unknown) => (e instanceof Error ? e.message : String(e));
