// shared/categories.json: the category list the app and the personas' data share (D-112, rule 5).
// Metro reaches it through metro.config.js (watchFolders).
import raw from '../../../shared/categories.json';

import type { Categories, Category, Direction } from '@/lib/entry';

export const CATEGORIES = raw as unknown as Categories;

/** The first chips shown for money out; every other category is one tap away ("More"). */
export const COMMON_OUT = ['food_home', 'eating_out', 'transport', 'shopping', 'housing', 'communication', 'family'];

export function findCategory(direction: Direction, key: string): Category | undefined {
  return CATEGORIES[direction].find((c) => c.key === key);
}
