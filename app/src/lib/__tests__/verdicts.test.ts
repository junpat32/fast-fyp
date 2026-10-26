import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { cushionVerdict, forecastVerdict, type VerdictLimits } from '../verdicts.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..', '..', '..');
const t = JSON.parse(readFileSync(join(ROOT, 'shared', 'thresholds.json'), 'utf-8')) as VerdictLimits;
const SAMPLES = join(HERE, '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));

const fc = (probability: number, base_rate: number, red_note: string | null = null) => ({ probability, base_rate, red_note });

test('the forecast verdict: high at the R10 limit, otherwise against the average on screen', () => {
  assert.equal(t.advice.forecast_elevated, 0.30);
  assert.deepEqual(forecastVerdict(fc(0.30, 0.12), t), { text: 'high', tone: 'bad' });     // R10 fires at >= 0.30
  assert.deepEqual(forecastVerdict(fc(0.2999, 0.12), t), { text: 'above average', tone: 'watch' });
  assert.deepEqual(forecastVerdict(fc(0.08, 0.12), t), { text: 'below average', tone: 'good' });
  // the same rounded numbers the screen prints: 12 and 12 read as equal, so the words say so
  assert.deepEqual(forecastVerdict(fc(0.1201, 0.1189), t), { text: 'about average', tone: 'neutral' });
});

test('no comparison with the average for a user already in Red (W3), but "high" still shows', () => {
  assert.equal(forecastVerdict(fc(0.08, 0.12, 'already Red'), t), null);
  assert.deepEqual(forecastVerdict(fc(0.34, 0.12, 'already Red'), t), { text: 'high', tone: 'bad' });
});

test('the cushion verdict uses the same tests as R05 and R06', () => {
  assert.equal(cushionVerdict(0.6, t).text, 'goal: 1 month');
  assert.equal(cushionVerdict(0.999, t).text, 'goal: 1 month');   // R05 still fires: "save about RM.. more"
  assert.equal(cushionVerdict(1, t).text, '✓ first goal');
  assert.equal(cushionVerdict(2.99, t).text, '✓ first goal');
  assert.equal(cushionVerdict(3, t).text, '✓ 3-month goal');
  assert.equal(cushionVerdict(-0.4, t).text, 'goal: 1 month');
});

test('the verdicts agree with each persona\'s advice', () => {
  for (const s of samples) {
    const rules = s.assess.advice.map((a: { rule: string }) => a.rule.split('_')[0]);
    const v = cushionVerdict(s.assess.cushion_months, t).text;
    if (rules.includes('R05')) assert.equal(v, 'goal: 1 month', s.persona.name);
    if (rules.includes('R06')) assert.equal(v, '✓ first goal', s.persona.name);
    const f = s.assess.forecast;
    if (f) assert.equal(forecastVerdict(f, t)?.text === 'high', rules.includes('R10'), s.persona.name);
  }
});
