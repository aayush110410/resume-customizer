import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** False in the server HTML and during hydration, true once React owns the page. Buttons that need JS stay
 * disabled until then, so a click on a slow (cold-start) load is never silently dropped. */
export function useHydrated(): boolean {
  return useSyncExternalStore(subscribe, () => true, () => false);
}
