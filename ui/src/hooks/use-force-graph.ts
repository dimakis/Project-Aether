/**
 * Brain-layout force-directed graph hook.
 *
 * Hybrid approach: each node has a fixed target position (brain layout)
 * with light d3-force physics for organic drift and drag interaction.
 *
 * - Nodes initialise at their target positions (no random scatter)
 * - Per-node forceX/forceY pulls each node toward its brain target
 * - Pinned nodes (e.g. Aether) are fixed and don't respond to physics
 * - Gentle charge repulsion and link forces add organic breathing
 * - ResizeObserver recomputes targets when the container resizes
 * - Reduced motion support disables ambient jitter
 *
 * The hook owns the simulation lifecycle and exposes reactive positions
 * plus pointer-event handlers for drag interaction.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCollide,
  forceX,
  forceY,
  type Simulation,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import type { AgentNodeState } from "@/lib/agent-activity-store";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ForceNode extends SimulationNodeDatum {
  id: string;
  /** Pixel target position computed from fractional brain layout. */
  targetX?: number;
  targetY?: number;
}

export interface ForceLink extends SimulationLinkDatum<ForceNode> {
  source: string | ForceNode;
  target: string | ForceNode;
}

/** Fractional (0-1) position for brain layout. */
export interface FractionalPosition {
  x: number;
  y: number;
}

export interface ForceGraphPositions {
  [agentId: string]: { x: number; y: number };
}

