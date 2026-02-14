import { motion } from "framer-motion";
import { ArrowDown, ArrowLeftRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { AGENT_NODES, EDGES, GROUPS, type AgentNodeDef } from "./config";

// ─── Detail Panel Component ──────────────────────────────────────────────────

export interface ArchitecturePanelProps {
  node: AgentNodeDef;
  onClose: () => void;
}

export function ArchitecturePanel({ node, onClose }: ArchitecturePanelProps) {
  const Icon = node.icon;

  const delegatesTo = EDGES.filter(
    (e) => e.from === node.id && e.type === "delegation",
  ).map((e) => AGENT_NODES.find((n) => n.id === e.to));

  const consultsWith = EDGES.filter(
    (e) =>
      (e.from === node.id || e.to === node.id) && e.type === "consultation",
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
