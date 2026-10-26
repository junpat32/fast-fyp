import assert from 'node:assert/strict';
import { test } from 'node:test';

import { authMessage, checkCredentials, gate, MIN_PASSWORD } from '../../api/auth.ts';
import { readConfig } from '../../api/config.ts';

const URL_ = 'https://abcd.supabase.co';
const ANON = 'sb_publishable_abc123';
const API = 'https://fast-api.onrender.com';
const jwt = (payload: object) => `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify(payload)).replace(/=+$/, '')}.sig`;

test('no settings: sample data; all three: live; some: a setup problem (D-106, D-145)', () => {
  assert.deepEqual(readConfig({}), { mode: 'sample' });
  assert.deepEqual(readConfig({ EXPO_PUBLIC_SUPABASE_URL: ' ', EXPO_PUBLIC_API_URL: '' }), { mode: 'sample' });
  assert.deepEqual(readConfig({ EXPO_PUBLIC_SUPABASE_URL: `${URL_}/`, EXPO_PUBLIC_SUPABASE_ANON_KEY: ANON, EXPO_PUBLIC_API_URL: `${API}/` }),
                   { mode: 'live', config: { supabaseUrl: URL_, anonKey: ANON, apiUrl: API } });
  const some = readConfig({ EXPO_PUBLIC_SUPABASE_URL: URL_ });
  assert.equal(some.mode, 'broken');
  assert.match(some.mode === 'broken' ? some.problem : '', /EXPO_PUBLIC_SUPABASE_ANON_KEY, EXPO_PUBLIC_API_URL/);
});

test('an admin key is refused, whichever kind (CF2, rule 7)', () => {
  for (const key of ['sb_secret_abc123', jwt({ role: 'service_role', iss: 'supabase' })]) {
    const r = readConfig({ EXPO_PUBLIC_SUPABASE_URL: URL_, EXPO_PUBLIC_SUPABASE_ANON_KEY: key, EXPO_PUBLIC_API_URL: API });
    assert.equal(r.mode, 'broken', key);
    assert.match(r.mode === 'broken' ? r.problem : '', /admin key/);
  }
  const anon = readConfig({ EXPO_PUBLIC_SUPABASE_URL: URL_, EXPO_PUBLIC_SUPABASE_ANON_KEY: jwt({ role: 'anon' }), EXPO_PUBLIC_API_URL: API });
  assert.equal(anon.mode, 'live');
});

test('Supabase over https only; the API over http only on this computer or the local network (CF3)', () => {
  const at = (supabase: string, api: string) =>
    readConfig({ EXPO_PUBLIC_SUPABASE_URL: supabase, EXPO_PUBLIC_SUPABASE_ANON_KEY: ANON, EXPO_PUBLIC_API_URL: api }).mode;
  assert.equal(at('http://abcd.supabase.co', API), 'broken');
  assert.equal(at(URL_, 'http://192.168.43.10:8000'), 'live');        // a phone hotspot
  assert.equal(at(URL_, 'http://10.0.0.5:8000'), 'live');
  assert.equal(at(URL_, 'http://localhost:8000'), 'live');
  assert.equal(at(URL_, 'http://fast-api.onrender.com'), 'broken');
  assert.equal(at(URL_, 'not a url'), 'broken');
});

test('the sign-in form: an email, a password, and 10 characters when creating an account (AU1)', () => {
  assert.deepEqual(checkCredentials('aina@example.com', 'short', false), {});
  assert.deepEqual(Object.keys(checkCredentials('aina', '', false)).sort(), ['email', 'password']);
  assert.match(checkCredentials('aina@example.com', 'x'.repeat(MIN_PASSWORD - 1), true).password ?? '', /at least 10/);
  assert.deepEqual(checkCredentials(' aina@example.com ', 'x'.repeat(MIN_PASSWORD), true), {});
});

test('Supabase Auth errors become sentences the user can act on', () => {
  assert.match(authMessage({ code: 'invalid_credentials', message: 'Invalid login credentials' }), /don't match/);
  assert.match(authMessage({ message: 'Email not confirmed' }), /Confirm your email/);
  assert.match(authMessage({ code: 'user_already_exists' }), /sign in instead/);
  assert.match(authMessage({ code: 'signup_disabled', message: 'Signups not allowed for this instance' }), /ask the researcher/);
  assert.match(authMessage({ code: 'weak_password' }), /at least 10/);
  assert.match(authMessage({ code: 'over_email_send_rate_limit' }), /wait a minute/);
  assert.match(authMessage({ status: 429 }), /wait a minute/);
  assert.match(authMessage({ message: 'TypeError: Network request failed' }), /No connection/);
  assert.equal(authMessage({ message: 'some internal detail 0x1f' }), 'Signing in did not work. Try again in a moment.');
});

test('the gate: nothing of the user\'s before a session, only sign-up before a profile (AU2)', () => {
  assert.equal(gate({ mode: 'sample', session: 'none', profile: 'none' }), 'sample');
  assert.equal(gate({ mode: 'broken', session: 'signed_in', profile: 'ready' }), 'setup_problem');
  assert.equal(gate({ mode: 'live', session: 'loading', profile: 'ready' }), 'loading');
  assert.equal(gate({ mode: 'live', session: 'none', profile: 'ready' }), 'sign_in');
  assert.equal(gate({ mode: 'live', session: 'signed_in', profile: 'loading' }), 'loading');
  assert.equal(gate({ mode: 'live', session: 'signed_in', profile: 'error' }), 'profile_problem');
  assert.equal(gate({ mode: 'live', session: 'signed_in', profile: 'none' }), 'sign_up_steps');
  assert.equal(gate({ mode: 'live', session: 'signed_in', profile: 'ready' }), 'app');
});
