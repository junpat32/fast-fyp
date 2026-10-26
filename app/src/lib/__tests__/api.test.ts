import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { ApiError, createApi } from '../../api/client.ts';
import {
  ShapeError, checkAssess, checkAssistant, checkCard, checkFuture, checkGame, checkStudy,
} from '../../api/validate.ts';

const SAMPLES = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'samples');
const samples = readdirSync(SAMPLES).filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(SAMPLES, f), 'utf-8')));

test('there is a sample for each of the four personas', () => {
  assert.deepEqual(samples.map((s) => s.persona.name), ['Aina', 'Jason', 'Priya', 'Daniel']);
});

for (const s of samples) {
  test(`the backend's real responses pass the app's checks: ${s.persona.name}`, () => {
    const a = checkAssess(s.assess);
    assert.equal(a.as_of, '2026-07-01');
    assert.ok(a.advice.length > 0 && a.assessed_month < a.as_of);
    checkFuture(s.future);
    checkGame(s.game);
    checkStudy(s.study);
    const card = checkCard(s.card);                       // GET /v1/card (D-117)
    assert.equal(card.week, '2026-06-29');                // the Monday of the study's start date
    assert.ok(card.answer === null || card.answer !== 'not_this_week');   // the persona's own answer that week (D-119)
    assert.ok(card.cost_low < card.cost_high && card.points === 5);
  });
}

const TRAVEL = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'travel');
const travel = readdirSync(TRAVEL).filter((f) => f.endsWith('.json')).sort()
  .map((f) => JSON.parse(readFileSync(join(TRAVEL, f), 'utf-8')) as { dates: Record<string, Record<string, unknown>> });

test('time travel has every later study date for each persona (D-119)', () => {
  assert.equal(travel.length, 4);
  for (const t of travel) {
    assert.deepEqual(Object.keys(t.dates), ['2026-08-01', '2026-09-01', '2026-10-01', '2026-11-01', '2026-12-01', '2027-01-01']);
  }
});

travel.forEach((t, i) => {
  test(`every later date passes the app's checks: ${samples[i].persona.name}`, () => {
    for (const [date, day] of Object.entries(t.dates)) {
      const a = checkAssess(day.assess);
      assert.equal(a.as_of, date);
      assert.ok(a.assessed_month < date);
      assert.equal(checkGame(day.game).as_of, date);
      checkFuture(day.future);
      assert.ok(checkCard(day.card).week <= date);
      assert.ok((day.checkins as { month: string }[]).every((c) => c.month < date));
    }
  });
});

test('the card\'s answers are the database\'s, and a wrong coverage fails loudly', () => {
  const card = samples[0].card;
  assert.deepEqual(card.responses.map((r: { id: string }) => r.id), ['use_savings', 'cut_spending', 'set_goal', 'not_this_week']);
  assert.throws(() => checkCard({ ...card, coverage: 'maybe' }), ShapeError);
  assert.throws(() => checkCard({ ...card, answer: 'spend_it' }), ShapeError);
});

test('the money helper\'s reply passes the checks; a reply of an unknown kind fails loudly (D-123)', () => {
  const reply = { answer: 'Your band is Yellow because…', kind: 'answer', by: 'model', grounded: true, as_of: '2026-07-01',
                  assessed_month: '2026-06-01', shared_with_assistant: samples[0].helper_facts };
  assert.equal(checkAssistant(reply).by, 'model');
  assert.equal(checkAssistant({ ...reply, kind: 'crisis', by: 'fast', shared_with_assistant: null }).shared_with_assistant, null);
  assert.throws(() => checkAssistant({ ...reply, kind: 'advice' }), ShapeError);
  assert.throws(() => checkAssistant({ ...reply, shared_with_assistant: 'facts' }), ShapeError);
});

test('a changed backend shape fails loudly, naming the field', () => {
  const bad = structuredClone(samples[0].assess);
  delete bad.forecast.reasons[0].text;
  assert.throws(() => checkAssess(bad), (e: unknown) => e instanceof ShapeError && /reasons\[0\]\.text/.test(e.message));
  assert.throws(() => checkAssess({ ...samples[0].assess, band: 'PURPLE' }), /not a band/);
});

function fakeFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const seen: { url: string; init: RequestInit }[] = [];
  const fn = (async (url: string, init: RequestInit) => {
    seen.push({ url, init });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
  }) as unknown as typeof fetch;
  return { fn, seen };
}

test('the client sends the token and returns a checked response', async () => {
  const { fn, seen } = fakeFetch(200, samples[2].assess);
  const api = createApi({ baseUrl: 'https://api.example/', getToken: async () => 'tok', fetchFn: fn });
  const a = await api.assess();
  assert.equal(a.band, 'RED');
  assert.equal(seen[0].url, 'https://api.example/v1/assess');
  assert.equal((seen[0].init.headers as Record<string, string>).Authorization, 'Bearer tok');
});

test('server refusals come back as ApiError with the gentle detail and Retry-After', async () => {
  const conflict = createApi({ baseUrl: 'https://x', getToken: async () => 't',
                               fetchFn: fakeFetch(409, { detail: 'no choice available yet' }).fn });
  await assert.rejects(conflict.gameAction({ kind: 'buy_tree' }),
                       (e: unknown) => e instanceof ApiError && e.status === 409 && e.detail === 'no choice available yet');
  const limited = createApi({ baseUrl: 'https://x', getToken: async () => 't',
                              fetchFn: fakeFetch(429, { detail: 'too many requests' }, { 'Retry-After': '30' }).fn });
  await assert.rejects(limited.assess(), (e: unknown) => e instanceof ApiError && e.retryAfter === 30);
});

test('no token means sign in again, without calling the server', async () => {
  const { fn, seen } = fakeFetch(200, {});
  const api = createApi({ baseUrl: 'https://x', getToken: async () => null, fetchFn: fn });
  await assert.rejects(api.study(), (e: unknown) => e instanceof ApiError && e.status === 401);
  assert.equal(seen.length, 0);
});

test('a game action is posted as the API expects it', async () => {
  const { fn, seen } = fakeFetch(200, samples[0].game);
  const api = createApi({ baseUrl: 'https://x', getToken: async () => 't', fetchFn: fn });
  await api.gameAction({ kind: 'plant', cell: [6, 8], item: 'serai' });
  assert.equal(seen[0].init.method, 'POST');
  assert.deepEqual(JSON.parse(String(seen[0].init.body)), { kind: 'plant', cell: [6, 8], item: 'serai' });
});
