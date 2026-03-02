import { useState } from "react";
import {
  Activity,
  CheckCircle2,
  Clock,
  Loader2,
  MessageSquare,
  Search,
  Sparkles,
  XCircle,
  Compass,
  Cpu,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useJobs } from "@/api/hooks";
import type { Job } from "@/api/client/jobs";

// ─── Config ─────────────────────────────────────────────────────────────────

const JOB_TYPE_CONFIG: Record<
  string,
  { icon: typeof MessageSquare; label: string; className: string }
> = {
  chat: { icon: MessageSquare, label: "Chat", className: "text-blue-400" },
  analysis: { icon: Search, label: "Analysis", className: "text-violet-400" },
  optimization: { icon: Sparkles, label: "Optimization", className: "text-amber-400" },
  discovery: { icon: Compass, label: "Discovery", className: "text-emerald-400" },
  other: { icon: Cpu, label: "Other", className: "text-muted-foreground" },
};

const STATUS_CONFIG: Record<
  string,
  { icon: typeof CheckCircle2; label: string; className: string; badgeBg: string }
> = {
  running: {
    icon: Loader2,
    label: "Running",
    className: "text-blue-400",
    badgeBg: "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30",
  },
  completed: {
    icon: CheckCircle2,
    label: "Completed",
    className: "text-emerald-500",
    badgeBg: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30",
  },
  failed: {
    icon: XCircle,
    label: "Failed",
    className: "text-red-500",
    badgeBg: "bg-red-500/15 text-red-400 ring-1 ring-red-500/30",
  },
};

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "chat", label: "Chat" },
  { value: "analysis", label: "Analysis" },
  { value: "optimization", label: "Optimization" },
  { value: "discovery", label: "Discovery" },
];

function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSec = seconds % 60;
  return `${minutes}m ${remainingSec}s`;
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Component ──────────────────────────────────────────────────────────────

export function JobsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const { data, isLoading, error } = useJobs(50, typeFilter || undefined);

  const hasRunning = data?.jobs.some((j) => j.status === "running");

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Recent agent jobs and workflow executions
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasRunning && (
            <div className="flex items-center gap-1.5 text-xs text-blue-400">
              <div className="relative h-2 w-2">
                <div className="absolute inset-0 animate-ping rounded-full bg-blue-400/60" />
                <div className="relative h-2 w-2 rounded-full bg-blue-400" />
              </div>
              Auto-refreshing
            </div>
          )}
          {data && (
            <Badge variant="secondary" className="text-xs">
              {data.total} job{data.total !== 1 ? "s" : ""}
            </Badge>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {TYPE_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setTypeFilter(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              typeFilter === f.value
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
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="flex items-center gap-3 py-8 text-destructive">
            <XCircle className="h-5 w-5" />
            <p>Failed to load jobs: {(error as Error).message}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty */}
      {data && data.jobs.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Activity className="h-10 w-10 text-muted-foreground/50" />
            <div>
              <p className="font-medium">No jobs found</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {typeFilter
                  ? `No ${typeFilter} jobs recorded yet. Try a different filter.`
                  : "Jobs appear here as agents execute workflows."}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Job table */}
      {data && data.jobs.length > 0 && (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Type
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Title
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Status
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Started
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Duration
                </th>
              </tr>
            </thead>
            <tbody>
              {data.jobs.map((job) => (
                <JobRow key={job.job_id} job={job} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── JobRow ─────────────────────────────────────────────────────────────────

function JobRow({ job }: { job: Job }) {
  const typeCfg = JOB_TYPE_CONFIG[job.job_type] ?? JOB_TYPE_CONFIG.other;
  const TypeIcon = typeCfg.icon;
  const statusCfg = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.completed;
  const StatusIcon = statusCfg.icon;

  return (
    <tr className="border-b last:border-0 transition-colors hover:bg-muted/30">
      {/* Type */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <TypeIcon className={cn("h-4 w-4", typeCfg.className)} />
          <span className="text-xs font-medium">{typeCfg.label}</span>
        </div>
      </td>

      {/* Title */}
      <td className="px-4 py-3">
        <span className="font-medium">{job.title}</span>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
            statusCfg.badgeBg,
          )}
        >
          <StatusIcon
            className={cn(
              "h-3 w-3",
              job.status === "running" && "animate-spin",
            )}
          />
          {statusCfg.label}
        </span>
      </td>

      {/* Started */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span className="text-xs">{formatTimestamp(job.started_at)}</span>
        </div>
      </td>

      {/* Duration */}
      <td className="px-4 py-3">
        <span className="text-xs text-muted-foreground">
          {formatDuration(job.duration_ms)}
        </span>
      </td>
    </tr>
  );
}
