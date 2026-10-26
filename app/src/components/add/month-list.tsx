import { Pressable, StyleSheet, View } from 'react-native';

import type { Entry } from '@/api/entries';
import { Card } from '@/components/card';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { findCategory } from '@/data/categories';
import { useTheme } from '@/hooks/use-theme';
import { canEdit, dayLabel, dayShort, monthTotals, rmText } from '@/lib/entry';

/** This month's entries (study task 7: "find it in the list"), newest first; an entry opens for a fix
 * while the database still allows it (48 hours, by the user's clock). */
export function MonthList({ entries, quietDays, today, now, onOpen, local }: {
  entries: Entry[]; quietDays: string[]; today: string; now: Date; onOpen: (e: Entry) => void; local: boolean;
}) {
  const totals = monthTotals(entries);
  const t = useTheme();
  const row = [styles.row, { borderColor: t.line }];
  return (
    <Card title="This month">
      <ThemedText type="small" themeColor="textSecondary">
        {rmText(totals.out)} out · {rmText(totals.in)} in
      </ThemedText>
      {entries.length === 0 && quietDays.length === 0 && (
        <ThemedText type="small" themeColor="textSecondary">Nothing logged yet this month.</ThemedText>
      )}
      {quietDays.map((d) => (
        <View key={`quiet-${d}`} style={row}>
          <ThemedText type="small" themeColor="textSecondary" style={styles.day}>{dayShort(d)}</ThemedText>
          <ThemedText type="small" style={styles.what}>No spending ✓</ThemedText>
        </View>
      ))}
      {entries.map((e) => {
        const open = canEdit(e.created_at, now);
        const label = findCategory(e.direction, e.category)?.label ?? e.category;
        const amount = `${e.direction === 'in' ? '+' : '−'}${rmText(e.amount)}`;
        return (
          <Pressable key={e.id} onPress={open ? () => onOpen(e) : undefined} disabled={!open} style={row}
                     accessibilityRole="button"
                     accessibilityLabel={`${label}, ${amount}, ${dayLabel(e.occurred_on, today)}${open ? '. Tap to fix or delete.' : '. Locked.'}`}>
            <ThemedText type="small" themeColor="textSecondary" style={styles.day}>
              {dayShort(e.occurred_on)}
            </ThemedText>
            <View style={styles.what}>
              <ThemedText type="small">{label}</ThemedText>
              {e.note && <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>{e.note}</ThemedText>}
            </View>
            <ThemedText type="small" style={[styles.amount, e.direction === 'in' && { color: t.good }]}>{amount}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary" style={styles.chev}>{open ? '›' : ''}</ThemedText>
          </Pressable>
        );
      })}
      {local && entries.length > 0 && (
        <ThemedText type="small" themeColor="textSecondary">
          Sample data: entries stay on this phone until the app restarts, and the numbers on Money don't change.
        </ThemedText>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, minHeight: 44,
         borderTopWidth: 1 },
  day: { width: 48 },
  what: { flex: 1 },
  amount: { fontWeight: 700 },
  chev: { width: 10 },
});
