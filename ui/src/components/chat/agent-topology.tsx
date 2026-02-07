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

/** Agent metadata for the topology visualization */
const AGENTS: Record<
  string,
  {
    label: string;
    icon: typeof Bot;
    color: string;
    bgColor: string;
    group?: string;
  }
> = {
  architect: {
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10 border-blue-400/30",
  },
  data_scientist: {
    label: "Data Scientist",
    icon: BarChart3,
    color: "text-emerald-400",
    bgColor: "bg-emerald-400/10 border-emerald-400/30",
    group: "ds-team",
  },
  energy_analyst: {
    label: "Energy",
    icon: Zap,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10 border-yellow-400/30",
    group: "ds-team",
  },
  behavioral_analyst: {
    label: "Behavioral",
    icon: Users,
    color: "text-teal-400",
    bgColor: "bg-teal-400/10 border-teal-400/30",
    group: "ds-team",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    icon: Stethoscope,
    color: "text-rose-400",
    bgColor: "bg-rose-400/10 border-rose-400/30",
    group: "ds-team",
  },
  dashboard_designer: {
    label: "Dashboard",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    bgColor: "bg-indigo-400/10 border-indigo-400/30",
  },
  sandbox: {
    label: "Sandbox",
    icon: Code,
    color: "text-orange-400",
    bgColor: "bg-orange-400/10 border-orange-400/30",
  },
  librarian: {
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10 border-purple-400/30",
  },
  developer: {
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10 border-amber-400/30",
  },
  system: {
    label: "System",
    icon: Server,
    color: "text-muted-foreground",
    bgColor: "bg-muted/30 border-border/50",
  },
};

/** DS team specialists that form a consultation cluster */
const DS_TEAM_AGENTS = new Set([
  "energy_analyst",
  "behavioral_analyst",
  "diagnostic_analyst",
  "data_scientist",
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
}

/** A single agent node in the topology */
function AgentNode({
  agentKey,
  isActive,
  isCompleted,
  delay,
  compact,
}: {
  agentKey: string;
  isActive: boolean;
  isCompleted: boolean;
  delay: number;
  compact?: boolean;
}) {
  const agent = AGENTS[agentKey] ?? AGENTS.system;
  const Icon = agent.icon;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.3 }}
      className={cn(
        "relative flex items-center gap-1.5 rounded-lg border text-xs font-medium transition-all",
        compact ? "px-2 py-1" : "px-3 py-1.5",
        agent.bgColor,
        isActive && "ring-2 ring-primary/50 shadow-lg shadow-primary/10",
      )}
    >
      {/* Pulse indicator when active */}
      {isActive && (
        <motion.div
          className="absolute -left-1 -top-1 h-2.5 w-2.5 rounded-full bg-primary"
          animate={{ scale: [1, 1.4, 1], opacity: [1, 0.5, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}

      {/* Checkmark when complete */}
      {isCompleted && (
        <div className="absolute -left-1 -top-1 flex h-3 w-3 items-center justify-center rounded-full bg-emerald-500 text-[7px] text-white">
          ✓
        </div>
      )}

      <Icon className={cn(compact ? "h-3 w-3" : "h-3.5 w-3.5", agent.color)} />
      <span className={agent.color}>{agent.label}</span>
    </motion.div>
  );
}

/** Vertical connection arrow between nodes */
function ConnectionArrow({
  delay,
  dashed,
}: {
  delay: number;
  dashed?: boolean;
}) {
  return (
    <div className="flex flex-col items-center">
      <motion.div
        className={cn("h-4 w-px", dashed ? "border-l border-dashed border-border" : "bg-border")}
        initial={{ scaleY: 0 }}
        animate={{ scaleY: 1 }}
        transition={{ delay, duration: 0.3 }}
      />
      <motion.div
        className="h-0 w-0 border-l-[4px] border-r-[4px] border-t-[5px] border-l-transparent border-r-transparent border-t-border"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.2 }}
      />
    </div>
  );
}

/** Horizontal cross-consultation indicator between DS team members */
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

/** DS team cluster — groups specialists together */
function DSTeamCluster({
  dsAgents,
  activeAgent,
  isCompleted,
  baseDelay,
}: {
  dsAgents: string[];
  activeAgent?: string | null;
  isCompleted: boolean;
  baseDelay: number;
}) {
  if (dsAgents.length === 0) return null;

  // Only show cluster wrapper when there are multiple DS team members
  const showCluster = dsAgents.length > 1;

  if (!showCluster) {
    return (
      <AgentNode
        agentKey={dsAgents[0]}
        isActive={activeAgent === dsAgents[0]}
        isCompleted={isCompleted}
        delay={baseDelay}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: baseDelay, duration: 0.3 }}
      className="rounded-xl border border-dashed border-emerald-400/20 bg-emerald-400/5 px-2 py-1.5"
    >
      <p className="mb-1 text-center text-[8px] font-medium uppercase tracking-wider text-emerald-400/50">
        DS Team
      </p>
      <div className="flex flex-col items-center gap-0.5">
        {dsAgents.map((agentKey, j) => (
          <div key={agentKey} className="flex flex-col items-center">
            {j > 0 && <CrossConsultationIndicator delay={baseDelay + j * 0.1} />}
            <AgentNode
              agentKey={agentKey}
              isActive={activeAgent === agentKey}
              isCompleted={isCompleted}
              delay={baseDelay + j * 0.1}
              compact
            />
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export function AgentTopology({
  agents,
  activeAgent,
  rootSpan,
  isLive,
}: AgentTopologyProps) {
  // Extract the unique agents in order of appearance from the span tree
  const orderedAgents = agents.length > 0 ? agents : ["architect"];

  // Filter to only known agents
  const knownAgents = orderedAgents.filter((a) => a in AGENTS);

  if (knownAgents.length === 0) {
    knownAgents.push("architect");
  }

  const isCompleted = !isLive && !activeAgent;

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
      // Skip individual DS agents (they're in the cluster)
    } else {
      renderItems.push({ type: "agent", key: agentKey });
    }
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
            {/* Connection line from previous item */}
            {i > 0 && (
              <div className="mb-1">
                <ConnectionArrow
                  delay={delay}
                  dashed={item.type === "ds-cluster"}
                />
              </div>
            )}

            {item.type === "agent" ? (
              <AgentNode
                agentKey={item.key}
                isActive={activeAgent === item.key}
                isCompleted={isCompleted}
                delay={delay}
              />
            ) : (
              <DSTeamCluster
                dsAgents={item.agents}
                activeAgent={activeAgent}
                isCompleted={isCompleted}
                baseDelay={delay}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
