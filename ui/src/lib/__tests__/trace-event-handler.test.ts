/**
 * Unit tests for trace event handling logic.
 *
 * TDD: Verifies that SSE trace events are correctly mapped to
 * AgentActivity state updates for the activity panel.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  handleTraceEvent,
  type TraceEventChunk,
} from "@/lib/trace-event-handler";
import type { AgentActivity, AgentNodeState } from "@/lib/agent-activity-store";

/** Build a fresh default AgentActivity snapshot. */
function defaultActivity(overrides?: Partial<AgentActivity>): AgentActivity {
  return {
    isActive: false,
    activeAgent: null,
    agentsSeen: [],
    agentStates: {},
    liveTimeline: [],
    thinkingStream: "",
    activeEdges: [],
    delegationMessages: [],
    ...overrides,
  };
}

describe("handleTraceEvent", () => {
  let setActivity: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivity = vi.fn();
  });

  // ─── Architect start ─────────────────────────────────────────────────

  it("sets architect as activeAgent on start event", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity, defaultActivity());

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("architect");
    expect(call.delegatingTo).toBeNull();
  });

  it("creates aether → architect edge when architect starts", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity, defaultActivity());

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.activeEdges).toEqual(
      expect.arrayContaining([["aether", "architect"]]),
    );
  });

  it("sets aether to firing when architect starts", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity, defaultActivity());

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.agentStates?.aether).toBe("firing");
    expect(call.agentStates?.architect).toBe("firing");
  });

  it("includes aether in agentsSeen when architect starts", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity, defaultActivity());

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.agentsSeen).toContain("aether");
    expect(call.agentsSeen).toContain("architect");
  });

  // ─── Delegated agent start ──────────────────────────────────────────

  it("sets delegatingTo when a delegated agent starts", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
      activeEdges: [["aether", "architect"]],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "behavioral_analyst",
      event: "start",
      ts: 1001,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("behavioral_analyst");
    expect(call.delegatingTo).toBe("behavioral_analyst");
  });

  it("sets architect to 'done' (not 'idle') when delegating", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
      activeEdges: [["aether", "architect"]],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "behavioral_analyst",
      event: "start",
      ts: 1001,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.agentStates?.architect).toBe("done");
    // Aether should remain firing
    expect(call.agentStates?.aether).toBe("firing");
  });

  it("creates edge from architect to delegated agent", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
      activeEdges: [["aether", "architect"]],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "behavioral_analyst",
      event: "start",
      ts: 1001,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.activeEdges).toEqual(
      expect.arrayContaining([
        ["aether", "architect"],
        ["architect", "behavioral_analyst"],
      ]),
    );
  });

  // ─── Delegated agent end ────────────────────────────────────────────

  it("resets delegatingTo and resumes architect firing when delegated agent ends", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "behavioral_analyst",
      agentsSeen: ["aether", "architect", "behavioral_analyst"],
      agentStates: {
        aether: "firing",
        architect: "done",
        behavioral_analyst: "firing",
      },
      activeEdges: [["aether", "architect"], ["architect", "behavioral_analyst"]],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "behavioral_analyst",
      event: "end",
      ts: 1002,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("architect");
    expect(call.delegatingTo).toBeNull();
    expect(call.agentStates?.architect).toBe("firing");
    expect(call.agentStates?.behavioral_analyst).toBe("done");
    expect(call.agentStates?.aether).toBe("firing");
  });

  // ─── Architect end ──────────────────────────────────────────────────

  it("keeps architect as activeAgent when architect ends", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "end",
      ts: 1003,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("architect");
    expect(call.delegatingTo).toBeNull();
    // Aether stays firing
    expect(call.agentStates?.aether).toBe("firing");
  });

  // ─── Complete ───────────────────────────────────────────────────────

  it("marks all agents (including aether) as done on complete", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect", "behavioral_analyst"],
      agentStates: {
        aether: "firing",
        architect: "firing",
        behavioral_analyst: "done",
      },
    });

    const event: TraceEventChunk = {
      type: "trace",
      event: "complete",
      agents: ["architect", "behavioral_analyst"],
      ts: 1004,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(false);
    expect(call.activeAgent).toBeNull();
    expect(call.agentStates?.aether).toBe("done");
    expect(call.agentStates?.architect).toBe("done");
    expect(call.agentStates?.behavioral_analyst).toBe("done");
  });

  // ─── Tool events ───────────────────────────────────────────────────

  it("handles tool_call event without changing agent", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
      liveTimeline: [],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "tool_call",
      tool: "get_entity_state",
      ts: 1005,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("architect");
  });

  it("handles tool_result event under delegated agent", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "energy_analyst",
      agentsSeen: ["aether", "architect", "energy_analyst"],
      agentStates: { aether: "firing", architect: "done", energy_analyst: "firing" },
      liveTimeline: [],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "energy_analyst",
      event: "tool_result",
      ts: 1006,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.activeAgent).toBe("energy_analyst");
  });

  // ─── Edge cases ────────────────────────────────────────────────────

  it("handles system agent start with delegation", () => {
    const current = defaultActivity({
      isActive: true,
      activeAgent: "architect",
      agentsSeen: ["aether", "architect"],
      agentStates: { aether: "firing", architect: "firing" },
      activeEdges: [["aether", "architect"]],
    });

    const event: TraceEventChunk = {
      type: "trace",
      agent: "system",
      event: "start",
      ts: 1007,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.isActive).toBe(true);
    expect(call.activeAgent).toBe("system");
    expect(call.delegatingTo).toBe("system");
  });

  it("appends to liveTimeline on every event", () => {
    const current = defaultActivity();
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity, current);

    const call = setActivity.mock.calls[0][0] as Partial<AgentActivity>;
    expect(call.liveTimeline).toHaveLength(1);
    expect(call.liveTimeline![0]).toMatchObject({
      agent: "architect",
      event: "start",
      ts: 1000,
    });
  });
});
