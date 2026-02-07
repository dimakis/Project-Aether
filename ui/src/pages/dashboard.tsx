import { Link } from "react-router-dom";
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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useSystemStatus,
  usePendingProposals,
  useInsightsSummary,
  useDomainsSummary,
} from "@/api/hooks";

export function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useSystemStatus();
  const { data: pendingProposals, isLoading: proposalsLoading } =
    usePendingProposals();
  const { data: insightsSummary, isLoading: insightsLoading } =
    useInsightsSummary();
  const { data: domainsSummary, isLoading: domainsLoading } =
    useDomainsSummary();

  const totalEntities =
    domainsSummary?.reduce((sum, d) => sum + d.count, 0) ?? 0;
  const domainCount = domainsSummary?.length ?? 0;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your Home Assistant AI system
        </p>
      </div>

      {/* Stats Grid */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* System Status */}
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
              <Activity className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">System</p>
              {statusLoading ? (
                <Skeleton className="mt-1 h-5 w-16" />
              ) : (
                <p className="text-lg font-semibold">
                  {status?.status === "healthy" ? "Healthy" : "Degraded"}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Proposals */}
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
              <FileCheck className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Pending Proposals
              </p>
              {proposalsLoading ? (
                <Skeleton className="mt-1 h-5 w-8" />
              ) : (
                <p className="text-lg font-semibold">
                  {pendingProposals?.length ?? 0}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Insights */}
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Lightbulb className="h-5 w-5 text-info" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Pending Insights
              </p>
              {insightsLoading ? (
                <Skeleton className="mt-1 h-5 w-8" />
              ) : (
                <p className="text-lg font-semibold">
                  {insightsSummary?.pending_count ?? 0}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Entities */}
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Cpu className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Entities</p>
              {domainsLoading ? (
                <Skeleton className="mt-1 h-5 w-16" />
              ) : (
                <p className="text-lg font-semibold">
                  {totalEntities}
                  <span className="ml-1 text-sm font-normal text-muted-foreground">
                    in {domainCount} domains
                  </span>
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pending Proposals */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4 text-warning" />
              Awaiting Approval
            </CardTitle>
            <Link to="/proposals">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {proposalsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : (pendingProposals?.length ?? 0) > 0 ? (
              <div className="space-y-3">
                {pendingProposals?.slice(0, 5).map((p) => (
                  <Link
                    key={p.id}
                    to={`/proposals?id=${p.id}`}
                    className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-accent"
                  >
                    <div>
                      <p className="text-sm font-medium">{p.name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {p.description || "No description"}
                      </p>
                    </div>
                    <Badge variant="warning">Pending</Badge>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center py-8 text-center">
                <CheckCircle2 className="mb-2 h-8 w-8 text-success/50" />
                <p className="text-sm text-muted-foreground">
                  No proposals awaiting approval
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Insights Overview */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-info" />
              Insights Summary
            </CardTitle>
            <Link to="/insights">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {insightsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : insightsSummary ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
                  <span className="text-sm text-muted-foreground">Total</span>
                  <span className="text-sm font-semibold">
                    {insightsSummary.total}
                  </span>
                </div>
                {insightsSummary.high_impact_count > 0 && (
                  <div className="flex items-center justify-between rounded-lg bg-destructive/5 px-3 py-2">
                    <span className="flex items-center gap-2 text-sm text-destructive">
                      <AlertTriangle className="h-3 w-3" />
                      High Impact
                    </span>
                    <span className="text-sm font-semibold text-destructive">
                      {insightsSummary.high_impact_count}
                    </span>
                  </div>
                )}
                {Object.entries(insightsSummary.by_status).map(
                  ([status, count]) => (
                    <div
                      key={status}
                      className="flex items-center justify-between px-3 py-1"
                    >
                      <span className="text-sm capitalize text-muted-foreground">
                        {status}
                      </span>
                      <span className="text-sm">{count as number}</span>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center py-8 text-center">
                <Zap className="mb-2 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  Run an analysis to generate insights
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Entity Domains */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="h-4 w-4 text-primary" />
              Entity Domains
            </CardTitle>
            <Link to="/entities">
              <Button variant="ghost" size="sm">
                Browse
                <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {domainsLoading ? (
              <div className="flex gap-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-20" />
                ))}
              </div>
            ) : (domainsSummary?.length ?? 0) > 0 ? (
              <div className="flex flex-wrap gap-2">
                {domainsSummary?.map((d) => (
                  <Link key={d.domain} to={`/entities?domain=${d.domain}`}>
                    <Badge
                      variant="secondary"
                      className="cursor-pointer transition-colors hover:bg-accent"
                    >
                      {d.domain}
                      <span className="ml-1.5 text-muted-foreground">
                        {d.count}
                      </span>
                    </Badge>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No entities discovered yet. Run entity sync from the Entities
                page.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
