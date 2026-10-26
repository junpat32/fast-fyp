import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import type { CardAnswer } from '@/api/types';
import { Card } from '@/components/card';
import { LifeEventCard } from '@/components/future/life-event-card';
import { RangeCard } from '@/components/future/range-card';
import { SelvesCard } from '@/components/future/selves-card';
import { ScreenHeader } from '@/components/screen-header';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useTheme } from '@/hooks/use-theme';
import { THRESHOLDS } from '@/data/thresholds';
import { useRequest } from '@/data/use-request';
import { monthsText } from '@/lib/format';
import { futureMood, moodNow, rangeShort } from '@/lib/future';

/**
 * The Future screen (docs/app_plan.md §3, game_design §9; study task 4, B6): "You now" and "You in
 * 6 months", and the range of possible savings "if recent habits continue" (D-81). Reads
 * GET /v1/future; the room and mood now come from GET /v1/game, the cushion now from GET /v1/assess
 * (the Money screen's number). No percentage here (D-100). Below, this week's life-event card: a "what if"
 * checked against the money the user has now (GET/POST /v1/card, G-08, D-117).
 */
export default function FutureScreen() {
  const { api, entries, look, version, changed } = useApi();
  const theme = useTheme();
  const { data: f, error, loading } = useRequest(() => api.future(), [api, version]);
  const { data: game } = useRequest(() => api.game(), [api, version]);
  const { data: a } = useRequest(() => api.assess(), [api, version]);
  const { data: card } = useRequest(() => api.card(), [api, version]);
  const now = a?.cushion_months ?? game?.game_cushion ?? 0;
  const answer = async (r: CardAnswer) => {
    try {
      await api.answerCard(r);
      changed();                                          // the card and the game's points reload
      return null;
    } catch (e) {
      return e instanceof ApiError ? e.detail : String(e);
    }
  };
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView contentContainerStyle={styles.content}>
          <ScreenHeader title="Future" />
          <ThemedText type="small" themeColor="textSecondary" style={styles.horizon}>
            Where your habits are taking you in the next 6 months
          </ThemedText>
          {loading && <ActivityIndicator style={styles.loading} />}
          {error && <ThemedText style={{ color: theme.bad }}>Couldn't load your Future Self: {error}</ThemedText>}
          {f && !loading && !f.available && (
            <Card title="Not yet">
              <ThemedText>Your Future Self appears once you have 3 complete months of records.</ThemedText>
            </Card>
          )}
          {f && !loading && f.available && (
            <>
              <SelvesCard
                look={look}
                now={{ mood: moodNow(game?.look.mood ?? 'calm'), room: game?.room_level ?? null,
                       saved: monthsText(now) }}
                later={{ mood: futureMood(f.median_path_final_cushion, THRESHOLDS), room: f.median_path_room_level,
                         saved: rangeShort(f.months) }}
              />
              <RangeCard label={f.label} months={f.months} now={now} basedOn={f.based_on_months} />
              {a && a.advice.length > 0 && (
                <Card title="To lift this range">
                  <ThemedText type="default" style={styles.step}>{a.advice[0].short}</ThemedText>
                </Card>
              )}
              {card && <LifeEventCard card={card} onAnswer={answer} local={entries.local} />}
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
  horizon: { marginTop: -Spacing.one },
  loading: { marginTop: Spacing.four },
  step: { fontWeight: 700 },
});
