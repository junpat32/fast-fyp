import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';

import { Card } from '@/components/card';
import { Expandable } from '@/components/expandable';
import { MoneyField as Money } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { GAME_RULES } from '@/data/game-rules';
import { useTheme } from '@/hooks/use-theme';
import {
  buildCheckin, canEditCheckin, closes, formOf, monthEnd, monthWord, myDate, nextOpens, openMonth, type CheckinErrors,
  type CheckinForm, type CheckinRow,
} from '@/lib/checkin';
import { dayShort, rmText } from '@/lib/entry';

import { Segmented } from './choice';

const blank: CheckinForm = { cash: '', epfFleksibel: '', emergency: '', others: '', epfRetirement: '', debt: '', income: '',
                             bills: null, ranShort: null };
const rm = (n: number) => rmText(n.toFixed(2));

/**
 * The monthly check-in (game_design §2, §3a; D-75, D-77; D-118): today's balances in the money
 * sections and what is owed, take-home pay, bills on time, "ran short?". It opens on the month's last
 * day for 7 days; it can be fixed for 48 hours. The game counts the money as at the month's end (the
 * database takes off what was logged after it). A check-in earns the least of the game's rewards
 * (+20); verified, saving, bills and cushion points come from the check-in and the entries together.
 */
export function CheckinPanel({ today }: { today: string }) {
  const { checkins, profile, now, version, changed } = useApi();
  const t = useTheme();
  const [rows, setRows] = useState<CheckinRow[] | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<CheckinForm>(blank);
  const [errors, setErrors] = useState<CheckinErrors>({});
  const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    checkins.list().then((r) => alive && setRows(r));
    return () => { alive = false; };
  }, [checkins, version]);
  if (!rows || !profile) return <ActivityIndicator />;

  const month = openMonth(today, myDate(profile.created_at));
  const existing = month ? rows.find((r) => r.month === month) : undefined;
  const before = rows.filter((r) => !month || r.month < month).at(-1);         // last month's, for hints
  const set = (patch: Partial<CheckinForm>) => {
    setForm((f) => ({ ...f, ...patch }));
    setErrors((e) => {
      const next = { ...e };
      for (const k of Object.keys(patch)) delete next[k as keyof CheckinForm];
      return next;
    });
  };
  const save = async () => {
    const r = buildCheckin(form, month!);
    if (!r.ok) { setErrors(r.errors); return; }
    await checkins.save(r.row);
    setSaved(existing ? `Fixed: ${monthWord(month!)}` : `Checked in for ${monthWord(month!)}`);
    setEditing(false);
    changed();
  };

  if (saved) {
    return (
      <Card title="Monthly check-in">
        <Animated.View entering={ZoomIn.springify()} style={styles.done}>
          <ThemedText type="subtitle" style={{ color: t.good }}>✓</ThemedText>
          <ThemedText type="smallBold">{saved}</ThemedText>
          {!saved.startsWith('Fixed') && (
            <ThemedText type="smallBold" style={{ color: t.reward }}>+{GAME_RULES.points.checkin} points for checking in</ThemedText>
          )}
        </Animated.View>
        <ThemedText type="small">
          The game counts your money as at the end of {monthWord(month!)}. Verified, saving, bills and cushion points come from
          this check-in and your entries together.
        </ThemedText>
        {checkins.local && (
          <ThemedText type="small" themeColor="textSecondary">Sample data: saved on this phone for now; the points come once you sign in.</ThemedText>
        )}
        <Pressable onPress={() => setSaved(null)} accessibilityRole="button" hitSlop={8}>
          <ThemedText type="small" style={[styles.link, { color: t.accent }]}>See the month</ThemedText>
        </Pressable>
      </Card>
    );
  }

  if (!month) {
    return (
      <Card title="Monthly check-in">
        <ThemedText type="default">Your next check-in opens on {dayShort(nextOpens(today))}.</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">It opens on the month's last day and stays open for 7 days. About 3 minutes.</ThemedText>
        {before && <MonthSummary row={before} />}
      </Card>
    );
  }

  if (existing && !editing) {
    const open = canEditCheckin(existing.created_at, now());
    return (
      <Card title={`Checked in for ${monthWord(month)} ✓`}>
        <MonthSummary row={existing} />
        {open ? (
          <Pressable onPress={() => { setForm(formOf(existing)); setErrors({}); setEditing(true); }}
                     accessibilityRole="button" style={[styles.quiet, { borderColor: t.accent }]}>
            <ThemedText type="small" style={[styles.link, { color: t.accent }]}>Fix something (you can for 48 hours)</ThemedText>
          </Pressable>
        ) : (
          <ThemedText type="small" themeColor="textSecondary">Locked: a check-in can be fixed for 48 hours.</ThemedText>
        )}
        <ThemedText type="small" themeColor="textSecondary">The next one opens on {dayShort(nextOpens(today))}.</ThemedText>
      </Card>
    );
  }

  const hint = (n: number | null | undefined) => (n === null || n === undefined ? undefined : `Last month: ${rm(n)}`);
  return (
    <Card title={`${existing ? 'Fix the' : ''} ${monthWord(month)} check-in`.trim()}>
      <ThemedText type="small" themeColor="textSecondary">
        Open until {dayShort(closes(month))} · about 3 minutes{existing ? '' : ` · +${GAME_RULES.points.checkin} points`}
      </ThemedText>
      <ThemedText type="smallBold">Money you have today</ThemedText>
      <Money label="Cash, bank and e-wallets" value={form.cash} onChange={(v) => set({ cash: v })} error={errors.cash}
             hint={hint(before?.cash_bank_ewallet)} />
      <Expandable label="More places your money is">
        <Money label="EPF Account Fleksibel (counts as cushion)" value={form.epfFleksibel} onChange={(v) => set({ epfFleksibel: v })}
               error={errors.epfFleksibel} hint={hint(before?.epf_fleksibel)} />
        <Money label="Emergency savings kept elsewhere (counts as cushion)" value={form.emergency}
               onChange={(v) => set({ emergency: v })} error={errors.emergency} hint={hint(before?.others_emergency)} />
        <Money label="Other savings, e.g. ASB (not for emergencies)" value={form.others} onChange={(v) => set({ others: v })}
               error={errors.others} hint={hint(before?.others)} />
        <Money label="EPF retirement, Persaraan + Sejahtera (shown only)" value={form.epfRetirement}
               onChange={(v) => set({ epfRetirement: v })} error={errors.epfRetirement} hint={hint(before?.epf_retirement)} />
      </Expandable>
      <ThemedText type="smallBold">What you owe today</ThemedText>
      <Money label="All your debts together" value={form.debt} onChange={(v) => set({ debt: v })} error={errors.debt}
             hint={hint(before?.debt_total)} />
      <ThemedText type="smallBold">{monthWord(month)}</ThemedText>
      <Money label={`Take-home pay for ${monthWord(month)} (optional)`} value={form.income} onChange={(v) => set({ income: v })}
             error={errors.income} hint={`You said about ${rm(profile.declared_income)} a month`} />
      <YesNo label="Were your bills paid on time?" value={form.bills} onChange={(v) => set({ bills: v })} error={errors.bills} />
      <YesNo label="Did you run short (out of cash, or a payment missed)?" value={form.ranShort}
             onChange={(v) => set({ ranShort: v })} error={errors.ranShort} />
      <Pressable onPress={save} accessibilityRole="button" style={[styles.save, { backgroundColor: t.accent }]}>
        <ThemedText type="default" style={[styles.saveText, { color: t.onAccent }]}>
          {existing ? 'Save the fix' : `Check in for ${monthWord(month)}`}
        </ThemedText>
      </Pressable>
      {existing && (
        <Pressable onPress={() => setEditing(false)} accessibilityRole="button" hitSlop={8}>
          <ThemedText type="small" style={[styles.link, styles.center, { color: t.accent }]}>Cancel</ThemedText>
        </Pressable>
      )}
    </Card>
  );
}

