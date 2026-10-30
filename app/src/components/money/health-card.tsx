import { StyleSheet, View } from 'react-native';

import type { Health } from '@/api/types';
import { Counted, GrowBar } from '@/components/motion';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { MOTION } from '@/lib/motion';

import { TapRow } from './tap-row';

const whole = (n: number) => String(Math.round(n));

const PARTS: [keyof Health['indicators'], string][] = [
  ['spend', 'Spending less than you earn'],
  ['savings', 'Savings cushion'],
  ['debt', 'Manageable debt'],
  ['bills', 'Bills on time'],
];
const TIER_TONE = { Healthy: 'good', Coping: 'watch', Vulnerable: 'bad' } as const;

/** The health score out of 100 and its tier (D-48) in one row; its four parts open underneath (D-109).
 * The score counts up and the parts' bars grow (D-154). */
export function HealthCard({ h }: { h: Health }) {
  const t = useTheme();
  if (h.score === null || h.tier === null) return null;
  const score = Math.round(h.score);
  const parts = PARTS.filter(([k]) => h.indicators[k] !== undefined);
  return (
    <TapRow label={`Health score ${score} out of 100, ${h.tier}. Tap for its parts.`}
            summary={
              <ThemedText type="default">
                Health score <ThemedText type="default" style={styles.strong}><Counted to={score} text={whole} /></ThemedText>
                <ThemedText type="default" themeColor="textSecondary"> / 100 · </ThemedText>
                <ThemedText type="default" style={[styles.strong, { color: t[TIER_TONE[h.tier]] }]}>{h.tier}</ThemedText>
              </ThemedText>
            }>
      {parts.map(([k, label], i) => {
        const v = Math.round(h.indicators[k] ?? 0);
        return (
          <View key={k} style={styles.row}>
            <ThemedText type="small" style={styles.label}>{label}</ThemedText>
            <View style={[styles.track, { backgroundColor: t.line }]}>
              <GrowBar share={v / 100} delay={i * MOTION.growStepMs} style={[styles.bar, { backgroundColor: t.barFill }]} />
            </View>
            <ThemedText type="small" style={styles.value}>{v}</ThemedText>
          </View>
        );
      })}
    </TapRow>
  );
}

const styles = StyleSheet.create({
  strong: { fontWeight: 700 },                    // one text size in the row; only the weight changes
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  label: { flex: 1.4 },
  track: { flex: 1, height: 8, borderRadius: 4, overflow: 'hidden' },
  bar: { height: 8, borderRadius: 4 },
  value: { width: 28, textAlign: 'right' },
});
