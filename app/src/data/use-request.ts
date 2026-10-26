import { useEffect, useState } from 'react';

/**
 * Load one API answer for a screen: loading, data or a readable error. Re-runs when `deps` change
 * (e.g. another sample persona). Production vs coursework: TanStack Query (docs/app_plan.md §2) adds
 * caching and refetch-after-write; it replaces this once the real API is connected.
 */
export function useRequest<T>(load: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>(
    { data: null, error: null, loading: true });
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    load()
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((e: unknown) => alive && setState({ data: null, error: e instanceof Error ? e.message : String(e),
                                                  loading: false }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}
