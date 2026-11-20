import { useSyncExternalStore } from "react";

/** Breakpoint do celular (< 640px), igual ao `sm:` do Tailwind. */
export const MOBILE_QUERY = "(max-width: 639px)";

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}
