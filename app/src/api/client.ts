/**
 * The FAST API client (api/main.py). Every call sends the user's Supabase sign-in token; the user id
 * always comes from the token on the server, never from the app (api/auth.py). Responses are checked
 * (validate.ts) before the screens see them. Pure TypeScript: `fetch` is passed in, so Node can test it.
 *
 * Errors: the server's status and its gentle "detail" text come back as ApiError, for example
 * 409 "no choice available yet" (a game action the rules don't allow) or 429 with Retry-After.
 */
import type {
  AssistantReply, AssessResponse, CardAnswer, CardResponse, FutureResponse, GameResponse, StudyResponse,
} from './types.ts';
import { checkAssess, checkAssistant, checkCard, checkFuture, checkGame, checkStudy } from './validate.ts';

export class ApiError extends Error {
  status: number;
  detail: string;
  retryAfter: number | null;
  constructor(status: number, detail: string, retryAfter: number | null = null) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export type GameAction =
  | { kind: 'plant'; cell: [number, number]; item: string }
  | { kind: 'dig'; cell: [number, number] }
  | { kind: 'buy_tree' }
  | { kind: 'decorate' | 'move_decoration'; item: string; spot: string }
  | { kind: 'choose_animal' | 'add_animal'; item: string };

export interface FastApi {
  assess(): Promise<AssessResponse>;
  future(): Promise<FutureResponse>;
  game(): Promise<GameResponse>;
  gameAction(action: GameAction): Promise<GameResponse>;
  card(): Promise<CardResponse>;                              // this week's life-event card (D-117)
  answerCard(response: CardAnswer): Promise<CardResponse>;
  study(): Promise<StudyResponse>;
  timeTravel(step: 'next' | 'previous' | 'first' | 'last'): Promise<StudyResponse>;
  assistant(question: string): Promise<AssistantReply>;
}

export type ApiConfig = {
  baseUrl: string;                                  // e.g. https://fast-api.onrender.com (EXPO_PUBLIC_API_URL)
  getToken: () => Promise<string | null>;           // the Supabase session's access token
  fetchFn?: typeof fetch;
};

export function createApi({ baseUrl, getToken, fetchFn = fetch }: ApiConfig): FastApi {
  async function call(method: 'GET' | 'POST', path: string, body?: unknown): Promise<unknown> {
    const token = await getToken();
    if (!token) throw new ApiError(401, 'please sign in again');
    const res = await fetchFn(`${baseUrl.replace(/\/$/, '')}${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = res.statusText || 'something went wrong';
      try {
        const j = (await res.json()) as { detail?: unknown };
        if (typeof j.detail === 'string') detail = j.detail;
      } catch {
        // not JSON: keep the status text
      }
      const ra = Number(res.headers.get('Retry-After'));
      throw new ApiError(res.status, detail, Number.isFinite(ra) && ra > 0 ? ra : null);
    }
    return res.json();
  }

  return {
    assess: async () => checkAssess(await call('GET', '/v1/assess')),
    future: async () => checkFuture(await call('GET', '/v1/future')),
    game: async () => checkGame(await call('GET', '/v1/game')),
    gameAction: async (action) => checkGame(await call('POST', '/v1/game/actions', action)),
    card: async () => checkCard(await call('GET', '/v1/card')),
    answerCard: async (response) => checkCard(await call('POST', '/v1/card', { response })),
    study: async () => checkStudy(await call('GET', '/v1/study')),
    timeTravel: async (step) => checkStudy(await call('POST', '/v1/study/time-travel', { step })),
    assistant: async (question) => checkAssistant(await call('POST', '/v1/assistant', { question })),
  };
}
