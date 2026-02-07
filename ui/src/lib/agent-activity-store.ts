/**
 * Lightweight global store for agent activity state.
 *
 * Used by:
 * - ChatPage: setAgentActivity / clearAgentActivity when streaming
 * - AppLayout sidebar: useAgentActivity to show live indicator
 *
 * Uses useSyncExternalStore for React 18+ compatibility.
 */

import { useSyncExternalStore } from "react";

export interface AgentActivity {
  isActive: boolean;
  activeAgent: string | null;
  delegatingTo?: string | null;
  agents?: string[];
}

const DEFAULT: AgentActivity = { isActive: false, activeAgent: null };

let current: AgentActivity = DEFAULT;
const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

export function setAgentActivity(activity: Partial<AgentActivity>) {
  current = { ...current, ...activity };
  notify();
}

export function clearAgentActivity() {
  current = DEFAULT;
  notify();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): AgentActivity {
  return current;
}

/** React hook to read the current agent activity state. */
export function useAgentActivity(): AgentActivity {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
