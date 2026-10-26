import { useState } from 'react';

import { Card } from '@/components/card';
import { MoneyField } from '@/components/fields';
import { ThemedText } from '@/components/themed-text';
import { comparePlans, planInputs } from '@/lib/debt-plan';
import { parseMoney, type DebtRow } from '@/lib/debts';
import { rmText } from '@/lib/entry';

const rm = (x: number) => rmText(x.toFixed(2));
const outcome = (n: number | null, interest: number) => (n === null ? 'not cleared within 30 years at these payments'
  : `debt-free in ${n} month${n === 1 ? '' : 's'}, ${rm(interest)} in interest`);

/**
 * "Which to pay off first?" (WP-14c, D-144): the same monthly budget paid out highest rate first and
 * smallest balance first, from the rates the user typed (lib/debt-plan.ts). Hidden with fewer than two
 * open debts; asks for the missing rates rather than guessing them. The wording is a draft for W2.
 */
export function DebtPlanCard({ debts, today }: { debts: DebtRow[]; today: string }) {
  const [extra, setExtra] = useState('');
  const inputs = planInputs(debts, today);
  if (!inputs.ok && inputs.reason === 'too_few') return null;
  if (!inputs.ok) {
    return (
      <Card title="Which to pay off first?">
        <ThemedText type="small" themeColor="textSecondary">
          Add the interest rate to {inputs.missing.join(', ')} to compare two ways of paying off your debts.
        </ThemedText>
      </Card>
    );
  }
  const typed = extra.trim() === '' ? { ok: true as const, value: '0.00' } : parseMoney(extra);
  const plus = typed.ok ? Number(typed.value) : 0;
  const c = comparePlans(inputs.plans, plus);
  const budget = inputs.plans.reduce((a, d) => a + d.monthly_payment, 0) + plus;
  const saving = c.snowball_interest - c.avalanche_interest;
  return (
    <Card title="Which to pay off first?">
      <MoneyField label="Extra you could pay each month" value={extra} onChange={setExtra}
                  error={typed.ok ? undefined : typed.error} />
      <ThemedText type="small">Paying {rm(budget)} a month in all:</ThemedText>
      <ThemedText type="small">
        <ThemedText type="smallBold">Highest rate first:</ThemedText> {outcome(c.avalanche_months, c.avalanche_interest)}
      </ThemedText>
      <ThemedText type="small">
        <ThemedText type="smallBold">Smallest balance first:</ThemedText> {outcome(c.snowball_months, c.snowball_interest)}
      </ThemedText>
      {c.avalanche_months !== null && c.snowball_months !== null && (
        <ThemedText type="small">
          {Math.abs(saving) < 1 ? 'Both ways cost about the same here.'
            : saving > 0 ? `Highest rate first saves about ${rm(saving)} in interest.`
              : `Smallest balance first saves about ${rm(-saving)} in interest here.`}
        </ThemedText>
      )}
      <ThemedText type="small" themeColor="textSecondary">
        An estimate from the rates you typed, with these payments kept the same. A loan quoted at a flat rate
        costs more than its rate suggests.
      </ThemedText>
    </Card>
  );
}
