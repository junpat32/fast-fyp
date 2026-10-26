import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { CATEGORIES, COMMON_OUT, findCategory } from '@/data/categories';
import { useTheme } from '@/hooks/use-theme';
import type { Direction } from '@/lib/entry';

import { Chip } from './choice';

/** The category, as chips: for money out the common ones first and the rest, by group, one tap away
 * (D-108's progressive disclosure); for money in, all five. */
export function CategoryPicker({ direction, value, onChange }: {
  direction: Direction; value: string; onChange: (key: string) => void;
}) {
  const [more, setMore] = useState(false);
  const t = useTheme();
  if (direction === 'in') {
    return (
      <View style={styles.chips}>
        {CATEGORIES.in.map((c) => <Chip key={c.key} label={c.label} on={c.key === value} onPress={() => onChange(c.key)} />)}
      </View>
    );
  }
  const shown = COMMON_OUT.includes(value) || value === '' ? COMMON_OUT : [...COMMON_OUT, value];
  return (
    <View style={styles.wrap}>
      <View style={styles.chips}>
        {shown.map((k) => {
          const c = findCategory('out', k);
          return c ? <Chip key={k} label={c.label} on={k === value} onPress={() => onChange(k)} /> : null;
        })}
        <Pressable onPress={() => setMore(!more)} style={styles.more} accessibilityRole="button"
                   accessibilityState={{ expanded: more }} hitSlop={4}>
          <ThemedText type="small" style={[styles.moreText, { color: t.accent }]}>{more ? 'Fewer ˄' : 'More ›'}</ThemedText>
        </Pressable>
      </View>
      {more && Object.entries(CATEGORIES.groups).map(([g, title]) => {
        const rest = CATEGORIES.out.filter((c) => c.group === g && !COMMON_OUT.includes(c.key));
        if (rest.length === 0) return null;
        return (
          <View key={g} style={styles.group}>
            <ThemedText type="small" themeColor="textSecondary" style={styles.groupTitle}>{title.toUpperCase()}</ThemedText>
            <View style={styles.chips}>
              {rest.map((c) => <Chip key={c.key} label={c.label} on={c.key === value} onPress={() => onChange(c.key)} />)}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.three },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  more: { paddingHorizontal: Spacing.two, minHeight: 36, justifyContent: 'center' },
  moreText: { fontWeight: 600 },
  group: { gap: Spacing.two },
  groupTitle: { fontSize: 11, letterSpacing: 0.8, fontWeight: 600 },
});
