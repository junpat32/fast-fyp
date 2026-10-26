import type { Forecast } from '@/api/types';
import { Expandable } from '@/components/expandable';
import { ThemedText } from '@/components/themed-text';
import { useTheme } from '@/hooks/use-theme';
import { outOf100 } from '@/lib/format';

import { Card } from '@/components/card';

/** Why the forecast says what it says (B5): the top reason, the others one tap away (D-108). */
export function ReasonsCard({ f }: { f: Forecast | null }) {
  const t = useTheme();
  if (!f || f.reasons.length === 0) return null;
  const raises = f.reasons[0].direction !== 'lowers';
  const mark = (
    <ThemedText type="small" style={{ color: raises ? t.bad : t.good }}>{raises ? '▲' : '▼'}</ThemedText>
  );
  const [top, ...rest] = f.reasons;
  return (
    <Card title={`Why ${outOf100(f.probability)} in 100?`}>
      <ThemedText type="smallBold">{raises ? 'What raises your risk' : 'What keeps your risk low'}</ThemedText>
      <ThemedText type="default">{mark}  {top.text}</ThemedText>
      {(rest.length > 0 || f.note) && (
        <Expandable label={rest.length ? `+${rest.length} more` : 'More'}>
          {rest.map((r) => <ThemedText key={r.feature} type="default">{mark}  {r.text}</ThemedText>)}
          {f.note && <ThemedText type="small" themeColor="textSecondary">{f.note}</ThemedText>}
        </Expandable>
      )}
    </Card>
  );
}
