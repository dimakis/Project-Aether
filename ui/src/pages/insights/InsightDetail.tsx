import { useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { X, Lightbulb, Target, Clock, Activity, CheckCircle2, XCircle, Eye, Trash2, Loader2, Wand2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Insight } from "@/lib/types";
import { TYPE_CONFIG, IMPACT_STYLES } from "./types";
import { EvidencePanel } from "./EvidencePanel";

interface InsightDetailProps {
  insight: Insight;
  onClose: () => void;
  onReview: () => void;
  onDismiss: () => void;
  onDelete: () => void;
  isReviewing: boolean;
  isDismissing: boolean;
  isDeleting: boolean;
}

function MetricPill({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <div>
        <p className="text-[10px] text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

export function InsightDetail({
  insight,
  onClose,
  onReview,
  onDismiss,
  onDelete,
  isReviewing,
  isDismissing,
  isDeleting,
}: InsightDetailProps) {
  const navigate = useNavigate();
  const overlayRef = useRef<HTMLDivElement>(null);
  const config = TYPE_CONFIG[insight.type] ?? {
    icon: Lightbulb,
    label: insight.type,
    color: "text-muted-foreground",
  };
  const Icon = config.icon;
  const impactStyle = IMPACT_STYLES[insight.impact] ?? IMPACT_STYLES.low;

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        overlayRef.current &&
        !overlayRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/60 p-4 pt-[8vh] backdrop-blur-sm">
      <div
        ref={overlayRef}
        className="w-full max-w-2xl animate-in rounded-2xl border border-border bg-card shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6 pb-4">
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl",
                impactStyle.bg,
              )}
            >
              <Icon className={cn("h-5 w-5", config.color)} />
            </div>
            <div>
              <div className="mb-1 flex items-center gap-2">
                <Badge
                  className={cn(
                    "text-[10px] ring-1",
                    impactStyle.bg,
                    impactStyle.text,
                    impactStyle.ring,
                  )}
                >
                  {insight.impact} impact
                </Badge>
                <Badge variant="secondary" className="text-[10px]">
                  {config.label}
                </Badge>
                <Badge variant="secondary" className="text-[10px] capitalize">
                  {insight.status}
                </Badge>
              </div>
              <h2 className="text-lg font-semibold leading-snug">
                {insight.title}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 p-6">
          {/* Description */}
          <p className="text-sm leading-relaxed text-muted-foreground">
            {insight.description}
          </p>

          {/* Metrics row */}
          <div className="flex gap-4">
            <MetricPill
              icon={Target}
              label="Confidence"
              value={`${Math.round((insight.confidence ?? 0) * 100)}%`}
            />
            <MetricPill
              icon={Clock}
              label="Created"
              value={formatRelativeTime(insight.created_at)}
            />
            {insight.entities.length > 0 && (
              <MetricPill
                icon={Activity}
                label="Entities"
                value={String(insight.entities.length)}
              />
            )}
          </div>

          {/* Evidence Visualization */}
          {insight.evidence && <EvidencePanel evidence={insight.evidence} />}

          {/* Entities */}
          {insight.entities.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Related Entities
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {insight.entities.map((e) => (
                  <span
                    key={e}
                    className="rounded-md bg-muted px-2 py-1 text-[11px] font-mono text-muted-foreground"
                  >
                    {e}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-border p-4 px-6">
          <div className="flex items-center gap-2">
            {insight.mlflow_run_id && (
              <span className="text-[10px] font-mono text-muted-foreground">
                run: {insight.mlflow_run_id.slice(0, 12)}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={onDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="mr-1 h-3 w-3" />
              )}
              Delete
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const prompt = `Create an automation based on insight "${insight.title}" (ID: ${insight.id}). ${insight.description}`;
                navigate("/chat", { state: { prefill: prompt } });
              }}
            >
              <Wand2 className="mr-1 h-3 w-3" />
              Create Automation
            </Button>
          </div>
          <div className="flex gap-2">
            {insight.status === "pending" && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDismiss}
                  disabled={isDismissing}
                >
                  <XCircle className="mr-1 h-3 w-3" />
                  Dismiss
                </Button>
                <Button
                  size="sm"
                  onClick={onReview}
                  disabled={isReviewing}
                >
                  <Eye className="mr-1 h-3 w-3" />
                  Mark Reviewed
                </Button>
              </>
            )}
            {insight.status !== "pending" && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3 w-3" />
                <span className="capitalize">{insight.status}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
