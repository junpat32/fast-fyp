import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** A row of options, exactly one chosen (money out / in; how it was paid). */
export function Segmented<T extends string>({ options, value, onChange, label }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string;
}) {
  const t = useTheme();
  return (
    <View style={[styles.segmented, { backgroundColor: t.segment }]} accessibilityRole="radiogroup" accessibilityLabel={label}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => onChange(o.value)} style={[styles.segment, on && { backgroundColor: t.accent }]}
                     accessibilityRole="radio" accessibilityState={{ checked: on }}>
            <ThemedText type="small" style={[styles.segmentText, on && { color: t.onAccent }]}>{o.label}</ThemedText>
          </Pressable>
        );
      })}
    </View>
  );
}

/** One tappable chip (a category). */
export function Chip({ label, on, onPress }: { label: string; on: boolean; onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected: on }} hitSlop={4}
               style={[styles.chip, on ? { backgroundColor: t.accent, borderColor: t.accent }
                                       : { backgroundColor: t.card, borderColor: t.line }]}>
      <ThemedText type="small" style={on ? { color: t.onAccent } : undefined}>{label}</ThemedText>
    </Pressable>
  );
}

/** A yes/no line ("It was unexpected"). */
export function Check({ label, on, onChange }: { label: string; on: boolean; onChange: (v: boolean) => void }) {
  const t = useTheme();
  return (
    <Pressable onPress={() => onChange(!on)} style={styles.check} accessibilityRole="checkbox"
               accessibilityState={{ checked: on }}>
      <View style={[styles.box, on ? { backgroundColor: t.accent, borderColor: t.accent } : { borderColor: t.textSecondary }]}>
        {on && <ThemedText type="small" style={{ color: t.onAccent }}>✓</ThemedText>}
      </View>
      <ThemedText type="small" style={styles.checkText}>{label}</ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  segmented: { flexDirection: 'row', borderRadius: Spacing.three, padding: 3 },
  segment: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', borderRadius: Spacing.three - 2 },
  segmentText: { fontWeight: 600, textAlign: 'center' },
  chip: { paddingHorizontal: Spacing.three, minHeight: 36, justifyContent: 'center', borderRadius: Spacing.four, borderWidth: 1 },
  check: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, minHeight: 44 },
  box: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  checkText: { flex: 1 },
});
