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
  /** Truncated tool arguments (for tool_call events). */
  toolArgs?: string;
  /** Truncated tool result (for tool_result events). */
  toolResult?: string;
  ts: number;
}

// ─── Job Tracking ────────────────────────────────────────────────────────────

export type JobType = "chat" | "optimization" | "analysis" | "schedule" | "webhook" | "evaluation" | "discovery" | "other";

export interface JobInfo {
  jobId: string;
  jobType: JobType;
  title: string;
  status: "running" | "completed" | "failed";
  startedAt: number;
}

const MAX_TRACKED_JOBS = 30;

/** Map of jobId -> JobInfo for all known jobs (live + recent). */
const jobRegistry = new Map<string, JobInfo>();
const jobListeners = new Set<() => void>();
let _jobListSnapshot: JobInfo[] = [];

function _rebuildJobListSnapshot() {
  _jobListSnapshot = [...jobRegistry.values()].sort(
    (a, b) => b.startedAt - a.startedAt,
  );
}

function notifyJobList() {
  _rebuildJobListSnapshot();
  for (const listener of jobListeners) listener();
}

export function registerJob(info: JobInfo) {
  jobRegistry.set(info.jobId, info);
  while (jobRegistry.size > MAX_TRACKED_JOBS) {
    const oldest = _jobListSnapshot[_jobListSnapshot.length - 1];
    if (oldest) jobRegistry.delete(oldest.jobId);
  }
  notifyJobList();
}

export function updateJobStatus(jobId: string, status: JobInfo["status"]) {
  const existing = jobRegistry.get(jobId);
  if (existing) {
    jobRegistry.set(jobId, { ...existing, status });
    notifyJobList();
  }
}

export function getJobList(): JobInfo[] {
  return _jobListSnapshot;
}

function subscribeJobList(listener: () => void) {
  jobListeners.add(listener);
  return () => jobListeners.delete(listener);
}

/** React hook to read the tracked job list (sorted most recent first). */
export function useJobList(): JobInfo[] {
  return useSyncExternalStore(subscribeJobList, getJobList, getJobList);
}

