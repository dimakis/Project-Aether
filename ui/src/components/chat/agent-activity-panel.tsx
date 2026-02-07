import { motion, AnimatePresence } from "framer-motion";
import { X, Activity, Loader2 } from "lucide-react";
import { AgentTopology } from "./agent-topology";
import { TraceTimeline } from "./trace-timeline";
import {
  useAgentActivity,
  useActivityPanel,
  setActivityPanelOpen,
} from "@/lib/agent-activity-store";
import { useTraceSpans } from "@/api/hooks";

/**
 * Global Agent Activity Panel.
 *
 * Reads all state from the global agent-activity-store, so it can be
 * rendered at the AppLayout level and persist across page navigation.
 */
export function AgentActivityPanel() {
  const activity = useAgentActivity();
  const { lastTraceId, panelOpen } = useActivityPanel();
  const { data: trace, isLoading } = useTraceSpans(lastTraceId);

  const isStreaming = activity.isActive;
  const activeAgent = activity.activeAgent || "architect";

  return (
    <AnimatePresence>
      {panelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="flex h-full flex-col overflow-hidden border-l border-border bg-card/50"
        >
          {/* Header */}
          <div className="flex h-14 items-center justify-between border-b border-border px-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Agent Activity</span>
              {isStreaming && (
                <Loader2 className="h-3 w-3 animate-spin text-primary" />
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
          <div className="flex-1 overflow-auto p-3">
            {isStreaming && !trace ? (
              /* Streaming but no trace yet — show live indicator */
              <div>
                <p className="mb-3 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Agent Flow
                </p>
                <AgentTopology
                  agents={[activeAgent]}
                  activeAgent={activeAgent}
                  isLive
                />
                <div className="mt-4 flex items-center justify-center gap-2 text-xs text-muted-foreground/60">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Processing...</span>
                </div>
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground/30" />
              </div>
            ) : trace?.root_span ? (
              <div>
                {/* Agent topology */}
                <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Agent Flow
                </p>
                <AgentTopology
                  agents={trace.agents_involved}
                  activeAgent={isStreaming ? activeAgent : null}
                  rootSpan={trace.root_span}
                  isLive={isStreaming}
                />

                {/* Divider */}
                <div className="my-3 border-t border-border/50" />

                {/* Timeline */}
                <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  Timeline ({trace.span_count} spans, {(trace.duration_ms / 1000).toFixed(1)}s)
                </p>
                <TraceTimeline
                  rootSpan={trace.root_span}
                  isLive={isStreaming}
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Activity className="mb-2 h-8 w-8 text-muted-foreground/20" />
                <p className="text-xs text-muted-foreground/50">
                  Send a message to see agent activity
                </p>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
