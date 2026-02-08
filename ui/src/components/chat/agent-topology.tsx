import { motion } from "framer-motion";
import {
  Bot,
  BarChart3,
  Code,
  BookOpen,
  Wrench,
  Server,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SpanNode } from "@/lib/types";
import type { AgentNodeState } from "@/lib/agent-activity-store";

/** Agent metadata for the topology visualization */
const AGENTS: Record<
  string,
  {
    label: string;
    icon: typeof Bot;
    color: string;
    /** Tailwind colour value (without the text- prefix) for CSS custom properties. */
    glowRgb: string;
    bgColor: string;
    group?: string;
  }
> = {
  architect: {
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    glowRgb: "96 165 250",
    bgColor: "bg-blue-400/10 border-blue-400/30",
  },
  data_scientist: {
    label: "Data Scientist",
    icon: BarChart3,
    color: "text-emerald-400",
    glowRgb: "52 211 153",
    bgColor: "bg-emerald-400/10 border-emerald-400/30",
    group: "ds-team",
  },
  data_science_team: {
    label: "DS Team",
    icon: BarChart3,
    color: "text-emerald-400",
    glowRgb: "52 211 153",
    bgColor: "bg-emerald-400/10 border-emerald-400/30",
    group: "ds-team",
  },
  energy_analyst: {
    label: "Energy",
    icon: Zap,
    color: "text-yellow-400",
    glowRgb: "250 204 21",
    bgColor: "bg-yellow-400/10 border-yellow-400/30",
    group: "ds-team",
  },
  behavioral_analyst: {
    label: "Behavioral",
    icon: Users,
    color: "text-teal-400",
    glowRgb: "45 212 191",
    bgColor: "bg-teal-400/10 border-teal-400/30",
    group: "ds-team",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    icon: Stethoscope,
    color: "text-rose-400",
    glowRgb: "251 113 133",
    bgColor: "bg-rose-400/10 border-rose-400/30",
    group: "ds-team",
  },
  dashboard_designer: {
    label: "Dashboard",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    glowRgb: "129 140 248",
    bgColor: "bg-indigo-400/10 border-indigo-400/30",
  },
  sandbox: {
    label: "Sandbox",
    icon: Code,
    color: "text-orange-400",
    glowRgb: "251 146 60",
    bgColor: "bg-orange-400/10 border-orange-400/30",
  },
  librarian: {
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    glowRgb: "192 132 252",
    bgColor: "bg-purple-400/10 border-purple-400/30",
  },
  developer: {
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    glowRgb: "251 191 36",
    bgColor: "bg-amber-400/10 border-amber-400/30",
  },
  system: {
    label: "System",
    icon: Server,
    color: "text-muted-foreground",
    glowRgb: "161 161 170",
    bgColor: "bg-muted/30 border-border/50",
  },
};

/** DS team specialists that form a consultation cluster */
const DS_TEAM_AGENTS = new Set([
  "energy_analyst",
  "behavioral_analyst",
  "diagnostic_analyst",
  "data_scientist",
  "data_science_team",
]);

interface AgentTopologyProps {
  /** Agents involved in the trace, in order */
  agents: string[];
  /** Currently active agent (during streaming) */
  activeAgent?: string | null;
  /** Root span for extracting delegation flow */
  rootSpan?: SpanNode | null;
  /** Whether the trace is still in progress */
  isLive?: boolean;
  /** Per-agent visual state for neural activity (live mode). */
  agentStates?: Record<string, AgentNodeState>;
}

// ─── Agent Node ──────────────────────────────────────────────────────────────

