import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'react-native-reanimated';

import { countAt, MOTION } from '@/lib/motion';

/**
 * A number that counts up to `to` when it first shows, and from where it was when `to` changes (another
 * persona or day) (D-154). With "Remove animations" on, it is `to` at once. The caller formats it.
 */
export function useCountUp(to: number, ms: number = MOTION.countMs): number {
  const still = useReducedMotion();
  const [shown, setShown] = useState(still ? to : 0);
  const at = useRef(still ? to : 0);
  useEffect(() => {
    if (still) { at.current = to; setShown(to); return; }
    const from = at.current;
    const start = Date.now();
    let frame = 0;
    const step = () => {
      const v = countAt(from, to, Date.now() - start, ms);
      at.current = v;
      setShown(v);
      if (v !== to) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [to, ms, still]);
  return shown;
}
