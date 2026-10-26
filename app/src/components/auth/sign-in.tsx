import type { SupabaseClient } from '@supabase/supabase-js';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { authMessage, checkCredentials, MIN_PASSWORD, type AuthErrors } from '@/api/auth';
import { Button } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * Sign in (app_plan §3 "Login", D-145): email and password, "Sign in" and "Create account". Study
 * participants get accounts from the researcher (D-94) and only sign in. Creating an account sends
 * Supabase's confirmation email first (setup guide step 3: Confirm email on). The password never
 * leaves this form except to Supabase Auth (AU1). The wording is a draft for W2.
 */
export function SignIn({ client }: { client: SupabaseClient }) {
  const t = useTheme();
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<AuthErrors>({});
  const [failed, setFailed] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const e = checkCredentials(email, password, creating);
    setErrors(e);
    setFailed(null);
    if (Object.keys(e).length > 0) return;
    setBusy(true);
    const address = email.trim();
    if (creating) {
      const { data, error } = await client.auth.signUp({ email: address, password });
      if (error) setFailed(authMessage(error));
      else if (!data.session) setSent(address);                  // the session arrives after the email link
    } else {
      const { error } = await client.auth.signInWithPassword({ email: address, password });
      if (error) setFailed(authMessage(error));                  // success: the provider sees the new session
    }
    setBusy(false);
  };

  const field = (label: string, value: string, onChange: (v: string) => void, error: string | undefined, secret: boolean) => (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <TextInput value={value} onChangeText={onChange} secureTextEntry={secret} autoCapitalize="none" autoCorrect={false}
                 keyboardType={secret ? 'default' : 'email-address'} autoComplete={secret ? (creating ? 'new-password' : 'current-password') : 'email'}
                 textContentType={secret ? (creating ? 'newPassword' : 'password') : 'emailAddress'} accessibilityLabel={label}
                 style={[styles.input, { backgroundColor: t.input, borderColor: error ? t.bad : t.line, color: t.text }]} />
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.safe}>
          <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            <ThemedText type="title">FAST</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">Your money, explained. Build a cushion, grow a garden.</ThemedText>
            {sent ? (
              <View style={styles.form}>
                <ThemedText type="smallBold">Check your email</ThemedText>
                <ThemedText type="small">
                  FAST sent a link to {sent}. Open it to confirm your account, then come back and sign in.
                </ThemedText>
                <Button label="Back to sign in" fill onPress={() => { setSent(null); setCreating(false); setPassword(''); }} />
              </View>
            ) : (
              <View style={styles.form}>
                {field('Email', email, (v) => { setEmail(v); setErrors((x) => ({ ...x, email: undefined })); }, errors.email, false)}
                {field('Password', password, (v) => { setPassword(v); setErrors((x) => ({ ...x, password: undefined })); },
                       errors.password, true)}
                {creating && (
                  <ThemedText type="small" themeColor="textSecondary">
                    At least {MIN_PASSWORD} characters. FAST uses your email only to sign you in; what it keeps comes next.
                  </ThemedText>
                )}
                {failed && <ThemedText type="small" style={{ color: t.bad }}>{failed}</ThemedText>}
                <Button label={busy ? 'One moment…' : creating ? 'Create account' : 'Sign in'} fill disabled={busy} onPress={submit} />
                <Button label={creating ? 'I have an account: sign in' : 'Create an account'} quiet fill disabled={busy}
                        onPress={() => { setCreating(!creating); setErrors({}); setFailed(null); }} />
              </View>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safe: { flex: 1, maxWidth: MaxContentWidth },
  content: { flexGrow: 1, justifyContent: 'center', padding: Spacing.four, gap: Spacing.two },
  form: { gap: Spacing.three, marginTop: Spacing.four },
  field: { gap: Spacing.one },
  input: { borderWidth: 1, borderRadius: Spacing.two, paddingHorizontal: Spacing.three, minHeight: 44, fontSize: 16 },
});
