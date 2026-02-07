import { useState } from "react";
import {
  Lightbulb,
  Zap,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Wrench,
  GitBranch,
  BarChart3,
  Heart,
  Users,
  Play,
  Loader2,
  Eye,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatRelativeTime } from "@/lib/utils";
import {
  useInsights,
  useInsightsSummary,
  useReviewInsight,
  useDismissInsight,
  useRunAnalysis,
} from "@/api/hooks";
import type { Insight, InsightType } from "@/lib/types";

const TYPE_CONFIG: Record<InsightType, { icon: typeof Zap; label: string }> = {
  energy_optimization: { icon: Zap, label: "Energy" },
  anomaly_detection: { icon: AlertTriangle, label: "Anomaly" },
  usage_pattern: { icon: TrendingUp, label: "Usage" },
  cost_saving: { icon: DollarSign, label: "Cost Saving" },
  maintenance_prediction: { icon: Wrench, label: "Maintenance" },
  automation_gap: { icon: GitBranch, label: "Automation Gap" },
  automation_inefficiency: { icon: BarChart3, label: "Inefficiency" },
  correlation: { icon: GitBranch, label: "Correlation" },
  device_health: { icon: Heart, label: "Device Health" },
  behavioral_pattern: { icon: Users, label: "Behavioral" },
};

const IMPACT_VARIANT: Record<string, "destructive" | "warning" | "info" | "secondary"> = {
  critical: "destructive",
  high: "warning",
  medium: "info",
  low: "secondary",
};

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "reviewed", label: "Reviewed" },
  { value: "actioned", label: "Actioned" },
  { value: "dismissed", label: "Dismissed" },
];

export function InsightsPage() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data, isLoading } = useInsights(
    typeFilter || undefined,
    statusFilter || undefined,
  );
  const { data: summary } = useInsightsSummary();
  const reviewMut = useReviewInsight();
  const dismissMut = useDismissInsight();
  const analyzeMut = useRunAnalysis();

  const insightList = data?.items ?? [];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Lightbulb className="h-6 w-6" />
            Insights
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            AI-generated insights about your home automation
          </p>
        </div>
        <Button
          onClick={() => analyzeMut.mutate({})}
          disabled={analyzeMut.isPending}
        >
          {analyzeMut.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          Run Analysis
        </Button>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="mb-6 grid gap-3 sm:grid-cols-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-2xl font-bold">{summary.total}</p>
              <p className="text-xs text-muted-foreground">Total Insights</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-2xl font-bold text-warning">
                {summary.pending_count}
              </p>
              <p className="text-xs text-muted-foreground">Pending Review</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-2xl font-bold text-destructive">
                {summary.high_impact_count}
              </p>
              <p className="text-xs text-muted-foreground">High Impact</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-2xl font-bold text-success">
                {summary.by_status?.actioned ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Actioned</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-4">
        <div className="flex flex-wrap gap-1">
          <span className="mr-1 self-center text-xs text-muted-foreground">
            Status:
          </span>
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                statusFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          <span className="mr-1 self-center text-xs text-muted-foreground">
            Type:
          </span>
          <button
            onClick={() => setTypeFilter("")}
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              typeFilter === ""
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-accent",
            )}
          >
            All
          </button>
          {Object.entries(TYPE_CONFIG).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setTypeFilter(key)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                typeFilter === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {/* Insight Cards */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : insightList.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16">
            <Lightbulb className="mb-3 h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No insights found. Run an analysis to generate insights.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {insightList.map((insight) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              onReview={() => reviewMut.mutate(insight.id)}
              onDismiss={() =>
                dismissMut.mutate({ id: insight.id })
              }
              isReviewing={reviewMut.isPending}
              isDismissing={dismissMut.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function InsightCard({
  insight,
  onReview,
  onDismiss,
  isReviewing,
  isDismissing,
}: {
  insight: Insight;
  onReview: () => void;
  onDismiss: () => void;
  isReviewing: boolean;
  isDismissing: boolean;
}) {
  const typeConfig = TYPE_CONFIG[insight.type];
  const Icon = typeConfig?.icon ?? Lightbulb;

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <Badge variant="secondary" className="text-[10px]">
              {typeConfig?.label ?? insight.type}
            </Badge>
          </div>
          <Badge variant={IMPACT_VARIANT[insight.impact] ?? "secondary"}>
            {insight.impact}
          </Badge>
        </div>
        <CardTitle className="mt-2 text-sm leading-snug">
          {insight.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <p className="flex-1 text-xs leading-relaxed text-muted-foreground line-clamp-3">
          {insight.description}
        </p>

        {/* Confidence bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-medium">
              {Math.round(insight.confidence * 100)}%
            </span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${insight.confidence * 100}%` }}
            />
          </div>
        </div>

        {/* Entities */}
        {insight.entities.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {insight.entities.slice(0, 3).map((e) => (
              <span
                key={e}
                className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
              >
                {e}
              </span>
            ))}
            {insight.entities.length > 3 && (
              <span className="text-[10px] text-muted-foreground">
                +{insight.entities.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        {insight.status === "pending" && (
          <div className="mt-3 flex gap-2 border-t border-border pt-3">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={onReview}
              disabled={isReviewing}
            >
              <Eye className="mr-1 h-3 w-3" />
              Review
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDismiss}
              disabled={isDismissing}
            >
              <XCircle className="mr-1 h-3 w-3" />
              Dismiss
            </Button>
          </div>
        )}
        {insight.status !== "pending" && (
          <div className="mt-3 flex items-center gap-1 border-t border-border pt-3 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3 w-3" />
            <span className="capitalize">{insight.status}</span>
            <span className="ml-auto">
              {formatRelativeTime(insight.created_at)}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
