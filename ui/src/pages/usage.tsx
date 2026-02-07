import { useState } from "react";
import {
  DollarSign,
  Cpu,
  Zap,
  Clock,
  BarChart3,
  TrendingUp,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useUsageSummary, useUsageDaily, useUsageByModel } from "@/api/hooks";

// ─── Constants ───────────────────────────────────────────────────────────────

const PERIOD_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
];

const CHART_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#f97316",
];

// ─── Page ────────────────────────────────────────────────────────────────────

export function UsagePage() {
  const [days, setDays] = useState(30);

  const { data: summary, isLoading: summaryLoading } = useUsageSummary(days);
  const { data: daily, isLoading: dailyLoading } = useUsageDaily(days);
  const { data: models, isLoading: modelsLoading } = useUsageByModel(days);

  const formatCurrency = (v: number) =>
    v < 0.01 ? `$${v.toFixed(4)}` : `$${v.toFixed(2)}`;

  const formatTokens = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
    return v.toString();
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">LLM Usage</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            API call tracking, token consumption, and cost estimates
          </p>
        </div>

        {/* Period selector */}
        <div className="flex gap-1 rounded-lg border border-border bg-card p-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDays(opt.value)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                days === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          icon={Zap}
          label="Total Calls"
          value={summary?.total_calls}
          loading={summaryLoading}
        />
        <SummaryCard
          icon={Cpu}
          label="Total Tokens"
          value={summary?.total_tokens}
          format={formatTokens}
          loading={summaryLoading}
        />
        <SummaryCard
          icon={DollarSign}
          label="Estimated Cost"
          value={summary?.total_cost_usd}
          format={formatCurrency}
          loading={summaryLoading}
        />
        <SummaryCard
          icon={BarChart3}
          label="Models Used"
          value={summary?.by_model?.length}
          loading={summaryLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {/* Daily Usage Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              Daily Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            {dailyLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : daily?.data && daily.data.length > 0 ? (
              <ResponsiveContainer width="100%" height={256}>
                <BarChart data={daily.data}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--color-border)"
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v) =>
                      new Date(v).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })
                    }
                    fontSize={11}
                    stroke="var(--color-muted-foreground)"
                  />
                  <YAxis
                    fontSize={11}
                    stroke="var(--color-muted-foreground)"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "0.5rem",
                      fontSize: "12px",
                    }}
                    labelFormatter={(v) =>
                      new Date(v).toLocaleDateString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                      })
                    }
                  />
                  <Bar
                    dataKey="calls"
                    fill="#3b82f6"
                    radius={[4, 4, 0, 0]}
                    name="Calls"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                No usage data yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cost by Model Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              Cost by Model
            </CardTitle>
          </CardHeader>
          <CardContent>
            {modelsLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : models?.models && models.models.length > 0 ? (
              <ResponsiveContainer width="100%" height={256}>
                <PieChart>
                  <Pie
                    data={models.models}
                    dataKey="cost_usd"
                    nameKey="model"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={({ model, percent }) =>
                      `${model.split("/").pop()} (${(percent * 100).toFixed(0)}%)`
                    }
                    labelLine={false}
                    fontSize={11}
                  >
                    {models.models.map((_, i) => (
                      <Cell
                        key={i}
                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "0.5rem",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                No model data yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Model Breakdown Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            Model Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          {modelsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : models?.models && models.models.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="pb-2 font-medium">Model</th>
                    <th className="pb-2 font-medium">Provider</th>
                    <th className="pb-2 text-right font-medium">Calls</th>
                    <th className="pb-2 text-right font-medium">Input</th>
                    <th className="pb-2 text-right font-medium">Output</th>
                    <th className="pb-2 text-right font-medium">Cost</th>
                    <th className="pb-2 text-right font-medium">Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {models.models.map((m, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/50 last:border-0"
                    >
                      <td className="py-2.5 font-medium">{m.model}</td>
                      <td className="py-2.5">
                        <Badge variant="secondary" className="text-[10px]">
                          {m.provider}
                        </Badge>
                      </td>
                      <td className="py-2.5 text-right tabular-nums">
                        {m.calls.toLocaleString()}
                      </td>
                      <td className="py-2.5 text-right tabular-nums">
                        {formatTokens(m.input_tokens)}
                      </td>
                      <td className="py-2.5 text-right tabular-nums">
                        {formatTokens(m.output_tokens)}
                      </td>
                      <td className="py-2.5 text-right tabular-nums font-medium text-primary">
                        {formatCurrency(m.cost_usd)}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                        {m.avg_latency_ms != null
                          ? `${m.avg_latency_ms.toLocaleString()}ms`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No usage data for this period.
              LLM calls will appear here once the system starts processing requests.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Summary Card ────────────────────────────────────────────────────────────

function SummaryCard({
  icon: Icon,
  label,
  value,
  format,
  loading,
}: {
  icon: typeof DollarSign;
  label: string;
  value: number | undefined;
  format?: (v: number) => string;
  loading: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          {loading ? (
            <Skeleton className="mt-1 h-6 w-20" />
          ) : (
            <p className="text-lg font-semibold tabular-nums">
              {value != null
                ? format
                  ? format(value)
                  : value.toLocaleString()
                : "—"}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
