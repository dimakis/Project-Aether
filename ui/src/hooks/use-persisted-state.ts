import { useState, useCallback, useEffect, useRef } from "react";
import { storageGet, storageSet } from "@/lib/storage";

/**
 * Like useState, but persisted to localStorage.
 * Reads the initial value from storage, writes on every change.
 *
 * Hardened against React StrictMode double-renders:
 * - Tracks the last written value to avoid redundant writes
 * - Skips the initial write (the stored value is already correct)
 * - Uses stable JSON comparison to prevent false-positive writes
 *
 * @param key - Storage key (auto-prefixed with "aether:")
 * @param fallback - Default value if nothing is stored
 */
export function usePersistedState<T>(
  key: string,
  fallback: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize lazily from storage
  const [state, setState] = useState<T>(() => storageGet(key, fallback));

  // Track the last value we actually wrote to storage so we can skip
  // redundant writes (including the initial mount write).
  const lastWritten = useRef<string | null>(null);

  // On first mount, capture what's already stored so the effect knows
  // not to re-write the same value.
  const initialized = useRef(false);
  if (!initialized.current) {
    initialized.current = true;
    try {
      lastWritten.current = JSON.stringify(state);
    } catch {
      lastWritten.current = null;
    }
  }

  useEffect(() => {
    let serialized: string;
    try {
      serialized = JSON.stringify(state);
    } catch {
      return; // un-serializable — skip
    }

    // Only write if the value actually changed from what's stored
    if (serialized !== lastWritten.current) {
      lastWritten.current = serialized;
      storageSet(key, state);
    }
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
