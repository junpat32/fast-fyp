import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildDebt } from '../debts.ts';
import {
  blankOnboarding, buildProfile, festiveMonth, STEPS, stepErrors, type Festivals, type OnboardingForm,
} from '../onboarding.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const festivals = read(join(ROOT, 'shared', 'festivals.json')) as Festivals;
const study = read(join(HERE, 'fixtures', 'onboarding.json')) as {
  card: [string, string][]; profile: Record<string, unknown>;
  debts: { kind: string; outstanding: number; monthly_payment: number; deducted_from_salary: boolean }[];
};
const SQL = readFileSync(join(ROOT, 'supabase', 'migrations', '20261014000000_init.sql'), 'utf-8');
const profiles = /create table public\.profiles \(([\s\S]*?)\n\);/.exec(SQL)![1];

/** The sign-up card, typed in as a participant would (docs/study/onboarding_card.md). */
function fromCard(): OnboardingForm {
  const debt = (kind: 'ptptn' | 'bnpl', owed: string, monthly: string) => {
    const r = buildDebt({ kind, label: '', monthly, owed, fromSalary: false });
    assert.ok(r.ok);
    return r.debt;
  };
  return { ...blankOnboarding(), work: 'employee', birthYear: '2002', income: '2,800', costs: '1900', vehicle: 'motorcycle',
           withParents: false, familySupport: true, festival: 'hari_raya_aidilfitri', cash: '1250',
           debts: [debt('ptptn', '14,500', '150'), debt('bnpl', '360', '120')], goal: '200', avatar: 3 };
}

test('the sign-up card gives exactly what the study\'s check looks for (tools/personas/onboarding.py)', () => {
  assert.ok(study.card.some(([k]) => k === 'Festival you celebrate'));
  for (const today of ['2026-07-01', '2026-12-01', '2027-01-15']) {               // the persona clock and the study's dates
    const p = buildProfile(fromCard(), festivals, today) as unknown as Record<string, unknown>;
    for (const [field, want] of Object.entries(study.profile)) {
      const got = p[field];
      assert.ok(typeof want === 'number' ? Math.abs(Number(got) - want) < 0.005 : got === want, `${field} on ${today}: ${String(got)}`);
    }
  }
  const debts = fromCard().debts;
  for (const want of study.debts) {
    const d = debts.find((x) => x.kind === want.kind)!;
    assert.equal(Number(d.outstanding), want.outstanding);
    assert.equal(Number(d.monthly_payment), want.monthly_payment);
    assert.equal(d.deducted_from_salary, want.deducted_from_salary);
  }
});

test('every field saved is a column of public.profiles, inside its checks (ON1)', () => {
  const p = buildProfile(fromCard(), festivals, '2026-07-01');
  for (const field of Object.keys(p)) assert.ok(new RegExp(`\\n  ${field} `).test(profiles), field);
  assert.ok(/employment_type in \('employee', 'gig', 'student'\)/.test(profiles));
  assert.ok(/vehicle in \('none', 'motorcycle', 'car', 'both'\)/.test(profiles));
  assert.ok(/birth_year between 1940 and 2015/.test(profiles));
  assert.equal(p.onboarding_counted_money, '1250.00');
  assert.equal(p.onboarding_debt, '14860.00');                                     // ON4: what the listed debts owe
  assert.equal(p.typical_monthly_costs, '1900.00');
});

test('each step says what is missing, in words; a finished step has nothing to say', () => {
  const blank = blankOnboarding();
  assert.deepEqual(Object.keys(stepErrors('you', blank)).sort(), ['birthYear', 'income', 'work']);
  assert.deepEqual(Object.keys(stepErrors('life', blank)).sort(), ['familySupport', 'festival', 'vehicle', 'withParents']);
  assert.ok(stepErrors('you', { ...blank, work: 'student', birthYear: '1939', income: '0' }).birthYear);
  assert.deepEqual(stepErrors('you', { ...blank, work: 'student', birthYear: '2005', income: '0' }), {});   // no allowance is an answer
  const card = fromCard();
  for (const s of STEPS) assert.deepEqual(stepErrors(s, card), {}, s);
  assert.throws(() => buildProfile(blank, festivals, '2026-07-01'));
});

test('the character: an avatar is needed; a skin tone and glasses are saved as chosen (D-125)', () => {
  assert.ok(stepErrors('character', { ...fromCard(), avatar: null }).avatar);
  const plain = buildProfile(fromCard(), festivals, '2026-07-01');
  assert.deepEqual([plain.avatar, plain.skin_tone, plain.glasses], [3, null, false]);   // no tone picked: the avatar's own
  const chosen = buildProfile({ ...fromCard(), tone: 5, glasses: true }, festivals, '2026-07-01');
  assert.deepEqual([chosen.skin_tone, chosen.glasses], [5, true]);
  assert.ok(/skin_tone smallint check \(skin_tone between 1 and 6\)/.test(profiles) && /glasses boolean not null default false/.test(profiles));
});

test('"not sure" is an answer: usual costs and the goal can wait (ON2)', () => {
  const p = buildProfile({ ...fromCard(), costs: '', costsUnsure: true, goal: '', goalUnsure: true }, festivals, '2026-07-01');
  assert.equal(p.typical_monthly_costs, null);
  assert.equal(p.savings_goal_monthly, null);
  assert.equal(p.savings_goal_share, null);
});

test('a gig worker\'s goal is a share of what comes in (0 to 1, three decimals)', () => {
  const gig = { ...fromCard(), work: 'gig' as const, goal: '10%' };
  assert.deepEqual(stepErrors('goal', gig), {});
  const p = buildProfile(gig, festivals, '2026-07-01');
  assert.equal(p.savings_goal_share, '0.100');
  assert.equal(p.savings_goal_monthly, null);
  assert.ok(stepErrors('goal', { ...gig, goal: '150' }).goal);
  assert.ok(stepErrors('goal', { ...gig, goal: '0' }).goal);
});

test('a festival is stored as the month of its next date; "None" stores no month (ON3)', () => {
  assert.equal(festiveMonth('chinese_new_year', festivals, '2026-07-01'), 2);   // Feb 2027
  assert.equal(festiveMonth('deepavali', festivals, '2026-07-01'), 11);         // 8 Nov 2026
  assert.equal(festiveMonth('deepavali', festivals, '2026-12-01'), 10);         // 29 Oct 2027
  assert.equal(festiveMonth('christmas', festivals, '2026-07-01'), 12);
  assert.equal(festiveMonth('unknown', festivals, '2026-07-01'), null);
  assert.equal(buildProfile({ ...fromCard(), festival: 'none' }, festivals, '2026-07-01').festive_month, null);
  const months = festivals.festivals.flatMap((f) => f.dates.map((d) => Number(d.slice(5, 7))));
  assert.ok(months.every((m) => m >= 1 && m <= 12));
});
