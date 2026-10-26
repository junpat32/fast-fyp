import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { HealthCard } from '@/components/money/health-card';
import { ListsCard } from '@/components/money/lists-card';
import { NextStep } from '@/components/money/next-step';
import { ProgressCard } from '@/components/money/progress-card';
import { ReasonsCard } from '@/components/money/reasons-card';
import { SummaryTiles } from '@/components/money/summary-tiles';
import { ScreenHeader } from '@/components/screen-header';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useTheme } from '@/hooks/use-theme';
import { useRequest } from '@/data/use-request';
import { monthName, shortDay } from '@/lib/format';

/**
 * The Money screen (docs/app_plan.md §3; step 4 of the core flow). Reads GET /v1/assess.
 * Progressive disclosure (D-108): three numbers with their verdicts and one next step at a glance;
 * every explanation is still on the screen, one tap away (ⓘ on a tile, "Read more", "+N more").
 * Target (D-109): status, next step and top reason on the first screen of a typical phone; health
 * and progress are one row each and may sit just below. Scrolling stays possible (font scaling,
 * smaller phones, opened panels), so nothing here is fixed-height.
 */
export default function MoneyScreen() {
  const { api, version } = useApi();
  const theme = useTheme();
  const { data: a, error, loading } = useRequest(() => api.assess(), [api, version]);
  const { data: game } = useRequest(() => api.game(), [api, version]);   // "Your progress" (D-107); optional
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView contentContainerStyle={styles.content}>
          <ScreenHeader title="Money" />
          {loading && <ActivityIndicator style={styles.loading} />}
          {error && <ThemedText style={{ color: theme.bad }}>Couldn't load your numbers: {error}</ThemedText>}
          {a && !loading && (
            <>
              <ThemedText type="small" themeColor="textSecondary" style={styles.dateLine}>
                {monthName(a.assessed_month)} · as of {shortDay(a.as_of)} · tap ⓘ to explain
              </ThemedText>
              <SummaryTiles a={a} />
              <NextStep advice={a.advice} />
              <ReasonsCard f={a.forecast} />
              <HealthCard h={a.health} />
              {game && <ProgressCard game={game} asOf={a.as_of} />}
              <ListsCard />
            </>
          )}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: BottomTabInset + Spacing.four },
  dateLine: { marginTop: -Spacing.one },
  loading: { marginTop: Spacing.four },
});
