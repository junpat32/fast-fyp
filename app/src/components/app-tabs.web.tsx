import { Tabs, TabList, TabTrigger, TabSlot, TabTriggerSlotProps, TabListProps } from 'expo-router/ui';
import { Pressable, View, StyleSheet } from 'react-native';

import { MaxContentWidth, Spacing } from '@/constants/theme';

import { ThemedText } from './themed-text';
import { ThemedView } from './themed-view';

// The same four tabs in a browser (Expo's web build). The bar takes its own row above the screens, so
// on a phone-width browser it never covers a screen's top, where the study bar sits (D-119, D-151).
export default function AppTabs() {
  return (
    <Tabs style={styles.tabs}>
      <TabList asChild>
        <CustomTabList>
          <TabTrigger name="index" href="/" asChild>
            <TabButton>Home</TabButton>
          </TabTrigger>
          <TabTrigger name="money" href="/money" asChild>
            <TabButton>Money</TabButton>
          </TabTrigger>
          <TabTrigger name="add" href="/add" asChild>
            <TabButton>Add</TabButton>
          </TabTrigger>
          <TabTrigger name="future" href="/future" asChild>
            <TabButton>Future</TabButton>
          </TabTrigger>
        </CustomTabList>
      </TabList>
      <TabSlot style={styles.slot} />
    </Tabs>
  );
}

// `ref` is left out: under TypeScript 6 and React Native 0.88 the slot's ref type doesn't match
// Pressable's (a mismatch in the Expo template), and the browser tab button doesn't need it.
export function TabButton({ children, isFocused, ref: _ref, ...props }: TabTriggerSlotProps) {
  return (
    <Pressable {...props} style={({ pressed }) => pressed && styles.pressed}>
      <ThemedView type={isFocused ? 'backgroundSelected' : 'backgroundElement'} style={styles.tabButtonView}>
        <ThemedText type="small" themeColor={isFocused ? 'text' : 'textSecondary'}>
          {children}
        </ThemedText>
      </ThemedView>
    </Pressable>
  );
}

export function CustomTabList(props: TabListProps) {
  return (
    <View {...props} style={styles.tabListContainer}>
      <ThemedView type="backgroundElement" style={styles.innerContainer}>
        <ThemedText type="smallBold" style={styles.brandText}>
          FAST
        </ThemedText>
        {props.children}
      </ThemedView>
    </View>
  );
}

const styles = StyleSheet.create({
  tabs: { flex: 1, overflow: 'hidden' },       // the screens scroll, never the page itself
  slot: { flex: 1, minHeight: 0 },
  tabListContainer: {
    width: '100%',
    paddingHorizontal: Spacing.two,
    paddingTop: Spacing.two,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
  },
  innerContainer: {                      // fits a 320 px phone: FAST and four tabs, nothing wider (D-152)
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.three,
    borderRadius: Spacing.five,
    flexDirection: 'row',
    alignItems: 'center',
    flexGrow: 1,
    flexShrink: 1,
    minWidth: 0,
    gap: Spacing.one,
    maxWidth: MaxContentWidth,
  },
  brandText: { marginRight: 'auto' },
  pressed: { opacity: 0.7 },
  tabButtonView: { paddingVertical: Spacing.two, paddingHorizontal: Spacing.two, borderRadius: Spacing.three },
});
