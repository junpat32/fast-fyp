import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, type ScrollViewInstance, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { Entry } from '@/api/entries';
import { CategoryPicker } from '@/components/add/category-picker';
import { CheckinPanel } from '@/components/add/checkin-panel';
import { Check, Segmented } from '@/components/add/choice';
import { MonthList } from '@/components/add/month-list';
import { QuickAdd } from '@/components/add/quick-add';
import { Card } from '@/components/card';
import { ScreenHeader } from '@/components/screen-header';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useTheme } from '@/hooks/use-theme';
import { CATEGORIES, findCategory } from '@/data/categories';
import { useRequest } from '@/data/use-request';
import {
  asksPurchaseQuestions, buildEntry, dayLabel, earliestDay, NOTE_MAX, rmText, stepDay, type Direction, type Errors,
  type Form, type PaidBy,
} from '@/lib/entry';

const blank = (today: string, direction: Direction = 'out'): Form =>
  ({ direction, amount: '', category: '', paidBy: 'now', unexpected: false, day: today, note: '' });

/**
 * The Add screen (docs/app_plan.md §3; core flow step 2; study task 7, D-96): amount, money out or in,
 * category, how it was paid, unexpected, day, note; Save; "No spending today"; this month's list,
 * where an entry opens for a fix or delete for 48 hours. No points per entry: logging volume is never
 * rewarded (D-75). Today is the server's date (a persona's study date, D-90). The switch at the top
 * opens the monthly check-in instead (D-118).
 */
