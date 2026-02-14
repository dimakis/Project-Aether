import { useNavigate, Link } from "react-router-dom";
import {
  FileCheck,
  Lightbulb,
  Cpu,
  AlertTriangle,
  ArrowRight,
  Zap,
  Play,
  MessageSquare,
  Search,
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
import { StatCard } from "./StatCard";
import {
  SystemOverviewCard,
  RecentActivityCard,
  EntityStatusCard,
} from "./cards";

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
        <SystemOverviewCard status={status} isLoading={statusLoading} />
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
          <RecentActivityCard
            pendingProposals={pendingProposals}
            proposalsLoading={proposalsLoading}
            recentProposals={recentProposals?.items ?? []}
            recentInsights={recentInsights?.items ?? []}
          />
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

          <EntityStatusCard
            domainsSummary={domainsSummary}
            isLoading={domainsLoading}
          />
        </div>
      </div>
    </div>
  );
}
