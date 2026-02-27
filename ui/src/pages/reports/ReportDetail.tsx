import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileBarChart,
  Image,
  Lightbulb,
  Loader2,
  MessageSquare,
  Users,
  XCircle,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useReport } from "@/api/hooks/reports";
import { env } from "@/lib/env";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import type { AnalysisReport, CommunicationEntry } from "@/lib/types";

// ─── Agent config for avatars ───────────────────────────────────────────────

const AGENT_CONFIG: Record<
  string,
  { label: string; color: string; bgColor: string }
> = {
  energy_analyst: {
    label: "Energy",
    color: "text-amber-700 dark:text-amber-400",
    bgColor: "bg-amber-100 dark:bg-amber-900/30",
  },
  behavioral_analyst: {
    label: "Behavioral",
    color: "text-blue-700 dark:text-blue-400",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
  },
  diagnostic_analyst: {
    label: "Diagnostic",
    color: "text-purple-700 dark:text-purple-400",
    bgColor: "bg-purple-100 dark:bg-purple-900/30",
  },
  data_science_team: {
    label: "DS Team",
    color: "text-emerald-700 dark:text-emerald-400",
    bgColor: "bg-emerald-100 dark:bg-emerald-900/30",
  },
  architect: {
    label: "Architect",
    color: "text-zinc-700 dark:text-zinc-400",
    bgColor: "bg-zinc-100 dark:bg-zinc-800/50",
  },
  team: {
    label: "Team",
    color: "text-emerald-700 dark:text-emerald-400",
    bgColor: "bg-emerald-100 dark:bg-emerald-900/30",
  },
};

const MSG_TYPE_STYLES: Record<string, string> = {
  finding: "border-l-emerald-500",
  question: "border-l-blue-500",
  cross_reference: "border-l-purple-500",
  synthesis: "border-l-amber-500",
  status: "border-l-zinc-400",
};

