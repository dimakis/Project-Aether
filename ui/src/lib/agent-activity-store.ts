/**
 * Lightweight global store for agent activity state.
 *
 * Feature 11: Live Agent Activity Trace.
 *
 * The chat page updates this store during streaming, and the sidebar
 * reads from it to show a subtle activity indicator.
 */

import { useSyncExternalStore } from "react";

interface AgentActivityState {
  /** Whether any agent is currently processing */
  isActive: boolean;
  /** The currently active agent (if any) */
  activeAgent: string | null;
  /** Target agent being delegated to (if any) */
  delegatingTo: string | null;
}

let state: AgentActivityState = {
  isActive: false,
  activeAgent: null,
  delegatingTo: null,
};

const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return state;
}

// ─── Public API ──────────────────────────────────────────────────────────────

export function setAgentActivity(update: Partial<AgentActivityState>) {
  state = { ...state, ...update };
  notify();
}

export function clearAgentActivity() {
  state = { isActive: false, activeAgent: null, delegatingTo: null };
  notify();
}

/** React hook to subscribe to agent activity state */
export function useAgentActivity(): AgentActivityState {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
