import { useNavigate, Link } from "react-router-dom";
import {
  FileCheck,
  Lightbulb,
  Cpu,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  Zap,
  Play,
  MessageSquare,
  Search,
  Wifi,
  WifiOff,
  DollarSign,
  Bot,
  MapPin,
  BarChart3,
  Webhook,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { AgentDetail, InsightSchedule, ModelPerformanceItem, UsageModelBreakdown } from "@/lib/types";
import {
  useSystemStatus,
  usePendingProposals,
  useInsightsSummary,
  useDomainsSummary,
  useProposals,
  useInsights,
  useRunAnalysis,
  useUsageSummary,
  useModelPerformance,
  useAgents,
  useInsightSchedules,
  useHAZones,
} from "@/api/hooks";
import { COMPONENT_ICONS, STATUS_COLORS } from "./constants";
import { formatUptime } from "./helpers";
import { StatCard } from "./StatCard";
import { RecentActivityFeed } from "./RecentActivityFeed";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: status, isLoading: statusLoading } = useSystemStatus();
  const { data: pendingProposals, isLoading: proposalsLoading } =
    usePendingProposals();
  const { data: insightsSummary, isLoading: insightsLoading } =
    useInsightsSummary();
  const { data: domainsSummary, isLoading: domainsLoading } =
    useDomainsSummary();
  const { data: recentProposals } = useProposals();
  const { data: recentInsights } = useInsights();
  const analyzeMut = useRunAnalysis();

  // New dashboard data sources
  const { data: usageSummary } = useUsageSummary();
  const { data: modelPerf } = useModelPerformance();
  const { data: agentsData } = useAgents();
  const { data: schedulesData } = useInsightSchedules();
  const { data: zonesData } = useHAZones();

  const totalEntities =
    domainsSummary?.reduce((sum, d) => sum + d.count, 0) ?? 0;
  const domainCount = domainsSummary?.length ?? 0;

  // Derived data for new cards
  const totalAgents = agentsData?.total ?? 0;
  const enabledAgents = agentsData?.agents?.filter(
    (a: AgentDetail) => a.status !== "disabled",
  ).length ?? 0;
  const draftAgents = agentsData?.agents?.filter(
    (a: AgentDetail) => a.active_config?.status === "draft",
  ).length ?? 0;

  const webhookSchedules = (schedulesData?.items ?? []).filter(
    (s: InsightSchedule) => s.trigger_type === "webhook",
  );
  const activeWebhooks = webhookSchedules.filter(
    (s: InsightSchedule) => s.enabled,
  ).length;

  const topModels = (modelPerf ?? [])
    .sort((a: ModelPerformanceItem, b: ModelPerformanceItem) => b.call_count - a.call_count)
    .slice(0, 3);

  const zonesCount = zonesData?.length ?? 0;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your Home Assistant AI system
        </p>
      </div>

      {/* Component Health Row */}
      <div className="mb-6">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          System Health
        </h2>
        {statusLoading ? (
          <div className="grid gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-4">
            {/* Overall status */}
            <Card
              className={cn(
                "cursor-pointer border transition-all hover:shadow-md",
                status?.status === "healthy"
                  ? "border-emerald-500/20"
                  : "border-amber-500/20",
              )}
              onClick={() => navigate("/diagnostics")}
            >
              <CardContent className="flex items-center gap-3 p-4">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    STATUS_COLORS[status?.status ?? "healthy"]?.bg,
                  )}
                >
                  <Activity
                    className={cn(
                      "h-5 w-5",
                      STATUS_COLORS[status?.status ?? "healthy"]?.text,
                    )}
                  />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    System
                  </p>
                  <p className="text-sm font-semibold capitalize">
                    {status?.status ?? "Unknown"}
                  </p>
                  {status?.uptime_seconds != null && (
                    <p className="text-[10px] text-muted-foreground">
                      Up {formatUptime(status.uptime_seconds)}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Individual components */}
            {status?.components?.map((comp) => {
              const colors = STATUS_COLORS[comp.status] ?? STATUS_COLORS.healthy;
              const Icon = COMPONENT_ICONS[comp.name] ?? Wifi;
              return (
                <Card
                  key={comp.name}
                  className="cursor-pointer transition-all hover:shadow-md"
                  onClick={() => navigate("/diagnostics")}
                >
                  <CardContent className="flex items-center gap-3 p-4">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg",
                        colors.bg,
                      )}
                    >
                      {comp.status === "unhealthy" ? (
                        <WifiOff className={cn("h-5 w-5", colors.text)} />
                      ) : (
                        <Icon className={cn("h-5 w-5", colors.text)} />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        {comp.name.replace(/_/g, " ")}
                      </p>
                      <p className="text-sm font-semibold capitalize">
                        {comp.status}
                      </p>
                      {comp.latency_ms != null && (
                        <p className="text-[10px] text-muted-foreground">
                          {comp.latency_ms.toFixed(0)}ms
                        </p>
                      )}
                    </div>
                    <div
                      className={cn("h-2 w-2 rounded-full", colors.dot)}
                    />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Clickable Stats */}
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          icon={FileCheck}
          label="Pending Proposals"
          value={pendingProposals?.length ?? 0}
          loading={proposalsLoading}
          color="text-amber-400"
          bgColor="bg-amber-400/10"
          onClick={() => navigate("/proposals?status=pending")}
        />
        <StatCard
          icon={Lightbulb}
          label="Pending Insights"
          value={insightsSummary?.pending_count ?? 0}
          loading={insightsLoading}
          color="text-blue-400"
          bgColor="bg-blue-400/10"
          onClick={() => navigate("/insights?status=pending")}
          detail={
            insightsSummary?.high_impact_count
              ? `${insightsSummary.high_impact_count} high impact`
              : undefined
          }
        />
        <StatCard
          icon={Cpu}
          label="Entities"
          value={totalEntities}
          loading={domainsLoading}
          color="text-purple-400"
          bgColor="bg-purple-400/10"
          onClick={() => navigate("/entities")}
          detail={`${domainCount} domains`}
        />
        <StatCard
          icon={AlertTriangle}
          label="High Impact"
          value={insightsSummary?.high_impact_count ?? 0}
          loading={insightsLoading}
          color="text-red-400"
          bgColor="bg-red-400/10"
          onClick={() => navigate("/insights")}
        />
        <StatCard
          icon={MapPin}
          label="HA Zones"
          value={zonesCount}
          loading={false}
          color="text-teal-400"
          bgColor="bg-teal-400/10"
          onClick={() => navigate("/settings/zones")}
          detail={zonesCount === 1 ? "1 server" : `${zonesCount} servers`}
        />
      </div>

      {/* Main content: Activity feed + Quick Actions */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Activity - spans 2 cols */}
        <div className="space-y-6 lg:col-span-2">
          {/* Pending Proposals */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-amber-400" />
                Awaiting Approval
              </CardTitle>
              <Link to="/proposals">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  View All
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {proposalsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-14" />
                  <Skeleton className="h-14" />
                </div>
              ) : (pendingProposals?.length ?? 0) > 0 ? (
                <div className="space-y-2">
                  {pendingProposals?.slice(0, 4).map((p) => (
                    <Link
                      key={p.id}
                      to={`/proposals?id=${p.id}`}
                      className="flex items-center justify-between rounded-lg border border-border/50 p-3 transition-all hover:border-border hover:bg-accent/50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">{p.name}</p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {p.description || "No description"}
                        </p>
                      </div>
                      <Badge className="ml-3 shrink-0 bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 text-[10px]">
                        Pending
                      </Badge>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-3 py-6 text-center">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400/50" />
                  <p className="text-sm text-muted-foreground">
                    No proposals awaiting approval
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Activity Feed */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Activity className="h-4 w-4 text-primary" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <RecentActivityFeed
                proposals={recentProposals?.items ?? []}
                insights={recentInsights?.items ?? []}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* LLM Usage Summary */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <DollarSign className="h-4 w-4 text-emerald-400" />
                LLM Usage (30d)
              </CardTitle>
              <Link to="/usage">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  Details
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {usageSummary ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Total Calls</span>
                    <span className="font-semibold tabular-nums">
                      {usageSummary.total_calls?.toLocaleString() ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Total Tokens</span>
                    <span className="font-semibold tabular-nums">
                      {usageSummary.total_tokens?.toLocaleString() ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Total Cost</span>
                    <span className="font-semibold tabular-nums text-emerald-400">
                      ${(usageSummary.total_cost_usd ?? 0).toFixed(2)}
                    </span>
                  </div>
                  {usageSummary.by_model?.length > 0 && (
                    <div className="mt-2 space-y-1 border-t border-border/50 pt-2">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Top Models
                      </p>
                      {usageSummary.by_model.slice(0, 3).map((m: UsageModelBreakdown) => (
                        <div key={m.model} className="flex justify-between text-[11px]">
                          <span className="truncate text-muted-foreground">{m.model}</span>
                          <span className="tabular-nums">${m.cost_usd.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No usage data yet</p>
              )}
            </CardContent>
          </Card>

          {/* Agent Fleet Overview */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Bot className="h-4 w-4 text-blue-400" />
                Agent Fleet
              </CardTitle>
              <Link to="/agents">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  Manage
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Total Agents</span>
                  <span className="font-semibold">{totalAgents}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Enabled</span>
                  <span className="font-semibold text-emerald-400">{enabledAgents}</span>
                </div>
                {draftAgents > 0 && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Pending Drafts</span>
                    <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400">
                      {draftAgents}
                    </Badge>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Model Performance Top 3 */}
          {topModels.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BarChart3 className="h-4 w-4 text-indigo-400" />
                  Model Performance
                </CardTitle>
                <Link to="/agents/registry">
                  <Button variant="ghost" size="sm" className="h-7 text-xs">
                    Full Report
                    <ArrowRight className="ml-1 h-3 w-3" />
                  </Button>
                </Link>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {topModels.map((m: ModelPerformanceItem) => (
                    <div
                      key={m.model}
                      className="flex items-center justify-between rounded-lg border border-border/30 px-2.5 py-1.5"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-xs font-medium">{m.model}</p>
                        <p className="text-[10px] text-muted-foreground">
                          {m.call_count} calls
                          {m.avg_latency_ms != null && ` | ${m.avg_latency_ms.toFixed(0)}ms avg`}
                        </p>
                      </div>
                      {m.total_cost_usd != null && (
                        <span className="text-[10px] tabular-nums text-muted-foreground">
                          ${m.total_cost_usd.toFixed(2)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-yellow-400" />
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => navigate("/chat")}
              >
                <MessageSquare className="mr-2 h-3.5 w-3.5" />
                New Conversation
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => analyzeMut.mutate({})}
                disabled={analyzeMut.isPending}
              >
                <Play className="mr-2 h-3.5 w-3.5" />
                {analyzeMut.isPending ? "Running..." : "Run Analysis"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => navigate("/entities")}
              >
                <Search className="mr-2 h-3.5 w-3.5" />
                Browse Entities
              </Button>
            </CardContent>
          </Card>

          {/* Webhook Activity */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Webhook className="h-4 w-4 text-orange-400" />
                Webhooks
              </CardTitle>
              <Link to="/webhooks">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  Manage
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Active Triggers</span>
                <span className="font-semibold">{activeWebhooks}</span>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Total Configured</span>
                <span>{webhookSchedules.length}</span>
              </div>
            </CardContent>
          </Card>

          {/* Insights Summary */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Lightbulb className="h-4 w-4 text-blue-400" />
                Insights
              </CardTitle>
              <Link to="/insights">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  View All
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {insightsLoading ? (
                <Skeleton className="h-20" />
              ) : insightsSummary ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Total</span>
                    <span className="font-semibold">{insightsSummary.total}</span>
                  </div>
                  {Object.entries(insightsSummary.by_status ?? {}).map(
                    ([s, count]) => (
                      <div key={s} className="flex justify-between text-xs">
                        <span className="capitalize text-muted-foreground">{s}</span>
                        <span>{count as number}</span>
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Run an analysis to generate insights
                </p>
              )}
            </CardContent>
          </Card>

          {/* Entity Domains */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Cpu className="h-4 w-4 text-purple-400" />
                Entity Domains
              </CardTitle>
              <Link to="/entities">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  Browse
                  <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {domainsLoading ? (
                <Skeleton className="h-16" />
              ) : (domainsSummary?.length ?? 0) > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {domainsSummary?.slice(0, 15).map((d) => (
                    <Link key={d.domain} to={`/entities?domain=${d.domain}`}>
                      <Badge
                        variant="secondary"
                        className="cursor-pointer text-[10px] transition-colors hover:bg-accent"
                      >
                        {d.domain}
                        <span className="ml-1 text-muted-foreground">
                          {d.count}
                        </span>
                      </Badge>
                    </Link>
                  ))}
                  {(domainsSummary?.length ?? 0) > 15 && (
                    <Badge variant="secondary" className="text-[10px]">
                      +{(domainsSummary?.length ?? 0) - 15} more
                    </Badge>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No entities discovered yet
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
