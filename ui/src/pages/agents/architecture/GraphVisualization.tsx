import { cn } from "@/lib/utils";
import {
  AGENT_NODES,
  EDGES,
  POSITIONS,
  EDGE_STYLES,
  SVG_W,
  SVG_H,
  NODE_R,
  type EdgeType,
} from "./AgentRoleConfig";

export interface GraphVisualizationProps {
  statusMap: Map<string, string>;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}

export function GraphVisualization({
  statusMap,
  selectedNodeId,
  onSelectNode,
}: GraphVisualizationProps) {
  return (
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

        const style = EDGE_STYLES[edge.type as EdgeType];
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
              onSelectNode(selectedNodeId === node.id ? null : node.id)
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
  );
}