function AgentNode({
  agentKey,
  nodeState,
  delay,
  compact,
}: {
  agentKey: string;
  /** Neural state: firing (glow), done (checkmark), idle (dim), undefined (normal). */
  nodeState?: AgentNodeState;
  delay: number;
  compact?: boolean;
}) {
  const agent = AGENTS[agentKey] ?? AGENTS.system;
  const Icon = agent.icon;

  const isFiring = nodeState === "firing";
  const isDone = nodeState === "done";
  const isIdle = nodeState === "idle";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{
        opacity: isIdle ? 0.4 : 1,
        scale: isFiring ? 1.05 : 1,
      }}
      transition={{ delay, duration: 0.3 }}
      className={cn(
        "relative flex items-center gap-1.5 rounded-lg border text-xs font-medium transition-all",
        compact ? "px-2 py-1" : "px-3 py-1.5",
        agent.bgColor,
        isFiring && "ring-2 ring-primary/60",
      )}
      style={
        isFiring
          ? {
              boxShadow: `0 0 12px 2px rgba(${agent.glowRgb} / 0.35), 0 0 24px 4px rgba(${agent.glowRgb} / 0.15)`,
            }
          : undefined
      }
    >
      {/* Firing pulse indicator — fast, bright */}
      {isFiring && (
        <motion.div
          className="absolute -left-1 -top-1 h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: `rgb(${agent.glowRgb})` }}
          animate={{ scale: [1, 1.6, 1], opacity: [1, 0.4, 1] }}
          transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Done checkmark */}
      {isDone && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className="absolute -left-1 -top-1 flex h-3 w-3 items-center justify-center rounded-full bg-emerald-500 text-[7px] text-white"
        >
          ✓
        </motion.div>
      )}

      <Icon
        className={cn(
          compact ? "h-3 w-3" : "h-3.5 w-3.5",
          agent.color,
          isIdle && "opacity-50",
        )}
      />
      <span className={cn(agent.color, isIdle && "opacity-50")}>
        {agent.label}
      </span>
    </motion.div>
  );
}

// ─── Connection Arrow ────────────────────────────────────────────────────────

function ConnectionArrow({
  delay,
  dashed,
  isActive,
}: {
  delay: number;
  dashed?: boolean;
  /** Whether data is flowing through this connection right now. */
  isActive?: boolean;
}) {
  return (
    <div className="relative flex flex-col items-center">
      <motion.div
        className={cn(
          "h-4 w-px",
          dashed
            ? "border-l border-dashed border-border"
            : "bg-border",
        )}
        initial={{ scaleY: 0 }}
        animate={{ scaleY: 1 }}
        transition={{ delay, duration: 0.3 }}
      />
      {/* Traveling pulse dot when active */}
      {isActive && (
        <motion.div
          className="absolute left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-primary"
          animate={{ top: [0, 16] }}
          transition={{ duration: 0.6, repeat: Infinity, ease: "linear" }}
        />
      )}
      <motion.div
        className={cn(
          "h-0 w-0 border-l-[4px] border-r-[4px] border-t-[5px] border-l-transparent border-r-transparent",
          isActive ? "border-t-primary" : "border-t-border",
        )}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.2 }}
      />
    </div>
  );
}

// ─── Cross-consultation indicator ────────────────────────────────────────────

function CrossConsultationIndicator({ delay }: { delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay, duration: 0.4 }}
      className="my-0.5 flex items-center justify-center gap-1"
    >
      <div className="h-px w-3 border-t border-dashed border-emerald-400/40" />
      <span className="text-[8px] text-emerald-400/60">consults</span>
      <div className="h-px w-3 border-t border-dashed border-emerald-400/40" />
    </motion.div>
  );
}

// ─── DS Team Cluster ─────────────────────────────────────────────────────────

