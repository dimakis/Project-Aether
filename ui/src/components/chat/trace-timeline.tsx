import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { SpanNode } from "@/lib/types";

/** Flatten a span tree into a timeline of notable events */
interface TimelineEvent {
  time_ms: number;
  agent: string;
  type: string; // "start", "tool_call", "llm", "end"
  name: string;
  detail?: string;
  duration_ms?: number;
  status: string;
}

function flattenSpans(span: SpanNode, events: TimelineEvent[] = []): TimelineEvent[] {
  // Determine event type
  let type = "start";
  if (span.type === "tool" || span.type === "tool_call") {
    type = "tool_call";
  } else if (span.type === "llm" || span.type === "chat_model") {
    type = "llm";
  } else if (span.type === "chain") {
    type = "start";
  }

  // Build a readable name
  let detail: string | undefined;
  if (span.attributes.model) {
    detail = String(span.attributes.model);
  }
  if (span.attributes.tokens) {
    detail = (detail ? detail + " · " : "") + `${span.attributes.tokens} tokens`;
  }
  if (span.attributes.tool) {
    detail = String(span.attributes.tool);
  }

  events.push({
    time_ms: span.start_ms,
    agent: span.agent,
    type,
    name: _friendlyName(span.name),
    detail,
    duration_ms: span.duration_ms,
    status: span.status,
  });

  // Recurse into children
  for (const child of span.children) {
    flattenSpans(child, events);
  }

  return events;
}

function _friendlyName(name: string): string {
  // Clean up MLflow span names for display
  return name
    .replace(/^(ChatOpenAI|OpenAI|Google)/, "LLM call")
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2");
}

const EVENT_ICONS: Record<string, string> = {
  start: "⚡",
  tool_call: "🔧",
  llm: "🧠",
  end: "✅",
};

import { agentColor } from "@/lib/agent-registry";

/** Format a wall-clock Date as compact HH:MM:SS */
function formatWallClock(date: Date): string {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

interface TraceTimelineProps {
  rootSpan: SpanNode;
  /** ISO-8601 trace start time for wall-clock display */
  startedAt?: string | null;
  isLive?: boolean;
}

export function TraceTimeline({ rootSpan, startedAt, isLive }: TraceTimelineProps) {
  const traceStart = startedAt ? new Date(startedAt).getTime() : null;
  const events = flattenSpans(rootSpan);

  // Sort by time and deduplicate very close events from the same agent
  events.sort((a, b) => a.time_ms - b.time_ms);

  // Filter out very short or redundant events, keep the interesting ones
  const filtered = events.filter((e) => {
    // Always keep tool calls and LLM calls
    if (e.type === "tool_call" || e.type === "llm") return true;
    // Keep agent starts (chain type) but not if it's a very short system span
    if (e.type === "start" && e.agent !== "system" && (e.duration_ms ?? 0) > 50) return true;
    // Keep first event always
    if (e === events[0]) return true;
    return false;
  });

  // Add a completion event
  const totalDuration = rootSpan.end_ms;
  if (!isLive) {
    filtered.push({
      time_ms: totalDuration,
      agent: "system",
      type: "end",
      name: "Complete",
      detail: `${(totalDuration / 1000).toFixed(1)}s total`,
      status: rootSpan.status,
    });
  }

  return (
    <div className="space-y-0">
      {filtered.map((event, i) => (
        <motion.div
          key={`${event.time_ms}-${event.name}-${i}`}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05, duration: 0.2 }}
          className="flex gap-2 py-1.5"
        >
          {/* Timestamp */}
          <span
            className={cn(
              "shrink-0 text-right text-[10px] tabular-nums text-muted-foreground/50",
              traceStart ? "w-[52px]" : "w-10",
            )}
            title={
              traceStart
                ? new Date(traceStart + event.time_ms).toISOString()
                : `+${(event.time_ms / 1000).toFixed(1)}s`
            }
          >
            {traceStart
              ? formatWallClock(new Date(traceStart + event.time_ms))
              : `${(event.time_ms / 1000).toFixed(1)}s`}
          </span>

          {/* Timeline dot */}
          <div className="relative flex flex-col items-center">
            <div
              className={cn(
                "z-10 flex h-4 w-4 items-center justify-center rounded-full text-[8px]",
                event.type === "end"
                  ? "bg-emerald-500/20"
                  : event.status === "ERROR"
                    ? "bg-red-500/20"
                    : "bg-muted",
              )}
            >
              {EVENT_ICONS[event.type] ?? "•"}
            </div>
            {/* Vertical line */}
            {i < filtered.length - 1 && (
              <div className="absolute top-4 h-full w-px bg-border/50" />
            )}
          </div>

          {/* Event detail */}
          <div className="min-w-0 flex-1 pb-1">
            <p className="text-[11px] font-medium leading-tight">
              <span className={agentColor(event.agent)}>
                {event.name}
              </span>
            </p>
            {event.detail && (
              <p className="truncate text-[10px] text-muted-foreground/60">
                {event.detail}
              </p>
            )}
            {event.duration_ms != null && event.type !== "end" && event.duration_ms > 100 && (
              <p className="text-[9px] text-muted-foreground/40">
                {(event.duration_ms / 1000).toFixed(1)}s
              </p>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
