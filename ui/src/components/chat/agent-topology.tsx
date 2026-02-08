import { useMemo } from "react";
import { motion } from "framer-motion";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SpanNode } from "@/lib/types";
import type { AgentNodeState } from "@/lib/agent-activity-store";

/** Agent metadata for the topology visualization */
const AGENTS: Record<
  string,
  {
    label: string;
    icon: typeof Bot;
    color: string;
    /** RGB value (space-separated) for glow effects */
    glowRgb: string;
    /** Hex colour for SVG edges */
    hex: string;
    group?: string;
  }
> = {
  architect: {
    label: "Architect",
    icon: Bot,
    color: "text-blue-400",
    glowRgb: "96 165 250",
    hex: "#60a5fa",
  },
  data_science_team: {
    label: "DS Team",
    icon: BarChart3,
    color: "text-emerald-400",
    glowRgb: "52 211 153",
    hex: "#34d399",
    group: "ds-team",
  },
  energy_analyst: {
    label: "Energy",
    icon: Zap,
    color: "text-yellow-400",
    glowRgb: "250 204 21",
    hex: "#facc15",
    group: "ds-team",
  },
  behavioral_analyst: {
    label: "Behavioral",
    icon: Users,
    color: "text-teal-400",
    glowRgb: "45 212 191",
    hex: "#2dd4bf",
    group: "ds-team",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    icon: Stethoscope,
    color: "text-rose-400",
    glowRgb: "251 113 133",
    hex: "#fb7185",
    group: "ds-team",
  },
  dashboard_designer: {
    label: "Dashboard",
    icon: LayoutDashboard,
    color: "text-indigo-400",
    glowRgb: "129 140 248",
    hex: "#818cf8",
  },
  sandbox: {
    label: "Sandbox",
    icon: Code,
    color: "text-orange-400",
    glowRgb: "251 146 60",
    hex: "#fb923c",
  },
  librarian: {
    label: "Librarian",
    icon: BookOpen,
    color: "text-purple-400",
    glowRgb: "192 132 252",
    hex: "#c084fc",
  },
  developer: {
    label: "Developer",
    icon: Wrench,
    color: "text-amber-400",
    glowRgb: "251 191 36",
    hex: "#fbbf24",
  },
  system: {
    label: "System",
    icon: Server,
    color: "text-muted-foreground",
    glowRgb: "161 161 170",
    hex: "#a1a1aa",
  },
};

/**
 * The canonical ordered list of all agents in the system.
 * Used by the activity panel to always show the full neural network.
 */
export const ALL_TOPOLOGY_AGENTS: string[] = [
  "architect",
  "data_science_team",
  "energy_analyst",
  "behavioral_analyst",
  "diagnostic_analyst",
  "dashboard_designer",
  "sandbox",
  "librarian",
  "developer",
];

/** Edges: which agents are connected to which */
const EDGES: [string, string][] = [
  ["architect", "data_science_team"],
  ["architect", "dashboard_designer"],
  ["architect", "sandbox"],
  ["architect", "librarian"],
  ["architect", "developer"],
  // DS team internal
  ["data_science_team", "energy_analyst"],
  ["data_science_team", "behavioral_analyst"],
  ["data_science_team", "diagnostic_analyst"],
  // Cross-consultation within DS team
  ["energy_analyst", "behavioral_analyst"],
  ["behavioral_analyst", "diagnostic_analyst"],
  ["energy_analyst", "diagnostic_analyst"],
];

interface AgentTopologyProps {
  /** Agents to display */
  agents: string[];
  /** Currently active agent (during streaming) */
  activeAgent?: string | null;
  /** Root span for extracting delegation flow */
  rootSpan?: SpanNode | null;
  /** Whether the trace is still in progress */
  isLive?: boolean;
  /** Per-agent visual state for neural activity (live mode). */
  agentStates?: Record<string, AgentNodeState>;
}

// ─── SVG Radial Graph ────────────────────────────────────────────────────────

const SVG_SIZE = 260;
const CENTER = SVG_SIZE / 2;
const RADIUS = 100;
const NODE_RADIUS = 16;

function getNodePositions(agents: string[]) {
  const positions: Record<string, { x: number; y: number }> = {};
  const n = agents.length;

  // Place architect at the top center
  const architectIdx = agents.indexOf("architect");

  agents.forEach((agent, i) => {
    let angle: number;
    if (agent === "architect") {
      // Architect at top
      angle = -Math.PI / 2;
    } else {
      // Distribute others evenly around the circle, starting from top-right
      const nonArchitectIdx = i > architectIdx ? i - 1 : i;
      const totalOther = n - 1;
      angle =
        -Math.PI / 2 +
        ((nonArchitectIdx + 1) * (2 * Math.PI)) / (totalOther + 1);
    }

    positions[agent] = {
      x: CENTER + RADIUS * Math.cos(angle),
      y: CENTER + RADIUS * Math.sin(angle),
    };
  });

  return positions;
}

