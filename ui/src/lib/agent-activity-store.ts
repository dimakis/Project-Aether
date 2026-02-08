/**
 * Lightweight global store for agent activity state.
 *
 * Used by:
 * - ChatPage: setAgentActivity / completeAgentActivity when streaming
 * - AppLayout: useAgentActivity to show live indicator + render panel
 * - Any page: toggleActivityPanel / useActivityPanel for panel visibility
 *
 * Persists lastTraceId and panelOpen to localStorage so they survive
 * page navigation and full page refreshes.
 *
 * Uses useSyncExternalStore for React 18+ compatibility.
 */

import { useSyncExternalStore } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

/** Visual state of an agent node in the neural topology. */
export type AgentNodeState = "dormant" | "idle" | "firing" | "done";

/** A single entry in the live event feed shown during streaming. */
export interface LiveTimelineEntry {
  agent: string;
  event: string; // "start" | "end" | "tool_call" | "tool_result" | "complete"
  tool?: string;
  ts: number;
}

// ─── Activity State (streaming indicator) ────────────────────────────────────

/** A captured inter-agent delegation message. */
export interface DelegationMessage {
  from: string;
  to: string;
  content: string;
  ts: number;
}

export interface AgentActivity {
  isActive: boolean;
  activeAgent: string | null;
  delegatingTo?: string | null;
  agents?: string[];
  /** Agents accumulated during the current stream (order of first appearance). */
  agentsSeen: string[];
  /** Per-agent visual state for the neural topology. */
  agentStates: Record<string, AgentNodeState>;
  /** Real-time event feed entries collected during streaming. */
  liveTimeline: LiveTimelineEntry[];
  /** Accumulated thinking/reasoning content from the LLM stream. */
  thinkingStream: string;
  /** Edges [from, to] that were activated during the current workflow. */
  activeEdges: [string, string][];
  /** Inter-agent delegation messages captured during the workflow. */
  delegationMessages: DelegationMessage[];
  /** Epoch ms when the last workflow completed (null while active or idle). */
  completedAt: number | null;
}

const DEFAULT_ACTIVITY: AgentActivity = {
  isActive: false,
  activeAgent: null,
  agentsSeen: [],
  agentStates: {},
  liveTimeline: [],
  thinkingStream: "",
  activeEdges: [],
  delegationMessages: [],
  completedAt: null,
};

let currentActivity: AgentActivity = DEFAULT_ACTIVITY;
const activityListeners = new Set<() => void>();

function notifyActivity() {
  for (const listener of activityListeners) {
    listener();
  }
}

export function setAgentActivity(activity: Partial<AgentActivity>) {
  // When transitioning from completed/idle → active, clear stale state first
  // so the new session starts fresh.
  if (activity.isActive && !currentActivity.isActive) {
    currentActivity = {
      ...DEFAULT_ACTIVITY,
      ...activity,
    };
  } else {
    currentActivity = { ...currentActivity, ...activity };
  }
  notifyActivity();
}

/**
 * Transition to a "completed" state that preserves the timeline,
 * agent states, and thinking content so the user can review them.
 *
 * The preserved state will be auto-cleared the next time
 * setAgentActivity is called with `isActive: true`.
 */
export function completeAgentActivity() {
  // Mark all seen agents as "done"
  const doneStates: Record<string, AgentNodeState> = {};
  for (const agent of currentActivity.agentsSeen) {
    doneStates[agent] = "done";
  }

  currentActivity = {
    ...currentActivity,
    isActive: false,
    activeAgent: null,
    delegatingTo: null,
    agentStates: doneStates,
    completedAt: Date.now(),
  };
  notifyActivity();
}

/**
 * Hard reset to default state. Prefer `completeAgentActivity()` for
 * normal workflow endings — use this only for explicit user-initiated
 * resets or error recovery.
 */
export function clearAgentActivity() {
  currentActivity = { ...DEFAULT_ACTIVITY };
  notifyActivity();
}

function subscribeActivity(listener: () => void) {
  activityListeners.add(listener);
  return () => activityListeners.delete(listener);
}

/** Get the current activity snapshot (for use outside React components). */
export function getActivitySnapshot(): AgentActivity {
  return currentActivity;
}

/** React hook to read the current agent activity state. */
export function useAgentActivity(): AgentActivity {
  return useSyncExternalStore(subscribeActivity, getActivitySnapshot, getActivitySnapshot);
}

// ─── Panel State (persistent across navigation) ─────────────────────────────

const STORAGE_KEY_TRACE_ID = "aether:lastTraceId";
const STORAGE_KEY_PANEL_OPEN = "aether:activityPanelOpen";

interface PanelState {
  lastTraceId: string | null;
  panelOpen: boolean;
}

function loadPanelState(): PanelState {
  try {
    const traceId = localStorage.getItem(STORAGE_KEY_TRACE_ID) || null;
    const panelOpen = localStorage.getItem(STORAGE_KEY_PANEL_OPEN) !== "false"; // default open
    return { lastTraceId: traceId, panelOpen };
  } catch {
    return { lastTraceId: null, panelOpen: true };
  }
}

let currentPanel: PanelState = loadPanelState();
const panelListeners = new Set<() => void>();

function notifyPanel() {
  for (const listener of panelListeners) {
    listener();
  }
}

export function setLastTraceId(traceId: string | null) {
  currentPanel = { ...currentPanel, lastTraceId: traceId };
  try {
    if (traceId) {
      localStorage.setItem(STORAGE_KEY_TRACE_ID, traceId);
    } else {
      localStorage.removeItem(STORAGE_KEY_TRACE_ID);
    }
  } catch {
    // localStorage may be unavailable
  }
  notifyPanel();
}

export function toggleActivityPanel() {
  currentPanel = { ...currentPanel, panelOpen: !currentPanel.panelOpen };
  try {
    localStorage.setItem(STORAGE_KEY_PANEL_OPEN, String(currentPanel.panelOpen));
  } catch {
    // localStorage may be unavailable
  }
  notifyPanel();
}

export function setActivityPanelOpen(open: boolean) {
  currentPanel = { ...currentPanel, panelOpen: open };
  try {
    localStorage.setItem(STORAGE_KEY_PANEL_OPEN, String(open));
  } catch {
    // localStorage may be unavailable
  }
  notifyPanel();
}

function subscribePanel(listener: () => void) {
  panelListeners.add(listener);
  return () => panelListeners.delete(listener);
}

function getPanelSnapshot(): PanelState {
  return currentPanel;
}

/** React hook to read the panel state (lastTraceId + panelOpen). */
export function useActivityPanel(): PanelState {
  return useSyncExternalStore(subscribePanel, getPanelSnapshot, getPanelSnapshot);
}