export default function AddScreen() {
  const { api, entries, now, version, changed } = useApi();
  const { data: a } = useRequest(() => api.assess(), [api, version]);    // time travel moves today (D-119)
  const today = a?.as_of ?? null;
  const [form, setForm] = useState<Form | null>(null);
  const [editing, setEditing] = useState<Entry | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [done, setDone] = useState<string | null>(null);
  const [list, setList] = useState<Entry[]>([]);
  const [quiet, setQuiet] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const scroll = useRef<ScrollViewInstance>(null);
  const c = useTheme();                                 // light by day, dark at night (D-114)
  const params = useLocalSearchParams<{ mode?: string }>();
  const [mode, setMode] = useState<'entry' | 'checkin'>(params.mode === 'checkin' ? 'checkin' : 'entry');
  useEffect(() => {                                     // Home's "check-in is open" pill lands here (D-118)
    if (params.mode === 'checkin') setMode('checkin');
  }, [params.mode]);

  useEffect(() => {                                     // a new day or another persona: a fresh form
    if (today) { setForm(blank(today)); setEditing(null); setErrors({}); setDone(null); }
  }, [today, entries]);
  useEffect(() => {
    if (!today) return;
    let alive = true;
    Promise.all([entries.month(today), entries.noSpendDays(today)]).then(([l, q]) => {
      if (alive) { setList(l); setQuiet(q); }
    });
    return () => { alive = false; };
  }, [entries, today, version]);

  const set = useCallback((patch: Partial<Form>) => {
    setForm((f) => (f ? { ...f, ...patch } : f));
    setErrors((e) => {
      const next = { ...e };
      for (const k of Object.keys(patch)) delete next[k as keyof Errors];
      return next;
    });
    setDone(null);
  }, []);

  if (!today || !form) {
    return (
      <ThemedView style={styles.container}>
        <SafeAreaView style={styles.safeArea} edges={['top']}><ActivityIndicator style={styles.loading} /></SafeAreaView>
      </ThemedView>
    );
  }

  const category = findCategory(form.direction, form.category);
  const purchase = asksPurchaseQuestions(form.direction, category);
  const spentToday = list.some((e) => e.occurred_on === today && e.direction === 'out' && !e.is_own_transfer);
  const quietToday = quiet.includes(today);

  async function save() {
    const r = buildEntry(form!, CATEGORIES, today!);
    if (!r.ok) { setErrors(r.errors); setDone(null); return; }
    setBusy(true);
    try {
      if (editing) await entries.update(editing.id, r.entry);
      else await entries.add(r.entry);
      setDone(`${editing ? 'Fixed' : 'Saved'}: ${rmText(r.entry.amount)} · ${category!.label}`);
      setForm(blank(today!, form!.direction));
      setEditing(null);
      changed();
    } catch (e) {
      setDone(null);
      Alert.alert("Couldn't save", e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function open(e: Entry) {
    setEditing(e);
    setForm({ direction: e.direction, amount: e.amount, category: e.category,
              paidBy: e.is_bnpl ? 'bnpl' : e.on_credit ? 'card' : 'now', unexpected: e.is_unexpected,
              day: e.occurred_on, note: e.note ?? '' });
    setErrors({});
    setDone(null);
    scroll.current?.scrollTo({ y: 0, animated: true });
  }

  function remove() {
    const e = editing!;
    const label = findCategory(e.direction, e.category)?.label ?? e.category;
    Alert.alert('Delete this entry?', `${rmText(e.amount)} · ${label}, ${dayLabel(e.occurred_on, today!)}`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        await entries.remove(e.id);
        setEditing(null);
        setForm(blank(today!, form!.direction));
        setDone('Deleted');
        changed();
      } },
    ]);
  }

  async function noSpending() {
    await entries.noSpend(today!);
    setDone('Marked: no spending today ✓');
    changed();
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView ref={scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <ScreenHeader title={editing ? 'Fix an entry' : 'Add'} />
          {!editing && (
            <Segmented<'entry' | 'checkin'> label="What to add" value={mode} onChange={setMode}
                                            options={[{ value: 'entry', label: 'Money in or out' },
                                                      { value: 'checkin', label: 'Monthly check-in' }]} />
          )}

          {mode === 'checkin' && !editing ? <CheckinPanel today={today} /> : (<>
          {!editing && (
            <QuickAdd today={today} month={list} onFill={(patch) => {
              setForm({ ...blank(today), ...patch });
              setErrors({});
              setDone(null);
            }} />
          )}
          <Card title={editing ? 'Fixing' : 'New entry'}>
            <Segmented label="Money out or in" value={form.direction}
                       options={[{ value: 'out', label: 'Money out' }, { value: 'in', label: 'Money in' }]}
                       onChange={(d) => set({ direction: d, category: '' })} />

            <View style={[styles.amountRow, { borderColor: errors.amount ? c.bad : c.line }]}>
              <ThemedText type="subtitle" themeColor="textSecondary">RM</ThemedText>
              <TextInput value={form.amount} onChangeText={(t) => set({ amount: t })} placeholder="0.00"
                         keyboardType="decimal-pad" style={[styles.amount, { color: c.text }]} accessibilityLabel="Amount in ringgit"
                         placeholderTextColor={c.textSecondary} maxLength={13} />
            </View>
            {errors.amount && <ThemedText type="small" style={{ color: c.bad }}>{errors.amount}</ThemedText>}

            <ThemedText type="smallBold">Category</ThemedText>
            <CategoryPicker direction={form.direction} value={form.category} onChange={(k) => set({ category: k })} />
            {errors.category && <ThemedText type="small" style={{ color: c.bad }}>{errors.category}</ThemedText>}

            {purchase && (
              <>
                <ThemedText type="smallBold">Paid with</ThemedText>
                <Segmented<PaidBy> label="Paid with" value={form.paidBy} onChange={(p) => set({ paidBy: p })}
                                   options={[{ value: 'now', label: 'Cash, bank, e-wallet' }, { value: 'card', label: 'Credit card' },
                                             { value: 'bnpl', label: 'BNPL' }]} />
                <Check label="It was unexpected (a repair, a fine, a doctor's visit)" on={form.unexpected}
                       onChange={(v) => set({ unexpected: v })} />
              </>
            )}

            <View style={[styles.dayRow, { backgroundColor: c.segment }]}>
              <Pressable onPress={() => set({ day: stepDay(form.day, -1, today) })} disabled={form.day <= earliestDay(today)}
                         style={styles.dayButton} accessibilityRole="button" accessibilityLabel="One day earlier" hitSlop={8}>
                <ThemedText type="subtitle" themeColor={form.day <= earliestDay(today) ? 'textSecondary' : 'text'}>‹</ThemedText>
              </Pressable>
              <ThemedText type="default" style={styles.day}>{dayLabel(form.day, today)}</ThemedText>
              <Pressable onPress={() => set({ day: stepDay(form.day, 1, today) })} disabled={form.day >= today}
                         style={styles.dayButton} accessibilityRole="button" accessibilityLabel="One day later" hitSlop={8}>
                <ThemedText type="subtitle" themeColor={form.day >= today ? 'textSecondary' : 'text'}>›</ThemedText>
              </Pressable>
            </View>
            {errors.day && <ThemedText type="small" style={{ color: c.bad }}>{errors.day}</ThemedText>}

            <TextInput value={form.note} onChangeText={(t) => set({ note: t })} placeholder="Note (optional)"
                       style={[styles.note, { backgroundColor: c.input, borderColor: c.line, color: c.text }]} maxLength={NOTE_MAX}
                       placeholderTextColor={c.textSecondary}
                       accessibilityLabel="Note, optional" />

            <Pressable onPress={save} disabled={busy} style={[styles.save, { backgroundColor: c.accent }, busy && styles.saveBusy]} accessibilityRole="button">
              <ThemedText type="default" style={[styles.saveText, { color: c.onAccent }]}>{editing ? 'Save the fix' : 'Save'}</ThemedText>
            </Pressable>
            {editing && (
              <View style={styles.editRow}>
                <Pressable onPress={() => { setEditing(null); setForm(blank(today)); }} accessibilityRole="button" hitSlop={8}>
                  <ThemedText type="small" style={[styles.link, { color: c.accent }]}>Cancel</ThemedText>
                </Pressable>
                <Pressable onPress={remove} accessibilityRole="button" hitSlop={8}>
                  <ThemedText type="small" style={[styles.link, { color: c.bad }]}>Delete this entry</ThemedText>
                </Pressable>
              </View>
            )}
            {done && <ThemedText type="small" style={[styles.link, { color: c.good }]}>✓ {done}</ThemedText>}
          </Card>

          {!editing && !spentToday && !quietToday && (
            <Pressable onPress={noSpending} style={[styles.quiet, { borderColor: c.accent }]} accessibilityRole="button">
              <ThemedText type="default" style={[styles.link, { color: c.accent }]}>No spending today</ThemedText>
            </Pressable>
          )}

          <MonthList entries={list} quietDays={quiet} today={today} now={now()} onOpen={open} local={entries.local} />
          </>)}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: BottomTabInset + Spacing.four },
  loading: { marginTop: Spacing.six },
  amountRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, borderBottomWidth: 2, paddingVertical: Spacing.one },
  amount: { flex: 1, minWidth: 0, fontSize: 32, fontWeight: 700, paddingVertical: Spacing.one },   // minWidth: a web input won't shrink
  dayRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
            borderRadius: Spacing.three, paddingHorizontal: Spacing.two, minHeight: 44 },
  dayButton: { paddingHorizontal: Spacing.three, minHeight: 44, justifyContent: 'center' },
  day: { fontWeight: 600 },
  note: { borderRadius: Spacing.two, borderWidth: 1, paddingHorizontal: Spacing.three, minHeight: 44, fontSize: 15 },
  save: { borderRadius: Spacing.three, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  saveBusy: { opacity: 0.6 },
  saveText: { fontWeight: 700 },
  editRow: { flexDirection: 'row', justifyContent: 'space-between' },
  link: { fontWeight: 600 },
  quiet: { borderWidth: 1, borderRadius: Spacing.three, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
});
