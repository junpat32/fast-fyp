import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/card';
import { Expandable } from '@/components/expandable';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { THRESHOLDS } from '@/data/thresholds';
import { useTheme } from '@/hooks/use-theme';
import { monthsText } from '@/lib/format';
import { chartTop, monthShort, rangeLine, type FutureMonth } from '@/lib/future';

const H = 132;                                   // the plot's height in dp

/**
 * B6 (task 4): the range of possible savings in 6 months, "if recent habits continue" (D-81), as a
 * sentence and a month-by-month chart; why it is a range sits one tap away (D-110). No percentage (D-100).
 */
export function RangeCard({ label, months, now, basedOn }: {
  label: string; months: FutureMonth[]; now: number; basedOn: number;
}) {
  const t = useTheme();
  const goal = THRESHOLDS.advice.cushion_first_goal_months;
  const top = chartTop(months, now, THRESHOLDS);
  const y = (v: number) => (Math.min(Math.max(v, 0), top) / top) * H;
  const last = months[months.length - 1];
  return (
    <Card title={label}>
      <ThemedText type="default">
        In 6 months you could have <ThemedText type="default" style={styles.strong}>{rangeLine(months)}</ThemedText> saved.
      </ThemedText>

      <View accessible accessibilityLabel={`Chart of possible savings: now ${monthsText(now)} months; by ${monthShort(last.month)}, ${rangeLine(months)}, the middle about ${monthsText(last.p50)}.`}>
        <View style={[styles.plot, { borderColor: t.textSecondary }]}>
          <ThemedText type="small" themeColor="textSecondary" style={styles.topLabel}>{top} months</ThemedText>
          <View style={[styles.goal, { bottom: y(goal), backgroundColor: t.watch }]} />
          <ThemedText type="small" style={[styles.goalLabel, { bottom: y(goal) + 2, color: t.watch }]}>
            goal: {goal} {goal === 1 ? 'month' : 'months'}
          </ThemedText>
          <View style={styles.columns}>
            <View style={styles.column}>
              <View style={[styles.now, { bottom: y(now) - 6, backgroundColor: t.accent }]} />
            </View>
            {months.map((m) => (
              <View key={m.month} style={styles.column}>
                <View style={[styles.bar, { bottom: y(m.p10), height: Math.max(y(m.p90) - y(m.p10), 3), backgroundColor: t.rangeBar,
                                            borderColor: t.rangeDot }]} />
                <View style={[styles.dot, { bottom: y(m.p50) - 4, backgroundColor: t.rangeDot }]} />
              </View>
            ))}
          </View>
        </View>
        <View style={styles.labels}>
          {['Now', ...months.map((m) => monthShort(m.month))].map((l) => (
            <ThemedText key={l} type="small" themeColor="textSecondary" style={styles.month}>{l}</ThemedText>
          ))}
        </View>
      </View>
      <View style={styles.legend}>
        <ThemedText type="small" themeColor="textSecondary"><ThemedText type="small" style={{ color: t.accent }}>◆</ThemedText> now</ThemedText>
        <View style={styles.key}>
          <View style={[styles.swatch, { backgroundColor: t.rangeBar, borderColor: t.rangeDot }]} />
          <ThemedText type="small" themeColor="textSecondary">possible range</ThemedText>
        </View>
        <ThemedText type="small" themeColor="textSecondary"><ThemedText type="small" style={{ color: t.rangeDot }}>●</ThemedText> middle</ThemedText>
      </View>

      <Expandable label="Why a range?">
        <ThemedText type="small">
          Nobody knows exactly what the coming months bring: pay can change, and repairs or festive costs
          come up. FAST plays out the next 6 months many times, each time picking from your last {basedOn}{' '}
          months, with the odd surprise cost, and shows the range where most of those runs end.
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          It's an illustration from your recent habits, not a promise.
        </ThemedText>
      </Expandable>
    </Card>
  );
}

const styles = StyleSheet.create({
  plot: { height: H, marginTop: Spacing.two, borderBottomWidth: 1 },
  topLabel: { position: 'absolute', top: 0, left: 0, fontSize: 11 },
  labels: { flexDirection: 'row', marginTop: Spacing.one },
  goal: { position: 'absolute', left: 0, right: 0, height: 1, opacity: 0.6 },
  goalLabel: { position: 'absolute', right: 0, fontSize: 11 },
  columns: { flexDirection: 'row', flex: 1 },
  column: { flex: 1, alignItems: 'center' },
  bar: { position: 'absolute', width: 14, borderRadius: 4, borderWidth: 1 },   // the edge: 3:1 on the card (D-153)
  key: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one },
  swatch: { width: 9, height: 13, borderRadius: 2, borderWidth: 1 },
  dot: { position: 'absolute', width: 8, height: 8, borderRadius: 4 },
  now: { position: 'absolute', width: 12, height: 12, transform: [{ rotate: '45deg' }] },
  month: { flex: 1, textAlign: 'center', fontSize: 11 },
  strong: { fontWeight: 700 },                    // same size as the sentence: only the weight changes
  legend: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.three },
});
