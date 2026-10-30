import { useEffect, useState, type ReactNode } from 'react';
import { StyleSheet, View, type DimensionValue, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';

import { useCountUp } from '@/hooks/use-count-up';
import { MOTION } from '@/lib/motion';

// The screens' motion (D-154; timings in lib/motion.ts). Reanimated's timings follow the phone's
// "Remove animations" setting by themselves: with it on, everything is at its end at once.
const OUT = Easing.out(Easing.cubic);

/**
 * Details that open and close by sliding: the height follows the content, so whatever is below moves
 * down smoothly instead of jumping, also when the content changes while open. Closed, the children are
 * not mounted (a screen reader skips them, as before); they stay mounted only while closing.
 */
export function Reveal({ open, children, style }: { open: boolean; children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const [mounted, setMounted] = useState(open);
  const height = useSharedValue(0);                // the content's height, as last measured
  const shown = useSharedValue(open ? 1 : 0);
  useEffect(() => {
    if (open) setMounted(true);
    shown.value = withTiming(open ? 1 : 0, { duration: MOTION.revealMs, easing: OUT });
    if (open) return;
    const gone = setTimeout(() => setMounted(false), MOTION.revealMs);
    return () => clearTimeout(gone);
  }, [open, shown]);
  const clip = useAnimatedStyle(() => ({ height: height.value * shown.value, opacity: shown.value }));
  if (!mounted) return null;
  return (
    <Animated.View style={[styles.clip, clip]}>
      <View style={[styles.content, style]} onLayout={(e) => {
        const h = e.nativeEvent.layout.height;
        height.value = height.value === 0 ? h : withTiming(h, { duration: MOTION.revealMs, easing: OUT });
      }}>
        {children}
      </View>
    </Animated.View>
  );
}

/** A value growing from 0 to `to` when it first shows, and on to a new `to` when that changes. */
function useGrown(to: number, delay: number) {
  const v = useSharedValue(0);
  useEffect(() => {
    v.value = withDelay(delay, withTiming(to, { duration: MOTION.growMs, easing: OUT }));
  }, [to, delay, v]);
  return v;
}

/** A bar growing to `share` (0-1) of its track's width. */
export function GrowBar({ share, delay = 0, style }: { share: number; delay?: number; style?: StyleProp<ViewStyle> }) {
  const v = useGrown(Math.min(Math.max(share, 0), 1), delay);
  const width = useAnimatedStyle(() => ({ width: `${v.value * 100}%` as DimensionValue }));
  return <Animated.View style={[style, width]} />;
}

/** A column growing up from its foot to `height` dp (place it with `bottom`). */
export function GrowColumn({ height, delay = 0, style }: { height: number; delay?: number; style?: StyleProp<ViewStyle> }) {
  const v = useGrown(height, delay);
  const tall = useAnimatedStyle(() => ({ height: v.value }));
  return <Animated.View style={[style, tall]} />;
}

/** A number inside a text that counts up to `to`, written by `text` (e.g. one decimal). */
export function Counted({ to, text }: { to: number; text: (n: number) => string }) {
  return <>{text(useCountUp(to))}</>;
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden' },
  content: { position: 'absolute', top: 0, left: 0, right: 0 },
});
