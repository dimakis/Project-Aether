import { Link } from "react-router-dom";
import { Cpu, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { DomainSummary } from "@/lib/types";

export interface EntityStatusCardProps {
  domainsSummary?: DomainSummary[] | null;
  isLoading: boolean;
}

export function EntityStatusCard({
  domainsSummary,
  isLoading,
}: EntityStatusCardProps) {
  return (
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
        {isLoading ? (
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
  );
}
