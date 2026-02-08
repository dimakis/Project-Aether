import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Brain, ChevronDown, Loader2, Cpu, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentTopology, ALL_TOPOLOGY_AGENTS } from "./agent-topology";
import { TraceTimeline } from "./trace-timeline";
import {
  useAgentActivity,
  useActivityPanel,
  setActivityPanelOpen,
} from "@/lib/agent-activity-store";
import type { LiveTimelineEntry, DelegationMessage } from "@/lib/agent-activity-store";
import { useTraceSpans } from "@/api/hooks";

// ─── Agent colours ───────────────────────────────────────────────────────────

const AGENT_COLORS: Record<string, string> = {
  aether: "text-primary",
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
  start: "\u26A1",
  end: "\u2713",
  tool_call: "\uD83D\uDD27",
  tool_result: "\u2714",
  complete: "\u2705",
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

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ─── Thinking Box ─────────────────────────────────────────────────────────────

function ThinkingBox({ content, isActive }: { content: string; isActive: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on every content change while streaming
  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [content]);

  if (!content && !isActive) return null;

  const wordCount = content ? content.split(/\s+/).filter(Boolean).length : 0;

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
        {wordCount > 0 && (
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px] tabular-nums text-muted-foreground/50">
            {wordCount}w
          </span>
        )}
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
                expanded ? "max-h-80" : "max-h-20",
              )}
            >
              <pre
                className={cn(
                  "whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-muted-foreground/70",
                  !expanded && "line-clamp-5",
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

// ─── Last Session Summary Card ───────────────────────────────────────────────

function LastSessionCard({
  trace,
  onExpand,
  isExpanded,
}: {
  trace: {
    agents_involved: string[];
    span_count: number;
    duration_ms: number;
    started_at: string | null;
    root_span: unknown;
  };
  onExpand: () => void;
  isExpanded: boolean;
}) {
  const ago = trace.started_at ? timeAgo(trace.started_at) : "unknown";

  return (
    <div className="rounded-lg border border-border/40 bg-muted/20">
      <button
        onClick={onExpand}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs"
      >
        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-medium text-muted-foreground">
          Last session
        </span>
        <span className="text-muted-foreground/50">
          {trace.span_count} spans, {(trace.duration_ms / 1000).toFixed(1)}s
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/40">
          {ago}
        </span>
        <motion.span
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.15 }}
        >
          <ChevronDown className="h-3 w-3 text-muted-foreground/50" />
        </motion.span>
      </button>
    </div>
  );
}

// ─── Live Feed ───────────────────────────────────────────────────────────────

