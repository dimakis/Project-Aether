import { Link } from "react-router-dom";
import { Lightbulb, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useInsights } from "@/api/hooks";

const ENERGY_TYPES = new Set([
  "energy_optimization",
  "cost_saving",
  "usage_pattern",
]);

export function RecentEnergyInsights() {
  const { data, isLoading } = useInsights();

  const energyInsights = (data?.items ?? [])
    .filter((i) => ENERGY_TYPES.has(i.insight_type))
    .slice(0, 5);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Lightbulb className="h-4 w-4 text-blue-400" />
          Recent Energy Insights
        </CardTitle>
        <Link to="/insights">
          <Button variant="ghost" size="sm" className="h-7 text-xs">
            View All
            <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))}
          </div>
        ) : energyInsights.length === 0 ? (
          <p className="py-4 text-center text-xs text-muted-foreground">
            No energy insights yet. Run an analysis to get started.
          </p>
        ) : (
          <div className="space-y-2">
            {energyInsights.map((insight) => (
              <div
                key={insight.id}
                className="flex items-start gap-2 rounded-lg border border-border/30 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium">{insight.title}</p>
                  <p className="mt-0.5 line-clamp-1 text-[10px] text-muted-foreground">
                    {insight.description}
                  </p>
                </div>
                <Badge variant="outline" className="shrink-0 text-[9px]">
                  {Math.round((insight.confidence ?? 0) * 100)}%
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
