/**
 * Unit tests for the registry-store module.
 *
 * The store uses module-level state + useSyncExternalStore, so tests
 * exercise the imperative setters and verify snapshot changes.
 */
import { describe, it, expect, beforeEach } from "vitest";

import {
  getRegistrySnapshot,
  setActiveTab,
  setSearchQuery,
  setEntityContext,
  setTriggerMessage,
  updateMessages,
  setDelegationMsgs,
  setSubmittedEdit,
  clearSubmittedEdit,
  clearRegistryState,
  subscribeRegistry,
} from "../registry-store";

describe("registry-store", () => {
  beforeEach(() => {
    clearRegistryState();
  });

  // ─── activeTab ───────────────────────────────────────────────────────

  it("defaults activeTab to 'overview'", () => {
    const s = getRegistrySnapshot();
    expect(s.activeTab).toBe("overview");
  });

  it("setActiveTab updates the snapshot", () => {
    setActiveTab("automations");
    expect(getRegistrySnapshot().activeTab).toBe("automations");
  });

  // ─── searchQuery ─────────────────────────────────────────────────────

  it("defaults searchQuery to empty string", () => {
    expect(getRegistrySnapshot().searchQuery).toBe("");
  });

  it("setSearchQuery updates the snapshot", () => {
    setSearchQuery("kitchen");
    expect(getRegistrySnapshot().searchQuery).toBe("kitchen");
  });

  // ─── entityContext ───────────────────────────────────────────────────

  it("defaults entityContext to null", () => {
    expect(getRegistrySnapshot().entityContext).toBeNull();
  });

  it("setEntityContext sets and clears context", () => {
    const ctx = {
      entityId: "automation.sunset",
      entityType: "automation" as const,
      label: "Sunset",
      configYaml: "alias: Sunset\n",
    };
    setEntityContext(ctx);
    expect(getRegistrySnapshot().entityContext).toEqual(ctx);

    setEntityContext(null);
    expect(getRegistrySnapshot().entityContext).toBeNull();
  });

  // ─── triggerMessage ──────────────────────────────────────────────────

  it("defaults triggerMessage to null", () => {
    expect(getRegistrySnapshot().triggerMessage).toBeNull();
  });

  it("setTriggerMessage updates the snapshot", () => {
    setTriggerMessage("Review automation.sunset");
    expect(getRegistrySnapshot().triggerMessage).toBe("Review automation.sunset");
  });

  // ─── messages ────────────────────────────────────────────────────────

  it("defaults messages to empty array", () => {
    expect(getRegistrySnapshot().messages).toEqual([]);
  });

  it("updateMessages applies an updater function", () => {
    updateMessages((prev) => [
      ...prev,
      { role: "user", content: "Hello" },
    ]);
    const msgs = getRegistrySnapshot().messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].content).toBe("Hello");
  });

  it("updateMessages appends to existing messages", () => {
    updateMessages(() => [{ role: "user", content: "First" }]);
    updateMessages((prev) => [...prev, { role: "assistant", content: "Second" }]);
    expect(getRegistrySnapshot().messages).toHaveLength(2);
  });

  // ─── delegationMsgs ─────────────────────────────────────────────────

  it("defaults delegationMsgs to empty array", () => {
    expect(getRegistrySnapshot().delegationMsgs).toEqual([]);
  });

  it("setDelegationMsgs replaces the array", () => {
    const msgs = [{ from: "architect", to: "energy", content: "Analyze", ts: 1 }];
    setDelegationMsgs(msgs);
    expect(getRegistrySnapshot().delegationMsgs).toEqual(msgs);
  });

  // ─── submittedEdits ──────────────────────────────────────────────────

  it("defaults submittedEdits to empty object", () => {
    expect(getRegistrySnapshot().submittedEdits).toEqual({});
  });

  it("setSubmittedEdit stores YAML keyed by entity ID", () => {
    setSubmittedEdit("automation.sunset", "alias: New Sunset\n");
    expect(getRegistrySnapshot().submittedEdits["automation.sunset"]).toBe(
      "alias: New Sunset\n",
    );
  });

  it("clearSubmittedEdit removes a single entity's edit", () => {
    setSubmittedEdit("automation.a", "yaml-a");
    setSubmittedEdit("automation.b", "yaml-b");
    clearSubmittedEdit("automation.a");

    const edits = getRegistrySnapshot().submittedEdits;
    expect(edits["automation.a"]).toBeUndefined();
    expect(edits["automation.b"]).toBe("yaml-b");
  });

  // ─── clearRegistryState ──────────────────────────────────────────────

  it("clearRegistryState resets everything to defaults", () => {
    setActiveTab("scripts");
    setSearchQuery("test");
    setEntityContext({ entityId: "x", entityType: "script", label: "X" });
    setTriggerMessage("go");
    updateMessages(() => [{ role: "user", content: "hi" }]);
    setDelegationMsgs([{ from: "a", to: "b", content: "c", ts: 1 }]);
    setSubmittedEdit("automation.foo", "yaml");

    clearRegistryState();

    const s = getRegistrySnapshot();
    expect(s.activeTab).toBe("overview");
    expect(s.searchQuery).toBe("");
    expect(s.entityContext).toBeNull();
    expect(s.triggerMessage).toBeNull();
    expect(s.messages).toEqual([]);
    expect(s.delegationMsgs).toEqual([]);
    expect(s.submittedEdits).toEqual({});
  });

  // ─── Listener notification ───────────────────────────────────────────

  it("notifies listeners on state change", () => {
    let notified = false;
    const unsub = subscribeRegistry(() => {
      notified = true;
    });

    setActiveTab("scenes");
    expect(notified).toBe(true);

    unsub();
  });

  it("unsubscribed listeners are not notified", () => {
    let count = 0;
    const unsub = subscribeRegistry(() => {
      count++;
    });

    setActiveTab("scripts");
    expect(count).toBe(1);

    unsub();

    setActiveTab("automations");
    expect(count).toBe(1); // still 1 — not notified after unsub
  });
});
