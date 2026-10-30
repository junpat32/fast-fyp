import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import type { AssessResponse } from '@/api/types';
import { Counted, Reveal } from '@/components/motion';
import { Tap } from '@/components/tap';
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
  const [panel, setPanel] = useState<Panel>(null);  // kept while the panel slides shut (D-154)
  const band = BandColors[a.band];
  const toggle = (p: Panel) => {
    const next = open === p ? null : p;
    setOpen(next);
    if (next) setPanel(next);
  };
  const f = a.forecast;
  const t = useTheme();
  return (
    <View>
      <View style={styles.wrap}>
        <Tile wide label="Band" value={a.band === 'INSUFFICIENT_INCOME' ? 'No band' : BAND_LABEL[a.band]}
              sub={a.band === 'INSUFFICIENT_INCOME' ? 'not enough income data' : `${Math.round(a.dsr * 100)}% of income to debts`}
              fill={band.fill} ink={band.text} onInfo={() => toggle('band')} active={open === 'band'} />
        <View style={styles.row}>
          <Tile label="Next 3 months" value={f ? String(outOf100(f.probability)) : '–'} unit={f ? 'in 100' : undefined}
                count={f ? { to: outOf100(f.probability), text: (n) => String(Math.round(n)) } : undefined}
                sub={!f ? 'no forecast yet' : f.red_note ? 'people like you run short' : 'people like you hit money trouble'}
                verdict={f ? forecastVerdict(f, THRESHOLDS) : null}
                onInfo={() => toggle('forecast')} active={open === 'forecast'} />
          <Tile label="Cushion" value={monthsText(a.cushion_months)} count={{ to: Math.max(a.cushion_months, 0), text: monthsText }}
                sub="months of costs saved" verdict={cushionVerdict(a.cushion_months, THRESHOLDS)}
                onInfo={() => toggle('cushion')} active={open === 'cushion'} />
        </View>
      </View>
      <Reveal open={open !== null} style={styles.panelSpace}>
        <View style={[styles.panel, { backgroundColor: t.card }]}>
          {panel === 'band' && <BandInfo a={a} />}
          {panel === 'forecast' && <ForecastInfo a={a} />}
          {panel === 'cushion' && <CushionInfo months={a.cushion_months} />}
        </View>
      </Reveal>
    </View>
  );
}


/** One tile. `count`: its number counts up to the value when it shows (D-154); screen readers hear the value. */
function Tile({ label, value, count, unit, sub, verdict, fill, ink, onInfo, active, wide = false }: {
  label: string; value: string; count?: { to: number; text: (n: number) => string }; unit?: string; sub: string;
  verdict?: Verdict | null; fill?: string; ink?: string; onInfo: () => void; active: boolean; wide?: boolean;
}) {
  const t = useTheme();
  const color = ink ? { color: ink } : undefined;
  const tone = verdict && verdict.tone !== 'neutral' ? t[verdict.tone] : undefined;   // the health tiers' colours
  return (
    <Tap onPress={onInfo} style={[styles.tile, !wide && styles.tileHalf, { backgroundColor: fill ?? t.card },
                                  active && [styles.tileActive, { borderColor: t.accent }]]}
         accessibilityRole="button"
         accessibilityLabel={`${label}: ${value}${unit ? ` ${unit}` : ''}, ${sub}${verdict ? `, ${verdict.text}` : ''}. Tap to explain.`}>
      <View style={styles.tileTop}>
        <ThemedText type="small" style={[styles.tileLabel, color]}>{label}</ThemedText>
        <ThemedText type="small" style={[styles.info, color]}>ⓘ</ThemedText>
      </View>
      <View style={wide ? styles.wideBody : undefined}>
        <ThemedText style={[styles.value, color]} numberOfLines={1}>
          {count ? <Counted to={count.to} text={count.text} /> : value}
          {unit ? <ThemedText style={[styles.unit, color]}> {unit}</ThemedText> : null}
        </ThemedText>
        <ThemedText type="small" style={[styles.sub, color, wide && styles.wideSub]}>{sub}</ThemedText>
      </View>
      {verdict && (
        <ThemedText type="small" themeColor={tone ? undefined : 'textSecondary'}
                    style={[styles.verdict, tone ? { color: tone } : null]}>{verdict.text}</ThemedText>
      )}
    </Tap>
  );
}

function BandInfo({ a }: { a: AssessResponse }) {
  const router = useRouter();
  const t = useTheme();
  const debts = (
    <Tap onPress={() => router.navigate('/debts')} accessibilityRole="link" hitSlop={8}>
      <ThemedText type="small" style={{ color: t.accent, fontWeight: 700 }}>See your debts ›</ThemedText>
    </Tap>
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
  panelSpace: { paddingTop: Spacing.two },          // the gap above the panel slides with it
});
