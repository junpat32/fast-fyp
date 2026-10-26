import { useCallback, useMemo, useState, type ReactNode } from 'react';

import { memoryCheckins, type CheckinStore } from '@/api/checkins';
import { ApiError, type FastApi } from '@/api/client';
import { readConfig } from '@/api/config';
import { memoryStore, type EntryStore } from '@/api/entries';
import { memoryBudgets, memoryDebts, type BudgetStore, type DebtStore } from '@/api/lists';
import { memoryProfile } from '@/api/profile';
import { NEW_USER, SAMPLES, sampleApi, sampleClock, sampleDay, sampleToday } from '@/api/sample';
import { SetupProblem } from '@/components/auth/gate-screens';
import { ApiContext, clockOf, lookOf, noonOn, type ApiState } from '@/data/api-state';
import { LiveProvider } from '@/data/live-provider';
import type { Look } from '@/lib/character';
import type { StudyClock } from '@/lib/study';

export { useApi } from '@/data/api-state';

/**
 * Which data the screens read (D-106, D-145). With the three public settings in app/.env
 * (EXPO_PUBLIC_SUPABASE_URL, EXPO_PUBLIC_SUPABASE_ANON_KEY, EXPO_PUBLIC_API_URL) the app is **live**:
 * sign-in, the user's own Supabase rows and the API (live-provider.tsx). Without them it runs in
 * **sample data** mode: the four personas' real backend responses, switchable with a picker, and
 * labelled on every screen. Some but not all of them is a setup mistake, shown as one (config.ts).
 * Expo inlines EXPO_PUBLIC_* only when each is written out in full, as below.
 */
const MODE = readConfig({
  EXPO_PUBLIC_SUPABASE_URL: process.env.EXPO_PUBLIC_SUPABASE_URL,
  EXPO_PUBLIC_SUPABASE_ANON_KEY: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  EXPO_PUBLIC_API_URL: process.env.EXPO_PUBLIC_API_URL,
});

export function ApiProvider({ children }: { children: ReactNode }) {
  if (MODE.mode === 'broken') return <SetupProblem problem={MODE.problem} />;
  if (MODE.mode === 'live') return <LiveProvider config={MODE.config}>{children}</LiveProvider>;
  return <SampleProvider>{children}</SampleProvider>;
}

const SAMPLE_APIS = new Map<string, FastApi>();                   // each persona keeps its session state
const SAMPLE_ENTRIES = new Map<string, EntryStore>();
const SAMPLE_CHECKINS = new Map<string, CheckinStore>();
const SAMPLE_DEBTS = new Map<string, DebtStore>();
const SAMPLE_BUDGETS = new Map<string, BudgetStore>();
const SIGN_UP = memoryProfile();                                  // sample data mode: kept on the phone

function once<T>(cache: Map<string, T>, key: string, make: () => T): T {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key)!;
}

function SampleProvider({ children }: { children: ReactNode }) {
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
      account: null,
      needsSignUp: false,
    };
  }, [key, version, clocks, looks, changed]);
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}
