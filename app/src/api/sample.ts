/**
 * "Sample data" mode (D-106): the same FastApi as client.ts, answering with real backend responses
 * for the four study personas (app/src/data/samples: the start date; app/src/data/travel: every later
 * study date; both from tools/app_fixtures.py). Used until Supabase and the deployed API exist; every
 * screen shows a "Sample data" label meanwhile.
 *
 * Time travel works here (D-119): each persona keeps its own study date for the session, and every
 * answer is that date's backend response. What the session did on the phone follows the clock as the
 * server would: game actions (plants D-115, the Home extras D-120) are dated and replayed on later
 * dates by the engine's rules, skipping any that no longer fit (the replay's strict=False); card
 * answers are per week (D-117). Approximations, since nothing is saved: a plant or tree put in here
 * doesn't grow while time passes, and the persona's own garden plan can take a spot first. The card's
 * points need the server's replay, so the game's points don't change here. The money helper can't
 * reach the AI: it says so, and shows the summary the AI would be given that day (D-123).
 */
import aina from '../data/samples/persona_01.json';
import jason from '../data/samples/persona_02.json';
import priya from '../data/samples/persona_03.json';
import daniel from '../data/samples/persona_04.json';
import ainaLater from '../data/travel/persona_01.json';
import jasonLater from '../data/travel/persona_02.json';
import priyaLater from '../data/travel/persona_03.json';
import danielLater from '../data/travel/persona_04.json';
import newUser from '../data/new_user.json';
import rules from '../../../shared/game.json';
import { applyActions, type GameMove, type GardenRules } from '../lib/garden.ts';
import { stepDate, type StudyClock } from '../lib/study.ts';
import { ApiError, type FastApi } from './client.ts';
import type { CardAnswer, GameResponse, SampleBundle, SampleDay } from './types.ts';
import { checkAssess, checkAssistant, checkCard, checkFuture, checkGame, checkStudy } from './validate.ts';

export const SAMPLES: SampleBundle[] = [aina, jason, priya, daniel].map((s) => s as unknown as SampleBundle);
/** The sign-up card's made-up person on day one (D-124): shown after "Try the sign-up"; no study clock. */
export const NEW_USER = newUser as unknown as SampleBundle;
const LATER = new Map<string, Record<string, SampleDay>>(
  [ainaLater, jasonLater, priyaLater, danielLater].map((t, i) => [SAMPLES[i].persona.key, (t as unknown as {
    dates: Record<string, SampleDay> }).dates]));
const DATES = new Map<string, string>();                   // each persona's study date this session
const ACTIONS = new Map<string, { action: GameMove; on: string }[]>();     // game actions, with their date
const ANSWERS = new Map<string, CardAnswer>();             // card answers, by "persona:week"

const bundle = (key: string) => [...SAMPLES, NEW_USER].find((x) => x.persona.key === key) ?? SAMPLES[0];

/** A persona's study date and range this session (starts on its first date, as every participant's
 * copy); null for the new user, who isn't a persona. */
export function sampleClock(key: string): StudyClock | null {
  const s = bundle(key).study;
  if (!s.persona) return null;
  return { date: DATES.get(key) ?? s.study_date, first: s.first, last: s.last };
}

/** The sample's today: a persona's study date, or the day the new user's data was made for. */
export const sampleToday = (key: string) => sampleClock(key)?.date ?? bundle(key).assess.as_of;

/** What the backend sends this persona on a study date (by default, its date now). */
export function sampleDay(key: string, date = sampleToday(key)): SampleDay {
  const s = bundle(key);
  return LATER.get(s.persona.key)?.[date] ?? s;
}

export function sampleApi(key: string): FastApi {
  if (!ACTIONS.has(key)) ACTIONS.set(key, []);
  const done = ACTIONS.get(key)!;
  const today = () => sampleDay(key);
  const study = () => {
    const c = sampleClock(key);
    return checkStudy(c ? { persona: true, study_date: c.date, first: c.first, last: c.last } : { persona: false });
  };
  /** The day's game with the session's actions up to today; `extra` is a new one, refused with a 409. */
  const game = (extra?: GameMove): GameResponse => {
    const date = sampleToday(key);
    const refusal = { why: '' };
    const list = [...done.filter((x) => x.on <= date).map((x) => x.action), ...(extra ? [extra] : [])];
    const after = applyActions(today().game, list, rules as unknown as GardenRules, (a, e) => {
      if (a === extra) refusal.why = e.message;              // the engine's reason, as the API's 409
    });
    if (refusal.why) throw new ApiError(409, refusal.why);
    return checkGame(after);
  };
  const answered = (week: string) => ANSWERS.get(`${key}:${week}`);
  return {
    assess: async () => checkAssess(today().assess),
    future: async () => checkFuture(today().future),
    game: async () => game(),
    gameAction: async (a) => {
      const after = game(a);
      done.push({ action: a, on: sampleToday(key) });
      return after;
    },
    card: async () => {
      const c = today().card;                              // the persona's own answer comes with the day
      return checkCard({ ...c, answer: answered(c.week) ?? c.answer });
    },
    answerCard: async (response) => {                      // as POST /v1/card: once a week, 409 after
      const c = today().card;
      if (answered(c.week) || c.answer) throw new ApiError(409, "you've already answered this week's card");
      ANSWERS.set(`${key}:${c.week}`, response);
      return checkCard({ ...c, answer: response });
    },
    study: async () => study(),
    timeTravel: async (step) => {                          // as POST /v1/study/time-travel
      const c = sampleClock(key);
      if (!c) throw new ApiError(403, 'time travel is only for study personas');
      DATES.set(key, stepDate(c, step));
      return study();
    },
    assistant: async () => checkAssistant({                // no AI here: FAST says so, and shows what it would get
      answer: 'Sample data can\'t reach the money helper: it runs on FAST\'s server with the AI, once you sign in. '
        + 'Below is everything the AI would be given about you, and nothing more.',
      kind: 'fallback', by: 'fast', grounded: true, as_of: today().assess.as_of,
      assessed_month: today().assess.assessed_month, shared_with_assistant: today().helper_facts,
    }),
  };
}
