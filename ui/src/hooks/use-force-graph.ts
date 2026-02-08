/**
 * Obsidian-style force-directed graph layout hook.
 *
 * Uses d3-force to simulate physics-based node positioning with:
 * - Full physics during drag (nodes connected by springs follow)
 * - ResizeObserver to reheat on container resize
 * - Ambient micro-drift when simulation settles (organic floating)
 * - Reduced motion support
 *
 * The hook owns the simulation lifecycle and exposes reactive positions
 * plus pointer-event handlers for drag interaction.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
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
}

export interface ForceLink extends SimulationLinkDatum<ForceNode> {
  source: string | ForceNode;
  target: string | ForceNode;
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

/** Jitter amplitude for ambient micro-drift (px). */
const JITTER_AMPLITUDE = 0.3;
/** Alpha threshold below which jitter kicks in. */
const JITTER_ALPHA_THRESHOLD = 0.02;
/** Minimum alpha to keep simulation alive for jitter. */
const JITTER_ALPHA_MIN = 0.005;

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useForceGraph(
  agentIds: string[],
  edges: [string, string][],
  agentStates?: Record<string, AgentNodeState>,
  prefersReducedMotion?: boolean,
): UseForceGraphReturn {
  const containerRef = useRef<SVGSVGElement | null>(null);
  const simRef = useRef<Simulation<ForceNode, ForceLink> | null>(null);
  const nodesRef = useRef<ForceNode[]>([]);
  const [positions, setPositions] = useState<ForceGraphPositions>({});
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const rafRef = useRef<number>(0);

  // Stable references for the simulation tick callback
  const agentStatesRef = useRef(agentStates);
  agentStatesRef.current = agentStates;
  const reducedMotionRef = useRef(prefersReducedMotion);
  reducedMotionRef.current = prefersReducedMotion;

  // ── Initialise / rebuild simulation when agents or edges change ──────

  useEffect(() => {
    const svg = containerRef.current;
    const width = svg?.clientWidth ?? 300;
    const height = svg?.clientHeight ?? 300;
    const cx = width / 2;
    const cy = height / 2;

    // Create or reuse nodes (preserving positions across re-renders)
    const existingMap = new Map(nodesRef.current.map((n) => [n.id, n]));
    const nodes: ForceNode[] = agentIds.map((id, i) => {
      const existing = existingMap.get(id);
      if (existing) return existing;
      // Initial positions: spread in a circle to give d3 a head start
      const angle = (2 * Math.PI * i) / agentIds.length - Math.PI / 2;
      const radius = id === "aether" ? 0 : 80;
      return {
        id,
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      };
    });
    nodesRef.current = nodes;

    const links: ForceLink[] = edges
      .filter(([a, b]) => agentIds.includes(a) && agentIds.includes(b))
      .map(([source, target]) => ({ source, target }));

    const sim = forceSimulation<ForceNode>(nodes)
      .force(
        "charge",
        forceManyBody<ForceNode>().strength((d) =>
          d.id === "aether" ? -300 : -180,
        ),
      )
      .force(
        "link",
        forceLink<ForceNode, ForceLink>(links)
          .id((d) => d.id)
          .distance(65)
          .strength(0.4),
      )
      .force("center", forceCenter(cx, cy).strength(0.05))
      .force(
        "collide",
        forceCollide<ForceNode>((d) =>
          d.id === "aether" ? AETHER_RADIUS + 8 : NODE_RADIUS + 8,
        ).strength(0.8),
      )
      // Gentle gravity to keep nodes in view
      .force("x", forceX<ForceNode>(cx).strength(0.02))
      .force("y", forceY<ForceNode>(cy).strength(0.02))
      .alphaDecay(0.02)
      .velocityDecay(0.3);

    // Custom tick: update positions and apply ambient jitter
    sim.on("tick", () => {
      // Apply ambient jitter when nearly settled (unless reduced motion)
      if (
        !reducedMotionRef.current &&
        sim.alpha() < JITTER_ALPHA_THRESHOLD
      ) {
        for (const node of nodes) {
          if (node.fx != null) continue; // skip pinned/dragged nodes
          node.vx = (node.vx ?? 0) + (Math.random() - 0.5) * JITTER_AMPLITUDE;
          node.vy = (node.vy ?? 0) + (Math.random() - 0.5) * JITTER_AMPLITUDE;
        }
        // Keep alive at minimum alpha for continuous gentle drift
        if (sim.alpha() < JITTER_ALPHA_MIN) {
          sim.alpha(JITTER_ALPHA_MIN);
        }
      }

      // Batch position updates via rAF to avoid excessive React renders
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const next: ForceGraphPositions = {};
        for (const node of nodes) {
          next[node.id] = { x: node.x ?? cx, y: node.y ?? cy };
        }
        setPositions(next);
      });
    });

    simRef.current = sim;

    return () => {
      sim.stop();
      cancelAnimationFrame(rafRef.current);
    };
    // We intentionally only rebuild when the identity of agents/edges changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentIds.join(","), edges.map((e) => e.join("-")).join(",")]);

  // ── ResizeObserver: reheat on container resize ──────────────────────

  useEffect(() => {
    const svg = containerRef.current;
    if (!svg) return;

    const observer = new ResizeObserver(() => {
      const sim = simRef.current;
      if (!sim) return;
      const width = svg.clientWidth;
      const height = svg.clientHeight;
      const cx = width / 2;
      const cy = height / 2;

      // Update centering forces
      sim.force("center", forceCenter(cx, cy).strength(0.05));
      sim.force("x", forceX<ForceNode>(cx).strength(0.02));
      sim.force("y", forceY<ForceNode>(cy).strength(0.02));
      sim.alpha(0.3).restart();
    });

    observer.observe(svg);
    return () => observer.disconnect();
  }, []);

  // ── React to agent state changes (firing nodes push others away) ────

  useEffect(() => {
    const sim = simRef.current;
    if (!sim || !agentStates) return;

    // Gently reheat when a new agent starts firing
    const anyFiring = Object.values(agentStates).some((s) => s === "firing");
    if (anyFiring && sim.alpha() < 0.1) {
      sim.alpha(0.08).restart();
    }
  }, [agentStates]);

  // ── Drag handlers ──────────────────────────────────────────────────

  const onNodePointerDown = useCallback(
    (agentId: string, event: React.PointerEvent) => {
      event.stopPropagation();
      const node = nodesRef.current.find((n) => n.id === agentId);
      if (!node) return;

      // Pin node to current position
      node.fx = node.x;
      node.fy = node.y;
      setDraggedNode(agentId);

      // Reheat simulation for spring response
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

      // Convert screen coordinates to SVG coordinates
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
      // Release pin — let physics settle
      node.fx = null;
      node.fy = null;
    }
    setDraggedNode(null);
    simRef.current?.alpha(0.2).restart();
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
