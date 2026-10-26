import { StyleSheet, View } from 'react-native';

import type { GameResponse } from '@/api/types';
import { PlantIcon } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { GAME_RULES } from '@/data/game-rules';
import { useTheme } from '@/hooks/use-theme';
import { dayName, monthName } from '@/lib/format';
import { checkinWindow, cushionProgress, gardenProgress, milestoneLine, monthStrip, progressLine,
         progressParts } from '@/lib/rewards';

import { TapRow } from './tap-row';

/** "Your progress" (D-107): the cushion milestones that grow the room (A) and the months that grow
 * the garden (C). Positive only: nothing random, compared or taken away. One row with the room and
 * the next unlock, points included (D-109); the milestone bar, garden and check-in open underneath. */
export function ProgressCard({ game, asOf }: { game: GameResponse; asOf: string }) {
  const cushion = cushionProgress(game, GAME_RULES);
  const garden = gardenProgress(game.garden, GAME_RULES);
  const strip = monthStrip(game.months);
  const window = checkinWindow(asOf, GAME_RULES);
  const line = progressLine(game, GAME_RULES);
  const t = useTheme();
  const { room, next } = progressParts(game, GAME_RULES);
  return (
    <TapRow label={`Your progress: ${line}. Tap for details.`}
            summary={
              <View style={styles.summary}>
                <PlantIcon stage={game.look.savings_plant} />
                <View style={styles.summaryText}>
                  <ThemedText type="default" style={styles.room}>{room}</ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">{next[0].toUpperCase() + next.slice(1)}</ThemedText>
                </View>
              </View>
            }>
      <View style={[styles.track, { backgroundColor: t.line }]}>
        <View style={[styles.fill, { width: `${cushion.fill * 100}%`, backgroundColor: t.rangeBar }]} />
        {cushion.milestones.map((m) => (
          <View key={m.months} style={[styles.tick, { left: `${(m.months / 3) * 100}%` },
                                       { backgroundColor: m.reached ? t.reward : t.textSecondary }]} />
        ))}
      </View>
      <View style={styles.labels}>
        {cushion.milestones.map((m) => (
          <ThemedText key={m.months} type="small" themeColor={m.reached ? 'text' : 'textSecondary'}
                      style={[styles.label, { left: `${(m.months / 3) * 100}%` }]}>
            {m.reached ? '✓ ' : ''}{m.months}
          </ThemedText>
        ))}
      </View>
      <ThemedText type="small">
        {cushion.next ? milestoneLine(cushion.next) : 'Every room level is unlocked. Keeping your cushion earns points each month.'}
      </ThemedText>

      <ThemedText type="smallBold" style={styles.section}>Garden level {garden.level} of {garden.top}</ThemedText>
      <ThemedText type="small">
        {!garden.open ? 'Your garden opens after your first 3 check-ins.'
          : garden.next ? `${garden.next.needs} more counted ${garden.next.needs === 1 ? 'month' : 'months'} to reach level ${garden.next.level}. ` +
            `A month counts when you meet your saving goal or keep at least 1 month of costs saved.`
          : 'Your garden is fully grown.'}
      </ThemedText>
      {strip.length > 0 && (
        <View style={styles.strip}>
          {strip.map((m) => (
            <View key={m.month} style={styles.month}>
              <ThemedText type="small" themeColor="textSecondary">{monthName(m.month).slice(0, 3)}</ThemedText>
              <ThemedText type="small">{m.verified ? '✓' : '·'}</ThemedText>
              <ThemedText type="small">{m.garden ? '🌱' : ' '}</ThemedText>
            </View>
          ))}
        </View>
      )}
      <ThemedText type="small" themeColor="textSecondary">✓ checked in and adds up · 🌱 counted for the garden</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        This month's check-in opens on {dayName(window.opens)} and stays open until {dayName(window.closes)}.
      </ThemedText>
    </TapRow>
  );
}

const styles = StyleSheet.create({
  summary: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  summaryText: { flex: 1, gap: Spacing.half },
  room: { fontWeight: 700 },
  track: { height: 12, borderRadius: 6, marginTop: Spacing.one, marginHorizontal: Spacing.two },
  fill: { height: 12, borderRadius: 6 },
  tick: { position: 'absolute', top: -2, width: 4, height: 16, marginLeft: -2, borderRadius: 2 },
  labels: { height: 20, marginHorizontal: Spacing.two },
  label: { position: 'absolute', width: 40, marginLeft: -20, textAlign: 'center' },
  section: { marginTop: Spacing.two },
  strip: { flexDirection: 'row', justifyContent: 'space-between', marginTop: Spacing.one },
  month: { alignItems: 'center', gap: Spacing.half, minWidth: 36 },
});
