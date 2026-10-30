/**
 * Runtime checks on what the API sends: if the backend's shape ever changes, the app fails with a
 * clear message ("assess.forecast.reasons[0].text is missing") instead of drawing nonsense.
 * Checks the fields the screens use, not every field. Pure TypeScript, tested by Node.
 */
import type {
  AssessResponse, AssistantReply, CardResponse, FutureResponse, GameResponse, StudyResponse,
} from './types.ts';

export class ShapeError extends Error {}

type Obj = Record<string, unknown>;

function obj(v: unknown, path: string): Obj {
  if (typeof v !== 'object' || v === null || Array.isArray(v)) throw new ShapeError(`${path} should be an object`);
  return v as Obj;
}

function num(o: Obj, key: string, path: string): number {
  if (typeof o[key] !== 'number' || !Number.isFinite(o[key])) throw new ShapeError(`${path}.${key} should be a number`);
  return o[key] as number;
}

function str(o: Obj, key: string, path: string): string {
  if (typeof o[key] !== 'string') throw new ShapeError(`${path}.${key} should be text`);
  return o[key] as string;
}

function arr(o: Obj, key: string, path: string): unknown[] {
  if (!Array.isArray(o[key])) throw new ShapeError(`${path}.${key} should be a list`);
  return o[key] as unknown[];
}

const BANDS = ['GREEN', 'YELLOW', 'RED', 'INSUFFICIENT_INCOME'];

export function checkAssess(v: unknown, path = 'assess'): AssessResponse {
  const o = obj(v, path);
  for (const k of ['band', 'raw_band_this_month']) {
    if (!BANDS.includes(str(o, k, path))) throw new ShapeError(`${path}.${k} is not a band: ${String(o[k])}`);
  }
  if (typeof o.insufficient_income !== 'boolean') throw new ShapeError(`${path}.insufficient_income should be true/false`);
  for (const k of ['dsr', 'dti', 'cushion_months']) num(o, k, path);
  for (const k of ['debt_payments', 'bnpl_instalments']) if (o[k] !== undefined) num(o, k, path);   // D-152
  str(o, 'as_of', path);
  str(o, 'assessed_month', path);
  const h = obj(o.health, `${path}.health`);
  if (h.score !== null) num(h, 'score', `${path}.health`);
  obj(h.indicators, `${path}.health.indicators`);
  if (o.forecast !== null) {
    const f = obj(o.forecast, `${path}.forecast`);
    num(f, 'probability', `${path}.forecast`);
    num(f, 'base_rate', `${path}.forecast`);
    arr(f, 'reasons', `${path}.forecast`).forEach((r, i) => {
      const ro = obj(r, `${path}.forecast.reasons[${i}]`);
      str(ro, 'text', `${path}.forecast.reasons[${i}]`);
      if (!['raises', 'lowers'].includes(str(ro, 'direction', `${path}.forecast.reasons[${i}]`))) {
        throw new ShapeError(`${path}.forecast.reasons[${i}].direction should be raises or lowers`);
      }
    });
  } else if (o.forecast_note !== null && typeof o.forecast_note !== 'string') {
    throw new ShapeError(`${path}.forecast_note should be text or empty`);
  }
  arr(o, 'advice', path).forEach((a, i) => {
    const ao = obj(a, `${path}.advice[${i}]`);
    str(ao, 'rule', `${path}.advice[${i}]`);
    str(ao, 'title', `${path}.advice[${i}]`);
    str(ao, 'short', `${path}.advice[${i}]`);
    str(ao, 'text', `${path}.advice[${i}]`);
  });
  return o as unknown as AssessResponse;
}

export function checkFuture(v: unknown, path = 'future'): FutureResponse {
  const o = obj(v, path);
  if (typeof o.available !== 'boolean') throw new ShapeError(`${path}.available should be true/false`);
  str(o, 'label', path);
  if (o.available) {
    arr(o, 'months', path).forEach((m, i) => {
      const mo = obj(m, `${path}.months[${i}]`);
      for (const k of ['p10', 'p50', 'p90']) num(mo, k, `${path}.months[${i}]`);
    });
  }
  return o as unknown as FutureResponse;
}

export function checkGame(v: unknown, path = 'game'): GameResponse {
  const o = obj(v, path);
  for (const k of ['points', 'room_level', 'game_cushion']) num(o, k, path);
  obj(o.garden, `${path}.garden`);
  arr(o, 'plants', path);
  arr(o, 'ledger', path);
  return o as unknown as GameResponse;
}

const ANSWERS = ['use_savings', 'cut_spending', 'set_goal', 'not_this_week'];

export function checkCard(v: unknown, path = 'card'): CardResponse {
  const o = obj(v, path);
  for (const k of ['week', 'event_id', 'title', 'text', 'coverage_text']) str(o, k, path);
  for (const k of ['cost_low', 'cost_high', 'points']) num(o, k, path);
  if (!['covered', 'partly', 'not_yet'].includes(str(o, 'coverage', path))) throw new ShapeError(`${path}.coverage is not a coverage`);
  arr(o, 'responses', path).forEach((r, i) => {
    if (!ANSWERS.includes(str(obj(r, `${path}.responses[${i}]`), 'id', `${path}.responses[${i}]`))) {
      throw new ShapeError(`${path}.responses[${i}].id is not an answer`);
    }
  });
  if (o.answer !== null && !ANSWERS.includes(o.answer as string)) throw new ShapeError(`${path}.answer is not an answer`);
  return o as unknown as CardResponse;
}

export function checkStudy(v: unknown, path = 'study'): StudyResponse {
  const o = obj(v, path);
  if (typeof o.persona !== 'boolean') throw new ShapeError(`${path}.persona should be true/false`);
  if (o.persona) for (const k of ['study_date', 'first', 'last']) str(o, k, path);
  return o as unknown as StudyResponse;
}

const REPLY_KINDS = ['answer', 'refused_product', 'refused_scope', 'crisis', 'fallback'];

/** POST /v1/assistant (D-92): the answer, who wrote it, and what the AI was given (or null). */
export function checkAssistant(v: unknown, path = 'assistant'): AssistantReply {
  const o = obj(v, path);
  str(o, 'answer', path);
  if (!REPLY_KINDS.includes(str(o, 'kind', path))) throw new ShapeError(`${path}.kind is not a reply kind: ${String(o.kind)}`);
  if (!['model', 'fast'].includes(str(o, 'by', path))) throw new ShapeError(`${path}.by should be model or fast`);
  if (o.shared_with_assistant !== null) obj(o.shared_with_assistant, `${path}.shared_with_assistant`);
  return o as unknown as AssistantReply;
}
