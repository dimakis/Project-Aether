import {
  Bot,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
  BookOpen,
  Wrench,
  Code,
  BarChart3,
  Brain,
  Tags,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ─── Agent Node Data ──────────────────────────────────────────────────────────

export interface AgentNodeDef {
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

export const AGENT_NODES: AgentNodeDef[] = [
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

export const AGENT_MAP = new Map(AGENT_NODES.map((n) => [n.id, n]));

// ─── Edge Definitions ─────────────────────────────────────────────────────────

export type EdgeType = "delegation" | "consultation" | "data-flow";

export interface EdgeDef {
  from: string;
  to: string;
  type: EdgeType;
  label?: string;
}

export const EDGES: EdgeDef[] = [
  { from: "aether", to: "architect", type: "data-flow" },
  { from: "architect", to: "data_science_team", type: "delegation", label: "consult DS" },
  { from: "data_science_team", to: "energy_analyst", type: "delegation" },
  { from: "data_science_team", to: "behavioral_analyst", type: "delegation" },
  { from: "data_science_team", to: "diagnostic_analyst", type: "delegation" },
  { from: "architect", to: "developer", type: "delegation" },
  { from: "architect", to: "dashboard_designer", type: "delegation" },
  { from: "architect", to: "librarian", type: "delegation" },
  { from: "architect", to: "sandbox", type: "delegation" },
  { from: "energy_analyst", to: "behavioral_analyst", type: "consultation" },
  { from: "energy_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "behavioral_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "dashboard_designer", to: "energy_analyst", type: "consultation", label: "consults" },
  { from: "dashboard_designer", to: "behavioral_analyst", type: "consultation", label: "consults" },
  { from: "librarian", to: "categorizer", type: "data-flow", label: "entities" },
];

export const EDGE_STYLES: Record<EdgeType, { dash: string; width: number }> = {
  delegation: { dash: "", width: 1.5 },
  consultation: { dash: "4 3", width: 1 },
  "data-flow": { dash: "2 2", width: 1 },
};

// ─── SVG Layout ────────────────────────────────────────────────────────────────

export const SVG_W = 700;
export const SVG_H = 480;
export const NODE_R = 24;

/** Hand-tuned positions for an organic architecture layout */
export const POSITIONS: Record<string, { x: number; y: number }> = {
  aether:              { x: 350, y: 40 },
  architect:           { x: 350, y: 130 },
  data_science_team:   { x: 160, y: 230 },
  energy_analyst:      { x: 60, y: 330 },
  behavioral_analyst:  { x: 170, y: 370 },
  diagnostic_analyst:  { x: 280, y: 330 },
  dashboard_designer:  { x: 440, y: 250 },
  developer:           { x: 560, y: 250 },
  sandbox:             { x: 640, y: 340 },
  librarian:           { x: 300, y: 430 },
  categorizer:         { x: 430, y: 430 },
};

// ─── Components ───────────────────────────────────────────────────────────────

export function AgentDetailSidebar({ node }: { node: AgentNodeDef }) {
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

export function Legend() {
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
