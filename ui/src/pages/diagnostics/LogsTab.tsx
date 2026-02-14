import { useState } from "react";
import {
  AlertTriangle,
  Loader2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useErrorLog } from "@/api/hooks";

export function LogsTab() {
  const { data, isLoading, error, refetch } = useErrorLog();
  const [selectedIntegration, setSelectedIntegration] = useState<string>("");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center py-12">
          <AlertTriangle className="mb-2 h-8 w-8 text-destructive/50" />
          <p className="text-sm text-muted-foreground">
            Unable to fetch error log.
          </p>
          <Button
            size="sm"
            variant="outline"
            className="mt-3"
            onClick={() => refetch()}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const integrations = data?.by_integration
    ? Object.keys(data.by_integration).sort()
    : [];
  const displayEntries = selectedIntegration
    ? data?.by_integration[selectedIntegration] ?? []
    : [];

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{data?.summary.total ?? 0}</p>
            <p className="text-xs text-muted-foreground">Total Entries</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-destructive">
              {data?.summary.errors ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Errors</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-amber-400">
              {data?.summary.warnings ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Warnings</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{integrations.length}</p>
            <p className="text-xs text-muted-foreground">Integrations</p>
          </CardContent>
        </Card>
      </div>

      {/* Known patterns */}
      {data?.known_patterns && data.known_patterns.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Known Error Patterns</h3>
          <div className="space-y-2">
            {data.known_patterns.map((p, idx) => (
              <Card key={idx}>
                <CardContent className="flex items-start gap-3 p-4">
                  <AlertCircle
                    className={cn(
                      "mt-0.5 h-4 w-4 shrink-0",
                      p.severity === "high"
                        ? "text-destructive"
                        : p.severity === "medium"
                          ? "text-amber-400"
                          : "text-muted-foreground",
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {p.pattern.replace(/_/g, " ")}
                      </span>
                      <Badge
                        variant={
                          p.severity === "high" ? "destructive" : "secondary"
                        }
                        className="text-[10px]"
                      >
                        {p.severity}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {p.matched_entries} occurrence
                        {p.matched_entries !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {p.suggestion}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Integration filter + log entries */}
      {integrations.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Errors by Integration</h3>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {integrations.map((int) => (
              <Button
                key={int}
                size="sm"
                variant={selectedIntegration === int ? "secondary" : "ghost"}
                className="h-7 text-xs"
                onClick={() =>
                  setSelectedIntegration(
                    selectedIntegration === int ? "" : int,
                  )
                }
              >
                {int}{" "}
                <Badge variant="outline" className="ml-1 text-[9px]">
                  {data?.by_integration[int]?.length ?? 0}
                </Badge>
              </Button>
            ))}
          </div>

          {selectedIntegration && displayEntries.length > 0 && (
            <div className="max-h-[400px] space-y-1 overflow-y-auto rounded-lg border border-border p-2">
              {displayEntries.map((entry, idx) => (
                <div
                  key={idx}
                  className="rounded-md bg-muted/30 px-3 py-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        entry.level === "ERROR" ? "destructive" : "secondary"
                      }
                      className="text-[9px]"
                    >
                      {entry.level}
                    </Badge>
                    <span className="text-muted-foreground">
                      {entry.timestamp}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px]">{entry.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
