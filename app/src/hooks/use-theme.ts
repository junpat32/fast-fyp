/**
 * The current palette: light by day, dark at night (D-114). Screens take every colour from here, so
 * the switch at 19:00 and 06:00 changes the whole app at once.
 */
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

export function useTheme() {
  return Colors[useColorScheme()];
}
