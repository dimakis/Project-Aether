import { Link } from "react-router-dom";
import { Clock, ArrowRight, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2 } from "lucide-react";
import { RecentActivityFeed } from "../RecentActivityFeed";
import type { Proposal } from "@/lib/types";
import type { Insight } from "@/lib/types";

export interface RecentActivityCardProps {
  pendingProposals?: Proposal[] | null;
  proposalsLoading: boolean;
  recentProposals: Proposal[];
  recentInsights: Insight[];
}

export function RecentActivityCard({
  pendingProposals,
  proposalsLoading,
  recentProposals,
  recentInsights,
}: RecentActivityCardProps) {
  return (
    <div className="space-y-6">
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
            proposals={recentProposals}
            insights={recentInsights}
          />
        </CardContent>
      </Card>
    </div>
  );
}
