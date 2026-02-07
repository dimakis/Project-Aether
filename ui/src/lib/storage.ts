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

// ─── Chat Session Types ──────────────────────────────────────────────────────

export interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  timestamp?: string; // ISO string for serialization
  traceId?: string; // MLflow trace ID for feedback
  feedback?: "positive" | "negative"; // User sentiment feedback
}

export interface ChatSession {
  id: string;
  title: string;
  messages: DisplayMessage[];
  model: string;
  createdAt: string; // ISO string
  updatedAt: string; // ISO string
}

// ─── Storage Keys ────────────────────────────────────────────────────────────

export const STORAGE_KEYS = {
  /** Last selected model ID */
  selectedModel: "selectedModel",
  /** Current chat messages (serialized DisplayMessage[]) — legacy, migrated to sessions */
  chatMessages: "chatMessages",
  /** Whether the sidebar is collapsed */
  sidebarCollapsed: "sidebarCollapsed",
  /** All local chat sessions */
  chatSessions: "chatSessions",
  /** Active session ID */
  activeSessionId: "activeSessionId",
} as const;

// ─── Session Helpers ─────────────────────────────────────────────────────────

/** Generate a short unique ID for sessions */
export function generateSessionId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

/** Auto-title from first user message, truncated to ~40 chars */
export function autoTitle(messages: DisplayMessage[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New Chat";
  const text = firstUser.content.trim();
  if (text.length <= 40) return text;
  return text.slice(0, 40).trimEnd() + "...";
}