// ─── Component ──────────────────────────────────────────────────────────────

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: report, isLoading, error } = useReport(id ?? "");

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-8 text-destructive">
          <XCircle className="h-5 w-5" />
          <p>
            {error
              ? `Failed to load report: ${(error as Error).message}`
              : "Report not found"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/reports"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Reports
      </Link>

      {/* Header */}
      <ReportHeader report={report} />

      {/* Summary */}
      {report.summary && <SummaryCard summary={report.summary} />}

      {/* Artifacts gallery */}
      {report.artifact_paths.length > 0 && (
        <ArtifactGallery reportId={report.id} paths={report.artifact_paths} />
      )}

      {/* Communication timeline */}
      {report.communication_log.length > 0 && (
        <CommunicationTimeline entries={report.communication_log} />
      )}

      {/* Linked insights */}
      {report.insight_ids.length > 0 && (
        <LinkedInsights insightIds={report.insight_ids} />
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function ReportHeader({ report }: { report: AnalysisReport }) {
  const createdAt = report.created_at
    ? new Date(report.created_at).toLocaleString()
    : "—";
  const completedAt = report.completed_at
    ? new Date(report.completed_at).toLocaleString()
    : null;

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {report.title}
          </h1>
          <p className="text-sm text-muted-foreground">
            {report.analysis_type.replace(/_/g, " ")}
          </p>
        </div>
        <StatusBadge status={report.status} />
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <Badge variant="secondary">{report.depth}</Badge>
        <div className="flex items-center gap-1">
          {report.strategy === "teamwork" ? (
            <Users className="h-3 w-3" />
          ) : (
            <Zap className="h-3 w-3" />
          )}
          {report.strategy}
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Created {createdAt}
        </div>
        {completedAt && (
          <div className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Completed {completedAt}
          </div>
        )}
        {report.insight_ids.length > 0 && (
          <div className="flex items-center gap-1">
            <Lightbulb className="h-3 w-3" />
            {report.insight_ids.length} insight
            {report.insight_ids.length !== 1 ? "s" : ""}
          </div>
        )}
        {report.communication_count > 0 && (
          <div className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {report.communication_count} message
            {report.communication_count !== 1 ? "s" : ""}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { icon: typeof CheckCircle2; variant: string }> = {
    completed: { icon: CheckCircle2, variant: "success" },
    running: { icon: Loader2, variant: "warning" },
    failed: { icon: XCircle, variant: "destructive" },
  };
  const c = cfg[status] ?? cfg.completed;
  const Icon = c.icon;

  return (
    <Badge variant={c.variant as any} className="gap-1">
      <Icon
        className={cn("h-3 w-3", status === "running" && "animate-spin")}
      />
      {status}
    </Badge>
  );
}

function SummaryCard({ summary }: { summary: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <FileBarChart className="h-4 w-4" />
          Executive Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MarkdownRenderer content={summary} className="text-sm" />
      </CardContent>
    </Card>
  );
}

function ArtifactGallery({
  reportId,
  paths,
}: {
  reportId: string;
  paths: string[];
}) {
  const baseUrl = `${env.API_URL}/v1/reports/${reportId}/artifacts`;

  const images = paths.filter((p) =>
    /\.(png|jpg|jpeg|svg|webp)$/i.test(p),
  );
  const others = paths.filter(
    (p) => !/\.(png|jpg|jpeg|svg|webp)$/i.test(p),
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Image className="h-4 w-4" />
          Artifacts ({paths.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Image grid */}
        {images.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {images.map((filename) => (
              <a
                key={filename}
                href={`${baseUrl}/${filename}`}
                target="_blank"
                rel="noopener noreferrer"
                className="group overflow-hidden rounded-lg border transition-shadow hover:shadow-md"
              >
                <img
                  src={`${baseUrl}/${filename}`}
                  alt={filename}
                  className="w-full object-cover transition-transform group-hover:scale-[1.02]"
                  loading="lazy"
                />
                <div className="px-2 py-1.5 text-[11px] text-muted-foreground truncate border-t">
                  {filename}
                </div>
              </a>
            ))}
          </div>
        )}

        {/* Other files */}
        {others.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {others.map((filename) => (
              <a
                key={filename}
                href={`${baseUrl}/${filename}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs hover:bg-muted transition-colors"
              >
                <FileBarChart className="h-3 w-3" />
                {filename}
              </a>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CommunicationTimeline({
  entries,
}: {
  entries: CommunicationEntry[];
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Agent Communication ({entries.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative space-y-0">
          {/* Timeline line */}
          <div className="absolute left-5 top-0 bottom-0 w-px bg-border" />

          {entries.map((entry, i) => {
            const agent =
              AGENT_CONFIG[entry.from_agent] ?? AGENT_CONFIG.team;
            const typeStyle =
              MSG_TYPE_STYLES[entry.message_type] ?? MSG_TYPE_STYLES.status;

            return (
              <div key={i} className="relative flex gap-3 py-2.5">
                {/* Agent avatar */}
                <div
                  className={cn(
                    "relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold",
                    agent.bgColor,
                    agent.color,
                  )}
                >
                  {agent.label.slice(0, 2).toUpperCase()}
                </div>

                {/* Message */}
                <div
                  className={cn(
                    "flex-1 rounded-lg border border-l-2 p-3",
                    typeStyle,
                  )}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn("text-xs font-medium", agent.color)}
                      >
                        {agent.label}
                      </span>
                      <Badge variant="outline" className="text-[9px]">
                        {entry.message_type.replace(/_/g, " ")}
                      </Badge>
                      {entry.to_agent !== "team" && (
                        <span className="text-[10px] text-muted-foreground">
                          → {AGENT_CONFIG[entry.to_agent]?.label ?? entry.to_agent}
                        </span>
                      )}
                    </div>
                  </div>
                  <MarkdownRenderer
                    content={entry.content}
                    className="text-xs text-muted-foreground"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function LinkedInsights({ insightIds }: { insightIds: string[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Lightbulb className="h-4 w-4" />
          Linked Insights ({insightIds.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {insightIds.map((id) => (
            <Link
              key={id}
              to={`/insights?id=${id}`}
              className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs hover:bg-muted transition-colors"
            >
              <Lightbulb className="h-3 w-3" />
              {id.slice(0, 8)}...
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
