/**
 * Typed localStorage helpers with JSON serialization.
 * All keys are prefixed with "aether:" to avoid collisions.
 */

const PREFIX = "aether:";

export function storageGet<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function storageSet<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

export function storageRemove(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key);
  } catch {
    // ignore
  }
}

// ─── Storage Keys ────────────────────────────────────────────────────────────

export const STORAGE_KEYS = {
  /** Last selected model ID */
  selectedModel: "selectedModel",
  /** Current chat messages (serialized DisplayMessage[]) */
  chatMessages: "chatMessages",
  /** Whether the sidebar is collapsed */
  sidebarCollapsed: "sidebarCollapsed",
} as const;
