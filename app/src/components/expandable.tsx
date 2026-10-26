import { useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** "Read more ›": hidden detail, one tap away (progressive disclosure, D-108). */
export function Expandable({ label, openLabel, children }: { label: string; openLabel?: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const t = useTheme();
  return (
    <View style={styles.wrap}>
      {open && <View style={styles.body}>{children}</View>}
      <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }}
                 hitSlop={8}>
        <ThemedText type="small" style={[styles.link, { color: t.accent }]}>
          {open ? (openLabel ?? 'Show less') + ' ˄' : label + ' ›'}
        </ThemedText>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.two },
  body: { gap: Spacing.two },
  link: { fontWeight: 600 },
});
