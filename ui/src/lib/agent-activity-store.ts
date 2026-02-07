/**
 * Lightweight global store for agent activity state.
 *
 * Used by:
 * - ChatPage: setAgentActivity / clearAgentActivity when streaming
 * - AppLayout: useAgentActivity to show live indicator + render panel
 * - Any page: toggleActivityPanel / useActivityPanel for panel visibility
 *
 * Persists lastTraceId and panelOpen to localStorage so they survive
 * page navigation and full page refreshes.
 *
 * Uses useSyncExternalStore for React 18+ compatibility.
 */

import { useSyncExternalStore } from "react";

// ─── Activity State (streaming indicator) ────────────────────────────────────

export interface AgentActivity {
  isActive: boolean;
  activeAgent: string | null;
  delegatingTo?: string | null;
  agents?: string[];
}

const DEFAULT_ACTIVITY: AgentActivity = { isActive: false, activeAgent: null };

let currentActivity: AgentActivity = DEFAULT_ACTIVITY;
const activityListeners = new Set<() => void>();

function notifyActivity() {
  for (const listener of activityListeners) {
    listener();
  }
}

export function setAgentActivity(activity: Partial<AgentActivity>) {
  currentActivity = { ...currentActivity, ...activity };
  notifyActivity();
}

export function clearAgentActivity() {
  currentActivity = DEFAULT_ACTIVITY;
  notifyActivity();
}

function subscribeActivity(listener: () => void) {
  activityListeners.add(listener);
  return () => activityListeners.delete(listener);
}

function getActivitySnapshot(): AgentActivity {
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