export interface UseForceGraphReturn {
  positions: ForceGraphPositions;
  /** Attach to the container SVG for resize observation. */
  containerRef: React.RefObject<SVGSVGElement | null>;
  /** Call on pointerdown on a node to start dragging. */
  onNodePointerDown: (agentId: string, event: React.PointerEvent) => void;
  /** Call on pointermove on the SVG (or window) during drag. */
  onPointerMove: (event: React.PointerEvent) => void;
  /** Call on pointerup to release the drag. */
  onPointerUp: () => void;
  /** Currently dragged node ID, or null. */
  draggedNode: string | null;
  /** Manually reheat the simulation (e.g., on state change). */
  reheat: (alpha?: number) => void;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const NODE_RADIUS = 15;
const AETHER_RADIUS = NODE_RADIUS + 4;

/** Padding from SVG edges to keep nodes (incl. labels) in view. */
const BOUNDARY_PADDING = 25;

/** How strongly nodes are pulled toward their brain target (0-1).
 *  High value keeps nodes pinned to their brain-layout positions;
 *  physics adds gentle organic breathing, not relocation. */
const TARGET_STRENGTH = 0.4;

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useForceGraph(
  agentIds: string[],
  edges: [string, string][],
  targetPositions: Record<string, FractionalPosition>,
  pinnedNodes: string[] = [],
  agentStates?: Record<string, AgentNodeState>,
  prefersReducedMotion?: boolean,
): UseForceGraphReturn {
  const containerRef = useRef<SVGSVGElement | null>(null);
  const simRef = useRef<Simulation<ForceNode, ForceLink> | null>(null);
  const nodesRef = useRef<ForceNode[]>([]);

  // Synchronous initial positions from brain layout so nodes appear
  // at correct positions on the very first render (no flash/scatter).
  const [positions, setPositions] = useState<ForceGraphPositions>(() => {
    const init: ForceGraphPositions = {};
    const size = 300; // matches SVG_SIZE in agent-topology.tsx
    for (const id of agentIds) {
      const t = targetPositions[id];
      if (t) init[id] = { x: t.x * size, y: t.y * size };
    }
    return init;
  });
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const rafRef = useRef<number>(0);
  const pinnedSetRef = useRef(new Set(pinnedNodes));
  pinnedSetRef.current = new Set(pinnedNodes);

  // Stable reference for the simulation tick callback
  const agentStatesRef = useRef(agentStates);
  agentStatesRef.current = agentStates;

  // ── Compute pixel targets from fractional layout ──────────────────

  function computeTargets(
    width: number,
    height: number,
    nodes: ForceNode[],
    targets: Record<string, FractionalPosition>,
    pinned: Set<string>,
  ) {
    for (const node of nodes) {
      const t = targets[node.id];
      if (!t) continue;
      node.targetX = t.x * width;
      node.targetY = t.y * height;
      // Pinned nodes get hard-fixed positions
      if (pinned.has(node.id)) {
        node.fx = node.targetX;
        node.fy = node.targetY;
      }
    }
  }

  // ── Initialise / rebuild simulation when agents or edges change ──────

  useEffect(() => {
    const svg = containerRef.current;
    const width = svg?.clientWidth ?? 300;
    const height = svg?.clientHeight ?? 300;
    const pinnedSet = pinnedSetRef.current;

    // Create or reuse nodes (preserving positions across re-renders)
    const existingMap = new Map(nodesRef.current.map((n) => [n.id, n]));
    const nodes: ForceNode[] = agentIds.map((id) => {
      const existing = existingMap.get(id);
      if (existing) return existing;
      // Initialise at the brain target position (not random)
      const t = targetPositions[id];
      return {
        id,
        x: t ? t.x * width : width / 2,
        y: t ? t.y * height : height / 2,
      };
    });
    nodesRef.current = nodes;

    // Compute pixel targets and apply pins
    computeTargets(width, height, nodes, targetPositions, pinnedSet);

    const links: ForceLink[] = edges
      .filter(([a, b]) => agentIds.includes(a) && agentIds.includes(b))
      .map(([source, target]) => ({ source, target }));

    const sim = forceSimulation<ForceNode>(nodes)
      // Light repulsion — layout is primarily target-driven
      .force(
        "charge",
        forceManyBody<ForceNode>().strength((d) =>
          d.id === "aether" ? -80 : -50,
        ),
      )
      // Gentle link springs for connected-node cohesion
      .force(
        "link",
        forceLink<ForceNode, ForceLink>(links)
          .id((d) => d.id)
          .distance(50)
          .strength(0.15),
      )
      .force(
        "collide",
        forceCollide<ForceNode>((d) =>
          d.id === "aether" ? AETHER_RADIUS + 6 : NODE_RADIUS + 6,
        ).strength(0.7),
      )
      // Per-node positional forces → brain layout targets
      .force(
        "x",
        forceX<ForceNode>((d) => (d as ForceNode).targetX ?? width / 2).strength(TARGET_STRENGTH),
      )
      .force(
        "y",
        forceY<ForceNode>((d) => (d as ForceNode).targetY ?? height / 2).strength(TARGET_STRENGTH),
      )
      .alpha(0.3)          // Start calm — nodes are already at targets
      .alphaDecay(0.03)    // Settle quickly
      .velocityDecay(0.6);

    // Custom tick: boundary clamping + position updates
    sim.on("tick", () => {
      // Clamp unpinned nodes to SVG bounds
      for (const node of nodes) {
        if (node.fx != null) continue;
        node.x = Math.max(BOUNDARY_PADDING, Math.min(width - BOUNDARY_PADDING, node.x ?? width / 2));
        node.y = Math.max(BOUNDARY_PADDING, Math.min(height - BOUNDARY_PADDING, node.y ?? height / 2));
      }

      // Batch position updates via rAF
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const next: ForceGraphPositions = {};
        for (const node of nodes) {
          next[node.id] = { x: node.x ?? width / 2, y: node.y ?? height / 2 };
        }
        setPositions(next);
      });
    });

    simRef.current = sim;

    return () => {
      sim.stop();
      cancelAnimationFrame(rafRef.current);
    };
    // Rebuild when agents, edges, or target layout identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    agentIds.join(","),
    edges.map((e) => e.join("-")).join(","),
    // Rerun if the target layout object changes identity
    targetPositions,
  ]);

  // ── ResizeObserver: recompute targets and reheat on container resize ──

  useEffect(() => {
    const svg = containerRef.current;
    if (!svg) return;

    const observer = new ResizeObserver(() => {
      const sim = simRef.current;
      const nodes = nodesRef.current;
      if (!sim || nodes.length === 0) return;

      const width = svg.clientWidth;
      const height = svg.clientHeight;

      // Recompute pixel targets for new dimensions
      computeTargets(width, height, nodes, targetPositions, pinnedSetRef.current);

      // Update positional forces with new targets
      sim.force(
        "x",
        forceX<ForceNode>((d) => (d as ForceNode).targetX ?? width / 2).strength(TARGET_STRENGTH),
      );
      sim.force(
        "y",
        forceY<ForceNode>((d) => (d as ForceNode).targetY ?? height / 2).strength(TARGET_STRENGTH),
      );
      sim.alpha(0.4).restart();
    });

    observer.observe(svg);
    return () => observer.disconnect();
  }, [targetPositions]);

  // ── React to agent state changes (firing nodes get a gentle nudge) ────

  useEffect(() => {
    const sim = simRef.current;
    if (!sim || !agentStates) return;

    const anyFiring = Object.values(agentStates).some((s) => s === "firing");
    if (anyFiring && sim.alpha() < 0.08) {
      sim.alpha(0.06).restart();
    }
  }, [agentStates]);

  // ── Drag handlers ──────────────────────────────────────────────────

  const onNodePointerDown = useCallback(
    (agentId: string, event: React.PointerEvent) => {
      event.stopPropagation();
      // Don't allow dragging pinned nodes
      if (pinnedSetRef.current.has(agentId)) return;

      const node = nodesRef.current.find((n) => n.id === agentId);
      if (!node) return;

      node.fx = node.x;
      node.fy = node.y;
      setDraggedNode(agentId);
      simRef.current?.alpha(0.3).restart();
    },
    [],
  );

  const onPointerMove = useCallback(
    (event: React.PointerEvent) => {
      if (!draggedNode) return;
      const node = nodesRef.current.find((n) => n.id === draggedNode);
      if (!node) return;

      const svg = containerRef.current;
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      const svgWidth = svg.clientWidth;
      const svgHeight = svg.clientHeight;
      const viewBox = svg.viewBox.baseVal;
      const scaleX = viewBox.width / svgWidth;
      const scaleY = viewBox.height / svgHeight;

      node.fx = (event.clientX - rect.left) * scaleX + viewBox.x;
      node.fy = (event.clientY - rect.top) * scaleY + viewBox.y;

      simRef.current?.alpha(0.3).restart();
    },
    [draggedNode],
  );

  const onPointerUp = useCallback(() => {
    if (!draggedNode) return;
    const node = nodesRef.current.find((n) => n.id === draggedNode);
    if (node) {
      node.fx = null;
      node.fy = null;
    }
    setDraggedNode(null);
    simRef.current?.alpha(0.15).restart();
  }, [draggedNode]);

  // ── Public reheat ──────────────────────────────────────────────────

  const reheat = useCallback((alpha = 0.3) => {
    simRef.current?.alpha(alpha).restart();
  }, []);

  return {
    positions,
    containerRef,
    onNodePointerDown,
    onPointerMove,
    onPointerUp,
    draggedNode,
    reheat,
  };
}
