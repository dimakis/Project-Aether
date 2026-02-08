import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
  BookOpen,
  Wrench,
  Code,
  Server,
  BarChart3,
  ArrowDown,
  ArrowLeftRight,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentDetail } from "@/lib/types";

// ─── Agent Node Data ──────────────────────────────────────────────────────────

interface AgentNodeDef {
  id: string;
  label: string;
  icon: typeof Bot;
  color: string;
  bgColor: string;
  borderColor: string;
  group: "orchestration" | "ds-team" | "deployment" | "discovery";
  description: string;
}

const AGENT_NODES: AgentNodeDef[] = [
  {
    id: "architect",
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
    group: "orchestration",
    description: "Primary orchestrator. Delegates analysis to DS team via a single tool call.",
  },
  {
    id: "energy_analyst",
    label: "Energy Analyst",
    icon: Zap,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
    borderColor: "border-yellow-400/30",
    group: "ds-team",
    description: "Analyzes energy consumption, cost optimization, and usage patterns.",
  },
  {
    id: "behavioral_analyst",
    label: "Behavioral Analyst",
    icon: Users,
    color: "text-teal-400",
    bgColor: "bg-teal-400/10",
    borderColor: "border-teal-400/30",
    group: "ds-team",
    description: "Detects user behavior patterns, routines, and automation opportunities.",
  },
  {
    id: "diagnostic_analyst",
    label: "Diagnostic Analyst",
    icon: Stethoscope,
    color: "text-rose-400",
    bgColor: "bg-rose-400/10",
    borderColor: "border-rose-400/30",
    group: "ds-team",
    description: "Monitors system health, diagnoses errors, and checks integrations.",
  },
  {
    id: "dashboard_designer",
    label: "Dashboard Designer",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    bgColor: "bg-indigo-400/10",
    borderColor: "border-indigo-400/30",
    group: "deployment",
    description: "Designs Lovelace dashboards, consults DS team for data-driven layouts.",
  },
  {
    id: "developer",
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10",
    borderColor: "border-amber-400/30",
    group: "deployment",
    description: "Deploys automations, scripts, and scenes to Home Assistant.",
  },
  {
    id: "librarian",
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
    group: "discovery",
    description: "Discovers and catalogs HA entities, devices, and areas.",
  },
];

// ─── Edge Definitions ─────────────────────────────────────────────────────────

type EdgeType = "delegation" | "consultation" | "data-flow";

interface EdgeDef {
  from: string;
  to: string;
  type: EdgeType;
  label?: string;
}

const EDGES: EdgeDef[] = [
  // Architect delegates to DS team via consult_data_science_team (single tool)
  { from: "architect", to: "energy_analyst", type: "delegation", label: "via DS team" },
  { from: "architect", to: "behavioral_analyst", type: "delegation", label: "via DS team" },
  { from: "architect", to: "diagnostic_analyst", type: "delegation", label: "via DS team" },
  // Architect delegates to other agents directly
  { from: "architect", to: "developer", type: "delegation" },
  { from: "architect", to: "dashboard_designer", type: "delegation" },
  { from: "architect", to: "librarian", type: "delegation" },
  // DS team cross-consultation (shared TeamAnalysis)
  { from: "energy_analyst", to: "behavioral_analyst", type: "consultation" },
  { from: "energy_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "behavioral_analyst", to: "diagnostic_analyst", type: "consultation" },
  // Dashboard Designer consults DS team
  { from: "dashboard_designer", to: "energy_analyst", type: "consultation", label: "consults" },
  { from: "dashboard_designer", to: "behavioral_analyst", type: "consultation", label: "consults" },
];

// ─── Group Metadata ───────────────────────────────────────────────────────────

const GROUPS: Record<string, { label: string; color: string; borderColor: string }> = {
  orchestration: {
    label: "Orchestration",
    color: "bg-blue-400/5",
    borderColor: "border-blue-400/20",
  },
  "ds-team": {
    label: "Data Science Team",
    color: "bg-emerald-400/5",
    borderColor: "border-emerald-400/20",
  },
  deployment: {
    label: "Deployment",
    color: "bg-amber-400/5",
    borderColor: "border-amber-400/20",
  },
  discovery: {
    label: "Discovery",
    color: "bg-purple-400/5",
    borderColor: "border-purple-400/20",
  },
};

// ─── Components ───────────────────────────────────────────────────────────────

function AgentGraphNode({
  node,
  isSelected,
  status,
  onClick,
}: {
  node: AgentNodeDef;
  isSelected: boolean;
  status?: string;
  onClick: () => void;
}) {
  const Icon = node.icon;

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={cn(
        "flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all",
        node.bgColor,
        node.borderColor,
        isSelected && "ring-2 ring-primary/50 shadow-lg",
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-lg",
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
              className="text-[9px] font-medium"
            >
              {status}
            </Badge>
          )}
        </div>
        <p className="truncate text-[11px] text-muted-foreground">
          {node.description}
        </p>
      </div>
    </motion.button>
  );
}

