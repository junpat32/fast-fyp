import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { StudyBar } from '@/components/study-bar';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * A screen's title, under the study bar (D-119: who the persona is, its date and time travel; in sample
 * data mode it also says the person is made up, D-106). For everyone else the title stands alone. Beside
 * it, "More" opens the More screen (D-127): the character, badges, how FAST works, privacy, the account.
 */
export function ScreenHeader({ title }: { title: string }) {
  const router = useRouter();
  const t = useTheme();
  return (
    <View style={styles.wrap}>
      <StudyBar />
      <View style={styles.row}>
        <ThemedText type="subtitle" style={styles.title}>{title}</ThemedText>
        <Pressable onPress={() => router.navigate('/more')} accessibilityRole="button" hitSlop={8}
                   accessibilityLabel="More: your character, badges, privacy"
                   style={[styles.more, { backgroundColor: t.card }]}>
          <ThemedText type="smallBold">More ›</ThemedText>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.two },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  title: { flex: 1 },
  more: { borderRadius: Spacing.four, paddingHorizontal: Spacing.three, minHeight: 36, justifyContent: 'center' },
});
