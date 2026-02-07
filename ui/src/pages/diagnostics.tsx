import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Server,
  Database,
  BarChart3,
  Radio,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useSystemStatus } from "@/api/hooks";

const COMPONENT_ICONS: Record<string, typeof Server> = {
  database: Database,
  mlflow: BarChart3,
  home_assistant: Radio,
};

export function DiagnosticsPage() {
  const { data: status, isLoading } = useSystemStatus();

  const components = status?.components ?? [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Activity className="h-6 w-6" />
          Diagnostics
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          System health and component status
        </p>
      </div>

      {/* Overall Status */}
      <Card className="mb-6">
        <CardContent className="flex items-center gap-4 p-6">
          {isLoading ? (
            <>
              <Skeleton className="h-12 w-12 rounded-xl" />
              <div>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="mt-1 h-4 w-48" />
              </div>
            </>
          ) : (
            <>
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-xl",
                  status?.status === "healthy"
                    ? "bg-success/10"
                    : "bg-destructive/10",
                )}
              >
                {status?.status === "healthy" ? (
                  <CheckCircle2 className="h-6 w-6 text-success" />
                ) : (
                  <XCircle className="h-6 w-6 text-destructive" />
                )}
              </div>
              <div>
                <h2 className="text-xl font-semibold">
                  {status?.status === "healthy"
                    ? "All Systems Operational"
                    : "System Degraded"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  Version {status?.version ?? "unknown"} &middot;{" "}
                  {status?.environment ?? "unknown"} environment
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Component Status */}
      <h3 className="mb-4 text-lg font-semibold">Components</h3>
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : components.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {components.map((comp) => {
            const Icon = COMPONENT_ICONS[comp.name] ?? Server;
            const isHealthy = comp.status === "healthy" || comp.status === "connected";

            return (
              <Card key={comp.name}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-lg",
                          isHealthy
                            ? "bg-success/10"
                            : "bg-destructive/10",
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4 w-4",
                            isHealthy
                              ? "text-success"
                              : "text-destructive",
                          )}
                        />
                      </div>
                      <div>
                        <p className="text-sm font-medium capitalize">
                          {comp.name.replace(/_/g, " ")}
                        </p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {comp.status}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={isHealthy ? "success" : "destructive"}
                      className="text-[10px]"
                    >
                      {isHealthy ? "OK" : "Error"}
                    </Badge>
                  </div>

                  {/* Message & Latency */}
                  {(comp.message || comp.latency_ms) && (
                    <div className="mt-3 space-y-1 border-t border-border pt-3">
                      {comp.message && (
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">
                            message
                          </span>
                          <span className="text-[10px] font-mono">
                            {comp.message}
                          </span>
                        </div>
                      )}
                      {comp.latency_ms != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">
                            latency
                          </span>
                          <span className="text-[10px] font-mono">
                            {comp.latency_ms.toFixed(1)}ms
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <AlertTriangle className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Unable to fetch component status
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
