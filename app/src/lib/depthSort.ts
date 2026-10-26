/**
 * Drawing order for the home scene (D-88): a port of tools/asset_generation/scenes.py depth_sort,
 * kept equal to it by a fixture generated from Python (tools/app_fixtures.py).
 *
 * Input: pieces already sorted by front cell and layer. Rule (isometric separating axis): A is drawn
 * before B when A's footprint lies wholly behind B's along gx (A.gx + A.w <= B.gx) or along gy
 * (A.gy + A.d <= B.gy). Only pairs whose screen columns overlap need an order. Pairs sharing cells
 * keep the incoming order. A topological sort that always takes the earliest ready piece keeps
 * everything else as it came.
 * Invariant: for every pair overlapping on screen, the one wholly behind comes first.
 * Cost: O(n^2) pair checks and O(n^2) for picking the earliest ready piece; n is at most ~300.
 */
export type Box = { gx: number; gy: number; w: number; d: number };

export function overlapOnScreen(a: Box, c: Box): boolean {
  const [a0, a1, b0, b1] = [a.gx, a.gx + a.w, a.gy, a.gy + a.d];
  const [c0, c1, d0, d1] = [c.gx, c.gx + c.w, c.gy, c.gy + c.d];
  return !(a1 - b0 <= c0 - d1 || c1 - d0 <= a0 - b1);       // screen columns (gx - gy) overlap
}

function whollyBehind(a: Box, c: Box): boolean {
  return a.gx + a.w <= c.gx || a.gy + a.d <= c.gy;
}

export function depthSort<T extends Box>(items: T[]): T[] {
  const n = items.length;
  const after: number[][] = Array.from({ length: n }, () => []);
  const indeg = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (!overlapOnScreen(items[i], items[j])) continue;
      let first = i;
      let second = j;
      if (whollyBehind(items[i], items[j])) {
        first = i; second = j;
      } else if (whollyBehind(items[j], items[i])) {
        first = j; second = i;
      }                                                       // else shared cells: incoming order
      after[first].push(second);
      indeg[second] += 1;
    }
  }
  const done = new Array<boolean>(n).fill(false);
  const ready = new Set<number>();
  for (let i = 0; i < n; i++) if (indeg[i] === 0) ready.add(i);
  const out: T[] = [];
  while (out.length < n) {
    let next: number;
    if (ready.size === 0) {
      next = done.findIndex((d) => !d);                      // a cycle (none in our layouts): incoming order
    } else {
      next = Math.min(...ready);
      ready.delete(next);
    }
    if (done[next]) continue;
    done[next] = true;
    out.push(items[next]);
    for (const j of after[next]) {
      indeg[j] -= 1;
      if (indeg[j] === 0 && !done[j]) ready.add(j);
    }
  }
  return out;
}

/** Pairs (earlier, later) where the later piece lies wholly behind the earlier one and they overlap
 * on screen: what depthSort rules out (for tests, and a debug check in the app). */
export function orderViolations<T extends Box>(items: T[]): [T, T][] {
  const out: [T, T][] = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      if (overlapOnScreen(items[i], items[j]) && whollyBehind(items[j], items[i])) out.push([items[i], items[j]]);
    }
  }
  return out;
}
