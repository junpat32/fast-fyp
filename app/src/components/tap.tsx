import { Pressable, StyleSheet, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { MOTION } from '@/lib/motion';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * Everything tappable in FAST (D-154): a Pressable that dims while a finger is on it and fades back
 * after, so a tap shows at once even when the answer takes a moment (the free API can take a minute to
 * wake). A disabled one doesn't react. Its own opacity (a disabled Button's) is kept and multiplied.
 */
export function Tap({ style, onPressIn, onPressOut, ...rest }: Omit<PressableProps, 'style'> & { style?: StyleProp<ViewStyle> }) {
  const dim = useSharedValue(1);
  const base = StyleSheet.flatten(style)?.opacity ?? 1;
  const faded = useAnimatedStyle(() => ({ opacity: Number(base) * dim.value }));
  return (
    <AnimatedPressable {...rest} style={[style, faded]}
                       onPressIn={(e) => { dim.value = withTiming(MOTION.pressedOpacity, { duration: MOTION.pressMs }); onPressIn?.(e); }}
                       onPressOut={(e) => { dim.value = withTiming(1, { duration: MOTION.releaseMs }); onPressOut?.(e); }} />
  );
}
