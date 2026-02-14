import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Info } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { AgentDetail } from "@/lib/types";
import {
  AGENT_NODES,
  Legend,
  AgentDetailSidebar,
} from "./architecture/AgentRoleConfig";
import { GraphVisualization } from "./architecture/GraphVisualization";

export function TeamArchitectureTab({
  agents,
}: {
  agents?: AgentDetail[];
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const statusMap = useMemo(() => {
    const m = new Map<string, string>();
    agents?.forEach((a) => m.set(a.name, a.status));
    return m;
  }, [agents]);

  const selectedNode = AGENT_NODES.find((n) => n.id === selectedNodeId);

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center justify-between">
        <Legend />
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
          <Info className="h-3 w-3" />
          Click a node for details
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* SVG Graph */}
        <div className="lg:col-span-2">
          <GraphVisualization
            statusMap={statusMap}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
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
                  Select a node to view details
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
