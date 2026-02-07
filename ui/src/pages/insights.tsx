import { useState, useRef, useEffect } from "react";
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
  X,
  ArrowRight,
  Activity,
  Clock,
  Target,
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

// ─── Config ──────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  InsightType,
  { icon: typeof Zap; label: string; color: string }
> = {
  energy_optimization: { icon: Zap, label: "Energy", color: "text-yellow-400" },
  anomaly_detection: {
    icon: AlertTriangle,
    label: "Anomaly",
    color: "text-red-400",
  },
  usage_pattern: {
    icon: TrendingUp,
    label: "Usage",
    color: "text-cyan-400",
  },
  cost_saving: {
    icon: DollarSign,
    label: "Cost Saving",
    color: "text-green-400",
  },
  maintenance_prediction: {
    icon: Wrench,
    label: "Maintenance",
    color: "text-orange-400",
  },
  automation_gap: {
    icon: GitBranch,
    label: "Automation Gap",
    color: "text-purple-400",
  },
  automation_inefficiency: {
    icon: BarChart3,
    label: "Inefficiency",
    color: "text-amber-400",
  },
  correlation: {
    icon: Activity,
    label: "Correlation",
    color: "text-indigo-400",
  },
  device_health: {
    icon: Heart,
    label: "Device Health",
    color: "text-pink-400",
  },
  behavioral_pattern: {
    icon: Users,
    label: "Behavioral",
    color: "text-teal-400",
  },
};

const IMPACT_STYLES: Record<string, { bg: string; text: string; ring: string }> = {
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    ring: "ring-red-500/30",
  },
  high: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    ring: "ring-orange-500/30",
  },
  medium: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    ring: "ring-blue-500/30",
  },
  low: {
    bg: "bg-zinc-500/10",
    text: "text-zinc-400",
    ring: "ring-zinc-500/30",
  },
};

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "reviewed", label: "Reviewed" },
  { value: "actioned", label: "Actioned" },
  { value: "dismissed", label: "Dismissed" },
];

// ─── Page ────────────────────────────────────────────────────────────────────

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
      <div className="mb-4 flex flex-wrap gap-4">
        <FilterGroup
          label="Status"
          options={STATUS_FILTERS}
          value={statusFilter}
          onChange={setStatusFilter}
        />
        <FilterGroup
          label="Type"
          options={[
            { value: "", label: "All" },
            ...Object.entries(TYPE_CONFIG).map(([key, c]) => ({
              value: key,
              label: c.label,
            })),
          ]}
          value={typeFilter}
          onChange={setTypeFilter}
        />
      </div>

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
        <InsightDetailOverlay
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

// ─── Summary stat card ───────────────────────────────────────────────────────

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
        <p className={cn("text-2xl font-bold", className)}>{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

// ─── Filter group ────────────────────────────────────────────────────────────

function FilterGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      <span className="mr-1 self-center text-xs text-muted-foreground">
        {label}:
      </span>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
            value === o.value
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-accent",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ─── Insight Card (grid item) ────────────────────────────────────────────────

function InsightCard({
  insight,
  isExpanded,
  onExpand,
}: {
  insight: Insight;
  isExpanded: boolean;
  onExpand: () => void;
}) {
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

        {/* Bottom row: confidence + entities + arrow */}
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

          <div className="ml-auto text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </button>
  );
}

// ─── Confidence ring (mini SVG) ──────────────────────────────────────────────

function ConfidenceRing({
  value,
  size = 20,
}: {
  value: number;
  size?: number;
}) {
  const radius = (size - 3) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value);

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="text-muted/50"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className={cn(
          value >= 0.8
            ? "text-green-400"
            : value >= 0.5
              ? "text-blue-400"
              : "text-orange-400",
        )}
      />
    </svg>
  );
}

// ─── Detail Overlay ──────────────────────────────────────────────────────────

