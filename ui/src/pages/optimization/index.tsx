import { useState } from "react";
import { usePersistedState } from "@/hooks/use-persisted-state";
import {
  Sparkles,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useSuggestions,
  useRunOptimization,
  useOptimizationJob,
} from "@/api/hooks";
import type { AutomationSuggestion } from "@/api/client/optimization";
import { SuggestionDetail } from "./SuggestionDetail";

const ANALYSIS_TYPES = [
  { value: "behavior_analysis", label: "Behavior Analysis" },
  { value: "automation_analysis", label: "Automation Analysis" },
  { value: "automation_gap_detection", label: "Gap Detection" },
  { value: "cost_optimization", label: "Cost Optimization" },
  { value: "device_health", label: "Device Health" },
  { value: "correlation_discovery", label: "Correlations" },
];

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string }> = {
  pending: { icon: Clock, color: "text-muted-foreground" },
  running: { icon: Loader2, color: "text-amber-500" },
  completed: { icon: CheckCircle2, color: "text-emerald-500" },
  failed: { icon: XCircle, color: "text-red-500" },
};

export function OptimizationPage() {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([
    "behavior_analysis",
  ]);
  const [hours, setHours] = useState(168);
  const [activeJobId, setActiveJobId] = usePersistedState<string | null>("optimization:activeJobId", null);
  const [expandedSuggestionId, setExpandedSuggestionId] = useState<string | null>(null);

  const runOpt = useRunOptimization();
  const { data: jobData } = useOptimizationJob(activeJobId);
  const { data: suggestionsData, isLoading: loadingSuggestions } =
    useSuggestions();

  const handleRun = () => {
    runOpt.mutate(
      { analysis_types: selectedTypes, hours },
      {
        onSuccess: (data) => setActiveJobId(data.job_id),
      },
    );
  };

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  const suggestions = suggestionsData?.items ?? [];
  const pendingSuggestions = suggestions.filter((s) => s.status === "pending");
  const expandedSuggestion = expandedSuggestionId
    ? suggestions.find((s) => s.id === expandedSuggestionId)
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Sparkles className="h-6 w-6" />
          Optimization
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Run behavioral analysis and discover automation opportunities
        </p>
      </div>

      {/* Run Analysis Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Run Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Analysis type selector */}
          <div>
            <p className="mb-2 text-xs text-muted-foreground">Analysis types</p>
            <div className="flex flex-wrap gap-2">
              {ANALYSIS_TYPES.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => toggleType(value)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                    selectedTypes.includes(value)
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Time range */}
          <div className="flex items-center gap-3">
            <label className="text-xs text-muted-foreground">Time range:</label>
            <select
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="rounded-md border bg-background px-2 py-1 text-sm"
            >
              <option value={24}>24 hours</option>
              <option value={72}>3 days</option>
              <option value={168}>1 week</option>
              <option value={336}>2 weeks</option>
              <option value={720}>30 days</option>
            </select>
          </div>

          <Button
            onClick={handleRun}
            disabled={runOpt.isPending || selectedTypes.length === 0}
          >
            {runOpt.isPending ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="mr-1.5 h-3.5 w-3.5" />
            )}
            Run Optimization
          </Button>
        </CardContent>
      </Card>

      {/* Active Job Status */}
      {jobData && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              {(() => {
                const cfg = STATUS_CONFIG[jobData.status] ?? STATUS_CONFIG.pending;
                const Icon = cfg.icon;
                return (
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      cfg.color,
                      jobData.status === "running" && "animate-spin",
                    )}
                  />
                );
              })()}
              Job {jobData.job_id.slice(0, 8)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 text-sm">
              <Badge variant="secondary">{jobData.status}</Badge>
              <span className="text-muted-foreground">
                {jobData.insight_count} insights, {jobData.suggestion_count}{" "}
                suggestions
              </span>
              {jobData.error && (
                <span className="text-red-500 text-xs">{jobData.error}</span>
              )}
            </div>
            {jobData.recommendations.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  Recommendations
                </p>
                {jobData.recommendations.map((r, i) => (
                  <p key={i} className="text-sm">
                    {r}
                  </p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Suggestions */}
      <div>
        <h2 className="mb-3 text-lg font-medium">
          Automation Suggestions
          {pendingSuggestions.length > 0 && (
            <Badge variant="secondary" className="ml-2 text-xs">
              {pendingSuggestions.length} pending
            </Badge>
          )}
        </h2>

        {loadingSuggestions ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-xl" />
            ))}
          </div>
        ) : suggestions.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <Zap className="h-10 w-10 text-muted-foreground/50" />
              <div>
                <p className="font-medium">No suggestions yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Run an optimization analysis to discover automation
                  opportunities.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {suggestions.map((s) => (
              <SuggestionCard
                key={s.id}
                suggestion={s}
                isExpanded={expandedSuggestionId === s.id}
                onExpand={() =>
                  setExpandedSuggestionId(expandedSuggestionId === s.id ? null : s.id)
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail overlay */}
      {expandedSuggestion && (
        <SuggestionDetail
          suggestion={expandedSuggestion}
          onClose={() => setExpandedSuggestionId(null)}
        />
      )}
    </div>
  );
}

function SuggestionCard({
  suggestion,
  isExpanded,
  onExpand,
}: {
  suggestion: AutomationSuggestion;
  isExpanded: boolean;
  onExpand: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onExpand}
      className={cn(
        "group relative flex flex-col rounded-xl border text-left transition-all duration-200",
        "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
        isExpanded && "border-primary/50 ring-2 ring-primary/20",
        "border-border",
      )}
    >
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-snug line-clamp-2 break-words">
            {suggestion.pattern}
          </p>
          <Badge
            variant={
              suggestion.status === "pending"
                ? "secondary"
                : suggestion.status === "accepted"
                  ? "default"
                  : "outline"
            }
            className="shrink-0 text-[10px]"
          >
            {suggestion.status}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2">
          <span className="font-medium">Trigger:</span> {suggestion.proposed_trigger}
        </p>
        <p className="text-xs text-muted-foreground line-clamp-1">
          <span className="font-medium">Action:</span> {suggestion.proposed_action}
        </p>
        {suggestion.entities.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {suggestion.entities.slice(0, 3).map((e) => (
              <Badge key={e} variant="outline" className="text-[10px] font-mono">
                {e}
              </Badge>
            ))}
            {suggestion.entities.length > 3 && (
              <Badge variant="outline" className="text-[10px]">
                +{suggestion.entities.length - 3}
              </Badge>
            )}
          </div>
        )}
        <div className="flex items-center justify-between pt-1">
          <span className="text-[10px] text-muted-foreground">
            {Math.round(suggestion.confidence * 100)}% confidence
          </span>
          <span className="text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <ArrowRight className="h-3.5 w-3.5" />
          </span>
        </div>
      </div>
    </button>
  );
}
