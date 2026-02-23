import { motion } from "framer-motion";
import { ArrowDown, ArrowLeftRight, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  GROUP_ORDER,
  GROUPS,
  type AgentNodeDef,
  type EdgeType,
} from "./config";

// ─── Agent Node Component ─────────────────────────────────────────────────────

interface FullAgentNodeProps {
  node: AgentNodeDef;
  isSelected: boolean;
  status?: string;
  onClick: () => void;
}

function FullAgentNode({ node, isSelected, status, onClick }: FullAgentNodeProps) {
  const Icon = node.icon;
  const isEnabled = !status || status !== "disabled";

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      layout
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 text-left transition-all",
        node.bgColor,
        node.borderColor,
        isSelected && "ring-2 ring-primary/50 shadow-lg",
        !isEnabled && "opacity-50",
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
          node.bgColor,
        )}
      >
        <Icon className={cn("h-5 w-5", node.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-semibold", node.color)}>
            {node.label}
          </span>
          {status && (
            <Badge
              variant="outline"
              className={cn(
                "text-[9px] font-medium",
                status === "enabled" && "text-emerald-400",
                status === "disabled" && "text-red-400",
                status === "primary" && "text-amber-400",
              )}
            >
              {status}
            </Badge>
          )}
        </div>
        <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
          {node.description}
        </p>
      </div>
    </motion.button>
  );
}

// ─── Graph Component ─────────────────────────────────────────────────────────

export interface ArchitectureGraphProps {
  groupedAgents: Record<string, AgentNodeDef[]>;
  statusMap: Map<string, string>;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  edgeFilter: EdgeType | "all";
}

export function ArchitectureGraph({
  groupedAgents,
  statusMap,
  selectedNodeId,
  onNodeSelect,
  edgeFilter,
}: ArchitectureGraphProps) {
  return (
    <div className="space-y-4">
      {GROUP_ORDER.map((groupId) => {
        const nodes = groupedAgents[groupId];
        if (!nodes || nodes.length === 0) return null;
        const group = GROUPS[groupId];

        return (
          <div
            key={groupId}
            className={cn(
              "rounded-2xl border border-dashed p-4",
              group.color,
              group.borderColor,
            )}
          >
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  {group.label}
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  {group.description}
                </p>
              </div>
              <Badge variant="outline" className="text-[9px]">
                {nodes.length} agent{nodes.length !== 1 ? "s" : ""}
              </Badge>
            </div>

            <div
              className={cn(
                "grid gap-3",
                nodes.length === 1
                  ? "grid-cols-1 max-w-md"
                  : nodes.length === 2
                    ? "grid-cols-1 md:grid-cols-2"
                    : "grid-cols-1 md:grid-cols-2 xl:grid-cols-3",
              )}
            >
              {nodes.map((node) => (
                <FullAgentNode
                  key={node.id}
                  node={node}
                  isSelected={selectedNodeId === node.id}
                  status={statusMap.get(node.id)}
                  onClick={() =>
                    onNodeSelect(selectedNodeId === node.id ? null : node.id)
                  }
                />
              ))}
            </div>

            {/* DS team cross-consultation indicator */}
            {groupId === "ds-team" &&
              (edgeFilter === "all" || edgeFilter === "consultation") && (
                <div className="mt-3 flex items-center justify-center gap-2 text-[10px] text-emerald-400/60">
                  <div className="h-px w-8 border-t border-dashed border-emerald-400/40" />
                  <ArrowLeftRight className="h-3 w-3" />
                  <span>all specialists cross-consult for holistic analysis</span>
                  <div className="h-px w-8 border-t border-dashed border-emerald-400/40" />
                </div>
              )}
          </div>
        );
      })}

      {/* Flow indicators */}
      <div className="flex flex-col items-center gap-2 py-2">
        {(edgeFilter === "all" || edgeFilter === "a2a") && (
          <div className="flex items-center gap-2 text-[11px] text-cyan-400/60">
            <Layers className="h-3.5 w-3.5" />
            <span>Orchestrator routes requests to Architect via A2A protocol</span>
          </div>
        )}
        {(edgeFilter === "all" || edgeFilter === "delegation") && (
          <div className="flex items-center gap-2 text-[11px] text-blue-400/60">
            <ArrowDown className="h-3.5 w-3.5" />
            <span>Architect delegates tasks to all specialist groups</span>
          </div>
        )}
        {(edgeFilter === "all" || edgeFilter === "consultation") && (
          <div className="flex items-center gap-2 text-[11px] text-indigo-400/60">
            <ArrowLeftRight className="h-3.5 w-3.5" />
            <span>
              Dashboard Designer consults Energy and Behavioral analysts
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
