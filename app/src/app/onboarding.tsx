import { useRouter } from 'expo-router';
import { useRef, useState, type ReactNode } from 'react';
import { Pressable, ScrollView, type ScrollViewInstance, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Check, Chip, Segmented } from '@/components/add/choice';
import { CharacterPicker } from '@/components/character/picker';
import { Button, MoneyField, TextField } from '@/components/fields';
import { DebtForm } from '@/components/lists/debt-form';
import { PrivacyNotice } from '@/components/onboarding/privacy';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { AVATARS } from '@/data/avatars';
import { FESTIVALS } from '@/data/festivals';
import { useTheme } from '@/hooks/use-theme';
import { TONES } from '@/lib/character';
import { myDate } from '@/lib/checkin';
import { debtName } from '@/lib/debts';
import { rmText } from '@/lib/entry';
import {
  blankOnboarding, buildProfile, incomeLabel, STEPS, stepErrors, VEHICLES, WORK, type OnboardingForm, type Step,
  type Vehicle, type Work,
} from '@/lib/onboarding';

const TITLES: Record<Step, string> = {
  welcome: 'Welcome to FAST', you: 'About you', costs: 'Your usual costs', life: 'Your life', money: 'Money and debts',
  goal: 'Your savings goal', character: 'Your character', review: 'Check and finish',
};
const money = (text: string) => (text.trim() === '' ? 'RM0.00' : rmText(Number(text.replace(/[^\d.]/g, '')).toFixed(2)));

/**
 * Sign-up (docs/app_plan.md §3 step 2; D-124; the study's sign-up task, D-94): the privacy notice, then
 * one question group a screen (about you, usual costs, your life, money and debts, the savings goal, a
 * character), then a check of every answer with a way back to each, and Finish. Each step says what is
 * missing before going on (lib/onboarding.ts). Every answer is asked, never inferred (D-35, D-42).
 */
