/**
 * Brain-architecture agent topology graph.
 *
 * Renders agents as neurons within a brain silhouette (coronal view).
 * Uses d3-force (via useForceGraph) for physics-based layout:
 * - Agents positioned within anatomical brain regions
 * - Neural pathway edges as curved connections between nodes
 * - Brain silhouette background with subtle cerebral fold textures
 * - Live neural pulse animation during active workflows
 * - Framer Motion handles visual effects; d3 owns (x, y) positions
 */

import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { AgentNodeState } from "@/lib/agent-activity-store";
import {
  TOPOLOGY_AGENT_IDS,
  DELEGATION_EDGES,
  BRAIN_LAYOUT,
  agentMeta,
} from "@/lib/agent-registry";
import { useForceGraph } from "@/hooks/use-force-graph";

// Re-export for consumers that still import from here
export { TOPOLOGY_AGENT_IDS as ALL_TOPOLOGY_AGENTS } from "@/lib/agent-registry";

// ─── Constants ───────────────────────────────────────────────────────────────

const SVG_SIZE = 300;
const NODE_RADIUS = 15;

// ─── Brain Silhouette Paths (coronal / top-down view, 300×300) ───────────────

const BRAIN_LEFT_HEMISPHERE =
  "M 147,25 C 115,25 70,40 45,80 C 22,118 18,160 22,195 C 28,235 55,265 90,275 C 118,282 140,278 147,270 Z";
const BRAIN_RIGHT_HEMISPHERE =
  "M 153,25 C 185,25 230,40 255,80 C 278,118 282,160 278,195 C 272,235 245,265 210,275 C 182,282 160,278 153,270 Z";
const BRAIN_FISSURE = "M 150,28 Q 149,150 150,272";

/** Subtle cerebral fold lines inside each hemisphere (gyri/sulci). */
const BRAIN_FOLDS_LEFT = [
  "M 105,50 Q 65,95 78,140",
  "M 42,105 Q 55,140 38,178",
  "M 68,175 Q 42,215 72,252",
];
const BRAIN_FOLDS_RIGHT = [
  "M 195,50 Q 235,95 222,140",
  "M 258,105 Q 245,140 262,178",
  "M 232,175 Q 258,215 228,252",
];

// ─── Edge Curve Helpers ──────────────────────────────────────────────────────

/**
 * Compute a quadratic bezier control point for a neural pathway edge.
 * Uses a deterministic hash to vary curve direction across edges.
 */
function edgeCurveControl(
  x1: number, y1: number,
  x2: number, y2: number,
  a: string, b: string,
): { cx: number; cy: number } {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist < 1) return { cx: mx, cy: my };

  // Perpendicular direction
  const px = -dy / dist;
  const py = dx / dist;

  // Deterministic hash for varied curve direction per edge
  const hash =
    a.split("").reduce((s, c) => s + c.charCodeAt(0), 0) +
    b.split("").reduce((s, c) => s + c.charCodeAt(0), 0);
  const sign = hash % 2 === 0 ? 1 : -1;
  const offset = sign * Math.min(dist * 0.2, 25);

  return { cx: mx + px * offset, cy: my + py * offset };
}

/**
 * Compute the midpoint of a quadratic bezier (at t = 0.5).
 * Used for 3-keyframe pulse animation that follows the curve.
 */
