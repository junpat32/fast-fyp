import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { factSections, isCrisis, redactQuestion, suggestions } from '../helper.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (p: string) => JSON.parse(readFileSync(p, 'utf-8'));
const fixture = read(join(HERE, 'fixtures', 'helper.json')) as { redact: [string, string][]; crisis: [string, boolean][] };
const shared = read(join(HERE, '..', '..', '..', '..', 'shared', 'helper.json'));
const aina = read(join(HERE, '..', '..', 'data', 'samples', 'persona_01.json'));

test('the phone redacts a question exactly as the server does (rule 11)', () => {
  for (const [q, want] of fixture.redact) assert.equal(redactQuestion(q), want, q);
});

test('crisis words are found as the server finds them, near misses included', () => {
  for (const [q, hit] of fixture.crisis) assert.equal(isCrisis(q, shared.crisis_words), hit, q);
  assert.match(shared.crisis_reply, /Befrienders/);
  assert.equal(shared.max_question_chars, 500);
});

test('"What the AI saw": the summary as readable lines, the user\'s results first', () => {
  const sections = factSections(aina.helper_facts);
  assert.deepEqual(sections.map((s) => s.title), ['Your results', 'How FAST works']);
  const mine = Object.fromEntries(sections[0].lines.map((l) => [l.label, l.value]));
  assert.equal(mine.Band, 'Yellow');
  assert.equal(mine['Debt payments share of income (DSR)'], '30%');
  assert.ok(Object.keys(mine).some((k) => k.startsWith('Forecast · chance band worse or money short')));
  assert.ok(Object.keys(mine).some((k) => k.startsWith('Advice 1')));
  const text = JSON.stringify(sections);
  assert.ok(!/transaction|merchant|email|@/i.test(text.replace(/scam/gi, '')));   // rule 10: none of those were sent
  assert.deepEqual(factSections(null), []);
});

test('questions to start with follow the screen: the band, the forecast, the cushion, the garden', () => {
  const label = (b: string) => b.charAt(0) + b.slice(1).toLowerCase();
  assert.deepEqual(suggestions(aina.assess, label), ['Why is my band Yellow?', 'What does "68 in 100" mean for me?',
    'How can I build my cushion?', 'How does my garden grow?']);
  assert.equal(suggestions({ band: 'INSUFFICIENT_INCOME', insufficient_income: true, forecast: null }, label)[0],
               'Why don\'t I have a band yet?');
});
