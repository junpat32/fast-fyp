import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { useTheme } from '@/hooks/use-theme';

// The four tabs of docs/app_plan.md §3 (A5), with FAST's own pixel icons (D-122, drawn in code by
// tools/asset_generation/tab_icons.py; black on clear, so "template" lets the tab bar tint them).
// SDK 57 imports native tabs from 'expo-router/unstable-native-tabs'; SDK 58 renames it
// 'expo-router/native-tabs' (D-105).
const TABS = [
  { name: 'index', label: 'Home', icon: require('@/assets/images/tabIcons/home.png') },
  { name: 'money', label: 'Money', icon: require('@/assets/images/tabIcons/money.png') },
  { name: 'add', label: 'Add', icon: require('@/assets/images/tabIcons/add.png') },
  { name: 'future', label: 'Future', icon: require('@/assets/images/tabIcons/future.png') },
] as const;

export default function AppTabs() {
  const colors = useTheme();                      // light by day, dark at night (D-114)
  return (
    <NativeTabs
      backgroundColor={colors.background}
      indicatorColor={colors.backgroundSelected}
      iconColor={{ default: colors.textSecondary, selected: colors.text }}
      labelStyle={{ default: { color: colors.textSecondary }, selected: { color: colors.text } }}>
      {TABS.map((t) => (
        <NativeTabs.Trigger key={t.name} name={t.name}>
          <NativeTabs.Trigger.Label>{t.label}</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={t.icon} renderingMode="template" />
        </NativeTabs.Trigger>
      ))}
    </NativeTabs>
  );
}
