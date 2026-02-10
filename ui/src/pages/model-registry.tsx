import { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Star,
  Plus,
  Loader2,
  BarChart3,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Zap,
  Clock,
  DollarSign,
  Hash,
  Activity,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  useModelSummary,
  useModelRatings,
  useCreateModelRating,
  useModelPerformance,
  useModels,
} from "@/api/hooks";
import type { ModelSummaryItem, ModelRatingItem, ModelPerformanceItem } from "@/api/client";

type PageView = "performance" | "notes";

const TIME_RANGES: { label: string; hours: number }[] = [
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
];

const AGENT_ROLES = [
  "architect",
  "data_scientist",
  "orchestrator",
  "developer",
  "librarian",
  "energy_analyst",
  "behavioral_analyst",
  "diagnostic_analyst",
  "dashboard_designer",
];

// ─── Star Rating Component ──────────────────────────────────────────────────

function StarRating({
  value,
  onChange,
  size = "sm",
  readonly = false,
}: {
  value: number;
  onChange?: (v: number) => void;
  size?: "sm" | "md";
  readonly?: boolean;
}) {
  const [hover, setHover] = useState(0);
  const sz = size === "md" ? "h-5 w-5" : "h-3.5 w-3.5";
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          className={cn(
            "transition-colors",
            readonly ? "cursor-default" : "cursor-pointer hover:scale-110",
          )}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
          onClick={() => onChange?.(star)}
        >
          <Star
            className={cn(
              sz,
              (hover || value) >= star
                ? "fill-amber-400 text-amber-400"
                : "text-muted-foreground/30",
            )}
          />
        </button>
      ))}
    </div>
  );
}

// ─── Performance Metric Card ────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card/50 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
      {sub && (
        <p className="text-[10px] text-muted-foreground">{sub}</p>
      )}
    </div>
  );
}

// ─── Performance Row ────────────────────────────────────────────────────────

