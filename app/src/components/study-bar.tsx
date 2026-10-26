import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { useTheme } from '@/hooks/use-theme';
import { dayName, shortDay } from '@/lib/format';
import { canGoBack, canGoOn, type TravelStep } from '@/lib/study';

/**
 * The study bar (docs/app_plan.md step 9; D-95, D-119): the top row of every tab for a study persona,
 * the same on each, so the session script can name it once ("a bar at the top with the persona's date
 * and time-travel buttons"). Left: who this is ("Sample: Aina ▾" in sample data mode), which opens the
 * persona's story and the switch to another persona; live, a study account's "Switch account" signs out
 * to the sign-in screen, for the next account on the participant's card (D-94, D-145). Right:
 * the persona's date, with ‹ a month back and › a month on (1 Jul 2026 to 1 Jan 2027); every screen
 * reloads for the new date. `floating`: see-through pills over the Home scene.
 */
export function StudyBar({ floating = false }: { floating?: boolean }) {
  const { sample, study, travel, account } = useApi();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useTheme();
  if (!sample && !study) return null;
  const bg = floating ? t.overlay : t.sand;
  const who = sample?.name ?? 'this persona';
  const go = async (step: TravelStep) => {
    setBusy(true);
    setError(null);
    setError(await travel(step));
    setBusy(false);
  };
  return (
    <View style={styles.wrap} pointerEvents="box-none">
      <View style={styles.row} pointerEvents="box-none">
        {sample && (
          <Pressable onPress={() => setOpen(!open)} style={[styles.pill, styles.who, { backgroundColor: bg }]} hitSlop={6}
                     accessibilityRole="button" accessibilityState={{ expanded: open }}
                     accessibilityLabel={`Sample data: ${sample.name}, a made-up person. Tap to change.`}>
            <ThemedText type="small">Sample: {sample.name} {open ? '▴' : '▾'}</ThemedText>
          </Pressable>
        )}
        {account && study && (
          <Pressable onPress={() => { account.signOut(); }} style={[styles.pill, styles.who, { backgroundColor: bg }]} hitSlop={6}
                     accessibilityRole="button" accessibilityLabel="Switch account: sign out and sign in to the next one">
            <ThemedText type="small">Switch account</ThemedText>
          </Pressable>
        )}
        {study && (
          <View style={[styles.pill, styles.clock, { backgroundColor: bg }]}>
            <Step label="‹" name="A month back" enabled={!busy && canGoBack(study)} onPress={() => go('previous')} />
            <ThemedText type="smallBold" style={styles.date} accessibilityLabel={`${who}'s date: ${dayName(study.date)}`}>
              {shortDay(study.date)}
            </ThemedText>
            <Step label="›" name="A month on" enabled={!busy && canGoOn(study)} onPress={() => go('next')} />
          </View>
        )}
      </View>
      {error && <ThemedText type="small" style={[styles.note, { color: t.bad, backgroundColor: bg }]}>{error}</ThemedText>}
      {open && sample && (
        <PersonaPanel bg={bg} onDone={() => setOpen(false)} onStart={study && canGoBack(study) ? () => go('first') : null} />
      )}
    </View>
  );
}

function Step({ label, name, enabled, onPress }: { label: string; name: string; enabled: boolean; onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable onPress={onPress} disabled={!enabled} hitSlop={8} accessibilityRole="button" accessibilityLabel={name}
               accessibilityState={{ disabled: !enabled }}
               style={[styles.step, { backgroundColor: t.chip, opacity: enabled ? 1 : 0.35 }]}>
      <ThemedText style={styles.arrow}>{label}</ThemedText>
    </Pressable>
  );
}

/** The persona's story, the four made-up people to switch to, the way back to the start date, and the
 * sign-up as a new user would see it (D-124). */
function PersonaPanel({ bg, onDone, onStart }: { bg: string; onDone: () => void; onStart: (() => void) | null }) {
  const { sample, samples, chooseSample, study } = useApi();
  const t = useTheme();
  const router = useRouter();
  if (!sample) return null;
  return (
    <View style={[styles.panel, { backgroundColor: bg }]}>
      <ThemedText type="smallBold">{sample.name} is a made-up person</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">{sample.story}</ThemedText>
      <View style={styles.choices}>
        {samples.map((s) => {
          const on = s.key === sample.key;
          return (
            <Pressable key={s.key} onPress={() => { chooseSample(s.key); onDone(); }}
                       style={[styles.choice, { backgroundColor: on ? t.accent : t.chip }]} accessibilityRole="button"
                       accessibilityState={{ selected: on }}>
              <ThemedText type="small" style={on ? { color: t.onAccent } : undefined}>{s.name}</ThemedText>
            </Pressable>
          );
        })}
      </View>
      {study && (
        <ThemedText type="small" themeColor="textSecondary">
          ‹ and › move {sample.name}&apos;s story a month at a time, from {shortDay(study.first)} to {shortDay(study.last)}.
        </ThemedText>
      )}
      {onStart && study && (
        <Pressable onPress={() => { onStart(); onDone(); }} accessibilityRole="button"
                   style={[styles.choice, styles.start, { backgroundColor: t.chip }]}>
          <ThemedText type="small">Back to {shortDay(study.first)}</ThemedText>
        </Pressable>
      )}
      <Pressable onPress={() => { onDone(); router.navigate('/onboarding'); }} accessibilityRole="button" hitSlop={6}>
        <ThemedText type="small" style={{ color: t.accent, fontWeight: 700 }}>Try the sign-up, as a new user ›</ThemedText>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.two },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two, flexWrap: 'wrap' },
  pill: { flexDirection: 'row', alignItems: 'center', borderRadius: Spacing.four, minHeight: 36 },
  who: { paddingHorizontal: Spacing.three },
  clock: { marginLeft: 'auto', paddingHorizontal: Spacing.one, gap: Spacing.one },
  date: { minWidth: 82, textAlign: 'center' },
  step: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },   // 48 with hitSlop
  arrow: { fontSize: 22, lineHeight: 24, fontWeight: 700 },
  note: { alignSelf: 'flex-end', borderRadius: Spacing.three, paddingHorizontal: Spacing.three, paddingVertical: Spacing.one },
  panel: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
  choices: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  choice: { paddingHorizontal: Spacing.three, paddingVertical: Spacing.one, borderRadius: Spacing.three },
  start: { alignSelf: 'flex-start' },
});
