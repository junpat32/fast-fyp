/**
 * Sign-up (docs/app_plan.md §3 step 2; D-124): the answers FAST needs, step by step, checked as they
 * are given, and turned into the rows the database keeps (public.profiles and public.debts). Every
 * answer is asked, never inferred (D-35, D-42). Pure TypeScript, tested by Node, including against the
 * study's own check (tools/personas/onboarding.py): the sign-up card typed in gives exactly the rows the
 * check expects.
 *
 * Invariants
 *   ON1  the database's rules: work type, vehicle and goal kinds as the table allows them; birth year
 *        1940-2015; amounts of zero or more as decimal strings (rule 9); a gig goal is a share (0, 1]
 *   ON2  "not sure" is an answer: usual costs may be left out (null), and so may the goal, for now
 *   ON3  the festival's month is the month of its next date on or after the sign-up day
 *        (shared/festivals.json); "none" stores no month
 *   ON4  money at sign-up: cash, bank and e-wallets plus EPF Fleksibel and emergency savings count as
 *        cushion (as at the check-in, D-77); other savings are kept apart; the debt at sign-up is what
 *        the listed debts still owe
 */
import { parseMoney, type NewDebt } from './debts.ts';
import { sumAmounts } from './entry.ts';

export type Work = 'employee' | 'gig' | 'student';
export type Vehicle = 'none' | 'motorcycle' | 'car' | 'both';
export type Festivals = { festivals: { key: string; label: string; dates: string[] }[] };

export const STEPS = ['welcome', 'you', 'costs', 'life', 'money', 'goal', 'character', 'review'] as const;
export type Step = (typeof STEPS)[number];

export type OnboardingForm = {
  work: Work | ''; birthYear: string; income: string;
  costs: string; costsUnsure: boolean;
  vehicle: Vehicle | ''; withParents: boolean | null; familySupport: boolean | null; festival: string;   // '' unset, 'none'
  cash: string; cushionOther: string; otherSavings: string;
  debts: NewDebt[];
  goal: string; goalUnsure: boolean;
  avatar: number | null; tone: number | null; glasses: boolean;   // tone 1-6; null: the avatar's own (D-125)
};

export type NewProfile = {
  employment_type: Work; birth_year: number; lives_with_parents: boolean; family_support: boolean;
  festive_month: number | null; vehicle: Vehicle; typical_monthly_costs: string | null; declared_income: string;
  onboarding_counted_money: string; onboarding_other_money: string; onboarding_debt: string;
  savings_goal_monthly: string | null; savings_goal_share: string | null;
  avatar: number; skin_tone: number | null; glasses: boolean;
};

export const blankOnboarding = (): OnboardingForm => ({
  work: '', birthYear: '', income: '', costs: '', costsUnsure: false, vehicle: '', withParents: null,
  familySupport: null, festival: '', cash: '', cushionOther: '', otherSavings: '', debts: [], goal: '',
  goalUnsure: false, avatar: null, tone: null, glasses: false,
});

export const WORK: { value: Work; label: string }[] = [
  { value: 'employee', label: 'Employee' }, { value: 'gig', label: 'Gig or freelance' }, { value: 'student', label: 'Student' },
];
export const VEHICLES: { value: Vehicle; label: string }[] = [
  { value: 'none', label: 'None' }, { value: 'motorcycle', label: 'Motorcycle' }, { value: 'car', label: 'Car' },
  { value: 'both', label: 'Both' },
];

/** The take-home question in the words of each kind of work. */
export function incomeLabel(work: Work | ''): string {
  if (work === 'gig') return 'What you usually take home in a month';
  if (work === 'student') return 'Allowance or pay you get in a month';
  return 'Take-home pay a month (after EPF and SOCSO)';
}

/** ON3: the month of the festival's next date on or after `today` (the last known one after that). */
export function festiveMonth(key: string, f: Festivals, today: string): number | null {
  const dates = f.festivals.find((x) => x.key === key)?.dates ?? [];
  if (dates.length === 0) return null;
  const next = dates.find((d) => d >= today) ?? dates[dates.length - 1];
  return Number(next.slice(5, 7));
}

