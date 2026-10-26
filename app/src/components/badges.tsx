import { StyleSheet, View } from 'react-native';

import type { GameResponse } from '@/api/types';
import { Sprite } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { GAME_RULES } from '@/data/game-rules';
import { useTheme } from '@/hooks/use-theme';
import { badgeList } from '@/lib/badges';

/**
 * The game's three badges (D-127): each medal, earned or not yet (grey), what earns it and, where the
 * game says, how close the user is. Medals are UI, not part of the room, so they keep their daylight
 * colours at night. Shown in the Home points panel and on the More screen.
 */
export function Badges({ game }: { game: GameResponse }) {
  const t = useTheme();
  return (
    <View style={styles.list}>
      {badgeList(game, GAME_RULES).map((b) => (
        <View key={b.key} style={styles.row} accessible
              accessibilityLabel={`${b.name}: ${b.earned ? 'earned' : `not yet. ${b.how} ${b.now ?? ''}`}`}>
          <Sprite name={`badge_${b.key}${b.earned ? '' : '_locked'}`} min={28} max={36} period="afternoon" />
          <View style={styles.text}>
            <ThemedText type="smallBold">
              {b.name}{b.earned && <ThemedText type="small" style={{ color: t.good, fontWeight: 700 }}> · earned</ThemedText>}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary" style={styles.small}>{b.how}</ThemedText>
            {b.now && <ThemedText type="small" style={styles.small}>{b.now}</ThemedText>}
          </View>
        </View>
      ))}
      <ThemedText type="small" themeColor="textSecondary" style={styles.small}>A badge, once earned, stays.</ThemedText>
    </View>
  );
}

/** The earned medals, small, beside the points (nothing when none is earned yet). */
export function EarnedMedals({ badges }: { badges: string[] }) {
  if (badges.length === 0) return null;
  return (
    <View style={styles.medals} accessible accessibilityLabel={`${badges.length} ${badges.length === 1 ? 'badge' : 'badges'} earned`}>
      {badges.map((b) => <Sprite key={b} name={`badge_${b}_small`} min={16} max={20} period="afternoon" />)}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: Spacing.two },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  text: { flex: 1, minWidth: 0 },
  small: { fontSize: 12 },
  medals: { flexDirection: 'row', gap: 2 },
});
