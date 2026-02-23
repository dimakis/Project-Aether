/**
 * Module-level store for HA registry page state.
 *
 * Follows the same pattern as agent-activity-store.ts:
 * module-level variables survive SPA navigation (React component unmounts)
 * but are cleared on full page refresh.
 *
 * Uses useSyncExternalStore for React 18+ compatibility.
 *
 * Used by:
 * - RegistryPage: activeTab, searchQuery, entityContext, triggerMessage
 * - InlineAssistant (on registry page): messages, delegationMsgs
 * - AutomationDetail / ScriptDetail / SceneDetail: submittedEdits
 */

import { useSyncExternalStore } from "react";
import type { EntityContext } from "./types";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface InlineMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export interface DelegationMsg {
  from: string;
  to: string;
  content: string;
  ts: number;
}

export type TabKey =
  | "overview"
  | "automations"
  | "scripts"
  | "scenes"
  | "services"
  | "helpers";

export interface RegistryState {
  // Page-level
  activeTab: TabKey;
  searchQuery: string;
  entityContext: EntityContext | null;
  triggerMessage: string | null;

  // InlineAssistant chat
  messages: InlineMessage[];
  delegationMsgs: DelegationMsg[];

  // Per-entity submitted YAML edits (keyed by entity_id)
  submittedEdits: Record<string, string>;
}

// ─── Defaults ───────────────────────────────────────────────────────────────

const DEFAULT_STATE: RegistryState = {
  activeTab: "overview",
  searchQuery: "",
  entityContext: null,
  triggerMessage: null,
  messages: [],
  delegationMsgs: [],
  submittedEdits: {},
};

// ─── Module-level state ─────────────────────────────────────────────────────

let current: RegistryState = { ...DEFAULT_STATE };
const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

// ─── Setters ────────────────────────────────────────────────────────────────

export function setActiveTab(tab: TabKey): void {
  current = { ...current, activeTab: tab };
  notify();
}

export function setSearchQuery(query: string): void {
  current = { ...current, searchQuery: query };
  notify();
}

export function setEntityContext(ctx: EntityContext | null): void {
  current = { ...current, entityContext: ctx };
  notify();
}

export function setTriggerMessage(msg: string | null): void {
  current = { ...current, triggerMessage: msg };
  notify();
}

export function setMessages(msgs: InlineMessage[]): void {
  current = { ...current, messages: msgs };
  notify();
}

export function updateMessages(
  updater: (prev: InlineMessage[]) => InlineMessage[],
): void {
  current = { ...current, messages: updater(current.messages) };
  notify();
}

export function setDelegationMsgs(
  msgs: DelegationMsg[] | ((prev: DelegationMsg[]) => DelegationMsg[]),
): void {
  const next = typeof msgs === "function" ? msgs(current.delegationMsgs) : msgs;
  current = { ...current, delegationMsgs: next };
  notify();
}

export function setSubmittedEdit(entityId: string, yaml: string): void {
  current = {
    ...current,
    submittedEdits: { ...current.submittedEdits, [entityId]: yaml },
  };
  notify();
}

export function clearSubmittedEdit(entityId: string): void {
  const { [entityId]: _, ...rest } = current.submittedEdits;
  current = { ...current, submittedEdits: rest };
  notify();
}

export function clearRegistryState(): void {
  current = { ...DEFAULT_STATE, submittedEdits: {} };
  notify();
}

// ─── Subscribe / snapshot (useSyncExternalStore) ────────────────────────────

export function subscribeRegistry(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getRegistrySnapshot(): RegistryState {
  return current;
}

/** React hook to read the full registry state. */
export function useRegistryState(): RegistryState {
  return useSyncExternalStore(
    subscribeRegistry,
    getRegistrySnapshot,
    getRegistrySnapshot,
  );
}
