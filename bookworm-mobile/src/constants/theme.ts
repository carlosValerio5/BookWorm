/**
 * BookWorm mobile — warm dark + vintage gold accents.
 */

import '@/global.css';

import { Platform } from 'react-native';

export const BookWormPalette = {
  ground: '#14120b',
  surface1: '#1b1913',
  surface2: '#201e18',
  text: '#edecec',
  text2: 'rgba(237, 236, 236, 0.6)',
  text3: 'rgba(237, 236, 236, 0.5)',
  line1: 'rgba(237, 236, 236, 0.025)',
  line2: 'rgba(237, 236, 236, 0.1)',
  line3: 'rgba(237, 236, 236, 0.2)',
  /** Live capture dot, star accents, badge borders — vintage gold, not orange. */
  gold: '#f2cc8f',
  goldBright: '#ffdd9a',
  goldMuted: 'rgba(242, 204, 143, 0.55)',
  goldLine: 'rgba(242, 204, 143, 0.35)',
  goldDeep: '#9a7b3c',
  accent: '#f54e00',
  good: '#1f8a65',
  bad: '#cf2d56',
  typeBook: '#9fc9a2',
  typeBarcode: '#e59a7c',
  typeTitle: '#9fbbe0',
} as const;

const spinePalette = [
  BookWormPalette.gold,
  BookWormPalette.goldDeep,
  BookWormPalette.typeTitle,
  BookWormPalette.typeBook,
  BookWormPalette.typeBarcode,
] as const;

export function spineColorForIsbn(isbn: string): string {
  let hash = 0;
  for (let i = 0; i < isbn.length; i += 1) {
    hash = (hash + isbn.charCodeAt(i)) % spinePalette.length;
  }
  return spinePalette[hash] ?? BookWormPalette.gold;
}

export const Colors = {
  dark: {
    text: BookWormPalette.text,
    textSecondary: BookWormPalette.text2,
    textTertiary: BookWormPalette.text3,
    background: BookWormPalette.ground,
    backgroundElement: BookWormPalette.surface1,
    backgroundSelected: BookWormPalette.surface2,
    border: BookWormPalette.line2,
    borderStrong: BookWormPalette.line3,
    gold: BookWormPalette.gold,
    goldLine: BookWormPalette.goldLine,
    accent: BookWormPalette.gold,
    good: BookWormPalette.good,
    bad: BookWormPalette.bad,
    primaryButtonFill: BookWormPalette.text,
    primaryButtonText: BookWormPalette.ground,
  },
  light: {
    text: '#14120b',
    textSecondary: 'rgba(20, 18, 11, 0.65)',
    textTertiary: 'rgba(20, 18, 11, 0.5)',
    background: '#f5f3ee',
    backgroundElement: '#ffffff',
    backgroundSelected: '#ebe8e0',
    border: 'rgba(20, 18, 11, 0.12)',
    borderStrong: 'rgba(20, 18, 11, 0.2)',
    gold: BookWormPalette.goldDeep,
    goldLine: 'rgba(154, 123, 60, 0.35)',
    accent: BookWormPalette.goldDeep,
    good: BookWormPalette.good,
    bad: BookWormPalette.bad,
    primaryButtonFill: '#14120b',
    primaryButtonText: '#edecec',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export function useBookWormColors() {
  return Colors.dark;
}

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
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
  hair: 2,
  xs: 4,
  sm: 6,
  md: 8,
  lg: 10,
  pane: 14,
  group: 20,
  screen: 24,
} as const;

export const Radius = {
  row: 8,
  sheet: 12,
  frame: 16,
  pill: 999,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
