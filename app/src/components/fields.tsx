import { useState } from 'react';
import { Platform, StyleSheet, TextInput, type TextStyle, View } from 'react-native';

import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** The browser's own focus ring, turned off where useOutline draws one on the box instead (web only:
 * Chrome draws an `auto` ring at any width, and React Native's types know no `none`, hence the cast). */
export const NO_OUTLINE = Platform.select({ web: { outlineStyle: 'none' } as unknown as TextStyle, default: {} });

/**
 * The outline of a box you type in (D-153): the field colour at rest (3:1 against the page, WCAG 1.4.11),
 * the accent at 2 px while typing, red on an error. The negative margin keeps the 2 px border from moving
 * anything. Spread `focus` on the TextInput; `color` is for a box drawn only as an underline.
 */
export function useOutline(error?: unknown) {
  const t = useTheme();
  const [focused, setFocused] = useState(false);
  const color = error ? t.bad : focused ? t.accent : t.field;
  return {
    color,
    box: [{ borderColor: color }, focused && !error && styles.focused],
    focus: { onFocus: () => setFocused(true), onBlur: () => setFocused(false) },
  };
}

/** An amount in ringgit, typed as text (rule 9: it stays a decimal string until the database). */
export function MoneyField({ label, value, onChange, error, hint }: {
  label: string; value: string; onChange: (v: string) => void; error?: string; hint?: string;
}) {
  const t = useTheme();
  const o = useOutline(error);
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <View style={[styles.input, { backgroundColor: t.input }, o.box]}>
        <ThemedText type="small" themeColor="textSecondary">RM</ThemedText>
        <TextInput value={value} onChangeText={onChange} keyboardType="decimal-pad" placeholder="0.00"
                   placeholderTextColor={t.textSecondary} style={[styles.inputText, { color: t.text }, NO_OUTLINE]}
                   accessibilityLabel={label} maxLength={13} {...o.focus} />
      </View>
      {error ? <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>
        : hint ? <ThemedText type="small" themeColor="textSecondary" style={styles.hint}>{hint}</ThemedText> : null}
    </View>
  );
}

/** A yearly percentage, typed as text (a debt's interest rate, D-144); empty is allowed. */
export function RateField({ label, value, onChange, error, hint }: {
  label: string; value: string; onChange: (v: string) => void; error?: string; hint?: string;
}) {
  const t = useTheme();
  const o = useOutline(error);
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <View style={[styles.input, { backgroundColor: t.input }, o.box]}>
        <TextInput value={value} onChangeText={onChange} keyboardType="decimal-pad" placeholder="not sure"
                   placeholderTextColor={t.textSecondary} style={[styles.inputText, { color: t.text }, NO_OUTLINE]}
                   accessibilityLabel={label} maxLength={7} {...o.focus} />
        <ThemedText type="small" themeColor="textSecondary">% a year</ThemedText>
      </View>
      {error ? <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>
        : hint ? <ThemedText type="small" themeColor="textSecondary" style={styles.hint}>{hint}</ThemedText> : null}
    </View>
  );
}

/** A short line of text (a debt's name, a year of birth); an error shows like MoneyField's (D-152). */
export function TextField({ label, value, onChange, placeholder, maxLength, error, keyboardType }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; maxLength: number;
  error?: string; keyboardType?: 'default' | 'number-pad' | 'decimal-pad';
}) {
  const t = useTheme();
  const o = useOutline(error);
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <TextInput value={value} onChangeText={onChange} placeholder={placeholder} placeholderTextColor={t.textSecondary}
                 maxLength={maxLength} accessibilityLabel={label} keyboardType={keyboardType} {...o.focus}
                 style={[styles.input, styles.text, { backgroundColor: t.input, color: t.text }, o.box, NO_OUTLINE]} />
      {error ? <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText> : null}
    </View>
  );
}

/** The main action of a form, or a quiet one beside it (Cancel, Paid off, Delete). `fill`: share a row. */
export function Button({ label, onPress, quiet, disabled, danger, fill }: {
  label: string; onPress: () => void; quiet?: boolean; disabled?: boolean; danger?: boolean; fill?: boolean;
}) {
  const t = useTheme();
  return (
    <Tap onPress={onPress} disabled={disabled} accessibilityRole="button" accessibilityState={{ disabled }}
         style={[styles.button, fill && styles.fill,
                 quiet ? { borderWidth: 1, borderColor: danger ? t.bad : t.line } : { backgroundColor: t.accent },
                 disabled && styles.disabled]}>
      <ThemedText type="small" style={[styles.buttonText, { color: quiet ? (danger ? t.bad : t.text) : t.onAccent }]}>{label}</ThemedText>
    </Tap>
  );
}

const styles = StyleSheet.create({
  field: { gap: Spacing.one },
  focused: { borderWidth: 2, margin: -1 },
  input: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, borderWidth: 1, borderRadius: Spacing.two,
           paddingHorizontal: Spacing.three, minHeight: 44 },
  inputText: { flex: 1, fontSize: 16, fontWeight: 600 },
  text: { fontSize: 16 },
  hint: { fontSize: 12 },
  fill: { flex: 1 },
  button: { borderRadius: Spacing.three, minHeight: 46, alignItems: 'center', justifyContent: 'center', paddingHorizontal: Spacing.three },
  buttonText: { fontWeight: 700 },
  disabled: { opacity: 0.45 },
});
