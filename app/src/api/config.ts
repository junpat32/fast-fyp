/**
 * Sample data or live (D-106, D-145): which mode the app runs in, from its three public settings.
 * All three set: live (Supabase sign-in, the deployed or local API). None set: sample data. Some but not
 * all: a setup mistake, shown as such rather than half working. Pure TypeScript, tested by Node.
 *
 * Invariants
 *   CF1  only public values: the Supabase URL, its anon (publishable) key and the API URL (rule 7;
 *        EXPO_PUBLIC_* values are bundled into the app, so anyone with the app can read them)
 *   CF2  a key that grants admin rights is refused: a legacy JWT whose role is service_role, or a
 *        new-style secret key (sb_secret_...); the app must never hold one (security review §4)
 *   CF3  the Supabase URL is https; the API URL may be http only on a local network (Metro on the
 *        same Wi-Fi or hotspot), never on a public host
 */
export type LiveConfig = { supabaseUrl: string; anonKey: string; apiUrl: string };
export type Mode =
  | { mode: 'sample' }
  | { mode: 'live'; config: LiveConfig }
  | { mode: 'broken'; problem: string };

export const SETTINGS = ['EXPO_PUBLIC_SUPABASE_URL', 'EXPO_PUBLIC_SUPABASE_ANON_KEY', 'EXPO_PUBLIC_API_URL'] as const;
type Env = Partial<Record<(typeof SETTINGS)[number], string | undefined>>;

const LOCAL = /^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$/;

function jwtRole(key: string): string | null {
  const part = key.split('.')[1];
  if (!part) return null;
  try {
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '='));
    const role = (JSON.parse(json) as { role?: unknown }).role;
    return typeof role === 'string' ? role : null;
  } catch {
    return null;
  }
}

function url(text: string): URL | null {
  try {
    return new URL(text);
  } catch {
    return null;
  }
}

export function readConfig(env: Env): Mode {
  const values = SETTINGS.map((k) => (env[k] ?? '').trim());
  const missing = SETTINGS.filter((_, i) => values[i] === '');
  if (missing.length === SETTINGS.length) return { mode: 'sample' };
  if (missing.length > 0) return { mode: 'broken', problem: `Missing in app/.env: ${missing.join(', ')}` };
  const [typedUrl, anonKey, apiUrl] = values;
  // the dashboard's Data API page shows the address with /rest/v1/ on the end; supabase-js adds its own (D-147)
  const supabaseUrl = typedUrl.replace(/\/+$/, '').replace(/\/(rest|auth)\/v1$/, '');
  if (anonKey.startsWith('sb_secret_') || jwtRole(anonKey) === 'service_role') {
    return { mode: 'broken', problem: 'EXPO_PUBLIC_SUPABASE_ANON_KEY is an admin key: use the anon (publishable) key' };
  }
  const s = url(supabaseUrl);
  if (!s || s.protocol !== 'https:') return { mode: 'broken', problem: 'EXPO_PUBLIC_SUPABASE_URL must be an https address' };
  const a = url(apiUrl);
  if (!a || !(a.protocol === 'https:' || (a.protocol === 'http:' && LOCAL.test(a.hostname)))) {
    return { mode: 'broken', problem: 'EXPO_PUBLIC_API_URL must be https, or http on this computer or local network' };
  }
  return { mode: 'live', config: { supabaseUrl: supabaseUrl.replace(/\/$/, ''), anonKey, apiUrl: apiUrl.replace(/\/$/, '') } };
}
