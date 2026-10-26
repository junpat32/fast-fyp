/**
 * The Supabase client for live mode (D-145), set up as Supabase documents for Expo: the session is kept
 * in AsyncStorage and refreshed while the app is in the foreground. Only the public URL and anon key are
 * used (rule 7, config.ts CF1-CF2). Production vs coursework: the session sits unencrypted in
 * AsyncStorage, acceptable for synthetic study accounts; a real release would encrypt it with a key in
 * Expo SecureStore (security review §4).
 */
import 'react-native-url-polyfill/auto';

import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { AppState } from 'react-native';

import type { LiveConfig } from './config';

let client: SupabaseClient | null = null;

export function supabaseFor(config: LiveConfig): SupabaseClient {
  if (client) return client;
  client = createClient(config.supabaseUrl, config.anonKey, {
    auth: { storage: AsyncStorage, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false },
  });
  const c = client;
  AppState.addEventListener('change', (state) => {
    if (state === 'active') c.auth.startAutoRefresh();
    else c.auth.stopAutoRefresh();
  });
  return c;
}
