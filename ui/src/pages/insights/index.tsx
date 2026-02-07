import { useState } from "react";
import { Lightbulb, Play, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useInsights,
  useInsightsSummary,
  useReviewInsight,
  useDismissInsight,
  useRunAnalysis,
} from "@/api/hooks";
import { InsightCard } from "./InsightCard";
import { InsightDetail } from "./InsightDetail";
import { InsightFilters } from "./InsightFilters";

function StatCard({
  value,
  label,
  className,
}: {
  value: number;
  label: string;
  className?: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className={`text-2xl font-bold ${className || ""}`}>{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

export function InsightsPage() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useInsights(
    typeFilter || undefined,
    statusFilter || undefined,
  );
  const { data: summary } = useInsightsSummary();
  const reviewMut = useReviewInsight();
  const dismissMut = useDismissInsight();
  const analyzeMut = useRunAnalysis();

  const insightList = data?.items ?? [];
  const expandedInsight = insightList.find((i) => i.id === expandedId) ?? null;

  return (
    <div className="relative p-6">
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
          <StatCard value={summary.total} label="Total Insights" />
          <StatCard
            value={summary.pending_count}
            label="Pending Review"
            className="text-warning"
          />
          <StatCard
            value={summary.high_impact_count}
            label="High Impact"
            className="text-destructive"
          />
          <StatCard
            value={summary.by_status?.actioned ?? 0}
            label="Actioned"
            className="text-success"
          />
        </div>
      )}

      {/* Filters */}
      <InsightFilters
        typeFilter={typeFilter}
        statusFilter={statusFilter}
        onTypeFilterChange={setTypeFilter}
        onStatusFilterChange={setStatusFilter}
      />

      {/* Insight Cards */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52" />
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
              isExpanded={expandedId === insight.id}
              onExpand={() =>
                setExpandedId(expandedId === insight.id ? null : insight.id)
              }
            />
          ))}
        </div>
      )}

      {/* Expanded Detail Overlay */}
      {expandedInsight && (
        <InsightDetail
          insight={expandedInsight}
          onClose={() => setExpandedId(null)}
          onReview={() => reviewMut.mutate(expandedInsight.id)}
          onDismiss={() =>
            dismissMut.mutate({ id: expandedInsight.id })
          }
          isReviewing={reviewMut.isPending}
          isDismissing={dismissMut.isPending}
        />
      )}
    </div>
  );
}

export default InsightsPage;
