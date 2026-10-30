import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';

import type { CardAnswer, CardResponse } from '@/api/types';
import { Card } from '@/components/card';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { dayShort, rmText } from '@/lib/entry';

const rm = (n: number) => rmText(n.toFixed(2)).replace(/\.00$/, '');

/**
 * This week's life-event card (game_design §10, G-08; D-117): a "what if", checked against the money
 * the user has now. Hypothetical: answering never changes money; any answer is fine and gets a kind
 * reply; the game's card points come once a week, none for "Not this week" (D-107 guardrails).
 */
export function LifeEventCard({ card, onAnswer, local }: {
  card: CardResponse;
  onAnswer: (a: CardAnswer) => Promise<string | null>;       // null = saved, else why not
  local: boolean;                                            // sample data: the game can't add the points
}) {
  const t = useTheme();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tone = { covered: t.good, partly: t.watch, not_yet: t.accent }[card.coverage];
  const badge = { covered: '✓ Covered', partly: 'Partly covered', not_yet: 'Not covered yet' }[card.coverage];
  const answered = card.responses.find((r) => r.id === card.answer);
  const answer = async (a: CardAnswer) => {
    setBusy(true);
    const why = await onAnswer(a);
    setBusy(false);
    setError(why);
  };
  return (
    <Card title={`This week's what-if · week of ${dayShort(card.week)}`}>
      <ThemedText type="default" style={styles.title}>{card.title}</ThemedText>
      <ThemedText type="small">{card.text}</ThemedText>
      <View style={styles.costRow}>
        <ThemedText type="small" themeColor="textSecondary">It usually costs</ThemedText>
        <ThemedText type="smallBold">{rm(card.cost_low)} to {rm(card.cost_high)}</ThemedText>
      </View>
      <View style={[styles.badge, { borderColor: tone }]}>
        <ThemedText type="smallBold" style={{ color: tone }}>{badge}</ThemedText>
        <ThemedText type="small" style={styles.badgeText}>{card.coverage_text}</ThemedText>
      </View>
      {answered ? (
        <Animated.View entering={ZoomIn.springify()} style={styles.done}>
          <ThemedText type="smallBold">{answered.label}</ThemedText>
          <ThemedText type="small">{answered.after}</ThemedText>
          {answered.id !== 'not_this_week' && (
            <ThemedText type="smallBold" style={{ color: t.reward }}>
              +{card.points} points this week{local ? ' (saved once you sign in)' : ''}
            </ThemedText>
          )}
        </Animated.View>
      ) : (
        <>
          <ThemedText type="small" themeColor="textSecondary">What would you do? There's no wrong answer.</ThemedText>
          {card.responses.filter((r) => r.id !== 'not_this_week').map((r) => (
            <Tap key={r.id} onPress={() => answer(r.id)} disabled={busy} accessibilityRole="button"
                 style={[styles.choice, { backgroundColor: t.card, borderColor: t.accent }, busy && styles.busy]}>
              <ThemedText type="small" style={styles.choiceText}>{r.label}</ThemedText>
              <ThemedText type="small" style={{ color: t.reward }}>+{card.points}</ThemedText>
            </Tap>
          ))}
          <Tap onPress={() => answer('not_this_week')} disabled={busy} accessibilityRole="button" hitSlop={8}>
            <ThemedText type="small" style={[styles.skip, { color: t.accent }]}>Not this week</ThemedText>
          </Tap>
        </>
      )}
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
    </Card>
  );
}

const styles = StyleSheet.create({
  title: { fontWeight: 700 },
  costRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  badge: { borderWidth: 1.5, borderRadius: Spacing.two, padding: Spacing.two, gap: Spacing.half },
  badgeText: {},
  choice: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: Spacing.three,
            minHeight: 44, paddingHorizontal: Spacing.three, gap: Spacing.two },
  choiceText: { flex: 1, fontWeight: 600 },
  busy: { opacity: 0.5 },
  skip: { textAlign: 'center', fontWeight: 600, paddingVertical: Spacing.one },
  done: { gap: Spacing.one },
});
