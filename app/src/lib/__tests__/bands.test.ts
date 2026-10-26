import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { changeRule, dsrLine, limitsLine, noBandLine, type Thresholds } from '../bands.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
const t = JSON.parse(readFileSync(join(ROOT, 'shared', 'thresholds.json'), 'utf-8')) as Thresholds;

test('the band card reads the shared thresholds (rule 5)', () => {
  assert.equal(limitsLine(t), 'Green below 30% · Yellow 30% to below 60% · Red 60% or more');
  assert.equal(changeRule(t), 'A worse band shows at once; a better one after 2 months in a row. ' +
    'Once Red, it stays Red until debt payments are below 55%.');
  assert.equal(noBandLine(t), 'No band yet: your typical monthly income is below RM300.');
});

test('the debt share line, and none without a band', () => {
  assert.equal(dsrLine('RED', 0.5915), 'Debt payments take 59% of your income');
  assert.equal(dsrLine('INSUFFICIENT_INCOME', 9.99), null);
});

test('a changed threshold changes the words', () => {
  const changed = { ...t, dsr: { ...t.dsr, red_at_or_above: 0.65 } };
  assert.match(limitsLine(changed), /Red 65% or more/);
});