function PerformanceRow({ perf }: { perf: ModelPerformanceItem }) {
  const [expanded, setExpanded] = useState(false);

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/50"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{perf.model}</span>
            {perf.agent_role && (
              <Badge variant="outline" className="text-[10px] capitalize shrink-0">
                {perf.agent_role.replace(/_/g, " ")}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-6 text-xs tabular-nums text-muted-foreground shrink-0">
          <span className="flex items-center gap-1">
            <Hash className="h-3 w-3" />
            {perf.call_count} calls
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {perf.avg_latency_ms ? `${Math.round(perf.avg_latency_ms)}ms` : "—"}
          </span>
          <span className="flex items-center gap-1">
            <Zap className="h-3 w-3" />
            {formatTokens(perf.total_tokens)} tok
          </span>
          <span className="flex items-center gap-1">
            <DollarSign className="h-3 w-3" />
            {perf.total_cost_usd != null ? `$${perf.total_cost_usd.toFixed(2)}` : "—"}
          </span>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 py-3">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricCard
                  icon={Clock}
                  label="Avg Latency"
                  value={perf.avg_latency_ms ? `${Math.round(perf.avg_latency_ms)}ms` : "—"}
                  sub={perf.p95_latency_ms ? `p95: ${Math.round(perf.p95_latency_ms)}ms` : undefined}
                />
                <MetricCard
                  icon={DollarSign}
                  label="Total Cost"
                  value={perf.total_cost_usd != null ? `$${perf.total_cost_usd.toFixed(4)}` : "—"}
                  sub={perf.avg_cost_per_call != null ? `$${perf.avg_cost_per_call.toFixed(4)}/call` : undefined}
                />
                <MetricCard
                  icon={Zap}
                  label="Input Tokens"
                  value={formatTokens(perf.total_input_tokens)}
                />
                <MetricCard
                  icon={Zap}
                  label="Output Tokens"
                  value={formatTokens(perf.total_output_tokens)}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Notes Tab (Manual Ratings) ─────────────────────────────────────────────

function NotesTab({ roleFilter }: { roleFilter: string }) {
  const { data: summaries, isLoading } = useModelSummary(roleFilter || undefined);
  const { data: modelsData } = useModels();
  const createMutation = useCreateModelRating();
  const [showRate, setShowRate] = useState(false);
  const [modelName, setModelName] = useState("");
  const [agentRole, setAgentRole] = useState("architect");
  const [rating, setRating] = useState(0);
  const [notes, setNotes] = useState("");

  const handleSubmit = () => {
    if (!modelName || !rating) return;
    createMutation.mutate(
      { model_name: modelName, agent_role: agentRole, rating, notes: notes || null, config_snapshot: null },
      { onSuccess: () => { setShowRate(false); setModelName(""); setRating(0); setNotes(""); } },
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={() => setShowRate(!showRate)}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add Note
        </Button>
      </div>

      <AnimatePresence>
        {showRate && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <Card className="border-amber-500/30 bg-amber-500/5">
              <CardContent className="space-y-4 pt-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs text-muted-foreground">Model</label>
                    <select
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                    >
                      <option value="">Select model...</option>
                      {modelsData?.data?.map((m) => (
                        <option key={m.id} value={m.id}>{m.id}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-muted-foreground">Agent Role</label>
                    <select
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={agentRole}
                      onChange={(e) => setAgentRole(e.target.value)}
                    >
                      {AGENT_ROLES.map((r) => (
                        <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">Rating</label>
                  <StarRating value={rating} onChange={setRating} size="md" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">Notes</label>
                  <textarea
                    className="min-h-[60px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    placeholder="How well did this model perform?"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setShowRate(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleSubmit} disabled={!modelName || !rating || createMutation.isPending}>
                    {createMutation.isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                    Submit
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : summaries && summaries.length > 0 ? (
        summaries.map((s: ModelSummaryItem) => (
          <NotesRow key={`${s.model_name}-${s.agent_role}`} summary={s} />
        ))
      ) : (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No manual notes yet. Add a note to supplement auto-collected metrics.
        </p>
      )}
    </div>
  );
}

function NotesRow({ summary }: { summary: ModelSummaryItem }) {
  const [expanded, setExpanded] = useState(false);
  const { data: ratingsData, isLoading } = useModelRatings(
    expanded ? summary.model_name : undefined,
    expanded ? summary.agent_role : undefined,
  );

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/50"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <div className="flex-1">
          <span className="text-sm font-medium">{summary.model_name}</span>
          <Badge variant="outline" className="ml-2 text-[10px] capitalize">
            {summary.agent_role.replace(/_/g, " ")}
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          <StarRating value={Math.round(summary.avg_rating)} readonly />
          <span className="text-sm tabular-nums text-amber-400">{summary.avg_rating.toFixed(1)}</span>
          <span className="text-xs text-muted-foreground">{summary.rating_count} note(s)</span>
        </div>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 py-3 space-y-2">
              {isLoading ? (
                <Loader2 className="mx-auto h-4 w-4 animate-spin" />
              ) : ratingsData?.items?.map((r: ModelRatingItem) => (
                <div key={r.id} className="flex items-start gap-3 rounded-md bg-muted/30 px-3 py-2">
                  <StarRating value={r.rating} readonly />
                  <div className="flex-1 min-w-0">
                    {r.notes && (
                      <p className="text-xs text-muted-foreground flex items-start gap-1">
                        <MessageSquare className="mt-0.5 h-3 w-3 shrink-0" />
                        {r.notes}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                      {new Date(r.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export function ModelRegistryPage() {
  const [searchParams] = useSearchParams();
  const initialRole = searchParams.get("agent_role") ?? "";
  const [view, setView] = useState<PageView>("performance");
  const [roleFilter, setRoleFilter] = useState(initialRole);
  const [timeRange, setTimeRange] = useState(168);

  // Always fetch ALL data — filter client-side for instant switching
  const { data: perfData, isLoading } = useModelPerformance(undefined, timeRange);

  // Derive role list from actual data (+ fallback for empty state)
  const dataRoles = useMemo(() => {
    if (!perfData || perfData.length === 0) return AGENT_ROLES;
    const roles = new Set<string>();
    for (const p of perfData) {
      if (p.agent_role) roles.add(p.agent_role);
    }
    return Array.from(roles).sort();
  }, [perfData]);

  // Client-side filter
  const filtered = useMemo(() => {
    const all = perfData ?? [];
    if (!roleFilter) return all;
    return all.filter((p) => p.agent_role === roleFilter);
  }, [perfData, roleFilter]);

  // Summary stats across all filtered rows
  const totalCalls = filtered.reduce((s, p) => s + p.call_count, 0);
  const totalCost = filtered.reduce((s, p) => s + (p.total_cost_usd ?? 0), 0);
  const totalTokens = filtered.reduce((s, p) => s + p.total_tokens, 0);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <BarChart3 className="h-6 w-6" />
          Model Performance
        </h1>
        <p className="text-sm text-muted-foreground">
          Auto-collected metrics from actual LLM usage across all agents.
        </p>
      </div>

      {/* View toggle */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 border-b border-border">
          {([
            { key: "performance" as const, label: "Performance", icon: Activity },
            { key: "notes" as const, label: "Notes", icon: MessageSquare },
          ] as const).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={cn(
                "flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
                view === key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {view === "performance" && (
          <div className="flex gap-1">
            {TIME_RANGES.map(({ label, hours }) => (
              <Button
                key={hours}
                size="sm"
                variant={timeRange === hours ? "secondary" : "ghost"}
                className="h-7 text-xs"
                onClick={() => setTimeRange(hours)}
              >
                {label}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Role filter */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground">Filter by role:</span>
        <div className="flex flex-wrap gap-1.5">
          <Button
            size="sm"
            variant={!roleFilter ? "secondary" : "ghost"}
            className="h-7 text-xs"
            onClick={() => setRoleFilter("")}
          >
            All
          </Button>
          {dataRoles.map((r) => (
            <Button
              key={r}
              size="sm"
              variant={roleFilter === r ? "secondary" : "ghost"}
              className="h-7 text-xs capitalize"
              onClick={() => setRoleFilter(roleFilter === r ? "" : r)}
            >
              {r.replace(/_/g, " ")}
            </Button>
          ))}
        </div>
      </div>

      {/* Performance View */}
      {view === "performance" && (
        <>
          {/* Summary cards */}
          {!isLoading && filtered.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              <MetricCard icon={Hash} label="Total Calls" value={totalCalls.toLocaleString()} />
              <MetricCard icon={Zap} label="Total Tokens" value={totalTokens >= 1_000_000 ? `${(totalTokens / 1_000_000).toFixed(1)}M` : `${(totalTokens / 1_000).toFixed(1)}K`} />
              <MetricCard icon={DollarSign} label="Total Cost" value={`$${totalCost.toFixed(2)}`} />
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length > 0 ? (
            <div className="space-y-2">
              {filtered.map((p) => (
                <PerformanceRow
                  key={`${p.model}-${p.agent_role}`}
                  perf={p}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center py-12">
                <Activity className="mb-2 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  No usage data yet. Performance metrics will appear automatically as you use agents.
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Notes View */}
      {view === "notes" && <NotesTab roleFilter={roleFilter} />}
    </div>
  );
}
