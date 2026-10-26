import type { Session } from '@supabase/supabase-js';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { gate } from '@/api/auth';
import { ApiError, createApi } from '@/api/client';
import type { LiveConfig } from '@/api/config';
import { supabaseDb } from '@/api/db';
import { liveBudgets, liveCheckins, liveDebts, liveEntries, liveProfile, readProfile, type ProfileFacts } from '@/api/live';
import { supabaseFor } from '@/api/supabase';
import { Loading, ProfileProblem } from '@/components/auth/gate-screens';
import { SignIn } from '@/components/auth/sign-in';
import { ApiContext, clockOf, lookOf, messageOf, noonOn, type ApiState } from '@/data/api-state';
import type { StudyClock } from '@/lib/study';

type Profile = ProfileFacts | null | 'loading' | 'error';

/**
 * Live mode (D-145): Supabase sign-in, then the user's own rows and the API, behind the same ApiState
 * as sample data. Until there is a session it shows only the sign-in screen; signed in without a
 * profile, only the sign-up steps (needsSignUp, _layout.tsx); a study persona's clock comes from
 * GET /v1/study (D-90). Signing out (or "Switch account", D-94) clears the session on this phone only.
 */
export function LiveProvider({ config, children }: { config: LiveConfig; children: ReactNode }) {
  const client = useMemo(() => supabaseFor(config), [config]);
  const db = useMemo(() => supabaseDb(client), [client]);
  const api = useMemo(() => createApi({
    baseUrl: config.apiUrl,
    getToken: async () => (await client.auth.getSession()).data.session?.access_token ?? null,
  }), [client, config.apiUrl]);
  const [session, setSession] = useState<Session | null | 'loading'>('loading');
  const [profile, setProfile] = useState<Profile>('loading');
  const [clock, setClock] = useState<StudyClock | null>(null);
  const [version, setVersion] = useState(0);
  const changed = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let alive = true;
    client.auth.getSession().then(({ data }) => { if (alive) setSession(data.session); });
    const { data } = client.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => { alive = false; data.subscription.unsubscribe(); };
  }, [client]);

  const userId = session && session !== 'loading' ? session.user.id : null;

  // quiet: refresh without the loading screen, so the screens (and the router) stay where they are
  const loadProfile = useCallback(async (uid: string, quiet = false) => {
    if (!quiet) setProfile('loading');
    try {
      const p = await readProfile(db, uid);
      let c: StudyClock | null = null;
      if (p) {
        try {
          c = clockOf(await api.study());
        } catch {
          c = null;                                                // the API is down: the screens say so themselves
        }
      }
      setClock(c);
      setProfile(p);
    } catch {
      setProfile('error');
    }
  }, [db, api]);

  useEffect(() => {
    if (userId) loadProfile(userId);
  }, [userId, loadProfile]);

  const signOut = useCallback(async () => {
    await client.auth.signOut({ scope: 'local' });               // this phone only
    setProfile('loading');
    setClock(null);
  }, [client]);

  const stores = useMemo(() => ({
    entries: liveEntries(db), checkins: liveCheckins(db), debts: liveDebts(db), budgets: liveBudgets(db),
  }), [db]);

  const value = useMemo<ApiState | null>(() => {
    if (!userId || session === 'loading' || !session || profile === 'loading' || profile === 'error') return null;
    const own = liveProfile(db, userId);
    const study = clock;
    return {
      api,
      ...stores,
      signUp: {
        local: false,
        create: async (p, debts) => {
          await own.create(p, debts);
          await loadProfile(userId, true);
        },
        saveLook: own.saveLook,
      },
      profile: profile ? { created_at: profile.created_at, declared_income: profile.declared_income } : null,
      look: lookOf(profile ?? { avatar: null, skin_tone: null, glasses: false }),
      setLook: async (look) => {
        try {
          await own.saveLook(look);
          await loadProfile(userId, true);
          return null;
        } catch (e) {
          return messageOf(e);
        }
      },
      now: study ? () => noonOn(study.date) : () => new Date(),
      study,
      travel: async (step) => {
        try {
          setClock(clockOf(await api.timeTravel(step)));
          changed();
          return null;
        } catch (e) {
          return e instanceof ApiError ? e.detail : messageOf(e);
        }
      },
      sample: null,
      samples: [],
      chooseSample: () => {},
      version,
      changed,
      account: {
        email: session.user.email ?? null,
        signOut,
        deleteAccount: async () => {
          try {
            await db.rpc('delete_my_account');                    // the database refuses a study persona
            await signOut();
            return null;
          } catch (e) {
            return messageOf(e);
          }
        },
      },
      needsSignUp: profile === null,
    };
  }, [userId, session, profile, clock, db, api, stores, loadProfile, signOut, version, changed]);

  const screen = gate({
    mode: 'live',
    session: session === 'loading' ? 'loading' : session ? 'signed_in' : 'none',
    profile: profile === 'loading' ? 'loading' : profile === 'error' ? 'error' : profile ? 'ready' : 'none',
  });
  if (screen === 'sign_in') return <SignIn client={client} />;
  if (screen === 'profile_problem' && userId) {
    return <ProfileProblem onRetry={() => loadProfile(userId)} onSignOut={signOut} />;
  }
  if (!value) return <Loading />;
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}
