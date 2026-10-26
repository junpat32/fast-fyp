import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { ApiProvider } from '@/data/api-context';
import { SchemeProvider, useScheme } from '@/data/scheme';
import { useTheme } from '@/hooks/use-theme';

SplashScreen.preventAutoHideAsync();

// FAST's root: light by day and dark at night (D-114), gestures (the Home scene's pinch, D-114), the
// data source (sample data until Supabase exists, D-106), and a stack: the four tabs (A5) at the
// bottom, Budgets, Debts (D-121), the money helper (D-123), sign-up (D-124) and More (D-127) opening over them. Login joins the stack in steps
// 1-2, once the Supabase project exists (docs/app_plan.md §6).
export default function RootLayout() {
  useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SchemeProvider>
        <Themed />
      </SchemeProvider>
    </GestureHandlerRootView>
  );
}

function Themed() {
  const { scheme } = useScheme();
  return (
    <ThemeProvider value={scheme === 'dark' ? DarkTheme : DefaultTheme}>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <ApiProvider>
        <Screens />
      </ApiProvider>
    </ThemeProvider>
  );
}

function Screens() {
  const t = useTheme();
  const header = { headerShown: true, headerStyle: { backgroundColor: t.background }, headerTintColor: t.text,
                   headerShadowVisible: false, contentStyle: { backgroundColor: t.background } };
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="debts" options={{ ...header, title: 'Debts' }} />
      <Stack.Screen name="budgets" options={{ ...header, title: 'Budgets' }} />
      <Stack.Screen name="helper" options={{ ...header, title: 'Money helper' }} />
      <Stack.Screen name="onboarding" options={{ ...header, title: 'Set up FAST' }} />
      <Stack.Screen name="more" options={{ ...header, title: 'More' }} />
    </Stack>
  );
}
