import {
  Bot,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
  BookOpen,
  Wrench,
} from "lucide-react";

// ─── Agent Node Definitions ───────────────────────────────────────────────────

export interface AgentNodeDef {
  id: string;
  label: string;
  icon: typeof Bot;
  color: string;
  bgColor: string;
  borderColor: string;
  group: "orchestration" | "ds-team" | "deployment" | "discovery";
  description: string;
}

export const AGENT_NODES: AgentNodeDef[] = [
  {
    id: "architect",
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
    group: "orchestration",
    description:
      "Primary orchestrator. Delegates to specialists, manages conversation, coordinates multi-agent workflows.",
  },
  {
    id: "energy_analyst",
    label: "Energy Analyst",
    icon: Zap,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
    borderColor: "border-yellow-400/30",
    group: "ds-team",
    description:
      "Analyzes energy consumption patterns, identifies cost optimization opportunities, and monitors power usage trends.",
  },
  {
    id: "behavioral_analyst",
    label: "Behavioral Analyst",
    icon: Users,
    color: "text-teal-400",
    bgColor: "bg-teal-400/10",
    borderColor: "border-teal-400/30",
    group: "ds-team",
    description:
      "Detects user behavior patterns, routines, scene/script usage, and identifies automation opportunities.",
  },
  {
    id: "diagnostic_analyst",
    label: "Diagnostic Analyst",
    icon: Stethoscope,
    color: "text-rose-400",
    bgColor: "bg-rose-400/10",
    borderColor: "border-rose-400/30",
    group: "ds-team",
    description:
      "Monitors system health, diagnoses integration errors, checks entity availability and config validity.",
  },
  {
    id: "dashboard_designer",
    label: "Dashboard Designer",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    bgColor: "bg-indigo-400/10",
    borderColor: "border-indigo-400/30",
    group: "deployment",
    description:
      "Designs and generates Lovelace dashboards, consults DS team for data-driven layouts, previews before deploy.",
  },
  {
    id: "developer",
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10",
    borderColor: "border-amber-400/30",
    group: "deployment",
    description:
      "Deploys automations, scripts, and scenes to Home Assistant. Generates YAML configurations.",
  },
  {
    id: "librarian",
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
    group: "discovery",
    description:
      "Discovers and catalogs HA entities, infers devices and areas, syncs entity database.",
  },
];

// ─── Edge Definitions ─────────────────────────────────────────────────────────

export type EdgeType = "delegation" | "consultation";

export interface EdgeDef {
  from: string;
  to: string;
  type: EdgeType;
  label?: string;
}

export const EDGES: EdgeDef[] = [
  { from: "architect", to: "energy_analyst", type: "delegation" },
  { from: "architect", to: "behavioral_analyst", type: "delegation" },
  { from: "architect", to: "diagnostic_analyst", type: "delegation" },
  { from: "architect", to: "developer", type: "delegation" },
  { from: "architect", to: "dashboard_designer", type: "delegation" },
  { from: "architect", to: "librarian", type: "delegation" },
  { from: "energy_analyst", to: "behavioral_analyst", type: "consultation" },
  { from: "energy_analyst", to: "diagnostic_analyst", type: "consultation" },
  { from: "behavioral_analyst", to: "diagnostic_analyst", type: "consultation" },
  {
    from: "dashboard_designer",
    to: "energy_analyst",
    type: "consultation",
    label: "consults",
  },
  {
    from: "dashboard_designer",
    to: "behavioral_analyst",
    type: "consultation",
    label: "consults",
  },
];

// ─── Group Metadata ───────────────────────────────────────────────────────────

export const GROUPS: Record<
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

export const GROUP_ORDER = ["orchestration", "ds-team", "deployment", "discovery"];