/** A check-in as the game counts it: the money at the month's end (D-77). */
function MonthSummary({ row }: { row: CheckinRow }) {
  const t = useTheme();
  const end = monthEnd(row);
  return (
    <View style={styles.summary}>
      <ThemedText type="small" themeColor="textSecondary">At the end of {monthWord(row.month)}</ThemedText>
      <View style={styles.pair}>
        <ThemedText type="small">Money that counts as cushion</ThemedText>
        <ThemedText type="smallBold">{rm(end.counted)}</ThemedText>
      </View>
      <View style={styles.pair}>
        <ThemedText type="small">What you owed</ThemedText>
        <ThemedText type="smallBold">{rm(end.owed)}</ThemedText>
      </View>
      <View style={styles.pair}>
        <ThemedText type="small">Bills on time</ThemedText>
        <ThemedText type="smallBold" style={{ color: row.bills_paid_on_time ? t.good : t.watch }}>
          {row.bills_paid_on_time ? 'Yes' : 'No'}
        </ThemedText>
      </View>
      {row.after_month_net !== 0 && (
        <ThemedText type="small" themeColor="textSecondary">
          Today's balance minus {rm(row.after_month_net)} that came in after the month ended.
        </ThemedText>
      )}
    </View>
  );
}

function YesNo({ label, value, onChange, error }: {
  label: string; value: boolean | null; onChange: (v: boolean) => void; error?: string;
}) {
  const t = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="small">{label}</ThemedText>
      <Segmented<'yes' | 'no' | ''> label={label} value={value === null ? '' : value ? 'yes' : 'no'}
                                     onChange={(v) => onChange(v === 'yes')}
                                     options={[{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }]} />
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: Spacing.one },
  save: { borderRadius: Spacing.three, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  saveText: { fontWeight: 700 },
  quiet: { borderWidth: 1, borderRadius: Spacing.three, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  link: { fontWeight: 600 },
  center: { textAlign: 'center' },
  done: { alignItems: 'center', gap: Spacing.one },
  summary: { gap: Spacing.one },
  pair: { flexDirection: 'row', justifyContent: 'space-between' },
});
