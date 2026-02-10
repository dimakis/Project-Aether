import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
  BookOpen,
  Wrench,
  Network,
  ArrowDown,
  ArrowLeftRight,
  Filter,
  Info,
  Loader2,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgents } from "@/api/hooks";

// ─── Agent Node Definitions ───────────────────────────────────────────────────

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
    description: "Primary orchestrator. Delegates to specialists, manages conversation, coordinates multi-agent workflows.",
  },
  {
    id: "energy_analyst",
    label: "Energy Analyst",
    icon: Zap,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
    borderColor: "border-yellow-400/30",
    group: "ds-team",
    description: "Analyzes energy consumption patterns, identifies cost optimization opportunities, and monitors power usage trends.",
  },
  {
    id: "behavioral_analyst",
    label: "Behavioral Analyst",
    icon: Users,
    color: "text-teal-400",
    bgColor: "bg-teal-400/10",
    borderColor: "border-teal-400/30",
    group: "ds-team",
    description: "Detects user behavior patterns, routines, scene/script usage, and identifies automation opportunities.",
  },
  {
    id: "diagnostic_analyst",
    label: "Diagnostic Analyst",
    icon: Stethoscope,
    color: "text-rose-400",
    bgColor: "bg-rose-400/10",
    borderColor: "border-rose-400/30",
    group: "ds-team",
    description: "Monitors system health, diagnoses integration errors, checks entity availability and config validity.",
  },
  {
    id: "dashboard_designer",
    label: "Dashboard Designer",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    bgColor: "bg-indigo-400/10",
    borderColor: "border-indigo-400/30",
    group: "deployment",
    description: "Designs and generates Lovelace dashboards, consults DS team for data-driven layouts, previews before deploy.",
  },
  {
    id: "developer",
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10",
    borderColor: "border-amber-400/30",
    group: "deployment",
    description: "Deploys automations, scripts, and scenes to Home Assistant. Generates YAML configurations.",
  },
  {
    id: "librarian",
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
    group: "discovery",
    description: "Discovers and catalogs HA entities, infers devices and areas, syncs entity database.",
  },
];

// ─── Edge Definitions ─────────────────────────────────────────────────────────

type EdgeType = "delegation" | "consultation";

interface EdgeDef {
  from: string;
  to: string;
  type: EdgeType;
  label?: string;
}

const EDGES: EdgeDef[] = [
  { from: "architect", to: "energy_analyst", type: "delegation" },
  { from: "architect", to: "behavioral_analyst", type: "delegation" },
  { from: "architect", to: "diagnostic_analyst", type: "delegation" },
  { from: "architect", to: "developer", type: "delegation" },
  { from: "architect", to: "dashboard_designer", type: "delegation" },
  { from: "architect", to: "librarian", type: "delegation" },
  { from: "energy_analyst", to: "behavioral_analyst", type: "consultation" },
  { from: "energy_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "behavioral_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "dashboard_designer", to: "energy_analyst", type: "consultation", label: "consults" },
  { from: "dashboard_designer", to: "behavioral_analyst", type: "consultation", label: "consults" },
];

// ─── Group Metadata ───────────────────────────────────────────────────────────

const GROUPS: Record<
  string,
  { label: string; description: string; color: string; borderColor: string }
> = {
  orchestration: {
    label: "Orchestration",
    description: "Central coordination and user interaction",
    color: "bg-blue-400/5",
    borderColor: "border-blue-400/20",
  },
  "ds-team": {
    label: "Data Science Team",
    description: "Analysis, patterns, and diagnostics",
    color: "bg-emerald-400/5",
    borderColor: "border-emerald-400/20",
  },
  deployment: {
    label: "Deployment",
    description: "Dashboard design and automation deployment",
    color: "bg-amber-400/5",
    borderColor: "border-amber-400/20",
  },
  discovery: {
    label: "Discovery",
    description: "Entity discovery and cataloging",
    color: "bg-purple-400/5",
    borderColor: "border-purple-400/20",
  },
};

const GROUP_ORDER = ["orchestration", "ds-team", "deployment", "discovery"];

// ─── Components ───────────────────────────────────────────────────────────────

