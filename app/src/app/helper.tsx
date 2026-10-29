import { useRef, useState } from 'react';
import { ActivityIndicator, ScrollView, type ScrollViewInstance, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { Chip } from '@/components/add/choice';
import { Card } from '@/components/card';
import { Expandable } from '@/components/expandable';
import { Button } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { HELPER } from '@/data/helper';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { BAND_LABEL } from '@/lib/bands';
import { factSections, isCrisis, redactQuestion, suggestions } from '@/lib/helper';

type Reply = { answer: string; kind: string; by: 'model' | 'fast'; shared: unknown | null };
type Turn = { id: number; question: string; reply: Reply };

/** The server's refusals and limits, in words for the user (the API's own detail where it has one). */
function trouble(e: unknown): string {
  if (e instanceof ApiError && e.status === 503) {
    return 'The money helper isn\'t switched on yet: it needs FAST\'s server and its AI. Your band and advice are on the Money screen.';
  }
  if (e instanceof ApiError && e.status === 429) return 'That\'s all the questions for today. Try again tomorrow.';
  const detail = e instanceof ApiError ? e.detail : e instanceof Error ? e.message : String(e);
  return `Couldn't reach the money helper (${detail}). Try again in a moment.`;
}

/**
 * The money helper (A6, T-17, D-92, D-123): a question about the user's own results, answered by an AI
 * (Groq) on FAST's server from a summary only. Before anything leaves the phone the question is
 * redacted (rule 11) and the user sees what will be sent; crisis words get FAST's reply with helplines
 * at once, without the server. Each answer says who wrote it (the AI, its numbers checked, or FAST's own
 * fixed words) and opens "What the AI saw": the exact summary it was given (rule 10). Nothing is stored:
 * the conversation goes when the screen closes. Opened from the Home shelf and the Money screen.
 */
export default function HelperScreen() {
  const { api, sample, version } = useApi();
  const t = useTheme();
  const { data: a } = useRequest(() => api.assess(), [api, version]);
  const [text, setText] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const scroll = useRef<ScrollViewInstance>(null);
  const next = useRef(1);
  const sending = redactQuestion(text);
  const redacted = text.trim() !== '' && sending !== text.trim();

  const add = (question: string, reply: Reply) => {
    setTurns((ts) => [...ts, { id: next.current++, question, reply }]);
    setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
  };
  const ask = async () => {
    const q = redactQuestion(text);
    if (!q || busy) return;
    setText('');
    if (isCrisis(q, HELPER.crisis_words)) {                 // the helplines at once, server or not
      add(q, { answer: HELPER.crisis_reply, kind: 'crisis', by: 'fast', shared: null });
      return;
    }
    setBusy(true);
    try {
      const r = await api.assistant(q);
      add(q, { answer: r.answer, kind: r.kind, by: r.by, shared: r.shared_with_assistant });
    } catch (e) {
      add(q, { answer: trouble(e), kind: 'error', by: 'fast', shared: null });
    }
    setBusy(false);
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['bottom']}>
        <ScrollView ref={scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Card title="Ask about your own numbers">
            <ThemedText type="small">
              Your band, debts, savings, the forecast or the garden. An AI answers from a summary of your results:
              it never sees your entries, names or accounts, and it never recommends banks, cards, loans or investments.
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              AI can be wrong. FAST checks every number it gives against your results. Nothing you ask is kept.
            </ThemedText>
          </Card>

          {turns.length === 0 && (
            <View style={styles.chips}>
              {suggestions(a, (b) => BAND_LABEL[b as keyof typeof BAND_LABEL] ?? b).map((s) => (
                <Chip key={s} label={s} on={false} onPress={() => setText(s)} />
              ))}
            </View>
          )}

          {turns.map((turn) => <TurnView key={turn.id} turn={turn} sample={!!sample} />)}
          {busy && <ActivityIndicator />}

          <View style={[styles.box, { backgroundColor: t.input, borderColor: t.line }]}>
            <TextInput value={text} onChangeText={setText} placeholder="Type a question" placeholderTextColor={t.textSecondary}
                       multiline maxLength={HELPER.max_question_chars} accessibilityLabel="Your question"
                       style={[styles.input, { color: t.text }]} />
            <ThemedText type="small" themeColor="textSecondary" style={styles.count}>
              {text.length}/{HELPER.max_question_chars}
            </ThemedText>
          </View>
          {redacted && (
            <View style={[styles.sent, { borderColor: t.line }]}>
              <ThemedText type="small" themeColor="textSecondary">Sent as (FAST took out private details):</ThemedText>
              <ThemedText type="small">{sending || '(nothing left to send)'}</ThemedText>
            </View>
          )}
          <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
            Don&apos;t type names, card or IC numbers.
          </ThemedText>
          <Button label={busy ? 'Asking…' : 'Ask'} onPress={ask} disabled={busy || sending === ''} />
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

function TurnView({ turn, sample }: { turn: Turn; sample: boolean }) {
  const t = useTheme();
  const { reply } = turn;
  const sections = factSections(reply.shared);
  const who = reply.by === 'model' ? 'Money helper · AI' : 'FAST';
  return (
    <View style={styles.turn}>
      <View style={[styles.bubble, styles.mine, { backgroundColor: t.accent }]}>
        <ThemedText type="small" style={{ color: t.onAccent }}>{turn.question}</ThemedText>
      </View>
      <View style={[styles.bubble, styles.theirs, { backgroundColor: t.card },
                    reply.kind === 'crisis' && { borderWidth: 2, borderColor: t.watch }]}>
        <ThemedText type="smallBold" themeColor="textSecondary" style={styles.small}>{who}</ThemedText>
        <ThemedText type="small">{reply.answer}</ThemedText>
        {reply.by === 'model' && (
          <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
            Written by the AI. Its numbers were checked against your results.
          </ThemedText>
        )}
        {sections.length > 0 ? (
          <Expandable label={sample ? 'What the AI would see' : 'What the AI saw'} openLabel="Hide">
            {sections.map((s) => (
              <View key={s.title} style={styles.facts}>
                <ThemedText type="smallBold">{s.title}</ThemedText>
                {s.lines.map((l) => (
                  <ThemedText key={l.label} type="small" style={styles.small}>
                    <ThemedText type="small" themeColor="textSecondary" style={styles.small}>{l.label}: </ThemedText>{l.value}
                  </ThemedText>
                ))}
              </View>
            ))}
            <ThemedText type="small" themeColor="textSecondary" style={styles.small}>
              That, and your question as sent, is all the AI {sample ? 'would get' : 'got'}.
            </ThemedText>
          </Expandable>
        ) : reply.kind !== 'error' && (
          <ThemedText type="small" themeColor="textSecondary" style={styles.small}>Nothing went to the AI for this answer.</ThemedText>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  safeArea: { flex: 1, maxWidth: MaxContentWidth },
  content: { padding: Spacing.three, gap: Spacing.two + Spacing.one, paddingBottom: Spacing.five },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  turn: { gap: Spacing.two },
  bubble: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.one, maxWidth: '92%' },
  mine: { alignSelf: 'flex-end' },
  theirs: { alignSelf: 'flex-start' },
  facts: { gap: Spacing.half },
  box: { borderWidth: 1, borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.one },
  input: { minHeight: 64, fontSize: 16, textAlignVertical: 'top' },
  count: { alignSelf: 'flex-end', fontSize: 12 },
  sent: { borderWidth: 1, borderStyle: 'dashed', borderRadius: Spacing.two, padding: Spacing.two, gap: Spacing.half },
  small: { fontSize: 12 },
});
