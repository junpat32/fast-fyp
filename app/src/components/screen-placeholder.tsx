import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';

type Props = { title: string; lines: string[]; step: string };

// A screen that isn't built yet: its name, what it will show (docs/app_plan.md §3) and the build
// step that brings it (§6). Replaced screen by screen.
export function ScreenPlaceholder({ title, lines, step }: Props) {
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.content}>
          <ThemedText type="subtitle">{title}</ThemedText>
          <ThemedView type="backgroundElement" style={styles.card}>
            {lines.map((line) => (
              <ThemedText key={line} type="small">
                • {line}
              </ThemedText>
            ))}
          </ThemedView>
          <ThemedText type="small" themeColor="textSecondary">
            Coming in {step}.
          </ThemedText>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.four, gap: Spacing.three, paddingBottom: BottomTabInset + Spacing.three },
  card: { gap: Spacing.two, padding: Spacing.three, borderRadius: Spacing.three },
});
