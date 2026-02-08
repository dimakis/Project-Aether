import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Brain, ChevronDown, Loader2, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentTopology, ALL_TOPOLOGY_AGENTS } from "./agent-topology";
import { TraceTimeline } from "./trace-timeline";
import {
  useAgentActivity,
  useActivityPanel,
  setActivityPanelOpen,
} from "@/lib/agent-activity-store";
import type { LiveTimelineEntry } from "@/lib/agent-activity-store";
import { useTraceSpans } from "@/api/hooks";

// ─── Agent colours (mirrors topology) ────────────────────────────────────────

const AGENT_COLORS: Record<string, string> = {
  architect: "text-blue-400",
  data_scientist: "text-emerald-400",
  data_science_team: "text-emerald-400",
  energy_analyst: "text-yellow-400",
  behavioral_analyst: "text-teal-400",
  diagnostic_analyst: "text-rose-400",
  dashboard_designer: "text-indigo-400",
  sandbox: "text-orange-400",
  librarian: "text-purple-400",
  developer: "text-amber-400",
  system: "text-muted-foreground",
};

const EVENT_LABELS: Record<string, string> = {
  start: "activated",
  end: "finished",
  tool_call: "tool",
  tool_result: "result",
  complete: "done",
};

const EVENT_ICONS: Record<string, string> = {
  start: "\u26A1",   // ⚡
  end: "\u2713",     // ✓
  tool_call: "\uD83D\uDD27", // 🔧
  tool_result: "\u2714",     // ✔
  complete: "\u2705", // ✅
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function friendlyAgent(agent: string): string {
  return agent
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Thinking Box ─────────────────────────────────────────────────────────────

/**
 * Condensed thinking stream box.
 * Shows 3-5 lines by default, expandable to full content.
 */
function ThinkingBox({ content, isActive }: { content: string; isActive: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when new content arrives and not expanded
  useEffect(() => {
    if (!expanded && boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [content, expanded]);

  if (!content && !isActive) return null;

  return (
    <div className="rounded-lg border border-border/40 bg-muted/20">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs"
      >
        <Brain
          className={cn(
            "h-3.5 w-3.5",
            isActive ? "animate-pulse text-primary" : "text-muted-foreground",
          )}
        />
        <span className="font-medium text-muted-foreground">
          {isActive ? "Reasoning..." : "Thought process"}
        </span>
        <motion.span
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.15 }}
          className="ml-auto"
        >
          <ChevronDown className="h-3 w-3 text-muted-foreground/50" />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {content && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div
              ref={boxRef}
              className={cn(
                "overflow-auto border-t border-border/20 px-3 py-2",
                expanded ? "max-h-80" : "max-h-[4.5rem]",
              )}
            >
              <pre
                className={cn(
                  "whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-muted-foreground/70",
                  !expanded && "line-clamp-4",
                )}
              >
                {content}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Live Feed ───────────────────────────────────────────────────────────────

function LiveEventFeed({ entries }: { entries: LiveTimelineEntry[] }) {
  const feedRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest entry
  useEffect(() => {
    const el = feedRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries.length]);

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground/50">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Waiting for activity...</span>
      </div>
    );
  }

  return (
    <div ref={feedRef} className="max-h-48 space-y-0 overflow-y-auto">
      {entries.map((entry, i) => {
        const color = AGENT_COLORS[entry.agent] ?? "text-muted-foreground";
        const icon = EVENT_ICONS[entry.event] ?? "\u2022";
        const label = EVENT_LABELS[entry.event] ?? entry.event;

        return (
          <motion.div
            key={`${entry.ts}-${entry.event}-${i}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-start gap-2 py-1"
          >
            {/* Timestamp */}
            <span className="shrink-0 w-[52px] text-right text-[10px] tabular-nums text-muted-foreground/40">
              {formatTime(entry.ts)}
            </span>

            {/* Icon dot */}
            <div className="relative flex flex-col items-center">
              <span className="text-[9px]">{icon}</span>
              {/* Vertical connector */}
              {i < entries.length - 1 && (
                <div className="absolute top-4 h-full w-px bg-border/30" />
              )}
            </div>

            {/* Description */}
            <div className="min-w-0 flex-1">
              <p className="text-[11px] leading-tight">
                <span className={cn("font-medium", color)}>
                  {friendlyAgent(entry.agent)}
                </span>
                <span className="text-muted-foreground/60"> {label}</span>
              </p>
              {entry.tool && (
                <p className="truncate text-[10px] text-muted-foreground/50">
                  {entry.tool}
                </p>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ─── Main Panel ──────────────────────────────────────────────────────────────

/**
 * System Activity Panel.
 *
 * Default view: Thinking box (persistent) + agent network graph.
 * During streaming: Thinking box + live neural topology + event feed.
 * After streaming: Complete MLflow-based trace timeline.
 */
export function AgentActivityPanel() {
  const activity = useAgentActivity();
  const { lastTraceId, panelOpen } = useActivityPanel();
  const isStreaming = activity.isActive;
  const { data: trace, isLoading } = useTraceSpans(lastTraceId, isStreaming);
  const activeAgent = activity.activeAgent || "architect";

  // During streaming we always have live data; prefer it over MLflow
  const hasLiveData =
    activity.agentsSeen.length > 0 || activity.liveTimeline.length > 0;

  // Build full agent states: agents not yet seen are "dormant"
  const fullAgentStates: Record<string, import("@/lib/agent-activity-store").AgentNodeState> = {};
  for (const agent of ALL_TOPOLOGY_AGENTS) {
    fullAgentStates[agent] = activity.agentStates[agent] ?? "dormant";
  }

  const hasThinking = !!activity.thinkingStream;

  return (
    <AnimatePresence>
      {panelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 300, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="flex h-full flex-col overflow-hidden border-l border-border bg-card/50"
        >
          {/* Header */}
          <div className="flex h-14 items-center justify-between border-b border-border px-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">System Activity</span>
              {isStreaming && (
                <motion.div
                  className="h-2 w-2 rounded-full bg-primary"
                  animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}
            </div>
            <button
              onClick={() => setActivityPanelOpen(false)}
              className="rounded-md p-1 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-3 space-y-3">
            {/* Thinking box — always shown when there is content */}
            {(hasThinking || isStreaming) && (
              <ThinkingBox
                content={activity.thinkingStream}
                isActive={isStreaming}
              />
            )}

            {isStreaming || hasLiveData ? (
              /* ── Live neural view ─────────────────────────────────── */
              <div>
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Neural Activity
                </p>
                <AgentTopology
                  agents={ALL_TOPOLOGY_AGENTS}
                  activeAgent={activeAgent}
                  isLive
                  agentStates={fullAgentStates}
                />

                {/* Divider */}
                <div className="my-3 border-t border-border/50" />

                {/* Live event feed */}
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Live Feed{" "}
                  {activity.liveTimeline.length > 0 && (
                    <span className="font-normal text-muted-foreground/40">
                      ({activity.liveTimeline.length})
                    </span>
                  )}
                </p>
                <LiveEventFeed entries={activity.liveTimeline} />
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground/30" />
              </div>
            ) : trace?.root_span ? (
              /* ── Post-stream MLflow view ──────────────────────────── */
              <div>
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Agent Flow
                </p>
                <AgentTopology
                  agents={trace.agents_involved}
                  activeAgent={null}
                  rootSpan={trace.root_span}
                  isLive={false}
                />

                <div className="my-3 border-t border-border/50" />

                <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Timeline ({trace.span_count} spans,{" "}
                  {(trace.duration_ms / 1000).toFixed(1)}s)
                </p>
                <TraceTimeline
                  rootSpan={trace.root_span}
                  startedAt={trace.started_at}
                  isLive={false}
                />
              </div>
            ) : !hasThinking ? (
              /* ── Default: graph + waiting message ────────────────── */
              <div>
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Agent Network
                </p>
                <AgentTopology
                  agents={ALL_TOPOLOGY_AGENTS}
                  activeAgent={null}
                  isLive={false}
                  agentStates={Object.fromEntries(
                    ALL_TOPOLOGY_AGENTS.map((a) => [a, "dormant" as const]),
                  )}
                />
                <p className="mt-3 text-center text-[10px] text-muted-foreground/40">
                  Send a message to see system activity
                </p>
              </div>
            ) : null}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