/** Hydrate the job registry from API data (e.g. GET /jobs on mount). */
export function hydrateJobs(apiJobs: Array<{ job_id: string; job_type: string; status: string; title: string; started_at: number }>) {
  for (const j of apiJobs) {
    if (!jobRegistry.has(j.job_id)) {
      jobRegistry.set(j.job_id, {
        jobId: j.job_id,
        jobType: j.job_type as JobType,
        title: j.title,
        status: j.status as JobInfo["status"],
        startedAt: j.started_at,
      });
    }
  }
  while (jobRegistry.size > MAX_TRACKED_JOBS) {
    const sorted = [...jobRegistry.values()].sort((a, b) => a.startedAt - b.startedAt);
    if (sorted[0]) jobRegistry.delete(sorted[0].jobId);
  }
  notifyJobList();
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

/** Session that currently owns the activity panel. */
let activeSessionId: string | null = null;

// ─── Per-Session Activity Cache ────────────────────────────────────────────

/** Cached activity snapshot for a completed session. */
export interface SessionActivitySnapshot {
  activity: AgentActivity;
  traceId: string | null;
  /** ISO timestamp when the snapshot was created. */
  cachedAt: string;
}

const MAX_CACHED_SESSIONS = 20;

/** Map of sessionId -> snapshot for completed sessions. */
const sessionCache = new Map<string, SessionActivitySnapshot>();

/** Ordered list of session IDs (most recent first) for the cycler UI. */
let sessionOrder: string[] = [];

// ─── Array Caps (prevent unbounded growth) ────────────────────────────────

const MAX_LIVE_TIMELINE = 200;
const MAX_ACTIVE_EDGES = 50;
const MAX_DELEGATION_MESSAGES = 50;

/** FIFO-cap an array: keep the last `max` elements. */
function cap<T>(arr: T[], max: number): T[] {
  return arr.length > max ? arr.slice(arr.length - max) : arr;
}

/** Apply caps to all bounded arrays in the activity state. */
function capArrays(state: AgentActivity): AgentActivity {
  const { liveTimeline, activeEdges, delegationMessages } = state;
  if (
    liveTimeline.length <= MAX_LIVE_TIMELINE &&
    activeEdges.length <= MAX_ACTIVE_EDGES &&
    delegationMessages.length <= MAX_DELEGATION_MESSAGES
  ) {
    return state; // nothing to cap — avoid unnecessary object creation
  }
  return {
    ...state,
    liveTimeline: cap(liveTimeline, MAX_LIVE_TIMELINE),
    activeEdges: cap(activeEdges, MAX_ACTIVE_EDGES),
    delegationMessages: cap(delegationMessages, MAX_DELEGATION_MESSAGES),
  };
}

function notifyActivity() {
  for (const listener of activityListeners) {
    listener();
  }
}

export function setAgentActivity(activity: Partial<AgentActivity>) {
  // When transitioning from completed/idle → active, clear stale state first
  // so the new session starts fresh.
  if (activity.isActive && !currentActivity.isActive) {
    currentActivity = capArrays({
      ...DEFAULT_ACTIVITY,
      ...activity,
    });
  } else {
    currentActivity = capArrays({ ...currentActivity, ...activity });
  }
  notifyActivity();
}

/** Returns true if the activity has meaningful data worth caching. */
function hasCacheableActivity(activity: AgentActivity): boolean {
  return (
    activity.agentsSeen.length > 0 ||
    activity.liveTimeline.length > 0 ||
    (activity.thinkingStream?.length ?? 0) > 0
  );
}

/**
 * Transition to a "completed" state that preserves the timeline,
 * agent states, and thinking content so the user can review them.
 *
 * The preserved state will be auto-cleared the next time
 * setAgentActivity is called with `isActive: true`.
 *
 * @param completingSessionId - Optional session ID that just completed.
 *   When provided (e.g. from chat), cache under this ID so the snapshot
 *   can be restored when switching sessions. Use this when the caller
 *   knows which session owns the activity, avoiding timing issues where
 *   activeSessionId may have changed (user switched) or not yet been set.
 */
export function completeAgentActivity(completingSessionId?: string | null) {
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
    activeEdges: [],
    completedAt: Date.now(),
  };

  // Cache the completed snapshot so it can be restored when switching sessions.
  // Use completingSessionId when provided (avoids timing issues); otherwise
  // fall back to activeSessionId. Only cache when currentActivity still
  // belongs to the session we're caching for (user didn't switch during stream).
  const cacheKey = completingSessionId ?? activeSessionId;
  const activityBelongsToCacheKey =
    !cacheKey ||
    activeSessionId === null ||
    activeSessionId === cacheKey;
  if (
    cacheKey &&
    hasCacheableActivity(currentActivity) &&
    activityBelongsToCacheKey
  ) {
    _cacheSessionSnapshot(cacheKey, currentActivity);
  }

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

/**
 * Set which session currently owns the activity panel.
 *
 * If a cached snapshot exists for the new session, it is restored.
 * Otherwise the panel starts with a clean slate.
 */
export function setActivitySession(sessionId: string | null) {
  // Save current session's state to cache before switching.
  // Cache whenever there's meaningful activity, not just agentsSeen.
  if (activeSessionId && hasCacheableActivity(currentActivity)) {
    _cacheSessionSnapshot(activeSessionId, currentActivity);
  }

  activeSessionId = sessionId;

  // Restore cached snapshot or start clean
  if (sessionId && sessionCache.has(sessionId)) {
    const cached = sessionCache.get(sessionId)!;
    currentActivity = cached.activity;
    // Also update the panel's lastTraceId to match the restored session
    if (cached.traceId) {
      setLastTraceId(cached.traceId);
    }
  } else {
    currentActivity = { ...DEFAULT_ACTIVITY };
  }
  // Rebuild session cache snapshot since activeSessionId changed
  _rebuildSessionCacheSnapshot();
  notifyActivity();
}

/** Get the session ID that currently owns the activity panel. */
export function getActivitySessionId(): string | null {
  return activeSessionId;
}

/** Get the current activity snapshot (for use outside React components). */
export function getActivitySnapshot(): AgentActivity {
  return currentActivity;
}

/** React hook to read the current agent activity state. */
export function useAgentActivity(): AgentActivity {
  return useSyncExternalStore(subscribeActivity, getActivitySnapshot, getActivitySnapshot);
}

// ─── Session Cache Internals ─────────────────────────────────────────────────

function _cacheSessionSnapshot(sessionId: string, activity: AgentActivity) {
  const traceId = currentPanel?.lastTraceId ?? null;
  sessionCache.set(sessionId, {
    activity: { ...activity },
    traceId,
    cachedAt: new Date().toISOString(),
  });

  // Update session order (most recent first)
  sessionOrder = [sessionId, ...sessionOrder.filter((id) => id !== sessionId)];

  // Evict oldest entries if over the cap
  while (sessionOrder.length > MAX_CACHED_SESSIONS) {
    const evicted = sessionOrder.pop();
    if (evicted) sessionCache.delete(evicted);
  }

  notifySessionCache();
}

// Listeners for the session cache (used by the cycler UI)
const sessionCacheListeners = new Set<() => void>();

function notifySessionCache() {
  _rebuildSessionCacheSnapshot();
  for (const listener of sessionCacheListeners) {
    listener();
  }
}

interface SessionCacheInfo {
  /** Ordered list of cached session IDs (most recent first). */
  sessionIds: string[];
  /** The currently active session ID. */
  activeSessionId: string | null;
}

// Memoised snapshot — only recreated when notifySessionCache() fires.
// useSyncExternalStore compares snapshots with Object.is, so returning
// a new object on every call would cause an infinite re-render loop.
let _sessionCacheSnapshot: SessionCacheInfo = { sessionIds: sessionOrder, activeSessionId };

function _rebuildSessionCacheSnapshot() {
  _sessionCacheSnapshot = { sessionIds: sessionOrder, activeSessionId };
}

function getSessionCacheSnapshot(): SessionCacheInfo {
  return _sessionCacheSnapshot;
}

function subscribeSessionCache(listener: () => void) {
  sessionCacheListeners.add(listener);
  return () => sessionCacheListeners.delete(listener);
}

/** React hook for the session cycler — returns cached session IDs and active session. */
export function useSessionCache(): SessionCacheInfo {
  return useSyncExternalStore(subscribeSessionCache, getSessionCacheSnapshot, getSessionCacheSnapshot);
}

/** Get a cached session's snapshot (for display in the cycler). */
export function getCachedSession(sessionId: string): SessionActivitySnapshot | null {
  return sessionCache.get(sessionId) ?? null;
}

// ─── Panel State (persistent across navigation) ─────────────────────────────

const STORAGE_KEY_TRACE_ID = "aether:lastTraceId";
const STORAGE_KEY_PANEL_OPEN = "aether:activityPanelOpen";
const STORAGE_KEY_PANEL_WIDTH = "aether:activityPanelWidth";

/** Resizable panel constraints (px). */
export const PANEL_MIN_WIDTH = 240;
export const PANEL_MAX_WIDTH = 480;
export const PANEL_DEFAULT_WIDTH = 300;

interface PanelState {
  lastTraceId: string | null;
  panelOpen: boolean;
  panelWidth: number;
}

function loadPanelState(): PanelState {
  try {
    const traceId = localStorage.getItem(STORAGE_KEY_TRACE_ID) || null;
    const panelOpen = localStorage.getItem(STORAGE_KEY_PANEL_OPEN) !== "false"; // default open
    const rawWidth = localStorage.getItem(STORAGE_KEY_PANEL_WIDTH);
    const panelWidth = rawWidth
      ? Math.min(PANEL_MAX_WIDTH, Math.max(PANEL_MIN_WIDTH, Number(rawWidth)))
      : PANEL_DEFAULT_WIDTH;
    return { lastTraceId: traceId, panelOpen, panelWidth };
  } catch {
    return { lastTraceId: null, panelOpen: true, panelWidth: PANEL_DEFAULT_WIDTH };
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

export function setActivityPanelWidth(width: number) {
  const clamped = Math.min(PANEL_MAX_WIDTH, Math.max(PANEL_MIN_WIDTH, width));
  currentPanel = { ...currentPanel, panelWidth: clamped };
  try {
    localStorage.setItem(STORAGE_KEY_PANEL_WIDTH, String(clamped));
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
