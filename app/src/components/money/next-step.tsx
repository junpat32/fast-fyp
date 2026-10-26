import { StyleSheet, View } from 'react-native';

import type { Advice } from '@/api/types';
import { Expandable } from '@/components/expandable';
import { PlantIcon } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { GAME_RULES } from '@/data/game-rules';
import { useTheme } from '@/hooks/use-theme';
import { adviceReward } from '@/lib/rewards';

import { Card } from '@/components/card';

/** The suggested next step (B9) as one action-first line; the full text and the other advice behind
 * "Read more" (D-108). Its real game reward follows the step in small type (D-107 guardrail). */
export function NextStep({ advice }: { advice: Advice[] }) {
  const t = useTheme();                         // before any return: hooks run on every render
  if (advice.length === 0) return null;
  const [top, ...rest] = advice;
  const reward = adviceReward(top.rule, GAME_RULES);
  return (
    <Card title="Your next step">
      <ThemedText type="default" style={styles.step}>{top.short}</ThemedText>
      {reward && (
        <View style={styles.rewardRow}>
          <PlantIcon stage={1} max={24} />
          <ThemedText type="small" style={[styles.reward, { color: t.reward }]}>{reward}</ThemedText>
        </View>
      )}
      <Expandable label={rest.length ? `Read more (+${rest.length} more tips)` : 'Read more'}>
        <ThemedText type="smallBold">{top.title}</ThemedText>
        <ThemedText type="small">{top.text}</ThemedText>
        {rest.map((a) => (
          <View key={a.rule} style={styles.item}>
            <ThemedText type="small" style={styles.itemTitle}>{a.title}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">{a.short}</ThemedText>
          </View>
        ))}
      </Expandable>
    </Card>
  );
}

const styles = StyleSheet.create({
  step: { fontWeight: 700, fontSize: 18, lineHeight: 24 },
  rewardRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  reward: { flex: 1 },
  item: { gap: Spacing.half, marginTop: Spacing.one },
  itemTitle: { fontWeight: 600 },
});
