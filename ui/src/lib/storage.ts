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
  thinkingContent?: string; // Accumulated reasoning/thinking tokens
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

/**
 * Generate a concise, meaningful title from the first user message.
 *
 * Instead of raw truncation, this:
 *  1. Uses only the first line (for multi-line messages)
 *  2. Strips conversational filler ("Can you", "I want to", "Please help me", …)
 *  3. Capitalises the first letter
 *  4. Removes trailing punctuation for a clean sidebar label
 *  5. Truncates at the last word boundary within 60 chars
 */
export function autoTitle(messages: DisplayMessage[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New Chat";

  // Use only the first non-empty line
  let text = firstUser.content.split("\n").map((l) => l.trim()).find((l) => l.length > 0) ?? "";
  if (!text) return "New Chat";

  // Strip leading filler phrases (case-insensitive)
  const fillerPatterns = [
    /^(hey\s+)?(can you|could you|would you)\s+(please\s+)?(help\s+me\s+)?(to\s+)?/i,
    /^(i('d| would) like to|i want to|i need to|let('s| us))\s+/i,
    /^(please\s+)?(help\s+me\s+)?(to\s+)?/i,
  ];
  for (const pattern of fillerPatterns) {
    const stripped = text.replace(pattern, "");
    if (stripped.length > 0 && stripped.length < text.length) {
      text = stripped;
      break; // apply only the first matching pattern
    }
  }

  // Remove trailing punctuation
  text = text.replace(/[?!.,;:]+$/, "");

  // Capitalise first letter
  text = text.charAt(0).toUpperCase() + text.slice(1);

  // Truncate at word boundary within limit
  const MAX_LEN = 60;
  if (text.length > MAX_LEN) {
    const cut = text.lastIndexOf(" ", MAX_LEN);
    text = cut > 20 ? text.slice(0, cut) : text.slice(0, MAX_LEN);
    text = text.replace(/[,;:\s]+$/, ""); // clean trailing junk after cut
  }

  return text || "New Chat";
}
