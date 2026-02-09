/**
 * Single source of truth for agent metadata across the activity panel.
 *
 * Consolidates agent colours, labels, icons, and delegation edges that
 * were previously duplicated across agent-activity-panel.tsx,
 * agent-topology.tsx, trace-timeline.tsx, and trace-event-handler.ts.
 */

import type { LucideIcon } from "lucide-react";
import {
  Bot,
  BarChart3,
  Code,
  BookOpen,
  Wrench,
  Server,
  Zap,
  Users,
  Stethoscope,
  LayoutDashboard,
  Brain,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AgentMeta {
  /** Display label (e.g. "Architect", "DS Team"). */
  label: string;
  /** Lucide icon component. */
  icon: LucideIcon;
  /** Tailwind text-colour class (e.g. "text-blue-400"). */
  color: string;
  /** Hex colour for SVG strokes and fills. */
  hex: string;
  /** Space-separated RGB for CSS glow effects (e.g. "96 165 250"). */
  glowRgb: string;
}

// ─── Agent Registry ──────────────────────────────────────────────────────────

export const AGENTS: Record<string, AgentMeta> = {
  aether: {
    label: "Aether",
    icon: Brain,
    color: "text-primary",
    hex: "#a855f7",
    glowRgb: "168 85 247",
  },
  architect: {
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    hex: "#60a5fa",
    glowRgb: "96 165 250",
  },
  data_science_team: {
    label: "DS Team",
    icon: BarChart3,
    color: "text-emerald-400",
    hex: "#34d399",
    glowRgb: "52 211 153",
  },
  energy_analyst: {
    label: "Energy",
    icon: Zap,
    color: "text-yellow-400",
    hex: "#facc15",
    glowRgb: "250 204 21",
  },
  behavioral_analyst: {
    label: "Behavioral",
    icon: Users,
    color: "text-teal-400",
    hex: "#2dd4bf",
    glowRgb: "45 212 191",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    icon: Stethoscope,
    color: "text-rose-400",
    hex: "#fb7185",
    glowRgb: "251 113 133",
  },
  dashboard_designer: {
    label: "Dashboard",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    hex: "#818cf8",
    glowRgb: "129 140 248",
  },
  synthesizer: {
    label: "Synthesizer",
    icon: Code,
    color: "text-orange-400",
    hex: "#fb923c",
    glowRgb: "251 146 60",
  },
  librarian: {
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    hex: "#c084fc",
    glowRgb: "192 132 252",
  },
  developer: {
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    hex: "#fbbf24",
    glowRgb: "251 191 36",
  },
  system: {
    label: "System",
    icon: Server,
    color: "text-muted-foreground",
    hex: "#a1a1aa",
    glowRgb: "161 161 170",
  },
};

// ─── Derived Helpers ─────────────────────────────────────────────────────────

/**
 * Canonical list of agents shown in the topology graph.
 * Excludes "system" which is an internal classification, not a real agent.
 */
export const TOPOLOGY_AGENT_IDS: string[] = [
  "aether",
  "architect",
  "data_science_team",
  "energy_analyst",
  "behavioral_analyst",
  "diagnostic_analyst",
  "dashboard_designer",
  "synthesizer",
  "librarian",
  "developer",
];

/**
 * Edges that reflect actual workflow delegation paths in the codebase.
 *
 * Sources:
 *  - aether -> architect: conversation entry point (system → primary agent)
 *  - architect -> data_science_team: consult_data_science_team tool
 *  - architect -> developer: developer_deploy_node (approved proposals)
 *  - architect -> librarian: discover_entities tool
 *  - architect -> dashboard_designer: dashboard generation workflow
 *  - data_science_team -> analysts: specialist_tools routing
 *  - energy -> behavioral -> diagnostic: team_analysis sequential pipeline
 *  - data_science_team -> synthesizer: auto-synthesis when 2+ specialists contribute
 */
export const DELEGATION_EDGES: [string, string][] = [
  // Entry point
  ["aether", "architect"],
  // Architect delegations
  ["architect", "data_science_team"],
  ["architect", "developer"],
  ["architect", "librarian"],
  ["architect", "dashboard_designer"],
  // DS team -> specialist analysts
  ["data_science_team", "energy_analyst"],
  ["data_science_team", "behavioral_analyst"],
  ["data_science_team", "diagnostic_analyst"],
  // Team analysis sequential pipeline
  ["energy_analyst", "behavioral_analyst"],
  ["behavioral_analyst", "diagnostic_analyst"],
  // Auto-synthesis after specialist analysis
  ["data_science_team", "synthesizer"],
];

/**
 * Brain layout: fractional (0-1) target positions for each agent.
 *
 * Arranged as a top-down neural hierarchy:
 *  - Tier 0 (crown): Aether — system entry, pinned at top
 *  - Tier 1 (cortex): Architect — primary routing hub
 *  - Tier 2 (lobes): Direct delegates fan out left-to-right
 *  - Tier 3 (deep): DS specialist analysts
 *  - Tier 4 (stem): Synthesizer — analysis output
 */
export const BRAIN_LAYOUT: Record<string, { x: number; y: number }> = {
  aether:             { x: 0.50, y: 0.07 },
  architect:          { x: 0.50, y: 0.26 },
  // Left lobe — utility / knowledge
  librarian:          { x: 0.12, y: 0.48 },
  dashboard_designer: { x: 0.34, y: 0.50 },
  // Center — execution
  developer:          { x: 0.56, y: 0.52 },
  // Right lobe — analytics
  data_science_team:  { x: 0.82, y: 0.40 },
  energy_analyst:     { x: 0.68, y: 0.68 },
  behavioral_analyst: { x: 0.90, y: 0.68 },
  diagnostic_analyst: { x: 0.79, y: 0.84 },
  synthesizer:        { x: 0.92, y: 0.92 },
};

// ─── Lookup Helpers ──────────────────────────────────────────────────────────

/** Get the Tailwind color class for an agent, with fallback. */
export function agentColor(agentId: string): string {
  return AGENTS[agentId]?.color ?? AGENTS.system.color;
}

/** Get the hex colour for an agent, with fallback. */
export function agentHex(agentId: string): string {
  return AGENTS[agentId]?.hex ?? AGENTS.system.hex;
}

/** Get the display label for an agent, with fallback. */
export function agentLabel(agentId: string): string {
  if (AGENTS[agentId]) return AGENTS[agentId].label;
  // Fallback: convert snake_case to Title Case
  return agentId
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Get full agent metadata, falling back to the "system" entry. */
export function agentMeta(agentId: string): AgentMeta {
  return AGENTS[agentId] ?? AGENTS.system;
}
