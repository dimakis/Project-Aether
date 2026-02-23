import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network,
  Filter,
  Info,
  Loader2,
  ArrowDown,
  ArrowLeftRight,
  Layers,
  Server,
  Monitor,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAgents, useAvailableAgents, useSystemStatus } from "@/api/hooks";
import { ArchitectureGraph } from "./ArchitectureGraph";
import { ArchitecturePanel } from "./ArchitecturePanel";
import {
  AGENT_NODES,
  type AgentNodeDef,
  type EdgeType,
} from "./config";

// ─── Architecture Page ────────────────────────────────────────────────────────

export function ArchitecturePage() {
  const { data, isLoading } = useAgents();
  const { data: availableData } = useAvailableAgents();
  const { data: systemStatus } = useSystemStatus();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [edgeFilter, setEdgeFilter] = useState<EdgeType | "all">("all");

  const agentsList = data?.agents ?? [];
  const statusMap = new Map<string, string>();
  agentsList.forEach((a) => statusMap.set(a.name, a.status));

  const deploymentMode = systemStatus?.deployment_mode ?? "monolith";

  // Merge dynamic agents from /agents/available into static config
  const mergedNodes = useMemo(() => {
    if (!availableData?.agents) return AGENT_NODES;

    const staticIds = new Set(AGENT_NODES.map((n) => n.id));
    const dynamicNodes: AgentNodeDef[] = availableData.agents
      .filter((a) => !staticIds.has(a.name))
      .map((a) => ({
        id: a.name,
        label: a.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        icon: Server,
        color: "text-slate-400",
        bgColor: "bg-slate-400/10",
        borderColor: "border-slate-400/30",
        group: "discovery" as const,
        description: a.description || `Dynamic agent: ${a.domain ?? "general"}`,
      }));

    return [...AGENT_NODES, ...dynamicNodes];
  }, [availableData]);

  const selectedNode = mergedNodes.find((n) => n.id === selectedNodeId);

  const groupedAgents: Record<string, AgentNodeDef[]> = {};
  for (const node of mergedNodes) {
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
            <Badge
              variant={deploymentMode === "distributed" ? "default" : "outline"}
              className="ml-2 gap-1 text-[10px]"
            >
              {deploymentMode === "distributed" ? (
                <Layers className="h-3 w-3" />
              ) : (
                <Monitor className="h-3 w-3" />
              )}
              {deploymentMode === "distributed" ? "Distributed" : "Monolith"}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Full team topology with delegation flows and cross-consultation
            channels.
            {availableData && (
              <span className="ml-1 text-muted-foreground/60">
                {availableData.total} routable agent{availableData.total !== 1 ? "s" : ""}
              </span>
            )}
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
              { key: "a2a" as const, label: "A2A" },
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
          <Layers className="h-3 w-3" />
          <span className="border-b border-double border-muted-foreground">
            A2A protocol
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
            <ArchitectureGraph
              groupedAgents={groupedAgents}
              statusMap={statusMap}
              selectedNodeId={selectedNodeId}
              onNodeSelect={setSelectedNodeId}
              edgeFilter={edgeFilter}
            />
          </div>

          {/* Detail sidebar */}
          <div className="xl:col-span-1">
            <div className="sticky top-6">
              <AnimatePresence mode="wait">
                {selectedNode ? (
                  <ArchitecturePanel
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