function DSTeamCluster({
  dsAgents,
  agentStates,
  baseDelay,
}: {
  dsAgents: string[];
  agentStates?: Record<string, AgentNodeState>;
  baseDelay: number;
}) {
  if (dsAgents.length === 0) return null;

  const showCluster = dsAgents.length > 1;
  const clusterFiring = dsAgents.some((a) => agentStates?.[a] === "firing");

  if (!showCluster) {
    return (
      <AgentNode
        agentKey={dsAgents[0]}
        nodeState={agentStates?.[dsAgents[0]]}
        delay={baseDelay}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: baseDelay, duration: 0.3 }}
      className={cn(
        "rounded-xl border border-dashed px-2 py-1.5 transition-all",
        clusterFiring
          ? "border-emerald-400/40 bg-emerald-400/10"
          : "border-emerald-400/20 bg-emerald-400/5",
      )}
    >
      <p className="mb-1 text-center text-[8px] font-medium uppercase tracking-wider text-emerald-400/50">
        DS Team
      </p>
      <div className="flex flex-col items-center gap-0.5">
        {dsAgents.map((agentKey, j) => (
          <div key={agentKey} className="flex flex-col items-center">
            {j > 0 && (
              <CrossConsultationIndicator delay={baseDelay + j * 0.1} />
            )}
            <AgentNode
              agentKey={agentKey}
              nodeState={agentStates?.[agentKey]}
              delay={baseDelay + j * 0.1}
              compact
            />
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ─── Main Topology ───────────────────────────────────────────────────────────

export function AgentTopology({
  agents,
  activeAgent,
  rootSpan,
  isLive,
  agentStates,
}: AgentTopologyProps) {
  const orderedAgents = agents.length > 0 ? agents : ["architect"];
  const knownAgents = orderedAgents.filter((a) => a in AGENTS);
  if (knownAgents.length === 0) knownAgents.push("architect");

  // If agentStates not provided (post-stream / legacy), derive from isLive + activeAgent
  const effectiveStates: Record<string, AgentNodeState> | undefined =
    agentStates && Object.keys(agentStates).length > 0
      ? agentStates
      : undefined;

  // Separate DS team for grouped rendering
  const dsAgents = knownAgents.filter((a) => DS_TEAM_AGENTS.has(a));

  type RenderItem =
    | { type: "agent"; key: string }
    | { type: "ds-cluster"; agents: string[] };

  const renderItems: RenderItem[] = [];
  let dsInserted = false;

  for (const agentKey of knownAgents) {
    if (DS_TEAM_AGENTS.has(agentKey)) {
      if (!dsInserted) {
        renderItems.push({ type: "ds-cluster", agents: dsAgents });
        dsInserted = true;
      }
    } else {
      renderItems.push({ type: "agent", key: agentKey });
    }
  }

  /**
   * Derive a node state when explicit agentStates aren't provided
   * (post-stream / MLflow-driven view).
   */
  function deriveNodeState(agentKey: string): AgentNodeState | undefined {
    if (effectiveStates) return effectiveStates[agentKey];
    if (!isLive) return "done";
    if (activeAgent === agentKey) return "firing";
    return undefined;
  }

  /** Is the connection between items[i-1] and items[i] actively carrying data? */
  function isConnectionActive(toIndex: number): boolean {
    if (!isLive || !effectiveStates) return false;
    const item = renderItems[toIndex];
    if (item.type === "agent") {
      return effectiveStates[item.key] === "firing";
    }
    // DS cluster — active if any member is firing
    return item.agents.some((a) => effectiveStates[a] === "firing");
  }

  return (
    <div className="flex flex-col items-center gap-1 py-2">
      {renderItems.map((item, i) => {
        const delay = i * 0.15;

        return (
          <div
            key={item.type === "agent" ? item.key : "ds-cluster"}
            className="flex flex-col items-center"
          >
            {i > 0 && (
              <div className="mb-1">
                <ConnectionArrow
                  delay={delay}
                  dashed={item.type === "ds-cluster"}
                  isActive={isConnectionActive(i)}
                />
              </div>
            )}

            {item.type === "agent" ? (
              <AgentNode
                agentKey={item.key}
                nodeState={deriveNodeState(item.key)}
                delay={delay}
              />
            ) : (
              <DSTeamCluster
                dsAgents={item.agents}
                agentStates={effectiveStates}
                baseDelay={delay}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
