import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card } from '@/components/card';
import { Button } from '@/components/fields';
import { DebtForm } from '@/components/lists/debt-form';
import { DebtPlanCard } from '@/components/lists/debt-plan-card';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { BAND_LABEL } from '@/lib/bands';
import { myDate } from '@/lib/checkin';
import { debtName, debtTotals, kindLabel, paidOff, type DebtRow, type NewDebt } from '@/lib/debts';
import { rmText } from '@/lib/entry';
import { monthName, shortDay } from '@/lib/format';

const rm = (x: number) => rmText(x.toFixed(2));
const why = (e: unknown) => (e instanceof Error ? e.message : String(e));

/**
 * The Debts screen (docs/app_plan.md §3; D-121): every loan, card and older BNPL plan with its monthly
 * payment and what is left to pay. These payments are the debt side of the band (DSR, rule 6), so the
 * top card puts the list's total next to the share of income the band counts, which also includes the
 * BNPL instalments worked out from logged purchases (DB4). Opened from the Money screen.
 */
export default function DebtsScreen() {
  const { api, debts, now, version, changed } = useApi();
  const t = useTheme();
  const { data: list, loading } = useRequest(() => debts.list(), [debts, version]);
  const { data: a } = useRequest(() => api.assess(), [api, version]);
  const [editing, setEditing] = useState<DebtRow | 'new' | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const today = myDate(now().toISOString());
  const open = (list ?? []).filter((d) => !paidOff(d, today)).sort((x, y) => y.monthly_payment - x.monthly_payment);
  const closed = (list ?? []).filter((d) => paidOff(d, today));
  const totals = debtTotals(open);

  const done = (message: string) => { setEditing(null); setNote(message); changed(); return null; };
  const attempt = async (job: () => Promise<string>) => {
    try { return done(await job()); } catch (e) { return why(e); }
  };
  const save = (d: NewDebt) => attempt(async () => {
    if (editing && editing !== 'new') { await debts.update(editing.id, d); return 'Saved.'; }
    await debts.add(d);
    return `Added: ${debtName({ kind: d.kind, label: d.label })}.`;
  });

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['bottom']}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Card title="Every month">
            <ThemedText type="subtitle">{rm(Number(totals.monthly))}</ThemedText>
            <ThemedText type="small">to the debts on this list · {rm(Number(totals.owed))} left to pay</ThemedText>
            {a && a.bnpl_instalments !== undefined && a.bnpl_instalments > 0 && (
              <ThemedText type="small">
                + <ThemedText type="smallBold">{rm(a.bnpl_instalments)}</ThemedText> in Buy Now Pay Later instalments from what you log
              </ThemedText>
            )}
            {a && (a.band === 'INSUFFICIENT_INCOME'
              ? <ThemedText type="small" themeColor="textSecondary">Your band waits for more income to be logged.</ThemedText>
              : <ThemedText type="small" themeColor="textSecondary">
                  Your band counts{' '}
                  <ThemedText type="smallBold">
                    {a.debt_payments !== undefined ? `${rm(a.debt_payments)} a month, ` : ''}{Math.round(a.dsr * 100)}% of your income
                  </ThemedText>
                  , in {monthName(a.assessed_month)} ({BAND_LABEL[a.band]}).
                </ThemedText>)}
          </Card>

          {note && <Animated.View entering={FadeIn}><ThemedText type="smallBold" style={{ color: t.reward }}>{note}</ThemedText></Animated.View>}
          {editing ? (
            <DebtForm key={editing === 'new' ? 'new' : editing.id} debt={editing === 'new' ? null : editing}
                      onSave={save} onCancel={() => setEditing(null)}
                      onPayOff={() => attempt(async () => {
                        const d = editing as DebtRow;
                        await debts.payOff(d.id, today);
                        return `Paid off: ${debtName(d)}. That's ${rm(d.monthly_payment)} a month you no longer owe.`;
                      })}
                      onDelete={() => attempt(async () => {
                        const d = editing as DebtRow;
                        await debts.remove(d.id);
                        return `Deleted: ${debtName(d)}.`;
                      })} />
          ) : (
            <Button label="Add a debt" onPress={() => { setNote(null); setEditing('new'); }} />
          )}

          {loading && !list && <ActivityIndicator />}
          {list && open.length === 0 && !editing && (
            <ThemedText type="small" themeColor="textSecondary">No debts on the list. Add any loan, card or older BNPL plan you pay each month.</ThemedText>
          )}
          {open.map((d) => (
            <Tap key={d.id} onPress={() => { setNote(null); setEditing(d); }} accessibilityRole="button"
                 accessibilityLabel={`${debtName(d)}: ${rm(d.monthly_payment)} a month, ${rm(d.outstanding)} left. Tap to change.`}
                 style={[styles.row, { backgroundColor: t.card }, editing !== 'new' && editing?.id === d.id && { borderColor: t.accent }]}>
              <View style={styles.flex}>
                <ThemedText type="smallBold">{debtName(d)}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {d.label && d.label !== kindLabel(d.kind) ? `${kindLabel(d.kind)} · ` : ''}{rm(d.outstanding)} left
                  {d.deducted_from_salary ? ' · off your salary' : ''}
                </ThemedText>
              </View>
              <ThemedText type="smallBold">{rm(d.monthly_payment)}<ThemedText type="small" themeColor="textSecondary"> /mo ›</ThemedText></ThemedText>
            </Tap>
          ))}

          {list && !editing && <DebtPlanCard debts={list} today={today} />}

          {closed.length > 0 && (
            <>
              <ThemedText type="smallBold" style={styles.section}>Paid off</ThemedText>
              {closed.map((d) => (
                <View key={d.id} style={[styles.row, { backgroundColor: t.card }]}>
                  <ThemedText type="small" style={styles.flex}>✓ {debtName(d)}</ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">{shortDay(d.ends_on!)}</ThemedText>
                </View>
              ))}
            </>
          )}

          <ThemedText type="small" themeColor="textSecondary" style={styles.foot}>
            Bought something with Buy Now Pay Later? Log it on Add as &quot;Buy Now Pay Later&quot; and FAST counts the
            instalments itself; list a BNPL plan here only if it started before you used FAST.
          </ThemedText>
          {debts.local && (
            <ThemedText type="small" themeColor="textSecondary" style={styles.foot}>
              Sample data: changes stay on this phone, and the band updates from them once you sign in.
            </ThemedText>
          )}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: Spacing.five },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three, borderRadius: Spacing.three, padding: Spacing.three,
         borderWidth: 1, borderColor: 'transparent' },
  flex: { flex: 1, gap: Spacing.half },
  section: { marginTop: Spacing.two },
  foot: { fontSize: 12 },
});
