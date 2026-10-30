import { useState, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Reveal } from '@/components/motion';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** "Read more ›": hidden detail, one tap away (progressive disclosure, D-108); it slides open (D-154). */
export function Expandable({ label, openLabel, children }: { label: string; openLabel?: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const t = useTheme();
  return (
    <View>
      <Reveal open={open} style={styles.body}>{children}</Reveal>
      <Tap onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }}
           hitSlop={8}>
        <ThemedText type="small" style={[styles.link, { color: t.accent }]}>
          {open ? (openLabel ?? 'Show less') + ' ˄' : label + ' ›'}
        </ThemedText>
      </Tap>
    </View>
  );
}

const styles = StyleSheet.create({
  body: { gap: Spacing.two, paddingBottom: Spacing.two },   // the space above the link slides with the detail
  link: { fontWeight: 600 },
});
