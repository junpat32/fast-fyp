import { Pressable, StyleSheet, View } from 'react-native';

import { Check } from '@/components/add/choice';
import { Portrait } from '@/components/sprite';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { AVATARS } from '@/data/avatars';
import { CHARACTERS } from '@/data/kit';
import { useTheme } from '@/hooks/use-theme';
import { suggestedTone, TONES } from '@/lib/character';

export type CharacterChoice = { avatar: number | null; tone: number | null; glasses: boolean };

/**
 * The character picker (D-124, D-125): six characters, six skin tones (each character's own until one
 * is chosen) and glasses, the portraits in daylight so skin and clothes look as they are. Used at
 * sign-up and on the More screen (D-127).
 */
export function CharacterPicker({ value, onChange, error }: {
  value: CharacterChoice; onChange: (patch: Partial<CharacterChoice>) => void; error?: string;
}) {
  const t = useTheme();
  const shown = value.tone ?? (value.avatar ? suggestedTone(value.avatar, CHARACTERS) : null);
  return (
    <>
      <View style={styles.avatars} accessibilityRole="radiogroup">
        {AVATARS.map(({ avatar, look }) => {
          const on = value.avatar === avatar;
          return (
            <Pressable key={avatar} onPress={() => onChange({ avatar })} accessibilityRole="radio" accessibilityState={{ checked: on }}
                       accessibilityLabel={look}
                       style={[styles.avatar, { backgroundColor: t.card, borderColor: on ? t.accent : 'transparent' }]}>
              <Portrait look={{ avatar, tone: value.tone ?? suggestedTone(avatar, CHARACTERS), glasses: value.glasses }}
                        mood="calm" label={look} period="afternoon" size={88} />
            </Pressable>
          );
        })}
      </View>
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
      <View style={styles.field}>
        <ThemedText type="small">Skin tone</ThemedText>
        <View style={styles.tones} accessibilityRole="radiogroup">
          {CHARACTERS.skin_tones.map((tone, k) => {
            const on = shown === k + 1;
            return (
              <Pressable key={k} onPress={() => onChange({ tone: k + 1 })} accessibilityRole="radio" hitSlop={4}
                         accessibilityState={{ checked: on }} accessibilityLabel={`Skin tone ${k + 1} of ${TONES}`}
                         style={[styles.tone, { backgroundColor: tone.afternoon[1], borderColor: on ? t.accent : t.line }]} />
            );
          })}
        </View>
      </View>
      <Check label="Glasses" on={value.glasses} onChange={(v) => onChange({ glasses: v })} />
    </>
  );
}

const styles = StyleSheet.create({
  avatars: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between' },
  avatar: { width: '31%', alignItems: 'center', borderRadius: Spacing.three, borderWidth: 3, paddingVertical: Spacing.two },
  field: { gap: Spacing.one },
  tones: { flexDirection: 'row', gap: Spacing.two, flexWrap: 'wrap' },
  tone: { width: 40, height: 40, borderRadius: 20, borderWidth: 3 },
});
