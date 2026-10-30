/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import '@/global.css';

import { Platform } from 'react-native';

// FAST's palette (D-114): light by day, dark at night, chosen by the clock (data/scheme.tsx). Light
// keeps the colours the screens were designed in; dark uses warm purples to sit with the night art.
// Every screen takes its colours from here (hooks/use-theme.ts), never as literals.
export const Colors = {
  light: {
    text: '#000000',
    background: '#ffffff',
    backgroundElement: '#F0F0F3',
    backgroundSelected: '#E0E1E6',
    textSecondary: '#60646C',
    card: '#F4F2EE',              // cards and tiles
    line: '#E2DED6',              // card borders, list rules, bar tracks
    sand: '#E8DFC9',              // the sample chip and panel, portrait frames
    chip: '#F7F3EA',              // unselected chips
    segment: '#E8E4DC',           // segmented controls, the day stepper
    input: '#FFFFFF',
    field: '#8A857C',             // the outline of a box you type in: 3:1 on the page and on cards (D-153)
    accent: '#5C4079',            // links, selected chips, the Save button
    onAccent: '#FFFFFF',
    good: '#2E7D4F',
    watch: '#8A6200',             // 4.9:1 on cards as small text (was #B07D00, 3.3:1; D-153)
    bad: '#B83A32',
    reward: '#3F6E34',            // game reward lines
    barFill: '#5B7F95',           // health score parts
    rangeBar: '#B9CFA8',          // the Future chart's ranges and the cushion bar, outlined in rangeDot (D-153)
    rangeDot: '#3F6E34',
    overlay: 'rgba(250, 247, 240, 0.9)',  // pills over the Home scene
    lawn: '#8BA86A',              // behind the Home scene, if a screen is taller than 9:20
  },
  dark: {
    text: '#F3EFE7',
    background: '#15131A',
    backgroundElement: '#221F29',
    backgroundSelected: '#2E2A37',
    textSecondary: '#B7B0C2',
    card: '#221F29',
    line: '#3A3542',
    sand: '#3A3346',
    chip: '#2C2834',
    segment: '#2C2834',
    input: '#1B1921',
    field: '#79728A',
    accent: '#BBA6E6',
    onAccent: '#1A1622',
    good: '#7CC79A',
    watch: '#E3B85A',
    bad: '#F0897F',
    reward: '#93CC82',
    barFill: '#8FB3C9',
    rangeBar: '#4E6B47',
    rangeDot: '#A5D893',
    overlay: 'rgba(28, 25, 34, 0.86)',
    lawn: '#2B3D33',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;
export type Palette = { [K in ThemeColor]: string };

/** The band's colour and a readable text colour on it (contrast checked by eye against WCAG AA;
 * dark text on yellow). Used for the band chip and card accents. */
export const BandColors = {
  GREEN: { fill: '#2E7D4F', text: '#FFFFFF', tint: '#E6F2EA' },
  YELLOW: { fill: '#E6B325', text: '#3A2E00', tint: '#FBF3DC' },
  RED: { fill: '#B83A32', text: '#FFFFFF', tint: '#F8E5E3' },
  INSUFFICIENT_INCOME: { fill: '#6B717B', text: '#FFFFFF', tint: '#EEF0F2' },
} as const;

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