export default function OnboardingScreen() {
  const { signUp, now, chooseSample, changed } = useApi();
  const t = useTheme();
  const router = useRouter();
  const scroll = useRef<ScrollViewInstance>(null);
  const [i, setI] = useState(0);
  const [form, setForm] = useState<OnboardingForm>(blankOnboarding());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [addingDebt, setAddingDebt] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const step = STEPS[i];
  const set = (patch: Partial<OnboardingForm>) => {
    setForm((f) => ({ ...f, ...patch }));
    setErrors((e) => { const n = { ...e }; for (const k of Object.keys(patch)) delete n[k]; return n; });
  };
  const go = (to: number) => { setI(to); setErrors({}); setAddingDebt(false); scroll.current?.scrollTo({ y: 0, animated: false }); };
  const next = () => {
    const e = stepErrors(step, form);
    setErrors(e);
    if (Object.keys(e).length === 0) go(i + 1);
  };
  const finish = async () => {
    setBusy(true);
    setFailed(null);
    try {
      await signUp.create(buildProfile(form, FESTIVALS, myDate(now().toISOString())), form.debts);
      changed();
      if (signUp.local) {
        chooseSample('new_user');                          // sample data: the card's new person on day one
        router.replace('/');
      }                                                    // live: the root layout opens the tabs (D-145)
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e));
    }
    setBusy(false);
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['bottom']}>
        <ScrollView ref={scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {i > 0 && (
            <View style={styles.progress} accessibilityLabel={`Step ${i} of ${STEPS.length - 1}`}>
              <ThemedText type="small" themeColor="textSecondary">Step {i} of {STEPS.length - 1}</ThemedText>
              <View style={[styles.bar, { backgroundColor: t.line }]}>
                <View style={[styles.fill, { width: `${(i / (STEPS.length - 1)) * 100}%`, backgroundColor: t.accent }]} />
              </View>
            </View>
          )}
          <ThemedText type="subtitle" style={styles.title}>{TITLES[step]}</ThemedText>

          {step === 'welcome' && (
            <>
              <ThemedText type="small">A few questions about your money, so FAST can show where you stand. It takes about 5 minutes.</ThemedText>
              <PrivacyNotice />
            </>
          )}

          {step === 'you' && (
            <>
              <Field label="Your work" error={errors.work}>
                <Segmented<Work | ''> label="Your work" value={form.work} onChange={(v) => set({ work: v })} options={WORK} />
              </Field>
              <TextField label="Year you were born" value={form.birthYear} onChange={(v) => set({ birthYear: v.replace(/\D/g, '') })}
                         placeholder="e.g. 2002" maxLength={4} keyboardType="number-pad" error={errors.birthYear} />
              <MoneyField label={incomeLabel(form.work)} value={form.income} onChange={(v) => set({ income: v })} error={errors.income}
                          hint="What reaches your account, not the amount before deductions" />
            </>
          )}

          {step === 'costs' && (
            <>
              {!form.costsUnsure && (
                <MoneyField label="Usual costs a month" value={form.costs} onChange={(v) => set({ costs: v })} error={errors.costs}
                            hint="Rent, food, transport, phone and bills: a rough figure is fine" />
              )}
              <Check label="Not sure" on={form.costsUnsure} onChange={(v) => set({ costsUnsure: v })} />
              {form.costsUnsure && <ThemedText type="small" themeColor="textSecondary">That&apos;s fine: FAST works it out from what you log.</ThemedText>}
            </>
          )}

          {step === 'life' && (
            <>
              <Field label="Do you have a vehicle?" error={errors.vehicle}>
                <Segmented<Vehicle | ''> label="Vehicle" value={form.vehicle} onChange={(v) => set({ vehicle: v })} options={VEHICLES} />
              </Field>
              <YesNo label="Do you live with your parents?" value={form.withParents} onChange={(v) => set({ withParents: v })}
                     error={errors.withParents} />
              <YesNo label="Do you send money to family regularly?" value={form.familySupport}
                     onChange={(v) => set({ familySupport: v })} error={errors.familySupport} />
              <Field label="Which festival do you celebrate?" error={errors.festival}>
                <View style={styles.chips}>
                  {FESTIVALS.festivals.map((f) => (
                    <Chip key={f.key} label={f.label} on={form.festival === f.key} onPress={() => set({ festival: f.key })} />
                  ))}
                  <Chip label="None, or rather not say" on={form.festival === 'none'} onPress={() => set({ festival: 'none' })} />
                </View>
              </Field>
            </>
          )}

          {step === 'money' && (
            <>
              <ThemedText type="smallBold">Money you have now</ThemedText>
              <MoneyField label="Cash, bank accounts and e-wallets" value={form.cash} onChange={(v) => set({ cash: v })} error={errors.cash} />
              <MoneyField label="EPF Account Fleksibel and emergency savings (optional)" value={form.cushionOther}
                          onChange={(v) => set({ cushionOther: v })} error={errors.cushionOther} />
              <MoneyField label="Other savings, e.g. ASB (optional)" value={form.otherSavings}
                          onChange={(v) => set({ otherSavings: v })} error={errors.otherSavings} />
              <ThemedText type="smallBold" style={styles.section}>Your debts</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                PTPTN, loans, credit cards and Buy Now Pay Later plans. No debts? Skip this.
              </ThemedText>
              {form.debts.map((d, k) => (
                <View key={k} style={[styles.debt, { backgroundColor: t.card }]}>
                  <View style={styles.flex}>
                    <ThemedText type="smallBold">{debtName(d)}</ThemedText>
                    <ThemedText type="small" themeColor="textSecondary">{rmText(d.monthly_payment)} a month · {rmText(d.outstanding)} left</ThemedText>
                  </View>
                  <Pressable onPress={() => set({ debts: form.debts.filter((_, j) => j !== k) })} hitSlop={10}
                             accessibilityRole="button" accessibilityLabel={`Remove ${debtName(d)}`}>
                    <ThemedText type="default" themeColor="textSecondary">✕</ThemedText>
                  </Pressable>
                </View>
              ))}
              {addingDebt ? (
                <DebtForm debt={null} onCancel={() => setAddingDebt(false)}
                          onSave={async (d) => { set({ debts: [...form.debts, d] }); setAddingDebt(false); return null; }}
                          onPayOff={async () => null} onDelete={async () => null} />
              ) : (
                <Button label={form.debts.length ? 'Add another debt' : 'Add a debt'} quiet onPress={() => setAddingDebt(true)} />
              )}
            </>
          )}

          {step === 'goal' && (
            <>
              <ThemedText type="small">How much would you like to put aside each month? Your garden grows when you meet it.</ThemedText>
              {!form.goalUnsure && (form.work === 'gig' ? (
                <>
                  <TextField label="A share of what you earn, in %" value={form.goal} onChange={(v) => set({ goal: v })}
                             placeholder="e.g. 10" maxLength={5} />
                  {errors.goal && <Err text={errors.goal} />}
                </>
              ) : (
                <MoneyField label="Save each month" value={form.goal} onChange={(v) => set({ goal: v })} error={errors.goal} />
              ))}
              <Check label="Not sure yet" on={form.goalUnsure} onChange={(v) => set({ goalUnsure: v })} />
            </>
          )}

          {step === 'character' && (
            <>
              <ThemedText type="small">Who lives in your room? You can choose again later, under More.</ThemedText>
              <CharacterPicker value={form} onChange={set} error={errors.avatar} />
            </>
          )}

          {step === 'review' && <Review form={form} onChange={go} local={signUp.local} />}
          {failed && <Err text={failed} />}

          <View style={styles.buttons}>
            {i > 0 && <Button label="Back" quiet fill onPress={() => go(i - 1)} disabled={busy} />}
            {step === 'review'
              ? <Button label={busy ? 'Saving…' : 'Finish'} fill onPress={finish} disabled={busy} />
              : <Button label={step === 'welcome' ? 'I understand: start' : 'Next'} fill onPress={next} />}
          </View>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

/** Every answer, grouped by step, each group with a way back to change it. */
function Review({ form, onChange, local }: { form: OnboardingForm; onChange: (step: number) => void; local: boolean }) {
  const festival = form.festival === 'none' ? 'None' : FESTIVALS.festivals.find((f) => f.key === form.festival)?.label ?? '';
  const groups: [Step, [string, string][]][] = [
    ['you', [['Work', WORK.find((w) => w.value === form.work)?.label ?? ''], ['Born', form.birthYear],
             ['Take-home a month', money(form.income)]]],
    ['costs', [['Usual costs a month', form.costsUnsure ? 'Not sure' : money(form.costs)]]],
    ['life', [['Vehicle', VEHICLES.find((v) => v.value === form.vehicle)?.label ?? ''],
              ['Lives with parents', form.withParents ? 'Yes' : 'No'], ['Sends money to family', form.familySupport ? 'Yes' : 'No'],
              ['Festival', festival]]],
    ['money', [['Cash, bank and e-wallets', money(form.cash)], ['EPF Fleksibel and emergency savings', money(form.cushionOther)],
               ['Other savings', money(form.otherSavings)],
               ...form.debts.map((d): [string, string] => [debtName(d), `${rmText(d.monthly_payment)} a month, ${rmText(d.outstanding)} left`]),
               ...(form.debts.length ? [] : [['Debts', 'None'] as [string, string]])]],
    ['goal', [['Savings goal', form.goalUnsure ? 'Not sure yet' : form.work === 'gig' ? `${form.goal.replace('%', '')}% of what you earn`
      : `${money(form.goal)} a month`]]],
    ['character', [['Character', AVATARS.find((a) => a.avatar === form.avatar)?.look ?? ''],
                   ['Skin tone', form.tone ? `${form.tone} of ${TONES}` : 'as shown'], ['Glasses', form.glasses ? 'Yes' : 'No']]],
  ];
  const t = useTheme();
  return (
    <>
      {groups.map(([step, rows]) => (
        <View key={step} style={[styles.group, { backgroundColor: t.card }]}>
          <View style={styles.groupHead}>
            <ThemedText type="smallBold" style={styles.flex}>{TITLES[step]}</ThemedText>
            <Pressable onPress={() => onChange(STEPS.indexOf(step))} hitSlop={8} accessibilityRole="button"
                       accessibilityLabel={`Change ${TITLES[step].toLowerCase()}`}>
              <ThemedText type="small" style={{ color: t.accent, fontWeight: 700 }}>Change</ThemedText>
            </Pressable>
          </View>
          {rows.map(([k, v]) => (
            <ThemedText key={k} type="small"><ThemedText type="small" themeColor="textSecondary">{k}: </ThemedText>{v}</ThemedText>
          ))}
        </View>
      ))}
      {local && (
        <ThemedText type="small" themeColor="textSecondary" style={styles.note}>
          Sample data: your answers stay on this phone. Next you&apos;ll see the sign-up card&apos;s made-up person on day
          one, worked out by FAST&apos;s own engine, whatever you typed here.
        </ThemedText>
      )}
    </>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  const t = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      {/* a choice still to make is outlined like a field in error (D-152) */}
      <View style={[styles.ring, { borderColor: error ? t.bad : 'transparent' }]}>{children}</View>
      {error && <Err text={error} />}
    </View>
  );
}

function YesNo({ label, value, onChange, error }: { label: string; value: boolean | null; onChange: (v: boolean) => void; error?: string }) {
  return (
    <Field label={label} error={error}>
      <Segmented<'yes' | 'no' | ''> label={label} value={value === null ? '' : value ? 'yes' : 'no'} onChange={(v) => onChange(v === 'yes')}
                                     options={[{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }]} />
    </Field>
  );
}

function Err({ text }: { text: string }) {
  const t = useTheme();
  return <ThemedText type="small" style={{ color: t.bad }}>{text}</ThemedText>;
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: Spacing.five },
  progress: { gap: Spacing.one },
  ring: { borderWidth: 1, borderRadius: Spacing.three + Spacing.one, padding: 1 },
  bar: { height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
  title: { fontSize: 26, lineHeight: 32 },
  field: { gap: Spacing.one },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  section: { marginTop: Spacing.two },
  debt: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three, borderRadius: Spacing.three, padding: Spacing.three },
  flex: { flex: 1 },
  group: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.half },
  groupHead: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.one },
  note: { fontSize: 12 },
  buttons: { flexDirection: 'row', gap: Spacing.two, marginTop: Spacing.two },
});
