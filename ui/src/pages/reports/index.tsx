import { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileBarChart,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Zap,
  Users,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useReports } from "@/api/hooks/reports";
import type { AnalysisReport, ReportStatus } from "@/lib/types";

// ─── Config ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  ReportStatus,
  { icon: typeof CheckCircle2; label: string; variant: string }
> = {
  running: { icon: Loader2, label: "Running", variant: "warning" },
  completed: { icon: CheckCircle2, label: "Completed", variant: "success" },
  failed: { icon: XCircle, label: "Failed", variant: "destructive" },
};

const DEPTH_CONFIG: Record<string, { label: string; variant: string }> = {
  quick: { label: "Quick", variant: "secondary" },
  standard: { label: "Standard", variant: "default" },
  deep: { label: "Deep", variant: "info" },
};

const STRATEGY_CONFIG: Record<string, { icon: typeof Zap; label: string }> = {
  parallel: { icon: Zap, label: "Parallel" },
  teamwork: { icon: Users, label: "Teamwork" },
};

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "running", label: "Running" },
  { value: "failed", label: "Failed" },
];

// ─── Component ──────────────────────────────────────────────────────────────

export function ReportsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const { data, isLoading, error } = useReports(statusFilter || undefined);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Analysis Reports
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Comprehensive analysis reports from the Data Science team
          </p>
        </div>
        {data && (
          <Badge variant="secondary" className="text-xs">
            {data.total} report{data.total !== 1 ? "s" : ""}
          </Badge>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              statusFilter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="flex items-center gap-3 py-8 text-destructive">
            <XCircle className="h-5 w-5" />
            <p>Failed to load reports: {(error as Error).message}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty */}
      {data && data.reports.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <FileBarChart className="h-10 w-10 text-muted-foreground/50" />
            <div>
              <p className="font-medium">No reports yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Reports are created when the Data Science team runs deep
                analysis. Ask the Architect to analyze your data!
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Report cards */}
      {data && data.reports.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── ReportCard ─────────────────────────────────────────────────────────────

function ReportCard({ report }: { report: AnalysisReport }) {
  const statusCfg = STATUS_CONFIG[report.status] ?? STATUS_CONFIG.completed;
  const StatusIcon = statusCfg.icon;
  const depthCfg = DEPTH_CONFIG[report.depth] ?? DEPTH_CONFIG.standard;
  const strategyCfg = STRATEGY_CONFIG[report.strategy] ?? STRATEGY_CONFIG.parallel;
  const StrategyIcon = strategyCfg.icon;

  const createdAt = report.created_at
    ? new Date(report.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

  return (
    <Link
      to={`/reports/${report.id}`}
      className={cn(
        "group relative flex flex-col rounded-xl border text-left transition-all duration-200",
        "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
      )}
    >
      {/* Status indicator strip */}
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-1 rounded-l-xl",
          report.status === "completed" && "bg-emerald-500",
          report.status === "running" && "bg-amber-500",
          report.status === "failed" && "bg-red-500",
        )}
      />

      <div className="flex flex-col gap-3 p-4 pl-5">
        {/* Top row: status + badges */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusIcon
              className={cn(
                "h-4 w-4",
                report.status === "completed" && "text-emerald-500",
                report.status === "running" && "text-amber-500 animate-spin",
                report.status === "failed" && "text-red-500",
              )}
            />
            <Badge variant={statusCfg.variant as any} className="text-[10px]">
              {statusCfg.label}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant={depthCfg.variant as any} className="text-[10px]">
              {depthCfg.label}
            </Badge>
            <div className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
              <StrategyIcon className="h-3 w-3" />
              {strategyCfg.label}
            </div>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-sm font-medium leading-snug line-clamp-2">
          {report.title}
        </h3>

        {/* Summary snippet */}
        {report.summary && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {report.summary}
          </p>
        )}

        {/* Footer: stats + date */}
        <div className="flex items-center justify-between pt-1 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-3">
            {report.insight_ids.length > 0 && (
              <span>{report.insight_ids.length} insight{report.insight_ids.length !== 1 ? "s" : ""}</span>
            )}
            {report.artifact_paths.length > 0 && (
              <span>{report.artifact_paths.length} artifact{report.artifact_paths.length !== 1 ? "s" : ""}</span>
            )}
            {report.communication_count > 0 && (
              <span>{report.communication_count} message{report.communication_count !== 1 ? "s" : ""}</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {createdAt}
          </div>
        </div>
      </div>

      {/* Hover arrow */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100">
        <ArrowRight className="h-4 w-4 text-muted-foreground" />
      </div>
    </Link>
  );
}
