import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Brain, ChevronDown, Loader2, Cpu, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentTopology } from "./agent-topology";
import { TOPOLOGY_AGENT_IDS, agentColor } from "@/lib/agent-registry";
import { TraceTimeline } from "./trace-timeline";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import {
  useAgentActivity,
  useActivityPanel,
  setActivityPanelOpen,
} from "@/lib/agent-activity-store";
import { buildNarrativeFeed, type NarrativeFeedEntry } from "@/lib/trace-event-handler";
import { useTraceSpans } from "@/api/hooks";

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
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

// ─── Smart Auto-Scroll ───────────────────────────────────────────────────────

/** Only auto-scroll if the user is already near the bottom of the container. */
function useSmartAutoScroll(dep: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  const isNearBottom = useRef(true);

  const onScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const threshold = 30; // px from bottom
    isNearBottom.current =
      el.scrollTop + el.clientHeight >= el.scrollHeight - threshold;
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (el && isNearBottom.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [dep]);

  return { ref, onScroll };
}

// ─── Thinking Box ─────────────────────────────────────────────────────────────

function ThinkingBox({ content, isActive }: { content: string; isActive: boolean }) {
  // Expanded by default while streaming; collapses to summary after completion
  const [collapsed, setCollapsed] = useState(false);
  const { ref: boxRef, onScroll } = useSmartAutoScroll(content);

  if (!content && !isActive) return null;

  const wordCount = content ? content.split(/\s+/).filter(Boolean).length : 0;
  // Show expanded when actively streaming (unless user manually collapsed)
  const isOpen = isActive ? !collapsed : !collapsed && !!content;

  return (
    <div className="rounded-lg border border-border/40 bg-muted/20">
      <button
        onClick={() => setCollapsed(!collapsed)}
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
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground/50">
            {wordCount} words
          </span>
        )}
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.15 }}
          className="ml-auto"
        >
          <ChevronDown className="h-3 w-3 text-muted-foreground/50" />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && content && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div
              ref={boxRef}
              onScroll={onScroll}
              className="max-h-48 overflow-auto border-t border-border/20 px-3 py-2"
            >
              <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted-foreground/70">
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

// ─── Narrative Feed ──────────────────────────────────────────────────────────

function NarrativeFeed({ entries }: { entries: NarrativeFeedEntry[] }) {
  const { ref: feedRef, onScroll } = useSmartAutoScroll(entries.length);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground/50">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Waiting for activity...</span>
      </div>
    );
  }

  return (
    <div ref={feedRef} onScroll={onScroll} className="max-h-48 space-y-0 overflow-y-auto">
      {entries.map((entry, i) => {
        const color = agentColor(entry.agentColor);
        const isExpanded = expandedIdx === i;

        return (
          <motion.div
            key={`${entry.ts}-${entry.kind}-${i}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-start gap-2 py-1"
          >
            <span className="shrink-0 w-[52px] text-right text-[10px] tabular-nums text-muted-foreground/40">
              {formatTime(entry.ts)}
            </span>
            <div className="relative flex flex-col items-center">
              <span className="text-[9px]">{entry.icon}</span>
              {i < entries.length - 1 && (
                <div className="absolute top-4 h-full w-px bg-border/30" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              {entry.detail ? (
                <button
                  onClick={() => setExpandedIdx(isExpanded ? null : i)}
                  className="w-full text-left"
                >
                  <p className={cn("text-[11px] leading-tight", color)}>
                    {entry.description}
                  </p>
                  {entry.detail && (
                    <p className={cn(
                      "text-[10px] text-muted-foreground/50",
                      !isExpanded && "truncate",
                    )}>
                      {isExpanded
                        ? entry.detail
                        : entry.detail.length > 80
                          ? entry.detail.slice(0, 80) + "..."
                          : entry.detail}
                    </p>
                  )}
                </button>
              ) : (
                <p className={cn("text-[11px] leading-tight", color)}>
                  {entry.description}
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

export function AgentActivityPanel() {
  const activity = useAgentActivity();
  const { lastTraceId, panelOpen } = useActivityPanel();
  const isStreaming = activity.isActive;
  // Don't poll during streaming — the backend builds the trace after the
  // workflow completes, so polling mid-stream just gets 404s.
  const { data: trace, isLoading } = useTraceSpans(lastTraceId, false);
  const activeAgent = activity.activeAgent || "architect";
  const [traceExpanded, setTraceExpanded] = useState(false);

  const hasLiveData =
    activity.agentsSeen.length > 0 || activity.liveTimeline.length > 0;

  // Build full agent states: unseen agents are "dormant"
  const fullAgentStates = useMemo(() => {
    const states: Record<string, import("@/lib/agent-activity-store").AgentNodeState> = {};
    for (const agent of TOPOLOGY_AGENT_IDS) {
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

  // Build narrative feed from raw events + delegation messages
  const narrativeFeed = useMemo(
    () => buildNarrativeFeed(activity.liveTimeline, activity.delegationMessages),
    [activity.liveTimeline, activity.delegationMessages],
  );

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
            {/* ── Neural graph — ALWAYS rendered ─────────────────── */}
            <ErrorBoundary fallback="Topology unavailable">
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                {isStreaming || hasLiveData ? "Neural Activity" : "Agent Network"}
              </p>
              <AgentTopology
                agents={TOPOLOGY_AGENT_IDS}
                activeAgent={isStreaming ? activeAgent : null}
                isLive={isStreaming || hasLiveData}
                agentStates={
                  isStreaming || hasLiveData
                    ? fullAgentStates
                    : Object.fromEntries(
                        TOPOLOGY_AGENT_IDS.map((a) => [a, "dormant" as const]),
                      )
                }
                activeEdges={
                  isStreaming || hasLiveData
                    ? activity.activeEdges
                    : undefined
                }
              />
            </div>
            </ErrorBoundary>

            {/* ── Thinking box (below topology, above feed) ──────── */}
            {(hasThinking || isStreaming) && (
              <ErrorBoundary fallback="Thinking stream unavailable">
                <ThinkingBox
                  content={activity.thinkingStream}
                  isActive={isStreaming}
                />
              </ErrorBoundary>
            )}

            {/* ── Live feed (during streaming) ───────────────────── */}
            {(isStreaming || hasLiveData) && (
              <ErrorBoundary fallback="Live feed unavailable">
              <div>
                <div className="my-2 border-t border-border/50" />
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Live Feed{" "}
                  {narrativeFeed.length > 0 && (
                    <span className="font-normal text-muted-foreground/40">
                      ({narrativeFeed.length})
                    </span>
                  )}
                </p>
                <NarrativeFeed entries={narrativeFeed} />
              </div>
              </ErrorBoundary>
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

            {/* Idle state — no recent activity */}
            {!isStreaming && !hasLiveData && !isLoading && (!trace?.root_span || traceIsStale) && (
              <p className="text-center text-[10px] text-muted-foreground/40">
                No recent activity
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
