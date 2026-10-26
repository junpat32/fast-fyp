import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Chip } from '@/components/add/choice';
import { Card } from '@/components/card';
import { Button, MoneyField } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { CATEGORIES, COMMON_OUT, findCategory } from '@/data/categories';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { budgetCategories, budgetLine, buildBudget, spentByCategory, type BudgetRow } from '@/lib/budgets';
import { myDate } from '@/lib/checkin';
import { rmText } from '@/lib/entry';
import { monthName } from '@/lib/format';

const nameOf = (key: string) => findCategory('out', key)?.label ?? key;

/**
 * The Budgets screen (docs/app_plan.md §3; D-121): a monthly limit for the categories the user wants to
 * keep an eye on, and this month's logged spending against each. Just for the user: no points either
 * way (D-11). Opened from the Home budget board and the Money screen.
 */
export default function BudgetsScreen() {
  const { budgets, entries, now, version, changed } = useApi();
  const t = useTheme();
  const today = myDate(now().toISOString());
  const { data: list, loading } = useRequest(() => budgets.list(), [budgets, version]);
  const { data: month } = useRequest(() => entries.month(today), [entries, version, today]);
  const [editing, setEditing] = useState<BudgetRow | 'new' | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const spent = spentByCategory(month ?? []);
  const rows = (list ?? []).map((b) => ({ ...b, line: budgetLine(b.monthly_limit, spent[b.category] ?? '0.00') }));

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['bottom']}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Card title={`${monthName(today)} so far`}>
            <ThemedText type="small">
              A monthly limit for anything you want to keep an eye on, against what you log on Add. Budgets are just
              for you: they never earn or cost points.
            </ThemedText>
          </Card>

          {note && <Animated.View entering={FadeIn}><ThemedText type="smallBold" style={{ color: t.reward }}>{note}</ThemedText></Animated.View>}
          {editing ? (
            <BudgetForm key={editing === 'new' ? 'new' : editing.category} budget={editing === 'new' ? null : editing}
                        taken={(list ?? []).map((b) => b.category)} onCancel={() => setEditing(null)}
                        onSave={async (category, limit) => {
                          await budgets.set({ category, monthly_limit: limit });
                          setEditing(null); setNote(`Budget set: ${nameOf(category)}, ${rmText(limit)} a month.`); changed();
                        }}
                        onRemove={async (category) => {
                          await budgets.remove(category);
                          setEditing(null); setNote(`Budget removed: ${nameOf(category)}.`); changed();
                        }} />
          ) : (
            <Button label="Set a budget" onPress={() => { setNote(null); setEditing('new'); }} />
          )}

          {loading && !list && <ActivityIndicator />}
          {list && list.length === 0 && (
            <ThemedText type="small" themeColor="textSecondary">No budgets yet. Eating out or shopping are good ones to start with.</ThemedText>
          )}
          {rows.map((b) => (
            <Pressable key={b.category} onPress={() => { setNote(null); setEditing(b); }} accessibilityRole="button"
                       accessibilityLabel={`${nameOf(b.category)}: ${rmText(spent[b.category] ?? '0.00')} of ${rmText(b.monthly_limit.toFixed(2))}. Tap to change.`}
                       style={[styles.row, { backgroundColor: t.card }]}>
              <View style={styles.head}>
                <ThemedText type="smallBold" style={styles.flex}>{nameOf(b.category)}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {rmText(spent[b.category] ?? '0.00')} of {rmText(b.monthly_limit.toFixed(2))} ›
                </ThemedText>
              </View>
              <View style={[styles.bar, { backgroundColor: t.line }]}>
                <View style={[styles.fill, { width: `${b.line.share * 100}%`, backgroundColor: b.line.over ? t.watch : t.barFill }]} />
              </View>
              <ThemedText type="small" style={{ color: b.line.over ? t.watch : t.textSecondary }}>
                {b.line.over ? `${rmText(b.line.over)} over this month` : `${rmText(b.line.left!)} left this month`}
              </ThemedText>
            </Pressable>
          ))}
          {budgets.local && (
            <ThemedText type="small" themeColor="textSecondary" style={styles.foot}>
              Sample data: budgets stay on this phone, and spending counts what you added on Add this session.
            </ThemedText>
          )}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

/** A new budget (a category without one yet, and its limit) or a change to one. */
function BudgetForm({ budget, taken, onSave, onRemove, onCancel }: {
  budget: BudgetRow | null; taken: string[]; onSave: (category: string, limit: string) => Promise<void>;
  onRemove: (category: string) => Promise<void>; onCancel: () => void;
}) {
  const t = useTheme();
  const [category, setCategory] = useState(budget?.category ?? '');
  const [limit, setLimit] = useState(budget ? budget.monthly_limit.toFixed(2) : '');
  const [errors, setErrors] = useState<Partial<Record<'category' | 'limit', string>>>({});
  const [more, setMore] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const free = budgetCategories(CATEGORIES).filter((c) => !taken.includes(c.key));
  const shown = more ? free : free.filter((c) => COMMON_OUT.includes(c.key));
  const save = () => {
    const r = buildBudget(category, limit, taken.filter((c) => c !== budget?.category), CATEGORIES);
    if (!r.ok) { setErrors(r.errors); return; }
    onSave(r.budget.category, r.budget.monthly_limit);
  };
  return (
    <View style={[styles.form, { backgroundColor: t.card }]}>
      <ThemedText type="smallBold">{budget ? `Budget for ${nameOf(budget.category).toLowerCase()}` : 'Set a budget'}</ThemedText>
      {!budget && (
        <>
          <View style={styles.chips}>
            {shown.map((c) => <Chip key={c.key} label={c.label} on={category === c.key} onPress={() => { setCategory(c.key); setErrors({}); }} />)}
            {!more && free.length > shown.length && <Chip label="More ›" on={false} onPress={() => setMore(true)} />}
          </View>
          {errors.category && <ThemedText type="small" style={{ color: t.bad }}>{errors.category}</ThemedText>}
        </>
      )}
      <MoneyField label="Monthly limit" value={limit} onChange={(v) => { setLimit(v); setErrors({}); }} error={errors.limit} />
      <View style={styles.buttons}>
        <Button label="Cancel" quiet fill onPress={onCancel} />
        <Button label={budget ? 'Save' : 'Set it'} fill onPress={save} />
      </View>
      {budget && (
        <Button label={confirm ? 'Tap again to remove' : 'Remove this budget'} quiet danger
                onPress={() => (confirm ? onRemove(budget.category) : setConfirm(true))} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: Spacing.five },
  row: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
  head: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  flex: { flex: 1 },
  bar: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },
  form: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  buttons: { flexDirection: 'row', gap: Spacing.two },
  foot: { fontSize: 12 },
});
