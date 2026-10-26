import { StyleSheet, View } from 'react-native';

import { Portrait } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Look } from '@/lib/character';
import type { Mood } from '@/lib/future';

type Self = { mood: Mood; room: number | null; saved: string };

/** "You now" and "You in 6 months" side by side (game_design §9, D-110): the same character's face in
 * a mood (portraits, D-111), the months of costs saved, and the room level the middle path reaches.
 * The future self is never shown suffering (D-12). */
export function SelvesCard({ look, now, later }: { look: Look; now: Self; later: Self }) {
  return (
    <View style={styles.row}>
      <SelfView title="You now" look={look} self={now} />
      <ThemedText type="subtitle" themeColor="textSecondary" style={styles.arrow}>›</ThemedText>
      <SelfView title="In 6 months" look={look} self={later} />
    </View>
  );
}

function SelfView({ title, look, self }: { title: string; look: Look; self: Self }) {
  const t = useTheme();
  return (
    <View style={[styles.self, { backgroundColor: t.card }]}>
      <ThemedText type="smallBold" themeColor="textSecondary" style={styles.title}>{title.toUpperCase()}</ThemedText>
      <View style={[styles.frame, { backgroundColor: t.sand }]}>
        <Portrait look={look} mood={self.mood} label={`${title}: looking ${self.mood.replace('_', ' and ')}`} />
      </View>
      <View style={styles.numbers}>
        <ThemedText type="subtitle" style={styles.value}>{self.saved}</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">months saved</ThemedText>
      </View>
      {self.room !== null && <ThemedText type="small" themeColor="textSecondary">Room level {self.room}</ThemedText>}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'stretch', gap: Spacing.one },   // both cards the same height
  arrow: { fontSize: 28, alignSelf: 'center' },
  self: { flex: 1, borderRadius: Spacing.three, paddingVertical: Spacing.three,
          paddingHorizontal: Spacing.two, alignItems: 'center', gap: Spacing.two },
  title: { letterSpacing: 0.8, fontSize: 12 },
  frame: { borderRadius: 999, overflow: 'hidden', alignItems: 'center',
           justifyContent: 'flex-end', width: 116, height: 116 },
  numbers: { alignItems: 'center' },
  value: { fontSize: 24, lineHeight: 30 },
});