function LiveEventFeed({
  entries,
  delegationMessages = [],
}: {
  entries: LiveTimelineEntry[];
  delegationMessages?: DelegationMessage[];
}) {
  const feedRef = useRef<HTMLDivElement>(null);
  const [expandedDelegation, setExpandedDelegation] = useState<number | null>(null);

  const totalCount = entries.length + delegationMessages.length;

  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [totalCount]);

  if (entries.length === 0 && delegationMessages.length === 0) {
    return (
      <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground/50">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Waiting for activity...</span>
      </div>
    );
  }

  // Merge timeline entries and delegation messages, sorted by timestamp
  type FeedItem =
    | { kind: "event"; entry: LiveTimelineEntry; ts: number }
    | { kind: "delegation"; msg: DelegationMessage; idx: number; ts: number };

  const items: FeedItem[] = [
    ...entries.map((entry): FeedItem => ({ kind: "event", entry, ts: entry.ts })),
    ...delegationMessages.map((msg, idx): FeedItem => ({ kind: "delegation", msg, idx, ts: msg.ts })),
  ].sort((a, b) => a.ts - b.ts);

  return (
    <div ref={feedRef} className="max-h-48 space-y-0 overflow-y-auto">
      {items.map((item, i) => {
        if (item.kind === "event") {
          const entry = item.entry;
          const color = AGENT_COLORS[entry.agent] ?? "text-muted-foreground";
          const icon = EVENT_ICONS[entry.event] ?? "\u2022";
          const label = EVENT_LABELS[entry.event] ?? entry.event;

          return (
            <motion.div
              key={`ev-${entry.ts}-${entry.event}-${i}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-start gap-2 py-1"
            >
              <span className="shrink-0 w-[52px] text-right text-[10px] tabular-nums text-muted-foreground/40">
                {formatTime(entry.ts)}
              </span>
              <div className="relative flex flex-col items-center">
                <span className="text-[9px]">{icon}</span>
                {i < items.length - 1 && (
                  <div className="absolute top-4 h-full w-px bg-border/30" />
                )}
              </div>
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
        }

        // Delegation message
        const { msg, idx } = item;
        const fromColor = AGENT_COLORS[msg.from] ?? "text-muted-foreground";
        const toColor = AGENT_COLORS[msg.to] ?? "text-muted-foreground";
        const isExpanded = expandedDelegation === idx;
        const preview = msg.content.length > 80 ? msg.content.slice(0, 80) + "..." : msg.content;

        return (
          <motion.div
            key={`del-${msg.ts}-${idx}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-start gap-2 py-1"
          >
            <span className="shrink-0 w-[52px] text-right text-[10px] tabular-nums text-muted-foreground/40">
              {formatTime(msg.ts)}
            </span>
            <div className="relative flex flex-col items-center">
              <span className="text-[9px]">{"\u2709"}</span>
              {i < items.length - 1 && (
                <div className="absolute top-4 h-full w-px bg-border/30" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <button
                onClick={() => setExpandedDelegation(isExpanded ? null : idx)}
                className="w-full text-left"
              >
                <p className="text-[11px] leading-tight">
                  <span className={cn("font-medium", fromColor)}>
                    {friendlyAgent(msg.from)}
                  </span>
                  <span className="text-muted-foreground/60"> {"\u2192"} </span>
                  <span className={cn("font-medium", toColor)}>
                    {friendlyAgent(msg.to)}
                  </span>
                </p>
                <p className="text-[10px] text-muted-foreground/50">
                  {isExpanded ? msg.content : preview}
                </p>
              </button>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ─── Main Panel ──────────────────────────────────────────────────────────────

export function AgentActivityPanel() {
  const activity = useAgentActivity();
  const { lastTraceId, panelOpen } = useActivityPanel();
  const isStreaming = activity.isActive;
  const { data: trace, isLoading } = useTraceSpans(lastTraceId, isStreaming);
  const activeAgent = activity.activeAgent || "architect";
  const [traceExpanded, setTraceExpanded] = useState(false);

  const hasLiveData =
    activity.agentsSeen.length > 0 || activity.liveTimeline.length > 0;

  // Build full agent states: unseen agents are "dormant"
  const fullAgentStates = useMemo(() => {
    const states: Record<string, import("@/lib/agent-activity-store").AgentNodeState> = {};
    for (const agent of ALL_TOPOLOGY_AGENTS) {
      states[agent] = activity.agentStates[agent] ?? "dormant";
    }
    return states;
  }, [activity.agentStates]);

  const hasThinking = !!activity.thinkingStream;

  // Is the last trace stale (>24h old)?
  const traceIsStale = useMemo(() => {
    if (!trace?.started_at) return true;
    const age = Date.now() - new Date(trace.started_at).getTime();
    return age > 24 * 60 * 60 * 1000;
  }, [trace?.started_at]);

  // Collapse trace details when a new stream starts
  useEffect(() => {
    if (isStreaming) setTraceExpanded(false);
  }, [isStreaming]);

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
            {/* Thinking box */}
            {(hasThinking || isStreaming) && (
              <ThinkingBox
                content={activity.thinkingStream}
                isActive={isStreaming}
              />
            )}

            {/* ── Neural graph — ALWAYS rendered ─────────────────── */}
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                {isStreaming || hasLiveData ? "Neural Activity" : "Agent Network"}
              </p>
              <AgentTopology
                agents={ALL_TOPOLOGY_AGENTS}
                activeAgent={isStreaming ? activeAgent : null}
                isLive={isStreaming || hasLiveData}
                agentStates={
                  isStreaming || hasLiveData
                    ? fullAgentStates
                    : Object.fromEntries(
                        ALL_TOPOLOGY_AGENTS.map((a) => [a, "dormant" as const]),
                      )
                }
                activeEdges={
                  isStreaming || hasLiveData
                    ? activity.activeEdges
                    : undefined
                }
              />
            </div>

            {/* ── Live feed (during streaming) ───────────────────── */}
            {(isStreaming || hasLiveData) && (
              <div>
                <div className="my-2 border-t border-border/50" />
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Live Feed{" "}
                  {activity.liveTimeline.length > 0 && (
                    <span className="font-normal text-muted-foreground/40">
                      ({activity.liveTimeline.length})
                    </span>
                  )}
                </p>
                <LiveEventFeed
                  entries={activity.liveTimeline}
                  delegationMessages={activity.delegationMessages}
                />
              </div>
            )}

            {/* ── Post-stream: compact last session summary ──────── */}
            {!isStreaming && !hasLiveData && trace?.root_span && !traceIsStale && (
              <div>
                <LastSessionCard
                  trace={trace}
                  onExpand={() => setTraceExpanded(!traceExpanded)}
                  isExpanded={traceExpanded}
                />
                <AnimatePresence>
                  {traceExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 space-y-2">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                          Timeline ({trace.span_count} spans,{" "}
                          {(trace.duration_ms / 1000).toFixed(1)}s)
                        </p>
                        <TraceTimeline
                          rootSpan={trace.root_span}
                          startedAt={trace.started_at}
                          isLive={false}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Loading state */}
            {!isStreaming && !hasLiveData && isLoading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/30" />
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
