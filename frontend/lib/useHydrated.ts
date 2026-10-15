import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** False in the server HTML and during hydration, true once React owns the page. Buttons that need JS stay
 * disabled until then, so an early click on a slow load is not silently lost. */
export function useHydrated(): boolean {
  return useSyncExternalStore(subscribe, () => true, () => false);
}
