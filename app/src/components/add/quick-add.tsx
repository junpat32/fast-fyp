import { useState } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import type { Entry } from '@/api/entries';
import { Chip } from '@/components/add/choice';
import { Card } from '@/components/card';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { CATEGORIES, findCategory } from '@/data/categories';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { earliestDay, rmText, type Form } from '@/lib/entry';
import { billsDue, parseQuick, repeats } from '@/lib/quickadd';

/**
 * Quicker logging (D-126): a sentence typed or spoken through the keyboard's mic ("RM12 lunch",
 * "salary 2800"), the debts on the list still to pay this month, and recent entries "same again".
 * Each fills the form below; the user checks it and taps Save, as with anything typed in.
 */
export function QuickAdd({ today, month, onFill }: {
  today: string; month: Entry[]; onFill: (patch: Partial<Form>) => void;
}) {
  const { entries, debts, version } = useApi();
  const t = useTheme();
  const [text, setText] = useState('');
  const [said, setSaid] = useState<{ text: string; ok: boolean } | null>(null);
  const { data: list } = useRequest(() => debts.list(), [debts, version]);
  const { data: last } = useRequest(() => entries.month(earliestDay(today)), [entries, version, today]);
  const bills = billsDue(list ?? [], month, today);
  const again = repeats([...month, ...(last ?? [])]);

  const fill = () => {
    if (!text.trim()) return;
    const q = parseQuick(text, CATEGORIES, today);
    onFill(q.patch);
    setText('');
    setSaid(!q.amount ? { text: 'No amount found: type it in below.', ok: false }
      : !q.category ? { text: `Filled in ${rmText(q.patch.amount!)}: choose a category below.`, ok: false }
      : { text: `Filled in below: ${rmText(q.patch.amount!)} · ${q.category}. Check it, then Save.`, ok: true });
  };
  const pick = (patch: Partial<Form>, what: string) => {
    onFill(patch);
    setSaid({ text: `Filled in below: ${what}. Check it, then Save.`, ok: true });
  };

  return (
    <Card title="Quick add">
      <View style={styles.row}>
        <TextInput value={text} onChangeText={setText} onSubmitEditing={fill} returnKeyType="done"
                   placeholder='Type or say it, e.g. "RM12 lunch"' placeholderTextColor={t.textSecondary} maxLength={120}
                   accessibilityLabel="Quick add: type or say what you spent or got"
                   style={[styles.input, { backgroundColor: t.input, borderColor: t.line, color: t.text }]} />
        <Pressable onPress={fill} accessibilityRole="button" style={[styles.go, { backgroundColor: t.accent }]}>
          <ThemedText type="small" style={{ color: t.onAccent, fontWeight: 700 }}>Fill in</ThemedText>
        </Pressable>
      </View>
      <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
        Tap the keyboard&apos;s mic to say it. Works for money in too: &quot;salary 2800&quot;.
      </ThemedText>
      {said && <ThemedText type="small" style={{ color: said.ok ? t.good : t.watch, fontWeight: 600 }}>{said.text}</ThemedText>}
      {bills.length > 0 && (
        <>
          <ThemedText type="smallBold" style={styles.label}>Due this month</ThemedText>
          <View style={styles.chips}>
            {bills.map((b) => (
              <Chip key={b.id} label={`${b.name} · ${rmText(b.amount)}`} on={false}
                    onPress={() => pick({ direction: 'out', amount: b.amount, category: b.category, paidBy: 'now', unexpected: false,
                                          note: b.name }, `${rmText(b.amount)} · ${b.name}`)} />
            ))}
          </View>
        </>
      )}
      {again.length > 0 && (
        <>
          <ThemedText type="smallBold" style={styles.label}>Same again</ThemedText>
          <View style={styles.chips}>
            {again.map((r) => {
              const label = findCategory(r.patch.direction!, r.patch.category!)?.label ?? r.patch.category;
              return <Chip key={r.key} label={`${rmText(r.patch.amount!)} · ${label}`} on={false}
                           onPress={() => pick(r.patch, `${rmText(r.patch.amount!)} · ${label}`)} />;
            })}
          </View>
        </>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: Spacing.two },
  input: { flex: 1, minWidth: 0, borderRadius: Spacing.two, borderWidth: 1, paddingHorizontal: Spacing.three, minHeight: 44, fontSize: 15 },
  go: { borderRadius: Spacing.two, paddingHorizontal: Spacing.three, justifyContent: 'center', minHeight: 44 },
  small: { fontSize: 12 },
  label: { marginTop: Spacing.one },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
});
