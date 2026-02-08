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
      let newSeen = addAgentSeen(current.agentsSeen, agent);
      const isDelegated = agent !== "architect";

      const newStates: Record<string, AgentNodeState> = {
        ...current.agentStates,
        [agent]: "firing",
      };

      let newEdges = current.activeEdges;

      // Ensure Aether is always visible and has an edge to the architect
      newSeen = addAgentSeen(newSeen, "aether");
      if (!newStates["aether"]) {
        newStates["aether"] = "firing";
      }

      if (agent === "architect") {
        // Architect starting — draw edge from Aether hub
        newEdges = addEdge(newEdges, "aether", "architect");
      } else {
        // Delegated agent starting — architect stays visually active (done)
        // so the user can see it delegated the work, not that it disappeared
        newStates["architect"] = "done";
        // Edge from the current active agent (architect) to the delegate
        const parent = current.activeAgent || "architect";
        newEdges = addEdge(newEdges, parent, agent);
      }

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
      }
      // Aether stays firing while the workflow is active
      newStates["aether"] = "firing";

      setActivity({
        isActive: true,
        activeAgent: "architect",
        delegatingTo: null,
        agentStates: newStates,
        liveTimeline: [...current.liveTimeline, entry],
      });
      break;
    }

    case "complete": {
      // Mark all seen agents (including Aether) as done
      const allSeen = addAgentSeen(current.agentsSeen, "aether");
      const doneStates: Record<string, AgentNodeState> = {};
      for (const a of allSeen) {
        doneStates[a] = "done";
      }

      setActivity({
        isActive: false,
        activeAgent: null,
        delegatingTo: null,
        agents: event.agents,
        agentsSeen: allSeen,
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