function FullAgentNode({
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

function DetailPanel({
  node,
  onClose,
}: {
  node: AgentNodeDef;
  onClose: () => void;
}) {
  const Icon = node.icon;

  const delegatesTo = EDGES.filter(
    (e) => e.from === node.id && e.type === "delegation",
  ).map((e) => AGENT_NODES.find((n) => n.id === e.to));

  const consultsWith = EDGES.filter(
    (e) =>
      (e.from === node.id || e.to === node.id) &&
      e.type === "consultation",
  ).map((e) => {
    const otherId = e.from === node.id ? e.to : e.from;
    return AGENT_NODES.find((n) => n.id === otherId);
  });

  const delegatedBy = EDGES.filter(
    (e) => e.to === node.id && e.type === "delegation",
  ).map((e) => AGENT_NODES.find((n) => n.id === e.from));

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
      className="space-y-4"
    >
      <Card className="p-5">
        <div className="mb-1 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-xl",
                node.bgColor,
              )}
            >
              <Icon className={cn("h-6 w-6", node.color)} />
            </div>
            <div>
              <h3 className={cn("text-lg font-bold", node.color)}>
                {node.label}
              </h3>
              <p className="text-xs text-muted-foreground">
                {GROUPS[node.group]?.label}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          {node.description}
        </p>
      </Card>

      {/* Relationships */}
      {delegatedBy.length > 0 && (
        <Card className="p-4">
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Receives tasks from
          </h4>
          <div className="space-y-1.5">
            {delegatedBy.map(
              (n) =>
                n && (
                  <div
                    key={n.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <ArrowDown className="h-3 w-3 text-muted-foreground/40" />
                    <n.icon className={cn("h-3.5 w-3.5", n.color)} />
                    <span className={n.color}>{n.label}</span>
                  </div>
                ),
            )}
          </div>
        </Card>
      )}

      {delegatesTo.length > 0 && (
        <Card className="p-4">
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Delegates to
          </h4>
          <div className="space-y-1.5">
            {delegatesTo.map(
              (n) =>
                n && (
                  <div
                    key={n.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <ArrowDown className="h-3 w-3 text-muted-foreground/40" />
                    <n.icon className={cn("h-3.5 w-3.5", n.color)} />
                    <span className={n.color}>{n.label}</span>
                  </div>
                ),
            )}
          </div>
        </Card>
      )}

      {consultsWith.length > 0 && (
        <Card className="p-4">
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Cross-consults with
          </h4>
          <div className="space-y-1.5">
            {consultsWith.map(
              (n) =>
                n && (
                  <div
                    key={n.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <ArrowLeftRight className="h-3 w-3 text-muted-foreground/40" />
                    <n.icon className={cn("h-3.5 w-3.5", n.color)} />
                    <span className={n.color}>{n.label}</span>
                  </div>
                ),
            )}
          </div>
        </Card>
      )}
    </motion.div>
  );
}

// ─── Architecture Page ────────────────────────────────────────────────────────

export function ArchitecturePage() {
  const { data, isLoading } = useAgents();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [edgeFilter, setEdgeFilter] = useState<EdgeType | "all">("all");

  const agentsList = data?.agents ?? [];
  const statusMap = new Map<string, string>();
  agentsList.forEach((a) => statusMap.set(a.name, a.status));

  const selectedNode = AGENT_NODES.find((n) => n.id === selectedNodeId);

  // Group agents
  const groupedAgents: Record<string, AgentNodeDef[]> = {};
  for (const node of AGENT_NODES) {
    if (!groupedAgents[node.group]) groupedAgents[node.group] = [];
    groupedAgents[node.group].push(node);
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Network className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">
              Agent Architecture
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Full team topology with delegation flows and cross-consultation channels.
          </p>
        </div>

        {/* Edge type filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {(
            [
              { key: "all" as const, label: "All" },
              { key: "delegation" as const, label: "Delegation" },
              { key: "consultation" as const, label: "Consultation" },
            ] as const
          ).map(({ key, label }) => (
            <Button
              key={key}
              variant={edgeFilter === key ? "default" : "outline"}
              size="sm"
              onClick={() => setEdgeFilter(key)}
              className="text-xs"
            >
              {label}
            </Button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-6 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <ArrowDown className="h-3 w-3" />
          <span>Delegation (task assignment)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <ArrowLeftRight className="h-3 w-3" />
          <span className="border-b border-dashed border-muted-foreground">
            Cross-consultation (bidirectional)
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>Enabled</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-amber-500" />
          <span>Primary</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-red-500" />
          <span>Disabled</span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-4">
          {/* Graph area */}
          <div className="space-y-4 xl:col-span-3">
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
                          setSelectedNodeId(
                            selectedNodeId === node.id ? null : node.id,
                          )
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
              {(edgeFilter === "all" || edgeFilter === "delegation") && (
                <div className="flex items-center gap-2 text-[11px] text-blue-400/60">
                  <ArrowDown className="h-3.5 w-3.5" />
                  <span>
                    Architect delegates tasks to all specialist groups
                  </span>
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

          {/* Detail sidebar */}
          <div className="xl:col-span-1">
            <div className="sticky top-6">
              <AnimatePresence mode="wait">
                {selectedNode ? (
                  <DetailPanel
                    key={selectedNode.id}
                    node={selectedNode}
                    onClose={() => setSelectedNodeId(null)}
                  />
                ) : (
                  <motion.div
                    key="placeholder"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <Card className="flex items-center justify-center p-10 text-center">
                      <div>
                        <Network className="mx-auto mb-3 h-10 w-10 text-muted-foreground/15" />
                        <p className="text-sm text-muted-foreground/50">
                          Select an agent to view its relationships
                        </p>
                        <p className="mt-1 flex items-center justify-center gap-1 text-[10px] text-muted-foreground/30">
                          <Info className="h-3 w-3" />
                          Click any node on the graph
                        </p>
                      </div>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
