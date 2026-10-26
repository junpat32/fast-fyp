import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';

/** The screens live mode shows before the app itself (D-145, api/auth.ts gate). */
function Centre({ children }: { children: React.ReactNode }) {
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safe}>
        <View style={styles.box}>{children}</View>
      </SafeAreaView>
    </ThemedView>
  );
}

export function Loading() {
  return (
    <Centre>
      <ActivityIndicator accessibilityLabel="Loading" />
    </Centre>
  );
}

/** Some but not all of the app's settings are there, or a wrong one (api/config.ts). For the developer. */
export function SetupProblem({ problem }: { problem: string }) {
  return (
    <Centre>
      <ThemedText type="subtitle">FAST isn&apos;t set up yet</ThemedText>
      <ThemedText type="small">{problem}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        Set all three in app/.env (or none, for sample data), then restart Metro.
      </ThemedText>
    </Centre>
  );
}

/** Signed in, but the profile couldn't be read: say so, and offer a retry or signing out. */
export function ProfileProblem({ onRetry, onSignOut }: { onRetry: () => void; onSignOut: () => void }) {
  return (
    <Centre>
      <ThemedText type="subtitle">FAST couldn&apos;t load your details</ThemedText>
      <ThemedText type="small">Check your internet, then try again.</ThemedText>
      <View style={styles.row}>
        <Button label="Sign out" quiet fill onPress={onSignOut} />
        <Button label="Try again" fill onPress={onRetry} />
      </View>
    </Centre>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safe: { flex: 1, maxWidth: MaxContentWidth, justifyContent: 'center' },
  box: { padding: Spacing.four, gap: Spacing.three, alignItems: 'stretch' },
  row: { flexDirection: 'row', gap: Spacing.two },
});