function bezierMidpoint(
  x1: number, y1: number,
  cx: number, cy: number,
  x2: number, y2: number,
): { x: number; y: number } {
  return {
    x: 0.25 * x1 + 0.5 * cx + 0.25 * x2,
    y: 0.25 * y1 + 0.5 * cy + 0.25 * y2,
  };
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface AgentTopologyProps {
  agents: string[];
  activeAgent?: string | null;
  isLive?: boolean;
  agentStates?: Record<string, AgentNodeState>;
  /** Edges activated during the current workflow (event-driven). */
  activeEdges?: [string, string][];
}

// ─── Component ───────────────────────────────────────────────────────────────

export function AgentTopology({
  agents,
  activeAgent,
  isLive,
  agentStates,
  activeEdges,
}: AgentTopologyProps) {
  const prefersReducedMotion = useReducedMotion();
  const displayAgents = agents.length > 0 ? agents : TOPOLOGY_AGENT_IDS;

  // ── Brain-layout force graph ─────────────────────────────────────

  const {
    positions,
    containerRef,
    onNodePointerDown,
    onPointerMove,
    onPointerUp,
    draggedNode,
  } = useForceGraph(
    displayAgents,
    DELEGATION_EDGES,
    BRAIN_LAYOUT,
    ["aether"],           // Pin Aether to the crown
    agentStates,
    prefersReducedMotion ?? false,
  );

  // ── Edge visibility ──────────────────────────────────────────────

  const visibleEdges = useMemo(
    () =>
      DELEGATION_EDGES.filter(
        ([a, b]) => displayAgents.includes(a) && displayAgents.includes(b),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [displayAgents.join(",")],
  );

  const activeEdgeSet = useMemo(() => {
    const set = new Set<string>();
    if (activeEdges) {
      for (const [a, b] of activeEdges) {
        set.add(`${a}-${b}`);
      }
    }
    return set;
  }, [activeEdges]);

  // ── Node state resolution ────────────────────────────────────────

  function getNodeState(agent: string): AgentNodeState {
    // Use agentStates as the single source of truth — avoids
    // inconsistencies from the activeAgent fallback that could
    // cause nodes to fail to light up.
    if (agentStates?.[agent]) return agentStates[agent];
    return isLive ? "dormant" : "idle";
  }

  // ── Spring configs for Framer Motion visual effects ──────────────

  const firingSpring = { type: "spring" as const, stiffness: 300, damping: 15 };
  const doneSpring = { type: "spring" as const, stiffness: 120, damping: 20 };

  return (
    <div className="flex items-center justify-center">
      <svg
        ref={containerRef}
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        width={SVG_SIZE}
        height={SVG_SIZE}
        className="overflow-visible select-none"
        style={{ cursor: draggedNode ? "grabbing" : "default" }}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        <defs>
          {displayAgents.map((agent) => {
            const meta = agentMeta(agent);
            return (
              <filter
                key={`glow-${agent}`}
                id={`glow-${agent}`}
                x="-80%"
                y="-80%"
                width="260%"
                height="260%"
              >
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feFlood floodColor={meta.hex} floodOpacity="0.8" />
                <feComposite in2="blur" operator="in" />
                <feMerge>
                  <feMergeNode />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            );
          })}
          {/* Edge glow filter for active edges */}
          <filter id="edge-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── Brain Silhouette Background ────────────────────── */}
        <g opacity={isLive ? 1 : 0.7}>
          {/* Left hemisphere */}
          <path
            d={BRAIN_LEFT_HEMISPHERE}
            fill="hsl(var(--muted-foreground))"
            fillOpacity={0.03}
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={0.8}
            strokeOpacity={0.12}
          />
          {/* Right hemisphere */}
          <path
            d={BRAIN_RIGHT_HEMISPHERE}
            fill="hsl(var(--muted-foreground))"
            fillOpacity={0.03}
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={0.8}
            strokeOpacity={0.12}
          />
          {/* Longitudinal fissure */}
          <path
            d={BRAIN_FISSURE}
            fill="none"
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={0.5}
            strokeOpacity={0.08}
          />
          {/* Cerebral folds — left hemisphere */}
          {BRAIN_FOLDS_LEFT.map((d, i) => (
            <path key={`fl-${i}`} d={d} fill="none" stroke="hsl(var(--muted-foreground))" strokeWidth={0.5} strokeOpacity={0.05} />
          ))}
          {/* Cerebral folds — right hemisphere */}
          {BRAIN_FOLDS_RIGHT.map((d, i) => (
            <path key={`fr-${i}`} d={d} fill="none" stroke="hsl(var(--muted-foreground))" strokeWidth={0.5} strokeOpacity={0.05} />
          ))}
        </g>

        {/* Live neural pulse overlay on brain outline */}
        {isLive && !prefersReducedMotion && (
          <motion.g
            animate={{ opacity: [0, 0.1, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          >
            <path d={BRAIN_LEFT_HEMISPHERE} fill="none" stroke="#a855f7" strokeWidth={1.5} />
            <path d={BRAIN_RIGHT_HEMISPHERE} fill="none" stroke="#a855f7" strokeWidth={1.5} />
          </motion.g>
        )}

        {/* ── Neural Pathway Edges ─────────────────────────────── */}
        {visibleEdges.map(([a, b]) => {
          const pA = positions[a];
          const pB = positions[b];
          if (!pA || !pB) return null;

          const edgeActive = activeEdgeSet.has(`${a}-${b}`);
          const metaA = agentMeta(a);
          const metaB = agentMeta(b);
          const sA = getNodeState(a);
          const aFiring = sA === "firing";

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

          // Curved neural pathway
          const ctrl = edgeCurveControl(pA.x, pA.y, pB.x, pB.y, a, b);
          const pathD = `M ${x1},${y1} Q ${ctrl.cx},${ctrl.cy} ${x2},${y2}`;

          const edgeColor = edgeActive
            ? aFiring ? metaA.hex : metaB.hex
            : "hsl(var(--border))";

          // Midpoint on curve for pulse animation
          const mid = bezierMidpoint(x1, y1, ctrl.cx, ctrl.cy, x2, y2);

          return (
            <g key={`${a}-${b}`}>
              {/* Active edge glow underlay */}
              {edgeActive && (
                <path
                  d={pathD}
                  fill="none"
                  stroke={edgeColor}
                  strokeWidth={4}
                  strokeOpacity={0.3}
                  filter="url(#edge-glow)"
                />
              )}

              {/* Neural pathway */}
              <path
                d={pathD}
                fill="none"
                stroke={edgeColor}
                strokeWidth={edgeActive ? 2.5 : 0.6}
                strokeLinecap="round"
                strokeOpacity={edgeActive ? 1 : 0.18}
              />

              {/* Traveling pulses along curved pathway when active */}
              {edgeActive && !prefersReducedMotion && (
                <>
                  <motion.circle
                    r={3}
                    fill={metaA.hex}
                    animate={{
                      cx: [x1, mid.x, x2],
                      cy: [y1, mid.y, y2],
                      opacity: [1, 0.8, 0.3],
                    }}
                    transition={{
                      duration: 0.8,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  />
                  <motion.circle
                    r={2}
                    fill={metaB.hex}
                    animate={{
                      cx: [x2, mid.x, x1],
                      cy: [y2, mid.y, y1],
                      opacity: [0.9, 0.7, 0.2],
                    }}
                    transition={{
                      duration: 1.1,
                      repeat: Infinity,
                      ease: "linear",
                      delay: 0.3,
                    }}
                  />
                </>
              )}
            </g>
          );
        })}

        {/* ── Nodes ─────────────────────────────────────────────── */}
        {displayAgents.map((agent) => {
          const pos = positions[agent];
          if (!pos) return null;
          const meta = agentMeta(agent);
          const Icon = meta.icon;
          const state = getNodeState(agent);
          const isFiring = state === "firing";
          const isDone = state === "done";
          const isAether = agent === "aether";
          const r = isAether ? NODE_RADIUS + 4 : NODE_RADIUS;
          const isDragging = draggedNode === agent;

          return (
            <motion.g
              key={agent}
              // Framer Motion for visual state (opacity, scale) — NOT position
              initial={{ opacity: 0, scale: 0.9 }}
              animate={
                isFiring
                  ? { opacity: 1, scale: 1.18 }
                  : isDone
                    ? { opacity: 0.9, scale: 1 }
                    : { opacity: 0.55, scale: 1 }
              }
              transition={isFiring ? firingSpring : doneSpring}
              style={{
                // Position is driven by d3-force, not Framer Motion
                transformOrigin: `${pos.x}px ${pos.y}px`,
                cursor: isDragging ? "grabbing" : "grab",
              }}
              onPointerDown={(e) => onNodePointerDown(agent, e)}
            >
              {/* Background circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill="hsl(var(--card))"
                stroke={isFiring ? meta.hex : isAether ? meta.hex : "hsl(var(--border))"}
                strokeWidth={isFiring ? 2.5 : isAether ? 1.5 : 1}
                strokeOpacity={isFiring ? 1 : isAether ? 0.7 : 0.6}
                filter={isFiring ? `url(#glow-${agent})` : undefined}
              />

              {/* Aether ambient glow ring */}
              {isAether && !isFiring && !prefersReducedMotion && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 6}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={0.8}
                  animate={{
                    r: [r + 3, r + 8, r + 3],
                    opacity: [0.2, 0.45, 0.2],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              )}

              {/* Firing: inner bright halo */}
              {isFiring && (
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 2}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={1.5}
                  strokeOpacity={0.6}
                  filter={`url(#glow-${agent})`}
                />
              )}

              {/* Firing pulse ring (expanding outward) */}
              {isFiring && !prefersReducedMotion && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 4}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={1.5}
                  animate={{
                    r: [r + 2, r + 14],
                    opacity: [0.8, 0],
                  }}
                  transition={{
                    duration: 0.8,
                    repeat: Infinity,
                    ease: "easeOut",
                  }}
                />
              )}

              {/* Firing: second slower pulse ring */}
              {isFiring && !prefersReducedMotion && (
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 6}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth={0.8}
                  animate={{
                    r: [r + 4, r + 18],
                    opacity: [0.5, 0],
                  }}
                  transition={{
                    duration: 1.4,
                    repeat: Infinity,
                    ease: "easeOut",
                    delay: 0.3,
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
                fontWeight={isFiring ? "700" : isAether ? "600" : "500"}
                fill={isFiring ? meta.hex : "currentColor"}
                className={cn(!isFiring && "fill-current", !isFiring && meta.color)}
                filter={isFiring ? `url(#glow-${agent})` : undefined}
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
