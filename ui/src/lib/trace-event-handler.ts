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
  DelegationMessage,
} from "@/lib/agent-activity-store";
import { agentLabel } from "@/lib/agent-registry";

/** Trace event shape from the SSE stream (subset of StreamChunk). */
export interface TraceEventChunk {
  type: "trace";
  agent?: string;
  event: string;
  tool?: string;
  tool_args?: string;
  tool_result?: string;
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
 * Helper: remove all edges targeting a specific agent.
 * Used when an agent finishes so its incoming edges deactivate.
 */
function removeEdgesTo(
  edges: [string, string][],
  agent: string,
): [string, string][] {
  return edges.filter(([, b]) => b !== agent);
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
  const agent = event.agent || "unknown";

  // Build a timeline entry for every event
  const entry: LiveTimelineEntry = {
    agent,
    event: event.event,
    tool: event.tool,
    toolArgs: event.tool_args,
    toolResult: event.tool_result,
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

      // Aether is always visible and firing during an active workflow
      newSeen = addAgentSeen(newSeen, "aether");
      newStates["aether"] = "firing";

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

      // Deactivate edges targeting the finished agent so they
      // fade back to the dim "dormant pathway" state.
      const newEdges = removeEdgesTo(current.activeEdges, agent);

      setActivity({
        isActive: true,
        activeAgent: "architect",
        delegatingTo: null,
        agentStates: newStates,
        activeEdges: newEdges,
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
        activeEdges: [],  // Clear all edges on completion
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

// ─── Narrative Feed ──────────────────────────────────────────────────────────

/** A single entry in the narrative feed (merged events + delegations). */
export interface NarrativeFeedEntry {
  ts: number;
  /** Human-readable description of what happened. */
  description: string;
  /** Optional secondary line (e.g., delegation content, tool name). */
  detail?: string;
  /** Agent colour class for the primary agent. */
  agentColor: string;
  /** Icon character. */
  icon: string;
  /** Entry kind for styling. */
  kind: "start" | "end" | "tool" | "delegation" | "complete";
}

const NARRATIVE_ICONS: Record<string, string> = {
  start: "⚡",
  end: "✓",
  tool_call: "🔧",
  tool_result: "✔",
  complete: "✅",
  delegation: "→",
};

/**
 * Convert raw events + delegation messages into a unified narrative feed.
 *
 * The descriptions are human-readable sentences instead of raw event types.
 */
export function buildNarrativeFeed(
  timeline: LiveTimelineEntry[],
  delegations: DelegationMessage[],
): NarrativeFeedEntry[] {
  const entries: NarrativeFeedEntry[] = [];

  // Track agent start times for duration calculation
  const startTimes = new Map<string, number>();

  for (const ev of timeline) {
    const label = agentLabel(ev.agent);

    switch (ev.event) {
      case "start":
        startTimes.set(ev.agent, ev.ts);
        entries.push({
          ts: ev.ts,
          description: `${label} is analyzing...`,
          agentColor: ev.agent,
          icon: NARRATIVE_ICONS.start,
          kind: "start",
        });
        break;

      case "end": {
        const startTs = startTimes.get(ev.agent);
        const duration = startTs ? ev.ts - startTs : undefined;
        const durationStr = duration ? ` (${duration.toFixed(1)}s)` : "";
        entries.push({
          ts: ev.ts,
          description: `${label} completed${durationStr}`,
          detail: ev.tool,
          agentColor: ev.agent,
          icon: NARRATIVE_ICONS.end,
          kind: "end",
        });
        break;
      }

      case "tool_call": {
        // Show tool args if available (e.g., "get_entity_state(light.kitchen)")
        const toolName = ev.tool ?? "tool";
        const argsStr = ev.toolArgs
          ? `(${ev.toolArgs.length > 80 ? ev.toolArgs.slice(0, 80) + "…" : ev.toolArgs})`
          : "";
        entries.push({
          ts: ev.ts,
          description: `${label} called ${toolName}${argsStr}`,
          agentColor: ev.agent,
          icon: NARRATIVE_ICONS.tool_call,
          kind: "tool",
        });
        break;
      }

      case "tool_result": {
        // Show truncated result summary
        const resultDetail = ev.toolResult
          ? ev.toolResult.length > 100 ? ev.toolResult.slice(0, 100) + "…" : ev.toolResult
          : ev.tool;
        entries.push({
          ts: ev.ts,
          description: `${label} received result`,
          detail: resultDetail,
          agentColor: ev.agent,
          icon: NARRATIVE_ICONS.tool_result,
          kind: "tool",
        });
        break;
      }

      case "complete":
        entries.push({
          ts: ev.ts,
          description: "Workflow complete",
          agentColor: "system",
          icon: NARRATIVE_ICONS.complete,
          kind: "complete",
        });
        break;
    }
  }

  // Merge delegation messages
  for (const del of delegations) {
    const fromLabel = agentLabel(del.from);
    const toLabel = agentLabel(del.to);
    entries.push({
      ts: del.ts,
      description: `${fromLabel} → ${toLabel}`,
      detail: del.content.length > 120 ? del.content.slice(0, 120) + "…" : del.content,
      agentColor: del.from,
      icon: NARRATIVE_ICONS.delegation,
      kind: "delegation",
    });
  }

  // Sort chronologically
  entries.sort((a, b) => a.ts - b.ts);
  return entries;
}
