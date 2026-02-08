import { useMemo, useState } from "react";
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
  Brain,
  Tags,
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
  hex: string;
  bgColor: string;
  borderColor: string;
  group: "orchestration" | "ds-team" | "deployment" | "discovery";
  agentType: "llm" | "programmatic";
  description: string;
}

const AGENT_NODES: AgentNodeDef[] = [
  {
    id: "aether",
    label: "Aether",
    icon: Brain,
    color: "text-primary",
    hex: "#a855f7",
    bgColor: "bg-primary/10",
    borderColor: "border-primary/30",
    group: "orchestration",
    agentType: "programmatic",
    description: "Central system hub. All signals flow through Aether.",
  },
  {
    id: "architect",
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    hex: "#60a5fa",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
    group: "orchestration",
    agentType: "llm",
    description: "Primary orchestrator. Delegates analysis to DS team via a single tool call.",
  },
  {
    id: "data_science_team",
    label: "DS Coordinator",
    icon: BarChart3,
    color: "text-emerald-400",
    hex: "#34d399",
    bgColor: "bg-emerald-400/10",
    borderColor: "border-emerald-400/30",
    group: "ds-team",
    agentType: "programmatic",
    description: "Head Data Scientist. Programmatic coordinator that selects and dispatches specialist analysts.",
  },
  {
    id: "energy_analyst",
    label: "Energy Analyst",
    icon: Zap,
    color: "text-yellow-400",
    hex: "#facc15",
    bgColor: "bg-yellow-400/10",
    borderColor: "border-yellow-400/30",
    group: "ds-team",
    agentType: "llm",
    description: "Analyzes energy consumption, cost optimization, and usage patterns.",
  },
  {
    id: "behavioral_analyst",
    label: "Behavioral Analyst",
    icon: Users,
    color: "text-teal-400",
    hex: "#2dd4bf",
    bgColor: "bg-teal-400/10",
    borderColor: "border-teal-400/30",
    group: "ds-team",
    agentType: "llm",
    description: "Detects user behavior patterns, routines, and automation opportunities.",
  },
  {
    id: "diagnostic_analyst",
    label: "Diagnostic Analyst",
    icon: Stethoscope,
    color: "text-rose-400",
    hex: "#fb7185",
    bgColor: "bg-rose-400/10",
    borderColor: "border-rose-400/30",
    group: "ds-team",
    agentType: "llm",
    description: "Monitors system health, diagnoses errors, and checks integrations.",
  },
  {
    id: "dashboard_designer",
    label: "Dashboard Designer",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    hex: "#818cf8",
    bgColor: "bg-indigo-400/10",
    borderColor: "border-indigo-400/30",
    group: "deployment",
    agentType: "llm",
    description: "Designs Lovelace dashboards, consults DS team for data-driven layouts.",
  },
  {
    id: "developer",
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    hex: "#fbbf24",
    bgColor: "bg-amber-400/10",
    borderColor: "border-amber-400/30",
    group: "deployment",
    agentType: "llm",
    description: "Deploys automations, scripts, and scenes to Home Assistant.",
  },
  {
    id: "sandbox",
    label: "Sandbox",
    icon: Code,
    color: "text-orange-400",
    hex: "#fb923c",
    bgColor: "bg-orange-400/10",
    borderColor: "border-orange-400/30",
    group: "deployment",
    agentType: "programmatic",
    description: "Isolated gVisor sandbox for running generated scripts safely.",
  },
  {
    id: "librarian",
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    hex: "#c084fc",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
    group: "discovery",
    agentType: "llm",
    description: "Discovers and catalogs HA entities, devices, and areas.",
  },
  {
    id: "categorizer",
    label: "Categorizer",
    icon: Tags,
    color: "text-zinc-400",
    hex: "#a1a1aa",
    bgColor: "bg-zinc-400/10",
    borderColor: "border-zinc-400/30",
    group: "discovery",
    agentType: "programmatic",
    description: "Categorizes and normalizes discovered entities into the registry.",
  },
];

const AGENT_MAP = new Map(AGENT_NODES.map((n) => [n.id, n]));

// ─── Edge Definitions ─────────────────────────────────────────────────────────

type EdgeType = "delegation" | "consultation" | "data-flow";

interface EdgeDef {
  from: string;
  to: string;
  type: EdgeType;
  label?: string;
}

