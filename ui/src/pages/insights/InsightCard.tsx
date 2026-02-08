import { ArrowRight, Lightbulb, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Insight } from "@/lib/types";
import { TYPE_CONFIG, IMPACT_STYLES } from "./types";
import { ConfidenceRing } from "./ConfidenceRing";

interface InsightCardProps {
  insight: Insight;
  isExpanded: boolean;
  onExpand: () => void;
}

export function InsightCard({
  insight,
  isExpanded,
  onExpand,
}: InsightCardProps) {
  const config = TYPE_CONFIG[insight.type] ?? {
    icon: Lightbulb,
    label: insight.type,
    color: "text-muted-foreground",
  };
  const Icon = config.icon;
  const impactStyle = IMPACT_STYLES[insight.impact] ?? IMPACT_STYLES.low;
  const confidence = insight.confidence ?? 0;

  // Failed insights get a distinct treatment
  const isFailed = insight.title === "Analysis Failed" || confidence === 0;

  return (
    <button
      onClick={onExpand}
      className={cn(
        "group relative flex flex-col rounded-xl border text-left transition-all duration-200",
        "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
        isExpanded
          ? "border-primary/50 ring-2 ring-primary/20"
          : "border-border",
        isFailed && "opacity-60",
      )}
    >
      {/* Impact indicator strip */}
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-1 rounded-l-xl",
          insight.impact === "critical" && "bg-red-500",
          insight.impact === "high" && "bg-orange-500",
          insight.impact === "medium" && "bg-blue-500",
          insight.impact === "low" && "bg-zinc-600",
        )}
      />

      <div className="flex flex-col gap-3 p-4 pl-5">
        {/* Top row: icon + type + impact */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg bg-card",
                impactStyle.bg,
              )}
            >
              <Icon className={cn("h-4 w-4", config.color)} />
            </div>
            <span className="text-xs font-medium text-muted-foreground">
              {config.label}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {insight.status !== "pending" && (
              <Badge variant="secondary" className="text-[10px] capitalize">
                {insight.status}
              </Badge>
            )}
            <Badge
              className={cn(
                "text-[10px] ring-1",
                impactStyle.bg,
                impactStyle.text,
                impactStyle.ring,
              )}
            >
              {insight.impact}
            </Badge>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold leading-snug">{insight.title}</h3>

        {/* Description preview */}
        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
          {insight.description}
        </p>

        {/* Task label badge */}
        {insight.task_label && (
          <div className="flex items-center gap-1.5">
            <Badge
              variant="outline"
              className="text-[10px] font-normal text-muted-foreground border-primary/20 bg-primary/5"
            >
              {insight.task_label}
            </Badge>
          </div>
        )}

        {/* Bottom row: confidence + entities + conversation link + arrow */}
        <div className="flex items-center gap-3 pt-1">
          {/* Confidence ring */}
          <div className="flex items-center gap-1.5">
            <ConfidenceRing value={confidence} size={20} />
            <span className="text-[10px] font-medium text-muted-foreground">
              {Math.round(confidence * 100)}%
            </span>
          </div>

          {insight.entities.length > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {insight.entities.length} entities
            </span>
          )}

          {/* Link to originating conversation */}
          {insight.conversation_id && (
            <Link
              to="/chat"
              state={{ conversationId: insight.conversation_id }}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 text-[10px] text-primary/70 hover:text-primary transition-colors"
              title="View originating conversation"
            >
              <MessageSquare className="h-3 w-3" />
              <span>Chat</span>
            </Link>
          )}

          <div className="ml-auto text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </button>
  );
}
