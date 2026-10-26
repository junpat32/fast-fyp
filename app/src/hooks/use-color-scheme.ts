// FAST's colour scheme follows the clock, not the phone's setting: dark at night (data/scheme.tsx, D-114).
import { useScheme } from '@/data/scheme';

export function useColorScheme(): 'light' | 'dark' {
  return useScheme().scheme;
}
