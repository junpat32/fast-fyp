/**
 * Signing in (app_plan §3 "Login", D-145): the form's checks, Supabase Auth's errors as plain sentences,
 * and the gate that picks what the app shows. Pure TypeScript, tested by Node; the screen is
 * components/auth/sign-in.tsx and the session lives in api/supabase.ts.
 *
 * Invariants
 *   AU1  passwords are checked only for length here (Supabase's setting: at least 10, setup guide
 *        step 3); they are never stored, logged or shown by the app
 *   AU2  a live app shows nothing of the user's until there is a session, and only the sign-up steps
 *        until the user has a profile; sample data mode never asks anyone to sign in (D-106)
 */
export const MIN_PASSWORD = 10;                              // Supabase Auth: minimum password length
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type AuthErrors = Partial<Record<'email' | 'password', string>>;

export function checkCredentials(email: string, password: string, creating: boolean): AuthErrors {
  const errors: AuthErrors = {};
  if (!EMAIL.test(email.trim())) errors.email = 'Type your email address';
  if (password === '') errors.password = 'Type your password';
  else if (creating && password.length < MIN_PASSWORD) errors.password = `Use at least ${MIN_PASSWORD} characters`;
  return errors;
}

/** Supabase Auth's error (its code where it has one, else its message) as a sentence for the user. */
export function authMessage(e: { message?: string; code?: string; status?: number } | null | undefined): string {
  const code = e?.code ?? '';
  const text = (e?.message ?? '').toLowerCase();
  if (code === 'invalid_credentials' || text.includes('invalid login credentials')) {
    return "That email and password don't match an account.";
  }
  if (code === 'email_not_confirmed' || text.includes('email not confirmed')) {
    return 'Confirm your email first: open the link FAST sent you, then sign in.';
  }
  if (code === 'signup_disabled' || text.includes('signups not allowed')) {      // setup guide: sign-ups off
    return 'New accounts are made by the FAST team for now: ask the researcher for one.';
  }
  if (code === 'user_already_exists' || text.includes('already registered')) {
    return 'There is already an account with that email: sign in instead.';
  }
  if (code === 'weak_password' || text.includes('password should be')) {
    return `Choose a longer password: at least ${MIN_PASSWORD} characters.`;
  }
  if (code.startsWith('over_') || e?.status === 429) return 'Too many tries: wait a minute, then try again.';
  if (/network request failed|failed to fetch|fetch failed/.test(text)) return 'No connection: check your internet and try again.';
  return 'Signing in did not work. Try again in a moment.';
}

export type Gate = 'sample' | 'setup_problem' | 'loading' | 'sign_in' | 'sign_up_steps' | 'app' | 'profile_problem';
export type GateInput = {
  mode: 'sample' | 'live' | 'broken';
  session: 'loading' | 'none' | 'signed_in';
  profile: 'loading' | 'none' | 'ready' | 'error';
};

/** What the app shows (AU2). */
export function gate({ mode, session, profile }: GateInput): Gate {
  if (mode === 'sample') return 'sample';
  if (mode === 'broken') return 'setup_problem';
  if (session === 'loading') return 'loading';
  if (session === 'none') return 'sign_in';
  if (profile === 'loading') return 'loading';
  if (profile === 'error') return 'profile_problem';
  return profile === 'none' ? 'sign_up_steps' : 'app';
}
