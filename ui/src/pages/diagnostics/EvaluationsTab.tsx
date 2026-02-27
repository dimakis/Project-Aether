import {
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useEvaluationSummary,
  useScorers,
  useRunEvaluation,
} from "@/api/hooks";

export function EvaluationsTab() {
  const { data: summary, isLoading: loadingSummary } = useEvaluationSummary();
  const { data: scorersData, isLoading: loadingScorers } = useScorers();
  const runEval = useRunEvaluation();

  return (
    <div className="space-y-6">
      {/* Header with trigger */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Trace Evaluations</h2>
          <p className="text-sm text-muted-foreground">
            MLflow scorer results across recent conversation traces
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => runEval.mutate(50)}
          disabled={runEval.isPending}
        >
          {runEval.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="mr-1.5 h-3.5 w-3.5" />
          )}
          Run Evaluation
        </Button>
      </div>

      {/* Success/error banner */}
      {runEval.isSuccess && (
        <Card className="border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-900/10">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            {runEval.data.message}
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      {loadingSummary ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-2xl font-bold">{summary.trace_count}</p>
                <p className="text-xs text-muted-foreground">Traces Evaluated</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-2xl font-bold">
                  {summary.scorer_results.length}
                </p>
                <p className="text-xs text-muted-foreground">Scorers</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground mb-1">Last Run</p>
                <p className="text-sm font-medium">
                  {summary.evaluated_at
                    ? new Date(summary.evaluated_at).toLocaleString()
                    : "Never"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Scorer results */}
          {summary.scorer_results.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <BarChart3 className="h-4 w-4" />
                  Scorer Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {summary.scorer_results.map((s) => (
                    <div
                      key={s.name}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold",
                            s.pass_rate !== null && s.pass_rate >= 0.8
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                              : s.pass_rate !== null && s.pass_rate >= 0.5
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                                : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                          )}
                        >
                          {s.pass_rate !== null
                            ? `${Math.round(s.pass_rate * 100)}`
                            : "—"}
                        </div>
                        <div>
                          <p className="text-sm font-medium">{s.name}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="flex items-center gap-0.5">
                              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                              {s.pass_count}
                            </span>
                            <span className="flex items-center gap-0.5">
                              <XCircle className="h-3 w-3 text-red-500" />
                              {s.fail_count}
                            </span>
                            {s.error_count > 0 && (
                              <span className="flex items-center gap-0.5">
                                <AlertTriangle className="h-3 w-3 text-amber-500" />
                                {s.error_count}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      {s.pass_rate !== null && (
                        <Badge
                          variant={
                            s.pass_rate >= 0.8
                              ? "default"
                              : s.pass_rate >= 0.5
                                ? "secondary"
                                : "destructive"
                          }
                        >
                          {Math.round(s.pass_rate * 100)}% pass rate
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <BarChart3 className="h-10 w-10 text-muted-foreground/50" />
            <div>
              <p className="font-medium">No evaluations yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Run an evaluation to see scorer results across your traces.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Available scorers */}
      {loadingScorers ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : (
        scorersData &&
        scorersData.count > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Available Scorers ({scorersData.count})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {scorersData.scorers.map((s) => (
                  <Badge key={s.name} variant="outline" className="text-xs">
                    {s.name}
                    {s.description && (
                      <span className="ml-1 text-muted-foreground">
                        — {s.description}
                      </span>
                    )}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      )}
    </div>
  );
}
