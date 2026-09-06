import { createContext, useContext } from "react";
import { fallbackConfig } from "../eventConfigFallback";

export const EventConfigContext = createContext({ config: fallbackConfig, loading: true });

export function useEventConfig() {
  return useContext(EventConfigContext);
}
