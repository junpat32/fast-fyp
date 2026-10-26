/**
 * The money helper on the phone (A6, D-92, D-123): the question is redacted here before it leaves
 * (rule 11; the same rules as the server's api/assistant.py redact(), which checks again), crisis words
 * get FAST's caring reply at once, even with no server, and the summary the AI was given is turned
 * into lines the user can read ("What the AI saw", rule 10). Pure TypeScript, tested by Node against
 * the server's own answers (fixtures/helper.json).
 */
const SECRET_LINE = /^.*\b(TAC|OTP|one[- ]time (password|pin|code)|PIN|password|kata laluan)\b.*(\n|$)/gim;
const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const IC = /(?<!\d)\d{6}-\d{2}-\d{4}(?!\d)|(?<!\d)\d{12}(?!\d)/g;                    // MyKad
const CARD = /(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)/g;                                     // 13-19 digits
const PHONE = /(?<![\d+])(?:\+?60|0)1\d[- ]?\d{3,4}[- ]?\d{4}(?!\d)/g;                 // Malaysian mobile
const ACCOUNT = /(?<!\d)\d{8,17}(?!\d)/g;
const last4 = (run: string) => `****${run.replace(/\D/g, '').slice(-4)}`;

/** Lines with a TAC, OTP, PIN or password go; IC numbers, emails and phones are removed; card and
 * account numbers keep their last 4 digits; < and > go, so the question can't close its tag. */
export function redactQuestion(text: string): string {
  return text.replace(SECRET_LINE, '').replace(EMAIL, '[email removed]').replace(IC, '[IC removed]')
    .replace(CARD, last4).replace(PHONE, '[phone removed]').replace(ACCOUNT, last4).replace(/[<>]/g, '').trim();
}

/** Words about suicide or self-harm (shared/helper.json, the same pattern the server uses). */
export function isCrisis(question: string, words: string): boolean {
  return new RegExp(words, 'i').test(question);
}

export type FactLine = { label: string; value: string };
export type FactSection = { title: string; lines: FactLine[] };

const label = (key: string) => {
  const words = key.replace(/_/g, ' ').replace(/ (dsr|dti)$/i, (_, w: string) => ` (${w.toUpperCase()})`);
  return words.charAt(0).toUpperCase() + words.slice(1);
};

function lines(obj: Record<string, unknown>, prefix = ''): FactLine[] {
  return Object.entries(obj).flatMap(([k, v]): FactLine[] => {
    const name = prefix ? `${prefix} · ${label(k).toLowerCase()}` : label(k);
    if (Array.isArray(v)) return v.map((x, i) => ({ label: v.length > 1 ? `${name} ${i + 1}` : name, value: String(x) }));
    if (v && typeof v === 'object') return lines(v as Record<string, unknown>, name);
    return [{ label: name, value: String(v) }];
  });
}

/** The summary the AI was given (api/assistant.py build_context), as readable lines: the user's own
 * results, then the rules of FAST it was told. Nothing else was sent (AS1). */
export function factSections(ctx: unknown): FactSection[] {
  if (!ctx || typeof ctx !== 'object') return [];
  const { user, about_fast: about } = ctx as { user?: Record<string, unknown>; about_fast?: Record<string, unknown> };
  const out: FactSection[] = [];
  if (user) out.push({ title: 'Your results', lines: lines(user) });
  if (about) out.push({ title: 'How FAST works', lines: lines(about) });
  return out;
}

type Assessed = { band: string; insufficient_income: boolean; forecast: { probability: number } | null };

/** Questions to start with, about what the Money screen shows now. */
export function suggestions(a: Assessed | null, bandLabel: (band: string) => string): string[] {
  const out: string[] = [];
  if (a && !a.insufficient_income && a.band !== 'INSUFFICIENT_INCOME') out.push(`Why is my band ${bandLabel(a.band)}?`);
  else out.push('Why don\'t I have a band yet?');
  if (a?.forecast) out.push(`What does "${Math.round(a.forecast.probability * 100)} in 100" mean for me?`);
  out.push('How can I build my cushion?', 'How does my garden grow?');
  return out;
}
