/**
 * Trace event handler for real-time agent activity updates.
 *
 * Processes SSE trace events from the backend and maps them to
 * AgentActivity state updates for the activity panel.
 */

import type { AgentActivity } from "@/lib/agent-activity-store";

/** Trace event shape from the SSE stream (subset of StreamChunk). */
export interface TraceEventChunk {
  type: "trace";
  agent?: string;
  event: string;
  tool?: string;
  ts?: number;
  agents?: string[];
}

/**
 * Process a single trace event and update agent activity state.
 *
 * @param event - The trace event from the SSE stream
 * @param setActivity - Function to update the agent activity store
 */
export function handleTraceEvent(
  event: TraceEventChunk,
  setActivity: (activity: Partial<AgentActivity>) => void,
): void {
  switch (event.event) {
    case "start": {
      const agent = event.agent || "architect";
      const isDelegated = agent !== "architect";
      setActivity({
        isActive: true,
        activeAgent: agent,
        delegatingTo: isDelegated ? agent : null,
      });
      break;
    }

    case "end": {
      const agent = event.agent || "architect";
      const isDelegated = agent !== "architect";
      if (isDelegated) {
        // Delegated agent finished — return to architect
        setActivity({
          isActive: true,
          activeAgent: "architect",
          delegatingTo: null,
        });
      } else {
        // Architect end — still active until complete
        setActivity({
          isActive: true,
          activeAgent: "architect",
          delegatingTo: null,
        });
      }
      break;
    }

    case "complete": {
      setActivity({
        isActive: true,
        activeAgent: "architect",
        agents: event.agents,
      });
      break;
    }

    case "tool_call":
    case "tool_result": {
      // Keep current agent active, don't change delegation
      setActivity({
        isActive: true,
        activeAgent: event.agent || "architect",
      });
      break;
    }
  }
}