const optional = (text: string) => (text.trim() === '' ? { ok: true as const, value: '0.00' } : parseMoney(text));

/** What is missing or wrong on one step (empty: the step is done). */
export function stepErrors(step: Step, f: OnboardingForm): Record<string, string> {
  const e: Record<string, string> = {};
  const money = (key: string, text: string, empty: string, zeroOk = true) => {
    const r = parseMoney(text);
    if (text.trim() === '') e[key] = empty;
    else if (!r.ok) e[key] = r.error;
    else if (!zeroOk && r.value === '0.00') e[key] = empty;
  };
  if (step === 'you') {
    if (f.work === '') e.work = 'Choose the kind of work you do';
    const y = Number(f.birthYear);
    if (!/^\d{4}$/.test(f.birthYear.trim()) || y < 1940 || y > 2015) e.birthYear = 'Type the year you were born, e.g. 2002';
    money('income', f.income, 'Type what you take home a month (0 if nothing)');
  }
  if (step === 'costs' && !f.costsUnsure) money('costs', f.costs, 'Type your usual costs, or tick "Not sure"');
  if (step === 'life') {
    if (f.vehicle === '') e.vehicle = 'Choose one';
    if (f.withParents === null) e.withParents = 'Choose yes or no';
    if (f.familySupport === null) e.familySupport = 'Choose yes or no';
    if (f.festival === '') e.festival = 'Choose one, or "None"';
  }
  if (step === 'money') {
    money('cash', f.cash, 'Type what you have now (0 if nothing)');
    for (const k of ['cushionOther', 'otherSavings'] as const) {
      const r = optional(f[k]);
      if (!r.ok) e[k] = r.error;
    }
  }
  if (step === 'goal' && !f.goalUnsure) {
    if (f.work === 'gig') {
      const pct = Number(f.goal.replace('%', '').trim());
      if (!/^\d{1,3}(\.\d)?%?$/.test(f.goal.trim()) || pct <= 0 || pct > 100) e.goal = 'Type a share from 1 to 100%, e.g. 10';
    } else money('goal', f.goal, 'Type an amount a month, or tick "Not sure yet"', false);
  }
  if (step === 'character' && f.avatar === null) e.avatar = 'Choose a character';
  return e;
}

/** The rows the database keeps (public.profiles; the debts go to public.debts as they are). */
export function buildProfile(f: OnboardingForm, festivals: Festivals, today: string): NewProfile {
  const bad = STEPS.find((s) => Object.keys(stepErrors(s, f)).length > 0);
  if (bad || f.work === '' || f.vehicle === '' || f.withParents === null || f.familySupport === null || f.avatar === null) {
    throw new Error(`sign-up isn't finished: ${bad ?? 'answers missing'}`);
  }
  const value = (text: string) => (parseMoney(text) as { value: string }).value;
  const gigShare = f.work === 'gig' && !f.goalUnsure;
  return {
    employment_type: f.work, birth_year: Number(f.birthYear), lives_with_parents: f.withParents,
    family_support: f.familySupport, festive_month: f.festival === 'none' ? null : festiveMonth(f.festival, festivals, today),
    vehicle: f.vehicle, typical_monthly_costs: f.costsUnsure ? null : value(f.costs), declared_income: value(f.income),
    onboarding_counted_money: sumAmounts([value(f.cash), (optional(f.cushionOther) as { value: string }).value]),
    onboarding_other_money: (optional(f.otherSavings) as { value: string }).value,
    onboarding_debt: sumAmounts(f.debts.map((d) => d.outstanding)),
    savings_goal_monthly: f.goalUnsure || f.work === 'gig' ? null : value(f.goal),
    savings_goal_share: gigShare ? (Number(f.goal.replace('%', '')) / 100).toFixed(3) : null,
    avatar: f.avatar, skin_tone: f.tone, glasses: f.glasses,          // no tone picked: the avatar's own (D-125)
  };
}
