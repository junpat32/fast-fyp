import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Badges } from '@/components/badges';
import { Card } from '@/components/card';
import { CharacterPicker, type CharacterChoice } from '@/components/character/picker';
import { Expandable } from '@/components/expandable';
import { Button } from '@/components/fields';
import { ListsCard } from '@/components/money/lists-card';
import { PrivacyNotice } from '@/components/onboarding/privacy';
import { Portrait } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { AVATARS } from '@/data/avatars';
import { GAME_RULES } from '@/data/game-rules';
import { THRESHOLDS } from '@/data/thresholds';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { changeRule, limitsLine } from '@/lib/bands';
import { pointsGuide } from '@/lib/badges';
import { TONES } from '@/lib/character';
import { moodNow } from '@/lib/future';

/**
 * More (D-127): everything that isn't one of the four tabs (A5). The character, changed with the
 * sign-up's own picker (the database lets it change at any time); the badges; the debts, budgets and
 * money helper; how the band and points work (every number from the shared files, rule 5); the privacy
 * notice the user agreed to at sign-up (D-91); and the account: signing out and deleting the account
 * (delete_my_account(), D-93 S-2; study personas can't) arrive with Supabase. Opened from "More" on
 * Home and beside each tab's title.
 */
export default function MoreScreen() {
  const { api, look, setLook, sample, study, version } = useApi();
  const t = useTheme();
  const { data: game } = useRequest(() => api.game(), [api, version]);
  const [choice, setChoice] = useState<CharacterChoice | null>(null);   // null: not changing it
  const [failed, setFailed] = useState<string | null>(null);
  const describe = AVATARS.find((a) => a.avatar === look.avatar)?.look ?? '';

  const save = async () => {
    if (!choice?.avatar) return;
    const err = await setLook({ avatar: choice.avatar, tone: choice.tone ?? look.tone, glasses: choice.glasses });
    setFailed(err);
    if (!err) setChoice(null);
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['bottom']}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Card title="Your character">
            <View style={styles.me}>
              <Portrait look={look} mood={moodNow(game?.look.mood ?? 'calm')} label={`Your character: ${describe}`} size={88} />
              <View style={styles.flex}>
                <ThemedText type="smallBold">{describe}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  Skin tone {look.tone} of {TONES} · {look.glasses ? 'glasses' : 'no glasses'}
                </ThemedText>
              </View>
            </View>
            {choice ? (
              <>
                <CharacterPicker value={choice} onChange={(patch) => setChoice((c) => (c ? { ...c, ...patch } : c))} />
                {failed && <ThemedText type="small" style={{ color: t.bad }}>{failed}</ThemedText>}
                <View style={styles.buttons}>
                  <Button label="Cancel" quiet fill onPress={() => { setChoice(null); setFailed(null); }} />
                  <Button label="Save" fill onPress={save} />
                </View>
              </>
            ) : (
              <Button label="Change character" quiet onPress={() => setChoice({ ...look })} />
            )}
            {sample && (
              <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
                Sample data: a new character lasts until the app closes.
              </ThemedText>
            )}
          </Card>

          <Card title="Your badges">
            {game ? <Badges game={game} /> : <ActivityIndicator />}
          </Card>

          <ListsCard />

          <Card title="How FAST works">
            <ThemedText type="smallBold">Your band</ThemedText>
            <ThemedText type="small">
              How much of your take-home pay goes to debt payments each month. {limitsLine(THRESHOLDS)}.
            </ThemedText>
            <ThemedText type="small">{changeRule(THRESHOLDS)}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              With a typical income below RM{THRESHOLDS.insufficient_income_below_rm} a month, FAST shows no band.
            </ThemedText>
            <ThemedText type="smallBold" style={styles.section}>The forecast and Future Self</ThemedText>
            <ThemedText type="small">
              They show what could happen if recent habits continue: a likely range, not a promise.
            </ThemedText>
            <ThemedText type="smallBold" style={styles.section}>Points</ThemedText>
            <ThemedText type="small">Points come from looking after your money, never from spending.</ThemedText>
            <Expandable label="How points are earned">
              {pointsGuide(GAME_RULES).map((l) => <ThemedText key={l} type="small">• {l}</ThemedText>)}
            </Expandable>
          </Card>

          <ThemedText type="smallBold" themeColor="textSecondary" style={styles.heading}>PRIVACY</ThemedText>
          <PrivacyNotice />

          <Card title="Account">
            {sample ? (
              <ThemedText type="small">
                Sample data mode: there is no account yet. Signing out, and deleting your account with everything in it,
                come with FAST&apos;s server.
              </ThemedText>
            ) : null}
            {study && (
              <ThemedText type="small" themeColor="textSecondary">
                This is a study account: the researcher deletes it, and everything in it, after the study.
              </ThemedText>
            )}
            <View style={styles.buttons}>
              <Button label="Sign out" quiet fill disabled={!!sample} onPress={() => {}} />
              {!study && <Button label="Delete my account" quiet danger fill disabled={!!sample} onPress={() => {}} />}
            </View>
          </Card>

          <ThemedText type="small" themeColor="textSecondary" style={styles.about}>
            FAST 0.1.0 · a Final Year Project at Multimedia University. FAST explains your own numbers; it is not a
            licensed financial adviser.
          </ThemedText>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: Spacing.five },
  me: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  flex: { flex: 1, minWidth: 0 },
  buttons: { flexDirection: 'row', gap: Spacing.two },
  small: { fontSize: 12 },
  section: { marginTop: Spacing.one },
  heading: { letterSpacing: 0.8, fontSize: 12, marginTop: Spacing.two },
  about: { fontSize: 12, textAlign: 'center', marginTop: Spacing.two },
});
