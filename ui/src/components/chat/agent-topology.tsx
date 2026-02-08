import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
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
import { cn } from "@/lib/utils";
import type { SpanNode } from "@/lib/types";
import type { AgentNodeState } from "@/lib/agent-activity-store";

// ─── Agent metadata ──────────────────────────────────────────────────────────

const AGENTS: Record<
  string,
  {
    label: string;
    icon: typeof Bot;
    color: string;
    glowRgb: string;
    hex: string;
  }
> = {
  aether: {
    label: "Aether",
    icon: Brain,
    color: "text-primary",
    glowRgb: "168 85 247",
    hex: "#a855f7",
  },
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
  },
  energy_analyst: {
    label: "Energy",
    icon: Zap,
    color: "text-yellow-400",
    glowRgb: "250 204 21",
    hex: "#facc15",
  },
  behavioral_analyst: {
    label: "Behavioral",
    icon: Users,
    color: "text-teal-400",
    glowRgb: "45 212 191",
    hex: "#2dd4bf",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    icon: Stethoscope,
    color: "text-rose-400",
    glowRgb: "251 113 133",
    hex: "#fb7185",
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

// ─── Canonical agent list ────────────────────────────────────────────────────

export const ALL_TOPOLOGY_AGENTS: string[] = [
  "aether",
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

// ─── Edges ───────────────────────────────────────────────────────────────────

/** All edges in the brain. Every agent connects to Aether (the hub). */
const EDGES: [string, string][] = [
  // Hub-and-spoke: Aether connects to every agent
  ["aether", "architect"],
  ["aether", "data_science_team"],
  ["aether", "energy_analyst"],
  ["aether", "behavioral_analyst"],
  ["aether", "diagnostic_analyst"],
  ["aether", "dashboard_designer"],
  ["aether", "sandbox"],
  ["aether", "librarian"],
  ["aether", "developer"],
  // Architect delegates
  ["architect", "data_science_team"],
  ["architect", "dashboard_designer"],
  ["architect", "sandbox"],
  ["architect", "librarian"],
  ["architect", "developer"],
  // DS team internal
  ["data_science_team", "energy_analyst"],
  ["data_science_team", "behavioral_analyst"],
  ["data_science_team", "diagnostic_analyst"],
  // DS cross-consultation
  ["energy_analyst", "behavioral_analyst"],
  ["behavioral_analyst", "diagnostic_analyst"],
  ["energy_analyst", "diagnostic_analyst"],
];

// ─── Organic brain layout ────────────────────────────────────────────────────

const SVG_SIZE = 300;
const CENTER = SVG_SIZE / 2;
const NODE_RADIUS = 15;

/**
 * Hand-tuned positions for an organic brain-like layout.
 * Aether at center. Architect above as "cortex".
 * DS cluster left hemisphere. Tool agents right. Support agents lower.
 */
const BRAIN_POSITIONS: Record<string, { x: number; y: number }> = {
  aether:              { x: CENTER,      y: CENTER },       // dead center
  architect:           { x: CENTER,      y: CENTER - 80 },  // top, cortex
  // Left hemisphere — DS team cluster
  data_science_team:   { x: CENTER - 75, y: CENTER - 30 },
  energy_analyst:      { x: CENTER - 115, y: CENTER + 20 },
  behavioral_analyst:  { x: CENTER - 60, y: CENTER + 55 },
  diagnostic_analyst:  { x: CENTER - 110, y: CENTER + 75 },
  // Right hemisphere — tool agents
  sandbox:             { x: CENTER + 80, y: CENTER - 25 },
  developer:           { x: CENTER + 110, y: CENTER + 30 },
  // Lower — support agents
  dashboard_designer:  { x: CENTER + 55, y: CENTER + 70 },
  librarian:           { x: CENTER - 10, y: CENTER + 90 },
};

// ─── Props ───────────────────────────────────────────────────────────────────

interface AgentTopologyProps {
  agents: string[];
  activeAgent?: string | null;
  rootSpan?: SpanNode | null;
  isLive?: boolean;
  agentStates?: Record<string, AgentNodeState>;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Deterministic pseudo-random per node for staggered idle timing.
 * Avoids synchronized pulsing -- each node breathes independently.
 */
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

export function AgentTopology({
  agents,
  activeAgent,
  isLive,
  agentStates,
}: AgentTopologyProps) {
  const prefersReducedMotion = useReducedMotion();
  const displayAgents = agents.length > 0 ? agents : ALL_TOPOLOGY_AGENTS;

  const positions = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    for (const agent of displayAgents) {
      pos[agent] = BRAIN_POSITIONS[agent] ?? { x: CENTER, y: CENTER };
    }
    return pos;
  }, [displayAgents.join(",")]);

  const visibleEdges = useMemo(
    () =>
      EDGES.filter(
        ([a, b]) => displayAgents.includes(a) && displayAgents.includes(b),
      ),
    [displayAgents.join(",")],
  );

  function getNodeState(agent: string): AgentNodeState {
    if (agentStates?.[agent]) return agentStates[agent];
    if (!isLive) return "done";
    if (activeAgent === agent) return "firing";
    return "idle";
  }

  // Spring configs
  const firingSpring = { type: "spring" as const, stiffness: 300, damping: 15 };
  const doneSpring = { type: "spring" as const, stiffness: 120, damping: 20 };

  return (
    <div className="flex items-center justify-center">
      <svg
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        width={SVG_SIZE}
        height={SVG_SIZE}
        className="overflow-visible"
      >
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
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feFlood floodColor={meta.hex} floodOpacity="0.5" />
                <feComposite in2="blur" operator="in" />
                <feMerge>
                  <feMergeNode />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            );
          })}
        </defs>

        {/* ── Edges ─────────────────────────────────────────────── */}
        {visibleEdges.map(([a, b], edgeIdx) => {
          const pA = positions[a];
          const pB = positions[b];
          if (!pA || !pB) return null;

          const sA = getNodeState(a);
          const sB = getNodeState(b);
          const aFiring = sA === "firing";
          const bFiring = sB === "firing";
          const edgeActive = aFiring || bFiring;

          const metaA = AGENTS[a] ?? AGENTS.system;
          const metaB = AGENTS[b] ?? AGENTS.system;

          // Shorten edge to not overlap with nodes
          const rA = a === "aether" ? NODE_RADIUS + 4 : NODE_RADIUS;
          const rB = b === "aether" ? NODE_RADIUS + 4 : NODE_RADIUS;
          const dx = pB.x - pA.x;
          const dy = pB.y - pA.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 1) return null;
          const nx = dx / dist;
          const ny = dy / dist;
          const x1 = pA.x + nx * (rA + 2);
          const y1 = pA.y + ny * (rA + 2);
          const x2 = pB.x - nx * (rB + 2);
          const y2 = pB.y - ny * (rB + 2);

          // Randomized shimmer timing per edge
          const shimmerDur = 3.5 + seededRandom(edgeIdx + 100) * 3;
          const shimmerDelay = seededRandom(edgeIdx + 200) * 2;

          return (
            <g key={`${a}-${b}`}>
              {/* Edge line */}
              <motion.line
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={
                  edgeActive
                    ? aFiring ? metaA.hex : metaB.hex
                    : "hsl(var(--border))"
                }
                strokeWidth={edgeActive ? 1.5 : 0.5}
                initial={false}
                animate={{
                  strokeOpacity: edgeActive
                    ? 0.7
                    : prefersReducedMotion
                      ? 0.1
                      : [0.06, 0.14, 0.06], // idle shimmer
                }}
                transition={
                  edgeActive
                    ? doneSpring
                    : {
                        duration: shimmerDur,
                        repeat: Infinity,
                        ease: "easeInOut",
                        delay: shimmerDelay,
                      }
                }
              />

              {/* Bidirectional traveling pulses when active */}
              {edgeActive && !prefersReducedMotion && (
                <>
                  {/* A -> B pulse */}
                  <motion.circle
                    r={2}
                    fill={metaA.hex}
                    animate={{
                      cx: [x1, x2],
                      cy: [y1, y2],
                      opacity: [0.9, 0.2],
                    }}
                    transition={{
                      duration: 1.0,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  />
                  {/* B -> A pulse (reverse, offset) */}
                  <motion.circle
                    r={1.5}
                    fill={metaB.hex}
                    animate={{
                      cx: [x2, x1],
                      cy: [y2, y1],
                      opacity: [0.7, 0.15],
                    }}
                    transition={{
                      duration: 1.3,
                      repeat: Infinity,
                      ease: "linear",
                      delay: 0.4,
                    }}
                  />
                </>
              )}
            </g>
          );
        })}

        {/* ── Nodes ─────────────────────────────────────────────── */}
        {displayAgents.map((agent, nodeIdx) => {
          const pos = positions[agent];
          if (!pos) return null;
          const meta = AGENTS[agent] ?? AGENTS.system;
          const Icon = meta.icon;
          const state = getNodeState(agent);
          const isFiring = state === "firing";
          const isDone = state === "done";
          const isAether = agent === "aether";
          const r = isAether ? NODE_RADIUS + 4 : NODE_RADIUS;

          // Randomized breathing parameters per node (seeded by index for stability)
          const rng = seededRandom(nodeIdx);
          const breatheBase = isAether ? 0.3 : 0.16 + rng * 0.06;
          const breathePeak = isAether ? 0.5 : 0.30 + rng * 0.08;
          const breatheDuration = isAether ? 2.5 : 2.5 + rng * 2.5; // 2.5-5s
          const breatheDelay = seededRandom(nodeIdx + 50) * 2.5; // 0-2.5s offset
          // Subtle scale oscillation range
          const scaleMin = isAether ? 0.98 : 0.97;
          const scaleMax = isAether ? 1.02 : 1.03;

          return (
            <motion.g
              key={agent}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={
                isFiring
                  ? { opacity: 1, scale: 1.08 }
                  : isDone
                    ? { opacity: 1, scale: 1 }
                    : prefersReducedMotion
                      ? { opacity: breathePeak, scale: 1 }
                      : {
                          // Breathing animation for idle/dormant
                          opacity: [breatheBase, breathePeak, breatheBase],
                          scale: [scaleMin, scaleMax, scaleMin],
                        }
              }
              transition={
                isFiring
                  ? firingSpring
                  : isDone
                    ? doneSpring
                    : {
                        duration: breatheDuration,
                        repeat: Infinity,
                        ease: "easeInOut",
                        delay: breatheDelay,
                      }
              }
              style={{ transformOrigin: `${pos.x}px ${pos.y}px` }}
            >
              {/* Background circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill="hsl(var(--card))"
                stroke={isFiring ? meta.hex : isAether ? meta.hex : "hsl(var(--border))"}
                strokeWidth={isFiring ? 2 : isAether ? 1.5 : 1}
                strokeOpacity={isFiring ? 1 : isAether ? 0.6 : 1}
                filter={isFiring ? `url(#glow-${agent})` : undefined}
              />

              {/* Aether ambient glow ring (always present, subtle) */}
              {isAether && !isFiring && !prefersReducedMotion && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 6}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={0.5}
                  animate={{
                    r: [r + 3, r + 8, r + 3],
                    opacity: [0.15, 0.3, 0.15],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              )}

              {/* Firing pulse ring */}
              {isFiring && !prefersReducedMotion && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 4}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={1}
                  animate={{
                    r: [r + 2, r + 10],
                    opacity: [0.6, 0],
                  }}
                  transition={{
                    duration: 0.9,
                    repeat: Infinity,
                    ease: "easeOut",
                  }}
                />
              )}

              {/* Done checkmark */}
              {isDone && !isAether && (
                <>
                  <circle
                    cx={pos.x + r * 0.6}
                    cy={pos.y - r * 0.6}
                    r={4.5}
                    fill="#22c55e"
                  />
                  <text
                    x={pos.x + r * 0.6}
                    y={pos.y - r * 0.6 + 1}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize="6"
                    fill="white"
                  >
                    ✓
                  </text>
                </>
              )}

              {/* Icon */}
              <foreignObject
                x={pos.x - (isAether ? 10 : 8)}
                y={pos.y - (isAether ? 10 : 8)}
                width={isAether ? 20 : 16}
                height={isAether ? 20 : 16}
              >
                <Icon
                  className={cn(
                    isAether ? "h-5 w-5" : "h-4 w-4",
                    meta.color,
                  )}
                />
              </foreignObject>

              {/* Label */}
              <text
                x={pos.x}
                y={pos.y + r + 10}
                textAnchor="middle"
                fontSize={isAether ? "9" : "8"}
                fontWeight={isAether ? "600" : "400"}
                fill="currentColor"
                className={cn("fill-current", meta.color)}
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
