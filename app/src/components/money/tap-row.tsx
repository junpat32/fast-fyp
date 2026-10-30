import { useState, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Reveal } from '@/components/motion';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** A one-row summary that opens its details underneath (D-109), sliding (D-154). The whole row is the
 * button, at least 48 dp tall (Android's minimum touch target). */
export function TapRow({ summary, label, children }: { summary: ReactNode; label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const t = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: t.card }]}>
      <Tap onPress={() => setOpen(!open)} style={styles.row} accessibilityRole="button"
           accessibilityLabel={label} accessibilityState={{ expanded: open }}>
        <View style={styles.summary}>{summary}</View>
        <ThemedText type="default" themeColor="textSecondary">{open ? '˄' : '›'}</ThemedText>
      </Tap>
      <Reveal open={open} style={styles.body}>{children}</Reveal>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: Spacing.three, paddingHorizontal: Spacing.three },
  row: { minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.two },
  summary: { flex: 1 },
  body: { gap: Spacing.two, paddingBottom: Spacing.three },
});
