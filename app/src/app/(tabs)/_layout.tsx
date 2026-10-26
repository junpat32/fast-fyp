import AppTabs from '@/components/app-tabs';

// The four tabs (A5) as one route group inside the root stack, so screens like Budgets and Debts
// (D-121), and later login and onboarding, open over them with a back button.
export default function TabsLayout() {
  return <AppTabs />;
}