export function AgentTopology({
  agents,
  activeAgent,
  isLive,
  agentStates,
}: AgentTopologyProps) {
  const displayAgents = agents.length > 0 ? agents : ALL_TOPOLOGY_AGENTS;

  const positions = useMemo(
    () => getNodePositions(displayAgents),
    [displayAgents.join(",")],
  );

  // Filter edges to only show those between displayed agents
  const visibleEdges = useMemo(
    () =>
      EDGES.filter(
        ([a, b]) =>
          displayAgents.includes(a) && displayAgents.includes(b),
      ),
    [displayAgents.join(",")],
  );

  function getNodeState(agent: string): AgentNodeState {
    if (agentStates?.[agent]) return agentStates[agent];
    if (!isLive) return "done";
    if (activeAgent === agent) return "firing";
    return "idle";
  }

  function isEdgeActive(a: string, b: string): boolean {
    if (!isLive || !agentStates) return false;
    const sA = agentStates[a];
    const sB = agentStates[b];
    return sA === "firing" || sB === "firing";
  }

  return (
    <div className="flex items-center justify-center">
      <svg
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        width={SVG_SIZE}
        height={SVG_SIZE}
        className="overflow-visible"
      >
        {/* SVG defs for glow filters */}
        <defs>
          {displayAgents.map((agent) => {
            const meta = AGENTS[agent];
            if (!meta) return null;
            return (
              <filter
                key={`glow-${agent}`}
                id={`glow-${agent}`}
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
              >
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feFlood floodColor={meta.hex} floodOpacity="0.6" />
                <feComposite in2="blur" operator="in" />
                <feMerge>
                  <feMergeNode />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            );
          })}

          {/* Animated pulse for active edges */}
          <marker
            id="arrowhead"
            markerWidth="6"
            markerHeight="4"
            refX="5"
            refY="2"
            orient="auto"
          >
            <polygon
              points="0 0, 6 2, 0 4"
              fill="currentColor"
              className="text-border"
            />
          </marker>
        </defs>

        {/* Edges */}
        {visibleEdges.map(([a, b]) => {
          const pA = positions[a];
          const pB = positions[b];
          if (!pA || !pB) return null;

          const active = isEdgeActive(a, b);
          const agentMeta = AGENTS[a] ?? AGENTS.system;

          // Shorten edge to not overlap with nodes
          const dx = pB.x - pA.x;
          const dy = pB.y - pA.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const nx = dx / dist;
          const ny = dy / dist;
          const x1 = pA.x + nx * (NODE_RADIUS + 2);
          const y1 = pA.y + ny * (NODE_RADIUS + 2);
          const x2 = pB.x - nx * (NODE_RADIUS + 2);
          const y2 = pB.y - ny * (NODE_RADIUS + 2);

          return (
            <g key={`${a}-${b}`}>
              <motion.line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={active ? agentMeta.hex : "hsl(var(--border))"}
                strokeWidth={active ? 1.5 : 0.5}
                strokeOpacity={active ? 0.8 : 0.2}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5 }}
              />
              {/* Traveling pulse on active edges */}
              {active && (
                <motion.circle
                  r={2}
                  fill={agentMeta.hex}
                  initial={{ opacity: 0 }}
                  animate={{
                    cx: [x1, x2],
                    cy: [y1, y2],
                    opacity: [1, 0.3],
                  }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                />
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {displayAgents.map((agent) => {
          const pos = positions[agent];
          if (!pos) return null;
          const meta = AGENTS[agent] ?? AGENTS.system;
          const Icon = meta.icon;
          const state = getNodeState(agent);
          const isFiring = state === "firing";
          const isDone = state === "done";
          const isDormant = state === "dormant";
          const isIdle = state === "idle";

          return (
            <motion.g
              key={agent}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{
                opacity: isDormant ? 0.2 : isIdle ? 0.4 : 1,
                scale: isFiring ? 1.1 : 1,
              }}
              transition={{ duration: 0.3 }}
              style={{ transformOrigin: `${pos.x}px ${pos.y}px` }}
            >
              {/* Background circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_RADIUS}
                fill="hsl(var(--card))"
                stroke={isFiring ? meta.hex : "hsl(var(--border))"}
                strokeWidth={isFiring ? 2 : 1}
                filter={isFiring ? `url(#glow-${agent})` : undefined}
              />

              {/* Firing pulse ring */}
              {isFiring && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={NODE_RADIUS + 4}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={1}
                  animate={{
                    r: [NODE_RADIUS + 2, NODE_RADIUS + 8],
                    opacity: [0.6, 0],
                  }}
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    ease: "easeOut",
                  }}
                />
              )}

              {/* Done checkmark */}
              {isDone && (
                <circle
                  cx={pos.x + NODE_RADIUS * 0.65}
                  cy={pos.y - NODE_RADIUS * 0.65}
                  r={5}
                  fill="#22c55e"
                />
              )}
              {isDone && (
                <text
                  x={pos.x + NODE_RADIUS * 0.65}
                  y={pos.y - NODE_RADIUS * 0.65 + 1}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize="7"
                  fill="white"
                >
                  ✓
                </text>
              )}

              {/* Icon (using foreignObject) */}
              <foreignObject
                x={pos.x - 8}
                y={pos.y - 8}
                width={16}
                height={16}
              >
                <Icon
                  className={cn(
                    "h-4 w-4",
                    meta.color,
                    (isIdle || isDormant) && "opacity-50",
                  )}
                />
              </foreignObject>

              {/* Label */}
              <text
                x={pos.x}
                y={pos.y + NODE_RADIUS + 10}
                textAnchor="middle"
                fontSize="8"
                fill="currentColor"
                className={cn(
                  "fill-current",
                  meta.color,
                  (isIdle || isDormant) && "opacity-50",
                )}
              >
                {meta.label}
              </text>
            </motion.g>
          );
        })}
      </svg>
    </div>
  );
}
