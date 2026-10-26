import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import { memoryCheckins, type CheckinStore } from '@/api/checkins';
import { ApiError, type FastApi } from '@/api/client';
import { memoryStore, type EntryStore } from '@/api/entries';
import { memoryBudgets, memoryDebts, type BudgetStore, type DebtStore } from '@/api/lists';
import { memoryProfile, type ProfileStore } from '@/api/profile';
import { NEW_USER, SAMPLES, sampleApi, sampleClock, sampleDay, sampleToday } from '@/api/sample';
import type { StudyResponse } from '@/api/types';
import { CHARACTERS } from '@/data/kit';
import { suggestedTone, type Look } from '@/lib/character';
import type { StudyClock, TravelStep } from '@/lib/study';

/**
 * Which data the screens read. Until Supabase and the deployed API exist, the app runs in
 * **sample data** mode (D-106): the four personas' real backend responses, switchable with a picker,
 * and labelled on every screen. Once EXPO_PUBLIC_API_URL and the sign-in exist, this provider returns
 * createApi(...) and Supabase stores instead, and the screens don't change.
 *
 * A study persona has its own date (A4, D-90): `study` holds it for the study bar, `now` is noon on
 * it (the database's study_now), and `travel` moves it a month at a time (D-119); every screen then
 * reloads, as after any write.
 */
type ApiState = {
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
};

const ApiContext = createContext<ApiState | null>(null);
const SAMPLE_APIS = new Map<string, FastApi>();                   // each persona keeps its session state
const SAMPLE_ENTRIES = new Map<string, EntryStore>();
const SAMPLE_CHECKINS = new Map<string, CheckinStore>();
const SAMPLE_DEBTS = new Map<string, DebtStore>();
const SAMPLE_BUDGETS = new Map<string, BudgetStore>();
const SIGN_UP = memoryProfile();                                  // sample data mode: kept on the phone

const noonOn = (date: string) => new Date(`${date}T04:00:00Z`);   // study_now: noon in KL (D-90)

function once<T>(cache: Map<string, T>, key: string, make: () => T): T {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key)!;
}

/** The character a profile describes; a missing tone is the avatar's suggested one (D-125). */
function lookOf(p: { avatar: number | null; skin_tone: number | null; glasses: boolean }): Look {
  const avatar = p.avatar ?? 1;
  return { avatar, tone: p.skin_tone ?? suggestedTone(avatar, CHARACTERS), glasses: !!p.glasses };
}

/** A persona's clock from the API's study answer (GET /v1/study, POST /v1/study/time-travel). */
const clockOf = (s: StudyResponse): StudyClock | null =>
  (s.persona ? { date: s.study_date, first: s.first, last: s.last } : null);

export function ApiProvider({ children }: { children: ReactNode }) {
  const [key, setKey] = useState(SAMPLES[0].persona.key);
  const [version, setVersion] = useState(0);
  // each persona's date as the API last answered it: React state, never read from the sample API's own
  // store during render (the React Compiler caches calls by their arguments, so a read there goes stale)
  const [clocks, setClocks] = useState<Record<string, StudyClock | null>>(
    () => Object.fromEntries(SAMPLES.map((s) => [s.persona.key, sampleClock(s.persona.key)])));
  // a character changed on the More screen, per person: React state, like the clocks
  const [looks, setLooks] = useState<Record<string, Look>>({});
  const changed = useCallback(() => setVersion((v) => v + 1), []);
  const value = useMemo<ApiState>(() => {
    const current = [...SAMPLES, NEW_USER].find((s) => s.persona.key === key) ?? SAMPLES[0];
    const study = clocks[key] ?? null;
    const today = study?.date ?? current.assess.as_of;            // the new user has no study clock: its day one
    const live = () => noonOn(sampleToday(key));                  // the stores read the clock when they're used
    const api = once(SAMPLE_APIS, key, () => sampleApi(key));
    return {
      api,
      entries: once(SAMPLE_ENTRIES, key, () => memoryStore(live)),
      checkins: once(SAMPLE_CHECKINS, key, () => memoryCheckins(() => sampleDay(key).checkins, live)),
      debts: once(SAMPLE_DEBTS, key, () => memoryDebts(current.debts, live)),
      budgets: once(SAMPLE_BUDGETS, key, () => memoryBudgets()),
      signUp: SIGN_UP,
      profile: current.profile,
      // sample data: the new user is the card's person, in the character just chosen at sign-up
      look: looks[key] ?? lookOf(current === NEW_USER && SIGN_UP.saved ? SIGN_UP.saved.profile : current.profile),
      setLook: async (look) => {
        try {
          await SIGN_UP.saveLook(look);
          setLooks((l) => ({ ...l, [key]: look }));
          return null;
        } catch (e) {
          return e instanceof Error ? e.message : String(e);
        }
      },
      now: () => noonOn(today),                                   // a new function per date: safe to call in render
      study,
      travel: async (step) => {
        try {
          const s = await api.timeTravel(step);
          setClocks((c) => ({ ...c, [key]: clockOf(s) }));
          changed();
          return null;
        } catch (e) {
          return e instanceof ApiError ? e.detail : e instanceof Error ? e.message : String(e);
        }
      },
      sample: current.persona,
      samples: SAMPLES.map((s) => ({ key: s.persona.key, name: s.persona.name })),
      chooseSample: setKey,
      version,
      changed,
    };
  }, [key, version, clocks, looks, changed]);
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApi(): ApiState {
  const v = useContext(ApiContext);
  if (!v) throw new Error('useApi must be used inside ApiProvider');
  return v;
}
