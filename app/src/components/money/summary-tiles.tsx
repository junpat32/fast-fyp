import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import type { AssessResponse } from '@/api/types';
import { ThemedText } from '@/components/themed-text';
import { BandColors, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { THRESHOLDS } from '@/data/thresholds';
import { BAND_LABEL, changeRule, limitsLine, noBandLine } from '@/lib/bands';
import { monthsText, outOf100 } from '@/lib/format';
import { cushionVerdict, forecastVerdict, type Verdict } from '@/lib/verdicts';

type Panel = 'band' | 'forecast' | 'cushion' | null;

/**
 * The Money screen's first glance (D-108): band (B1, B2), the forecast (B4) and the cushion (B7) as
 * three tiles; each ⓘ opens the explanation below them (B3 and the rest), one at a time. The band's
 * colour is its verdict; the other two get a few words from lib/verdicts.ts (D-109). The band takes a
 * full-width row and the other two share the next (D-152), so no number breaks across lines on a 360 dp
 * phone; the forecast's "in 100" sits small beside its number.
 */
export function SummaryTiles({ a }: { a: AssessResponse }) {
  const [open, setOpen] = useState<Panel>(null);
  const band = BandColors[a.band];
  const toggle = (p: Panel) => setOpen(open === p ? null : p);
  const f = a.forecast;
  const t = useTheme();
  return (
    <View style={styles.wrap}>
      <Tile wide label="Band" value={a.band === 'INSUFFICIENT_INCOME' ? 'No band' : BAND_LABEL[a.band]}
            sub={a.band === 'INSUFFICIENT_INCOME' ? 'not enough income data' : `${Math.round(a.dsr * 100)}% of income to debts`}
            fill={band.fill} ink={band.text} onInfo={() => toggle('band')} active={open === 'band'} />
      <View style={styles.row}>
        <Tile label="Next 3 months" value={f ? String(outOf100(f.probability)) : '–'} unit={f ? 'in 100' : undefined}
              sub={!f ? 'no forecast yet' : f.red_note ? 'people like you run short' : 'people like you hit money trouble'}
              verdict={f ? forecastVerdict(f, THRESHOLDS) : null}
              onInfo={() => toggle('forecast')} active={open === 'forecast'} />
        <Tile label="Cushion" value={monthsText(a.cushion_months)} sub="months of costs saved"
              verdict={cushionVerdict(a.cushion_months, THRESHOLDS)}
              onInfo={() => toggle('cushion')} active={open === 'cushion'} />
      </View>
      {open && (
        <View style={[styles.panel, { backgroundColor: t.card }]}>
          {open === 'band' && <BandInfo a={a} />}
          {open === 'forecast' && <ForecastInfo a={a} />}
          {open === 'cushion' && <CushionInfo months={a.cushion_months} />}
        </View>
      )}
    </View>
  );
}


function Tile({ label, value, unit, sub, verdict, fill, ink, onInfo, active, wide = false }: {
  label: string; value: string; unit?: string; sub: string; verdict?: Verdict | null; fill?: string; ink?: string;
  onInfo: () => void; active: boolean; wide?: boolean;
}) {
  const t = useTheme();
  const color = ink ? { color: ink } : undefined;
  const tone = verdict && verdict.tone !== 'neutral' ? t[verdict.tone] : undefined;   // the health tiers' colours
  return (
    <Pressable onPress={onInfo} style={[styles.tile, !wide && styles.tileHalf, { backgroundColor: fill ?? t.card },
                                        active && [styles.tileActive, { borderColor: t.accent }]]}
               accessibilityRole="button"
               accessibilityLabel={`${label}: ${value}${unit ? ` ${unit}` : ''}, ${sub}${verdict ? `, ${verdict.text}` : ''}. Tap to explain.`}>
      <View style={styles.tileTop}>
        <ThemedText type="small" style={[styles.tileLabel, color]}>{label}</ThemedText>
        <ThemedText type="small" style={[styles.info, color]}>ⓘ</ThemedText>
      </View>
      <View style={wide ? styles.wideBody : undefined}>
        <ThemedText style={[styles.value, color]} numberOfLines={1}>
          {value}{unit ? <ThemedText style={[styles.unit, color]}> {unit}</ThemedText> : null}
        </ThemedText>
        <ThemedText type="small" style={[styles.sub, color, wide && styles.wideSub]}>{sub}</ThemedText>
      </View>
      {verdict && (
        <ThemedText type="small" themeColor={tone ? undefined : 'textSecondary'}
                    style={[styles.verdict, tone ? { color: tone } : null]}>{verdict.text}</ThemedText>
      )}
    </Pressable>
  );
}

function BandInfo({ a }: { a: AssessResponse }) {
  const router = useRouter();
  const t = useTheme();
  const debts = (
    <Pressable onPress={() => router.navigate('/debts')} accessibilityRole="link" hitSlop={8}>
      <ThemedText type="small" style={{ color: t.accent, fontWeight: 700 }}>See your debts ›</ThemedText>
    </Pressable>
  );
  if (a.band === 'INSUFFICIENT_INCOME') return <><ThemedText type="small">{noBandLine(THRESHOLDS)}</ThemedText>{debts}</>;
  const waiting = a.raw_band_this_month !== a.band && a.raw_band_this_month !== 'INSUFFICIENT_INCOME';
  return (
    <>
      <ThemedText type="small">Your debt payments take {Math.round(a.dsr * 100)}% of your income each month.</ThemedText>
      {debts}
      {waiting && (
        <ThemedText type="small">
          This month on its own is {BAND_LABEL[a.raw_band_this_month]}: it shows once it holds for{' '}
          {THRESHOLDS.improvement_confirm_months} months in a row.
        </ThemedText>
      )}
      <ThemedText type="small" themeColor="textSecondary">{limitsLine(THRESHOLDS)}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">{changeRule(THRESHOLDS)}</ThemedText>
    </>
  );
}

function ForecastInfo({ a }: { a: AssessResponse }) {
  const f = a.forecast;
  if (!f) return <ThemedText type="small">{a.forecast_note ?? 'No forecast yet: it needs 3 months of records.'}</ThemedText>;
  return (
    <>
      <ThemedText type="small">
        About {outOf100(f.probability)} out of 100 people like you get into money trouble in the next 3 months:
        a worse band or running short.
      </ThemedText>
      {f.red_note && <ThemedText type="small">{f.red_note}</ThemedText>}
      <ThemedText type="small" themeColor="textSecondary">
        {/* in Red the forecast counts running short only, so the overall average isn't like for like (D-109) */}
        {f.red_note ? '' : `On average it's about ${outOf100(f.base_rate)} out of 100. `}
        An estimate from patterns like yours, not a certainty.
      </ThemedText>
    </>
  );
}

function CushionInfo({ months }: { months: number }) {
  const { cushion_first_goal_months: first, cushion_next_goal_months: next } = THRESHOLDS.advice;
  return (
    <>
      <ThemedText type="small">
        Your money covers about {monthsText(months)} months of essential costs and debt payments.
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">First goal: {first} month · next goal: {next} months.</ThemedText>
    </>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  tile: { borderRadius: Spacing.three, padding: Spacing.two + Spacing.one, gap: Spacing.half },
  tileHalf: { flex: 1, minHeight: 118 },     // the row's two tiles share its width, as tall as each other
  wideBody: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', gap: Spacing.three },
  wideSub: { flexShrink: 1, textAlign: 'right' },
  tileActive: { borderWidth: 2 },
  tileTop: { flexDirection: 'row', justifyContent: 'space-between' },
  tileLabel: { fontSize: 12, fontWeight: 600 },
  info: { fontSize: 13 },
  value: { fontSize: 26, lineHeight: 32, fontWeight: 700 },   // "68 in 100" fits half of a 320 dp phone
  unit: { fontSize: 14, fontWeight: 600 },
  sub: { fontSize: 12, lineHeight: 16 },
  verdict: { fontSize: 13, lineHeight: 17, fontWeight: 700, marginTop: 'auto' },   // sits at the tile's foot
  panel: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.two },
});
