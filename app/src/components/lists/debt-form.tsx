import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Check, Chip } from '@/components/add/choice';
import { Button, MoneyField, RateField, TextField } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import {
  asksFromSalary, blankDebt, buildDebt, DEBT_KINDS, debtName, formOf, LABEL_MAX, type DebtErrors, type DebtForm as Form,
  type DebtRow, type NewDebt,
} from '@/lib/debts';

type Props = {
  debt: DebtRow | null;                                    // null: a new one
  onSave: (d: NewDebt) => Promise<string | null>;          // null = saved, else why not
  onPayOff: () => Promise<string | null>;
  onDelete: () => Promise<string | null>;
  onCancel: () => void;
};

/**
 * Adding or changing a debt (D-121): its kind, an optional name, the monthly payment and what is left
 * to pay, an optional interest rate (D-144), and whether it comes straight off the salary. An existing one can be marked paid off (it
 * stays on record, DB3) or deleted when it was added by mistake; both ask for a second tap.
 */
export function DebtForm({ debt, onSave, onPayOff, onDelete, onCancel }: Props) {
  const t = useTheme();
  const [form, setForm] = useState<Form>(debt ? formOf(debt) : blankDebt());
  const [errors, setErrors] = useState<DebtErrors>({});
  const [failed, setFailed] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<'paid' | 'delete' | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<Form>) => {
    setForm((f) => ({ ...f, ...patch }));
    setErrors((e) => {
      const n = { ...e };
      for (const k of Object.keys(patch)) delete n[k as keyof DebtErrors];
      return n;
    });
  };
  const run = async (job: () => Promise<string | null>) => {
    setBusy(true);
    setFailed(await job());
    setBusy(false);
  };
  const save = () => {
    const r = buildDebt(form);
    if (!r.ok) { setErrors(r.errors); return; }
    run(() => onSave(r.debt));
  };
  const hint = DEBT_KINDS.find((k) => k.kind === form.kind)?.hint;
  return (
    <View style={[styles.card, { backgroundColor: t.card }]}>
      <ThemedText type="smallBold">{debt ? `Change ${debtName(debt).toLowerCase()}` : 'Add a debt'}</ThemedText>
      <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel="Kind of debt">
        {DEBT_KINDS.map((k) => <Chip key={k.kind} label={k.label} on={form.kind === k.kind} onPress={() => set({ kind: k.kind })} />)}
      </View>
      {errors.kind && <ThemedText type="small" style={{ color: t.bad }}>{errors.kind}</ThemedText>}
      {hint && <ThemedText type="small" themeColor="textSecondary">{hint}</ThemedText>}
      <TextField label="Name (optional)" value={form.label} onChange={(v) => set({ label: v })} maxLength={LABEL_MAX}
                 placeholder="e.g. Myvi loan, Maybank card" />
      <MoneyField label="Monthly payment" value={form.monthly} onChange={(v) => set({ monthly: v })} error={errors.monthly} />
      <MoneyField label="Left to pay" value={form.owed} onChange={(v) => set({ owed: v })} error={errors.owed} />
      <RateField label="Interest rate (optional)" value={form.rate} onChange={(v) => set({ rate: v })} error={errors.rate}
                 hint="From your statement or loan letter. Leave it empty if you're not sure: FAST won't guess it." />
      {asksFromSalary(form.kind) && (
        <Check label="It comes straight off my salary (potongan gaji)" on={form.fromSalary} onChange={(v) => set({ fromSalary: v })} />
      )}
      <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
        Don&apos;t type card or account numbers: FAST keeps only the last 4 digits of any it finds.
      </ThemedText>
      {failed && <ThemedText type="small" style={{ color: t.bad }}>{failed}</ThemedText>}
      <View style={styles.row}>
        <Button label="Cancel" quiet fill onPress={onCancel} />
        <Button label={debt ? 'Save changes' : 'Add it'} fill onPress={save} disabled={busy} />
      </View>
      {debt && (
        <View style={styles.row}>
          <Button label={confirm === 'paid' ? 'Tap again: paid off' : 'Paid off'} quiet fill disabled={busy}
                  onPress={() => (confirm === 'paid' ? run(onPayOff) : setConfirm('paid'))} />
          <Button label={confirm === 'delete' ? 'Tap again to delete' : 'Added by mistake'} quiet danger fill disabled={busy}
                  onPress={() => (confirm === 'delete' ? run(onDelete) : setConfirm('delete'))} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  small: { fontSize: 12 },
});
