import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { myDate } from '@/lib/checkin';
import { debtTotals, paidOff } from '@/lib/debts';
import { rmText } from '@/lib/entry';

/** The Money screen's way to the debts list and the budgets (D-121), one row each with a summary, and
 * to the money helper (D-123: the study's second persona asks it a question, so it is easy to find). */
export function ListsCard() {
  const { debts, budgets, now, version } = useApi();
  const router = useRouter();
  const t = useTheme();
  const { data: list } = useRequest(() => debts.list(), [debts, version]);
  const { data: limits } = useRequest(() => budgets.list(), [budgets, version]);
  const today = myDate(now().toISOString());
  const open = (list ?? []).filter((d) => !paidOff(d, today));
  const n = open.length;
  return (
    <View style={[styles.card, { backgroundColor: t.card }]}>
      <Row title="Debts" onPress={() => router.navigate('/debts')}
           sub={list ? (n ? `${rmText(debtTotals(open).monthly)} a month · ${n} ${n === 1 ? 'debt' : 'debts'}` : 'None listed') : ' '} />
      <View style={[styles.rule, { backgroundColor: t.line }]} />
      <Row title="Budgets" onPress={() => router.navigate('/budgets')}
           sub={limits ? (limits.length ? `${limits.length} set` : 'Set a monthly limit') : ' '} />
      <View style={[styles.rule, { backgroundColor: t.line }]} />
      <Row title="Questions?" onPress={() => router.navigate('/helper')} sub="Ask the money helper" />
    </View>
  );
}

function Row({ title, sub, onPress }: { title: string; sub: string; onPress: () => void }) {
  return (
    <Tap onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title}: ${sub}`} style={styles.row}>
      <ThemedText type="smallBold" style={styles.title}>{title}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary" style={styles.sub}>{sub} ›</ThemedText>
    </Tap>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: Spacing.three, paddingHorizontal: Spacing.three },
  row: { flexDirection: 'row', alignItems: 'center', minHeight: 48, gap: Spacing.two },
  title: { width: 88 },
  sub: { flex: 1, textAlign: 'right' },
  rule: { height: StyleSheet.hairlineWidth },
});
