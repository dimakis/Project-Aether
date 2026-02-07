import { useState, useCallback, useEffect, useRef } from "react";
import { storageGet, storageSet } from "@/lib/storage";

/**
 * Like useState, but persisted to localStorage.
 * Reads the initial value from storage, writes on every change.
 *
 * @param key - Storage key (auto-prefixed with "aether:")
 * @param fallback - Default value if nothing is stored
 */
export function usePersistedState<T>(
  key: string,
  fallback: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [state, setState] = useState<T>(() => storageGet(key, fallback));

  // Track if this is the initial mount to avoid double-writing the fallback
  const isInitial = useRef(true);

  useEffect(() => {
    if (isInitial.current) {
      isInitial.current = false;
      return;
    }
    storageSet(key, state);
  }, [key, state]);

  const setPersistedState = useCallback(
    (value: T | ((prev: T) => T)) => {
      setState((prev) => {
        const next = typeof value === "function" ? (value as (prev: T) => T)(prev) : value;
        return next;
      });
    },
    [],
  );

  return [state, setPersistedState];
}
