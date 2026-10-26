/**
 * Where sign-up goes (D-124). With Supabase: one insert into public.profiles as the user (the database
 * stamps when it arrived, the game's sign-up anchor, and copies the game's numbers, which lock after
 * 48 hours), then the debts into public.debts. Until the project exists, sample data mode keeps it on
 * the phone and shows the sign-up card's new user instead (its day one, made with the server's own
 * functions), and says so.
 */
import type { Look } from '../lib/character.ts';
import type { NewDebt } from '../lib/debts.ts';
import type { NewProfile } from '../lib/onboarding.ts';

export interface ProfileStore {
  /** Saves the sign-up: the profile, then the debts listed with it. */
  create(profile: NewProfile, debts: NewDebt[]): Promise<void>;
  /** A new character (the More screen, D-127): profiles.avatar, skin_tone and glasses, which the
   * database lets the user change at any time (only the sign-up numbers lock). */
  saveLook(look: Look): Promise<void>;
  readonly local: boolean;
}

export function memoryProfile(): ProfileStore & { saved: { profile: NewProfile; debts: NewDebt[] } | null; look: Look | null } {
  const store = {
    local: true,
    saved: null as { profile: NewProfile; debts: NewDebt[] } | null,
    look: null as Look | null,
    async create(profile: NewProfile, debts: NewDebt[]) {
      store.saved = { profile, debts };
    },
    async saveLook(look: Look) {
      store.look = look;
    },
  };
  return store;
}
