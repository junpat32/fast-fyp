import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** A titled card (the Money and Future screens). */
export function Card({ title, children, tint }: { title: string; children: ReactNode; tint?: string }) {
  const t = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: tint ?? t.card }]}>
      <ThemedText type="smallBold" themeColor="textSecondary" style={styles.title}>
        {title.toUpperCase()}
      </ThemedText>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
  title: { letterSpacing: 0.8, fontSize: 12 },
});