const EDGES: EdgeDef[] = [
  // Aether hub connections
  { from: "aether", to: "architect", type: "data-flow" },
  // Architect delegates to DS team via consult_data_science_team
  { from: "architect", to: "data_science_team", type: "delegation", label: "consult DS" },
  // DS coordinator dispatches to specialists
  { from: "data_science_team", to: "energy_analyst", type: "delegation" },
  { from: "data_science_team", to: "behavioral_analyst", type: "delegation" },
  { from: "data_science_team", to: "diagnostic_analyst", type: "delegation" },
  // Architect delegates to other agents directly
  { from: "architect", to: "developer", type: "delegation" },
  { from: "architect", to: "dashboard_designer", type: "delegation" },
  { from: "architect", to: "librarian", type: "delegation" },
  { from: "architect", to: "sandbox", type: "delegation" },
  // DS team cross-consultation (shared TeamAnalysis)
  { from: "energy_analyst", to: "behavioral_analyst", type: "consultation" },
  { from: "energy_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "behavioral_analyst", to: "diagnostic_analyst", type: "consultation" },
  // Dashboard Designer consults DS team
  { from: "dashboard_designer", to: "energy_analyst", type: "consultation", label: "consults" },
  { from: "dashboard_designer", to: "behavioral_analyst", type: "consultation", label: "consults" },
  // Librarian -> Categorizer pipeline
  { from: "librarian", to: "categorizer", type: "data-flow", label: "entities" },
];

// ─── SVG Graph Layout ─────────────────────────────────────────────────────────

const SVG_W = 700;
const SVG_H = 480;
const NODE_R = 24;

/** Hand-tuned positions for an organic architecture layout */
const POSITIONS: Record<string, { x: number; y: number }> = {
  aether:              { x: SVG_W / 2,       y: 40 },
  architect:           { x: SVG_W / 2,       y: 130 },
  // DS team cluster — left
  data_science_team:   { x: 160,             y: 230 },
  energy_analyst:      { x: 60,              y: 330 },
  behavioral_analyst:  { x: 170,             y: 370 },
  diagnostic_analyst:  { x: 280,             y: 330 },
  // Deployment — right
  dashboard_designer:  { x: 440,             y: 250 },
  developer:           { x: 560,             y: 250 },
  sandbox:             { x: 640,             y: 340 },
  // Discovery — bottom center
  librarian:           { x: SVG_W / 2 - 50,  y: 430 },
  categorizer:         { x: SVG_W / 2 + 80,  y: 430 },
};

const EDGE_STYLES: Record<EdgeType, { dash: string; width: number }> = {
  delegation:   { dash: "",          width: 1.5 },
  consultation: { dash: "4 3",       width: 1 },
  "data-flow":  { dash: "2 2",       width: 1 },
};

// ─── Components ───────────────────────────────────────────────────────────────

function AgentDetailSidebar({ node }: { node: AgentNodeDef }) {
  const Icon = node.icon;

  const delegatesTo = EDGES.filter(
    (e) => e.from === node.id && e.type === "delegation",
  ).map((e) => AGENT_MAP.get(e.to)?.label ?? e.to);

  const consultsWith = EDGES.filter(
    (e) =>
      (e.from === node.id || e.to === node.id) &&
      e.type === "consultation",
  ).map((e) => {
    const otherId = e.from === node.id ? e.to : e.from;
    return AGENT_MAP.get(otherId)?.label ?? otherId;
  });

  const delegatedBy = EDGES.filter(
    (e) => e.to === node.id && e.type === "delegation",
  ).map((e) => AGENT_MAP.get(e.from)?.label ?? e.from);

  const dataFlows = EDGES.filter(
    (e) =>
      (e.from === node.id || e.to === node.id) &&
      e.type === "data-flow",
  ).map((e) => {
    const otherId = e.from === node.id ? e.to : e.from;
    const dir = e.from === node.id ? "to" : "from";
    return { name: AGENT_MAP.get(otherId)?.label ?? otherId, dir };
  });

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", node.bgColor)}>
          <Icon className={cn("h-5 w-5", node.color)} />
        </div>
        <div>
          <h3 className={cn("text-base font-bold", node.color)}>{node.label}</h3>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[9px]">
              {node.agentType === "llm" ? "LLM Agent" : "Programmatic"}
            </Badge>
          </div>
        </div>
      </div>

      <p className="mb-4 text-sm text-muted-foreground">{node.description}</p>

      {delegatedBy.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Receives tasks from
          </p>
          <div className="flex flex-wrap gap-1">
            {delegatedBy.map((name) => (
              <Badge key={name} variant="outline" className="text-[10px]">{name}</Badge>
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
              <Badge key={name} variant="outline" className="text-[10px]">{name}</Badge>
            ))}
          </div>
        </div>
      )}

      {consultsWith.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Cross-consults with
          </p>
          <div className="flex flex-wrap gap-1">
            {consultsWith.map((name) => (
              <Badge key={name} variant="outline" className="text-[10px]">{name}</Badge>
            ))}
          </div>
        </div>
      )}

      {dataFlows.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Data flows
          </p>
          <div className="flex flex-wrap gap-1">
            {dataFlows.map(({ name, dir }) => (
              <Badge key={name} variant="outline" className="text-[10px]">
                {dir === "to" ? `-> ${name}` : `<- ${name}`}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
      <div className="flex items-center gap-1.5">
        <div className="h-px w-5 border-t-2 border-muted-foreground/40" />
        <span>Delegation</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-px w-5 border-t-2 border-dashed border-muted-foreground/40" />
        <span>Consultation</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-px w-5 border-t border-dotted border-muted-foreground/40" />
        <span>Data flow</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-3 w-3 rounded-full border border-primary/40 bg-primary/10" />
        <span>LLM</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-3 w-3 rounded-sm border border-muted-foreground/40 bg-muted/30" />
        <span>Programmatic</span>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

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
          <svg
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            className="w-full overflow-visible"
            style={{ maxHeight: 500 }}
          >
            <defs>
              <marker
                id="arrow-delegation"
                markerWidth="8"
                markerHeight="6"
                refX="7"
                refY="3"
                orient="auto"
              >
                <polygon
                  points="0 0, 8 3, 0 6"
                  fill="hsl(var(--muted-foreground))"
                  opacity={0.4}
                />
              </marker>
            </defs>

            {/* Edges */}
            {EDGES.map((edge) => {
              const pA = POSITIONS[edge.from];
              const pB = POSITIONS[edge.to];
              if (!pA || !pB) return null;

              const style = EDGE_STYLES[edge.type];
              const dx = pB.x - pA.x;
              const dy = pB.y - pA.y;
              const dist = Math.sqrt(dx * dx + dy * dy);
              if (dist < 1) return null;
              const nx = dx / dist;
              const ny = dy / dist;
              const x1 = pA.x + nx * (NODE_R + 3);
              const y1 = pA.y + ny * (NODE_R + 3);
              const x2 = pB.x - nx * (NODE_R + 3);
              const y2 = pB.y - ny * (NODE_R + 3);

              const midX = (x1 + x2) / 2;
              const midY = (y1 + y2) / 2;

              return (
                <g key={`${edge.from}-${edge.to}`}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="hsl(var(--border))"
                    strokeWidth={style.width}
                    strokeDasharray={style.dash || undefined}
                    strokeOpacity={0.5}
                    markerEnd={
                      edge.type === "delegation"
                        ? "url(#arrow-delegation)"
                        : undefined
                    }
                  />
                  {edge.label && (
                    <text
                      x={midX}
                      y={midY - 6}
                      textAnchor="middle"
                      fontSize="8"
                      fill="hsl(var(--muted-foreground))"
                      opacity={0.5}
                    >
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Nodes */}
            {AGENT_NODES.map((node) => {
              const pos = POSITIONS[node.id];
              if (!pos) return null;
              const Icon = node.icon;
              const isSelected = selectedNodeId === node.id;
              const status = statusMap.get(node.id);
              const isAether = node.id === "aether";
              const r = isAether ? NODE_R + 6 : NODE_R;

              return (
                <g
                  key={node.id}
                  className="cursor-pointer"
                  onClick={() =>
                    setSelectedNodeId(
                      selectedNodeId === node.id ? null : node.id,
                    )
                  }
                >
                  {/* Selection ring */}
                  {isSelected && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={r + 4}
                      fill="none"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      strokeOpacity={0.5}
                    />
                  )}

                  {/* Background */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={r}
                    fill="hsl(var(--card))"
                    stroke={isSelected ? "hsl(var(--primary))" : "hsl(var(--border))"}
                    strokeWidth={isSelected ? 2 : 1}
                  />

                  {/* Programmatic marker: square corner hint */}
                  {node.agentType === "programmatic" && !isAether && (
                    <rect
                      x={pos.x + r * 0.45}
                      y={pos.y - r - 2}
                      width={10}
                      height={10}
                      rx={2}
                      fill="hsl(var(--muted))"
                      stroke="hsl(var(--border))"
                      strokeWidth={0.5}
                    />
                  )}
                  {node.agentType === "programmatic" && !isAether && (
                    <text
                      x={pos.x + r * 0.45 + 5}
                      y={pos.y - r + 5}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fontSize="6"
                      fill="hsl(var(--muted-foreground))"
                    >
                      P
                    </text>
                  )}

                  {/* Status dot */}
                  {status && (
                    <circle
                      cx={pos.x - r * 0.6}
                      cy={pos.y - r * 0.6}
                      r={4}
                      fill={
                        status === "enabled" || status === "primary"
                          ? "#22c55e"
                          : status === "disabled"
                            ? "#ef4444"
                            : "#a1a1aa"
                      }
                    />
                  )}

                  {/* Icon */}
                  <foreignObject
                    x={pos.x - (isAether ? 12 : 10)}
                    y={pos.y - (isAether ? 12 : 10)}
                    width={isAether ? 24 : 20}
                    height={isAether ? 24 : 20}
                  >
                    <Icon
                      className={cn(
                        isAether ? "h-6 w-6" : "h-5 w-5",
                        node.color,
                      )}
                    />
                  </foreignObject>

                  {/* Label */}
                  <text
                    x={pos.x}
                    y={pos.y + r + 14}
                    textAnchor="middle"
                    fontSize="10"
                    fontWeight={isAether ? "600" : "500"}
                    fill="currentColor"
                    className={cn("fill-current", node.color)}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
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