function GroupContainer({
  groupId,
  children,
}: {
  groupId: string;
  children: React.ReactNode;
}) {
  const group = GROUPS[groupId];
  if (!group) return <>{children}</>;

  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed p-3",
        group.color,
        group.borderColor,
      )}
    >
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
        {group.label}
      </p>
      {children}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
      <div className="flex items-center gap-1.5">
        <ArrowDown className="h-3 w-3" />
        <span>Delegation</span>
      </div>
      <div className="flex items-center gap-1.5">
        <ArrowLeftRight className="h-3 w-3" />
        <span className="border-b border-dashed border-muted-foreground">
          Cross-consultation
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-2 rounded-full bg-emerald-500" />
        <span>Enabled</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-2 rounded-full bg-red-500" />
        <span>Disabled</span>
      </div>
    </div>
  );
}

function AgentDetailSidebar({ node }: { node: AgentNodeDef }) {
  const Icon = node.icon;

  // Find edges involving this agent
  const delegatesTo = EDGES.filter(
    (e) => e.from === node.id && e.type === "delegation",
  ).map((e) => AGENT_NODES.find((n) => n.id === e.to)?.label ?? e.to);

  const consultsWith = EDGES.filter(
    (e) =>
      (e.from === node.id || e.to === node.id) &&
      e.type === "consultation",
  ).map((e) => {
    const otherId = e.from === node.id ? e.to : e.from;
    return AGENT_NODES.find((n) => n.id === otherId)?.label ?? otherId;
  });

  const delegatedBy = EDGES.filter(
    (e) => e.to === node.id && e.type === "delegation",
  ).map((e) => AGENT_NODES.find((n) => n.id === e.from)?.label ?? e.from);

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl",
            node.bgColor,
          )}
        >
          <Icon className={cn("h-5 w-5", node.color)} />
        </div>
        <div>
          <h3 className={cn("text-base font-bold", node.color)}>
            {node.label}
          </h3>
          <p className="text-xs text-muted-foreground">
            {GROUPS[node.group]?.label}
          </p>
        </div>
      </div>

      <p className="mb-4 text-sm text-muted-foreground">
        {node.description}
      </p>

      {delegatedBy.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Receives tasks from
          </p>
          <div className="flex flex-wrap gap-1">
            {delegatedBy.map((name) => (
              <Badge key={name} variant="outline" className="text-[10px]">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {delegatesTo.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Delegates to
          </p>
          <div className="flex flex-wrap gap-1">
            {delegatesTo.map((name) => (
              <Badge key={name} variant="outline" className="text-[10px]">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {consultsWith.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Cross-consults with
          </p>
          <div className="flex flex-wrap gap-1">
            {consultsWith.map((name) => (
              <Badge key={name} variant="outline" className="text-[10px]">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function TeamArchitectureTab({
  agents,
}: {
  agents?: AgentDetail[];
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Build a status map from live agent data
  const statusMap = new Map<string, string>();
  agents?.forEach((a) => {
    statusMap.set(a.name, a.status);
  });

  const selectedNode = AGENT_NODES.find((n) => n.id === selectedNodeId);

  // Group agents by their group
  const groupedAgents: Record<string, AgentNodeDef[]> = {};
  for (const node of AGENT_NODES) {
    if (!groupedAgents[node.group]) {
      groupedAgents[node.group] = [];
    }
    groupedAgents[node.group].push(node);
  }

  // Render order for groups
  const groupOrder = ["orchestration", "ds-team", "deployment", "discovery"];

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center justify-between">
        <Legend />
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
          <Info className="h-3 w-3" />
          Click an agent for details
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Graph area */}
        <div className="space-y-3 lg:col-span-2">
          {groupOrder.map((groupId) => {
            const nodes = groupedAgents[groupId];
            if (!nodes || nodes.length === 0) return null;

            return (
              <GroupContainer key={groupId} groupId={groupId}>
                <div
                  className={cn(
                    "grid gap-2",
                    nodes.length === 1
                      ? "grid-cols-1"
                      : nodes.length === 2
                        ? "grid-cols-2"
                        : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
                  )}
                >
                  {nodes.map((node) => (
                    <AgentGraphNode
                      key={node.id}
                      node={node}
                      isSelected={selectedNodeId === node.id}
                      status={statusMap.get(node.id)}
                      onClick={() =>
                        setSelectedNodeId(
                          selectedNodeId === node.id ? null : node.id,
                        )
                      }
                    />
                  ))}
                </div>

                {/* Show cross-consultation arrows within DS team */}
                {groupId === "ds-team" && (
                  <div className="mt-2 flex items-center justify-center gap-2 text-[10px] text-emerald-400/60">
                    <div className="h-px w-6 border-t border-dashed border-emerald-400/40" />
                    <ArrowLeftRight className="h-3 w-3" />
                    <span>mutual cross-consultation</span>
                    <div className="h-px w-6 border-t border-dashed border-emerald-400/40" />
                  </div>
                )}
              </GroupContainer>
            );
          })}

          {/* Delegation flow indicators between groups */}
          <div className="flex items-center justify-center gap-2 text-[10px] text-muted-foreground/40">
            <ArrowDown className="h-3 w-3" />
            <span>Architect delegates to DS team via consult_data_science_team</span>
          </div>
        </div>

        {/* Detail sidebar */}
        <div className="lg:col-span-1">
          {selectedNode ? (
            <motion.div
              key={selectedNode.id}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
            >
              <AgentDetailSidebar node={selectedNode} />
            </motion.div>
          ) : (
            <Card className="flex items-center justify-center p-8 text-center">
              <div>
                <Bot className="mx-auto mb-2 h-8 w-8 text-muted-foreground/20" />
                <p className="text-xs text-muted-foreground/50">
                  Select an agent to view details
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
