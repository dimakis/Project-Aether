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

describe("handleTraceEvent", () => {
  let setActivity: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivity = vi.fn();
  });

  it("sets activeAgent on start event", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "start",
      ts: 1000,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
      delegatingTo: null,
    });
  });

  it("sets delegatingTo when a delegated agent starts", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "data_scientist",
      event: "start",
      ts: 1001,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "data_scientist",
      delegatingTo: "data_scientist",
    });
  });

  it("resets delegatingTo when delegated agent ends", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "data_scientist",
      event: "end",
      ts: 1002,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
      delegatingTo: null,
    });
  });

  it("keeps architect as activeAgent when architect ends", () => {
    // Architect end just means flow is returning, not that it's done
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "end",
      ts: 1003,
    };

    handleTraceEvent(event, setActivity);

    // Architect end doesn't change activity — still active until complete
    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
      delegatingTo: null,
    });
  });

  it("sets agents on complete event", () => {
    const event: TraceEventChunk = {
      type: "trace",
      event: "complete",
      agents: ["architect", "data_scientist"],
      ts: 1004,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
      agents: ["architect", "data_scientist"],
    });
  });

  it("handles tool_call event under current agent", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "tool_call",
      tool: "get_entity_state",
      ts: 1005,
    };

    handleTraceEvent(event, setActivity);

    // tool_call doesn't change the active agent
    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
    });
  });

  it("handles tool_call under delegated agent", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "data_scientist",
      event: "tool_call",
      tool: "analyze_energy",
      ts: 1006,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "data_scientist",
    });
  });

  it("handles system agent start", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "system",
      event: "start",
      ts: 1007,
    };

    handleTraceEvent(event, setActivity);

    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "system",
      delegatingTo: "system",
    });
  });

  it("handles tool_result event (no agent change)", () => {
    const event: TraceEventChunk = {
      type: "trace",
      agent: "architect",
      event: "tool_result",
      ts: 1008,
    };

    handleTraceEvent(event, setActivity);

    // tool_result keeps current agent
    expect(setActivity).toHaveBeenCalledWith({
      isActive: true,
      activeAgent: "architect",
    });
  });
});