function InsightDetailOverlay({
  insight,
  onClose,
  onReview,
  onDismiss,
  isReviewing,
  isDismissing,
}: {
  insight: Insight;
  onClose: () => void;
  onReview: () => void;
  onDismiss: () => void;
  isReviewing: boolean;
  isDismissing: boolean;
}) {
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
          {insight.evidence && <EvidenceSection evidence={insight.evidence} />}

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
          {insight.mlflow_run_id && (
            <span className="text-[10px] font-mono text-muted-foreground">
              run: {insight.mlflow_run_id.slice(0, 12)}
            </span>
          )}
          <div className="ml-auto flex gap-2">
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

// ─── Metric pill ─────────────────────────────────────────────────────────────

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

// ─── Evidence Section (renders based on evidence shape) ──────────────────────

function EvidenceSection({ evidence }: { evidence: Record<string, unknown> }) {
  const sections: React.ReactNode[] = [];

  // ── Cost savings highlight ─────────────────────────────────────────────────
  if ("estimated_cost_saving_usd" in evidence) {
    const saving = evidence.estimated_cost_saving_usd as number;
    const shiftable = evidence.total_shiftable_kwh as number;
    const peakRate = evidence.assumed_peak_rate_usd_per_kwh as number;
    const offpeakRate = evidence.assumed_offpeak_rate_usd_per_kwh as number;

    sections.push(
      <div key="savings" className="rounded-xl bg-green-500/5 p-4 ring-1 ring-green-500/20">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-green-400">
          Estimated Savings
        </h4>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold text-green-400">
            ${formatNumber(saving)}
          </span>
          <span className="text-sm text-muted-foreground">potential savings</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Shiftable kWh</p>
            <p className="font-semibold">{formatNumber(shiftable)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Peak rate</p>
            <p className="font-semibold">${peakRate}/kWh</p>
          </div>
          <div>
            <p className="text-muted-foreground">Off-peak rate</p>
            <p className="font-semibold">${offpeakRate}/kWh</p>
          </div>
        </div>
      </div>,
    );
  }

  // ── Top consumers bar chart ────────────────────────────────────────────────
  if ("top_consumers" in evidence) {
    const consumers = evidence.top_consumers as Array<{
      entity_id: string;
      total_kwh: number;
      pct_of_total: number;
    }>;

    sections.push(
      <div key="consumers">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Top Energy Consumers
        </h4>
        <div className="space-y-2">
          {consumers.map((c) => {
            const shortName = c.entity_id.split(".").pop() ?? c.entity_id;
            return (
              <div key={c.entity_id} className="group/bar">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span
                    className="truncate font-mono text-muted-foreground"
                    title={c.entity_id}
                  >
                    {shortName}
                  </span>
                  <div className="flex gap-3 text-right">
                    <span className="font-semibold">
                      {formatNumber(c.total_kwh)} kWh
                    </span>
                    <span className="w-12 text-muted-foreground">
                      {c.pct_of_total.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
                    style={{ width: `${Math.min(c.pct_of_total * 2.5, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>,
    );
  }

  // ── Peak / off-peak hours chart ────────────────────────────────────────────
  if ("peak_hours" in evidence && "off_peak_hours" in evidence) {
    const peakHours = evidence.peak_hours as Array<{
      hour_start_utc: string;
      kwh: number;
      pct_of_period: number;
    }>;
    const offPeakHours = evidence.off_peak_hours as Array<{
      hour_start_utc: string;
      kwh: number;
      pct_of_period: number;
    }>;
    const totalKwh = (evidence.hourly_profile_total_kwh as number) || 1;

    sections.push(
      <div key="peak-hours">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Peak &amp; Off-Peak Hours
        </h4>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-orange-500/5 p-3 ring-1 ring-orange-500/20">
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-orange-400">
              Peak Hours
            </p>
            {peakHours.map((h) => {
              const hour = new Date(h.hour_start_utc).getHours();
              return (
                <div
                  key={h.hour_start_utc}
                  className="flex items-center justify-between py-1 text-xs"
                >
                  <span className="font-mono text-muted-foreground">
                    {String(hour).padStart(2, "0")}:00
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-orange-400"
                        style={{
                          width: `${(h.kwh / totalKwh) * 100 * 4}%`,
                        }}
                      />
                    </div>
                    <span className="w-12 text-right font-semibold">
                      {h.pct_of_period.toFixed(1)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="rounded-lg bg-blue-500/5 p-3 ring-1 ring-blue-500/20">
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-blue-400">
              Off-Peak Hours
            </p>
            {offPeakHours.map((h) => {
              const hour = new Date(h.hour_start_utc).getHours();
              return (
                <div
                  key={h.hour_start_utc}
                  className="flex items-center justify-between py-1 text-xs"
                >
                  <span className="font-mono text-muted-foreground">
                    {String(hour).padStart(2, "0")}:00
                  </span>
                  <span className="font-semibold text-blue-400">
                    {h.kwh === 0 ? "Idle" : `${formatNumber(h.kwh)} kWh`}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>,
    );
  }

  // ── Candidates table (shifting opportunities) ──────────────────────────────
  if ("candidates_reported" in evidence) {
    const candidates = evidence.candidates_reported as Array<{
      entity_id: string;
      total_kwh: number;
      share_in_peak: number;
      keyword_flexible: boolean;
    }>;

    sections.push(
      <div key="candidates">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Shifting Candidates
        </h4>
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  Entity
                </th>
                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                  kWh
                </th>
                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                  Peak Share
                </th>
                <th className="px-3 py-2 text-center font-medium text-muted-foreground">
                  Flexible
                </th>
              </tr>
            </thead>
            <tbody>
              {candidates.slice(0, 8).map((c) => {
                const shortName =
                  c.entity_id.split(".").pop() ?? c.entity_id;
                return (
                  <tr
                    key={c.entity_id}
                    className="border-b border-border/50 last:border-0"
                  >
                    <td
                      className="max-w-[180px] truncate px-3 py-2 font-mono"
                      title={c.entity_id}
                    >
                      {shortName}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {formatNumber(c.total_kwh)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              c.share_in_peak > 0.6
                                ? "bg-red-400"
                                : c.share_in_peak > 0.3
                                  ? "bg-orange-400"
                                  : "bg-green-400",
                            )}
                            style={{
                              width: `${c.share_in_peak * 100}%`,
                            }}
                          />
                        </div>
                        <span className="w-10 text-right">
                          {(c.share_in_peak * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {c.keyword_flexible ? (
                        <CheckCircle2 className="mx-auto h-3.5 w-3.5 text-green-400" />
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {candidates.length > 8 && (
            <div className="border-t border-border bg-muted/20 px-3 py-1.5 text-center text-[10px] text-muted-foreground">
              +{candidates.length - 8} more candidates
            </div>
          )}
        </div>
      </div>,
    );
  }

  // ── Failed analysis ────────────────────────────────────────────────────────
  if ("exit_code" in evidence) {
    sections.push(
      <div
        key="failed"
        className="rounded-lg bg-red-500/5 p-4 ring-1 ring-red-500/20"
      >
        <div className="flex items-center gap-2 text-sm text-red-400">
          <XCircle className="h-4 w-4" />
          <span className="font-medium">Analysis Failed</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Exit code: {String(evidence.exit_code)} | Timed out:{" "}
          {String(evidence.timed_out ?? false)}
        </p>
      </div>,
    );
  }

  if (sections.length === 0) {
    // Fallback: render evidence as formatted JSON
    return (
      <div>
        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Evidence
        </h4>
        <pre className="overflow-auto rounded-lg bg-muted p-3 text-[11px] text-muted-foreground">
          {JSON.stringify(evidence, null, 2)}
        </pre>
      </div>
    );
  }

  return <div className="space-y-5">{sections}</div>;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toFixed(1);
}
