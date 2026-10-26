// shared/helper.json: the money helper's question limit, crisis words and crisis reply, one copy for
// the app and the API (D-123, rule 5). Metro reaches it through metro.config.js (watchFolders).
import raw from '../../../shared/helper.json';

export const HELPER = raw as { max_question_chars: number; crisis_words: string; crisis_reply: string };
