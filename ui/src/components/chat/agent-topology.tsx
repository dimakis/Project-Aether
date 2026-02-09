/**
 * Obsidian-style force-directed agent topology graph.
 *
 * Uses d3-force (via useForceGraph) for physics-based layout:
 * - Nodes float organically with ambient micro-drift
 * - Drag a node and connected nodes follow via spring forces
 * - Resizes automatically when the panel changes size
 * - Framer Motion handles visual effects (glow, pulse, opacity)
 *   while d3 owns the (x, y) positions
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
    if (agentStates?.[agent]) return agentStates[agent];
    if (!isLive) return "done";
    if (activeAgent === agent) return "firing";
    return "idle";
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

        {/* ── Edges ─────────────────────────────────────────────── */}
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

          const edgeColor = edgeActive
            ? aFiring ? metaA.hex : metaB.hex
            : "hsl(var(--border))";

          return (
            <g key={`${a}-${b}`}>
              {/* Active edge glow underlay */}
              {edgeActive && (
                <line
                  x1={x1} y1={y1} x2={x2} y2={y2}
                  stroke={edgeColor}
                  strokeWidth={4}
                  strokeOpacity={0.3}
                  filter="url(#edge-glow)"
                />
              )}

              {/* Edge line */}
              <line
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={edgeColor}
                strokeWidth={edgeActive ? 2.5 : 0.6}
                strokeLinecap="round"
                strokeOpacity={edgeActive ? 1 : 0.18}
              />

              {/* Traveling pulses when active */}
              {edgeActive && !prefersReducedMotion && (
                <>
                  <motion.circle
                    r={3}
                    fill={metaA.hex}
                    animate={{
                      cx: [x1, x2],
                      cy: [y1, y2],
                      opacity: [1, 0.3],
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
                      cx: [x2, x1],
                      cy: [y2, y1],
                      opacity: [0.9, 0.2],
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
              initial={{ opacity: 0, scale: 0.5 }}
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
