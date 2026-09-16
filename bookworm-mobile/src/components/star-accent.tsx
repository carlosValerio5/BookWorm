import { StyleSheet, Text, type TextStyle } from 'react-native';

import { BookWormPalette } from '@/constants/theme';

type StarAccentProps = {
  size?: number;
  style?: TextStyle;
  dim?: boolean;
};

/** Vintage gold star — decorative only, not a control. */
export function StarAccent({ size = 14, style, dim = false }: StarAccentProps) {
  return (
    <Text
      style={[
        styles.star,
        { fontSize: size, color: dim ? BookWormPalette.goldMuted : BookWormPalette.gold },
        style,
      ]}
      accessibilityElementsHidden
      importantForAccessibility="no">
      ✦
    </Text>
  );
}

const styles = StyleSheet.create({
  star: {
    lineHeight: undefined,
  },
});
