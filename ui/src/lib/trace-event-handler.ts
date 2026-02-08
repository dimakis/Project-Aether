/**
 * Trace event handler for real-time agent activity updates.
 *
 * Processes SSE trace events from the backend and maps them to
 * AgentActivity state updates for the activity panel — driving
 * the "neural activity" visualisation.
 */

import type {
  AgentActivity,
  AgentNodeState,
  LiveTimelineEntry,
} from "@/lib/agent-activity-store";

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
 * Helper: add an agent to agentsSeen if not already present and
 * return the updated array (or the original if unchanged).
 */
function addAgentSeen(seen: string[], agent: string): string[] {
  if (seen.includes(agent)) return seen;
  return [...seen, agent];
}

/**
 * Helper: add an edge [from, to] to activeEdges if not already present.
 */
function addEdge(
  edges: [string, string][],
  from: string,
  to: string,
): [string, string][] {
  if (edges.some(([a, b]) => a === from && b === to)) return edges;
  return [...edges, [from, to]];
}

/**
 * Process a single trace event and return the partial AgentActivity update.
 *
 * Pure function — all state changes are expressed as a Partial<AgentActivity>
 * that the caller passes to setAgentActivity.
 */
export function handleTraceEvent(
  event: TraceEventChunk,
  setActivity: (activity: Partial<AgentActivity>) => void,
  current: AgentActivity,
): void {
  const ts = event.ts ?? Date.now() / 1000;
  const agent = event.agent || "architect";

  // Build a timeline entry for every event
  const entry: LiveTimelineEntry = {
    agent,
    event: event.event,
    tool: event.tool,
    ts,
  };

  switch (event.event) {
    case "start": {
      const newSeen = addAgentSeen(current.agentsSeen, agent);
      const isDelegated = agent !== "architect";

      // When a delegated agent starts, set architect to idle
      const newStates: Record<string, AgentNodeState> = {
        ...current.agentStates,
        [agent]: "firing",
      };
      if (isDelegated) {
        newStates["architect"] = "idle";
      }

      // Build edge from the current active agent to the newly started agent
      const parent = current.activeAgent || "architect";
      const newEdges =
        parent !== agent
          ? addEdge(current.activeEdges, parent, agent)
          : current.activeEdges;

      setActivity({
        isActive: true,
        activeAgent: agent,
        delegatingTo: isDelegated ? agent : null,
        agentsSeen: newSeen,
        agentStates: newStates,
        activeEdges: newEdges,
        liveTimeline: [...current.liveTimeline, entry],
      });
      break;
    }

    case "end": {
      const isDelegated = agent !== "architect";
      const newStates: Record<string, AgentNodeState> = {
        ...current.agentStates,
        [agent]: "done",
      };

      if (isDelegated) {
        // Delegated agent finished — architect resumes firing
        newStates["architect"] = "firing";
        setActivity({
          isActive: true,
          activeAgent: "architect",
          delegatingTo: null,
          agentStates: newStates,
          liveTimeline: [...current.liveTimeline, entry],
        });
      } else {
        // Architect end — still active until complete
        setActivity({
          isActive: true,
          activeAgent: "architect",
          delegatingTo: null,
          agentStates: newStates,
          liveTimeline: [...current.liveTimeline, entry],
        });
      }
      break;
    }

    case "complete": {
      // Mark all seen agents as done
      const doneStates: Record<string, AgentNodeState> = {};
      for (const a of current.agentsSeen) {
        doneStates[a] = "done";
      }

      setActivity({
        isActive: false,
        activeAgent: null,
        delegatingTo: null,
        agents: event.agents,
        agentStates: doneStates,
        liveTimeline: [...current.liveTimeline, entry],
      });
      break;
    }

    case "tool_call":
    case "tool_result": {
      // Keep current agent firing, just append to the timeline
      setActivity({
        isActive: true,
        activeAgent: agent,
        liveTimeline: [...current.liveTimeline, entry],
      });
      break;
    }
  }
}
