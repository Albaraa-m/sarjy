import { useSyncExternalStore } from "react";

type HexColor = `#${string}`;

// Design tokens are fixed for the page's lifetime, so there's nothing to subscribe to.
const NEVER_CHANGES = () => () => {};

/**
 * A color token from design-tokens.css, for shaders that can't use CSS classes.
 * Undefined during server rendering, which has no CSS; useSyncExternalStore makes that safe for hydration.
 */
export function useCssColor(token: `--color-${string}`): HexColor | undefined {
  return useSyncExternalStore(
    NEVER_CHANGES,
    () => getComputedStyle(document.documentElement).getPropertyValue(token).trim() as HexColor,
    () => undefined,
  );
}
