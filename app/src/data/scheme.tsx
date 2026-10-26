import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import { periodAt, type Period } from '@/lib/timeOfDay';

import { TIMES } from './art-index';

/**
 * Light by day, dark at night (D-114, Patrick): the whole app follows the Home scene's clock, the
 * art kit's own night (19:00-05:59, manifest "times"), so the screens never jar with the night art.
 * Checked once a minute.
 */
type Scheme = { period: Period; scheme: 'light' | 'dark' };

const now = (): Period => {
  const d = new Date();
  return periodAt(d.getHours(), d.getMinutes(), TIMES);
};
const SchemeContext = createContext<Scheme>({ period: 'afternoon', scheme: 'light' });

export function SchemeProvider({ children }: { children: ReactNode }) {
  const [period, setPeriod] = useState<Period>(now);
  useEffect(() => {
    const t = setInterval(() => setPeriod(now()), 60_000);
    return () => clearInterval(t);
  }, []);
  return (
    <SchemeContext.Provider value={{ period, scheme: period === 'night' ? 'dark' : 'light' }}>
      {children}
    </SchemeContext.Provider>
  );
}

export function useScheme(): Scheme {
  return useContext(SchemeContext);
}
