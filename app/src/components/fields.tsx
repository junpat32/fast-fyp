import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** An amount in ringgit, typed as text (rule 9: it stays a decimal string until the database). */
export function MoneyField({ label, value, onChange, error, hint }: {
  label: string; value: string; onChange: (v: string) => void; error?: string; hint?: string;
}) {
  const t = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <View style={[styles.input, { backgroundColor: t.input, borderColor: error ? t.bad : t.line }]}>
        <ThemedText type="small" themeColor="textSecondary">RM</ThemedText>
        <TextInput value={value} onChangeText={onChange} keyboardType="decimal-pad" placeholder="0.00"
                   placeholderTextColor={t.textSecondary} style={[styles.inputText, { color: t.text }]}
                   accessibilityLabel={label} maxLength={13} />
      </View>
      {error ? <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>
        : hint ? <ThemedText type="small" themeColor="textSecondary" style={styles.hint}>{hint}</ThemedText> : null}
    </View>
  );
}

/** A short line of text (a debt's name). */
export function TextField({ label, value, onChange, placeholder, maxLength }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; maxLength: number;
}) {
  const t = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <TextInput value={value} onChangeText={onChange} placeholder={placeholder} placeholderTextColor={t.textSecondary}
                 maxLength={maxLength} accessibilityLabel={label}
                 style={[styles.input, styles.text, { backgroundColor: t.input, borderColor: t.line, color: t.text }]} />
    </View>
  );
}

/** The main action of a form, or a quiet one beside it (Cancel, Paid off, Delete). `fill`: share a row. */
export function Button({ label, onPress, quiet, disabled, danger, fill }: {
  label: string; onPress: () => void; quiet?: boolean; disabled?: boolean; danger?: boolean; fill?: boolean;
}) {
  const t = useTheme();
  return (
    <Pressable onPress={onPress} disabled={disabled} accessibilityRole="button" accessibilityState={{ disabled }}
               style={[styles.button, fill && styles.fill,
                       quiet ? { borderWidth: 1, borderColor: danger ? t.bad : t.line } : { backgroundColor: t.accent },
                       disabled && styles.disabled]}>
      <ThemedText type="small" style={[styles.buttonText, { color: quiet ? (danger ? t.bad : t.text) : t.onAccent }]}>{label}</ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  field: { gap: Spacing.one },
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
