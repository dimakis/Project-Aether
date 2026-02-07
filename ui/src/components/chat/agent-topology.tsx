import { motion } from "framer-motion";
import { Bot, BarChart3, Code, BookOpen, Wrench, Server } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SpanNode } from "@/lib/types";

/** Agent metadata for the topology visualization */
const AGENTS: Record<
  string,
  { label: string; icon: typeof Bot; color: string; bgColor: string }
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

export function AgentTopology({
  agents,
  activeAgent,
  rootSpan,
  isLive,
}: AgentTopologyProps) {
  // Extract the unique agents in order of appearance from the span tree
  const orderedAgents = agents.length > 0 ? agents : ["architect"];

  // Filter to only known agents
  const displayAgents = orderedAgents.filter((a) => a in AGENTS);

  if (displayAgents.length === 0) {
    displayAgents.push("architect");
  }

  return (
    <div className="flex flex-col items-center gap-1 py-2">
      {displayAgents.map((agentKey, i) => {
        const agent = AGENTS[agentKey] ?? AGENTS.system;
        const Icon = agent.icon;
        const isActive = activeAgent === agentKey;
        const isCompleted = !isLive && !activeAgent;

        return (
          <div key={agentKey} className="flex flex-col items-center">
            {/* Connection line from previous agent */}
            {i > 0 && (
              <div className="mb-1 flex flex-col items-center">
                <motion.div
                  className="h-4 w-px bg-border"
                  initial={{ scaleY: 0 }}
                  animate={{ scaleY: 1 }}
                  transition={{ delay: i * 0.2, duration: 0.3 }}
                />
                <motion.div
                  className="h-0 w-0 border-l-[4px] border-r-[4px] border-t-[5px] border-l-transparent border-r-transparent border-t-border"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.2 + 0.2 }}
                />
              </div>
            )}

            {/* Agent node */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.15, duration: 0.3 }}
              className={cn(
                "relative flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
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

              <Icon className={cn("h-3.5 w-3.5", agent.color)} />
              <span className={agent.color}>{agent.label}</span>
            </motion.div>
          </div>
        );
      })}
    </div>
  );
}
