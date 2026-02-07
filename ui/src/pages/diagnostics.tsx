import { useState } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Server,
  Database,
  BarChart3,
  Radio,
  Heart,
  FileWarning,
  Shield,
  Workflow,
  Loader2,
  RefreshCw,
  Clock,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useSystemStatus,
  useHAHealth,
  useErrorLog,
  useConfigCheck,
  useRecentTraces,
} from "@/api/hooks";

// ─── Types ──────────────────────────────────────────────────────────────────

type DiagTab = "overview" | "ha-health" | "error-log" | "traces" | "config";

const TABS: Array<{ id: DiagTab; label: string; icon: typeof Activity }> = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "ha-health", label: "HA Health", icon: Heart },
  { id: "error-log", label: "Error Log", icon: FileWarning },
  { id: "traces", label: "Agent Traces", icon: Workflow },
  { id: "config", label: "Config Check", icon: Shield },
];

const COMPONENT_ICONS: Record<string, typeof Server> = {
  database: Database,
  mlflow: BarChart3,
  home_assistant: Radio,
};

// ─── Page ───────────────────────────────────────────────────────────────────

export function DiagnosticsPage() {
  const [activeTab, setActiveTab] = useState<DiagTab>("overview");

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Activity className="h-6 w-6" />
          Diagnostics
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          System health, HA diagnostics, error analysis, and agent traces.
        </p>
      </div>

      {/* Tab navigation */}
      <div className="mb-6 flex gap-1 rounded-lg border border-border bg-muted/30 p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              activeTab === id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && <OverviewTab />}
      {activeTab === "ha-health" && <HAHealthTab />}
      {activeTab === "error-log" && <ErrorLogTab />}
      {activeTab === "traces" && <TracesTab />}
      {activeTab === "config" && <ConfigCheckTab />}
    </div>
  );
}

// ─── Overview Tab ───────────────────────────────────────────────────────────

function OverviewTab() {
  const { data: status, isLoading } = useSystemStatus();
  const components = status?.components ?? [];

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card>
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
      <h3 className="text-lg font-semibold">Components</h3>
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
            const isHealthy =
              comp.status === "healthy" || comp.status === "connected";

            return (
              <Card key={comp.name}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-lg",
                          isHealthy ? "bg-success/10" : "bg-destructive/10",
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4 w-4",
                            isHealthy ? "text-success" : "text-destructive",
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

// ─── HA Health Tab ──────────────────────────────────────────────────────────

function HAHealthTab() {
  const { data, isLoading, error, refetch } = useHAHealth();

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
            Unable to fetch HA health data. Is Home Assistant connected?
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

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Unavailable Entities
              </span>
              <Badge
                variant={
                  data?.summary.unavailable_count
                    ? "destructive"
                    : "success"
                }
              >
                {data?.summary.unavailable_count ?? 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Stale Entities
              </span>
              <Badge
                variant={
                  data?.summary.stale_count ? "destructive" : "success"
                }
              >
                {data?.summary.stale_count ?? 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Unhealthy Integrations
              </span>
              <Badge
                variant={
                  data?.summary.unhealthy_integration_count
                    ? "destructive"
                    : "success"
                }
              >
                {data?.summary.unhealthy_integration_count ?? 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Unavailable Entities */}
      {data?.unavailable_entities && data.unavailable_entities.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Unavailable Entities</h3>
          <div className="rounded-lg border border-border">
            <div className="grid grid-cols-4 gap-4 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>Entity ID</span>
              <span>State</span>
              <span>Integration</span>
              <span>Last Changed</span>
            </div>
            {data.unavailable_entities.map((e) => (
              <div
                key={e.entity_id}
                className="grid grid-cols-4 gap-4 border-b border-border px-4 py-2 text-sm last:border-0"
              >
                <span className="font-mono text-xs">{e.entity_id}</span>
                <Badge variant="destructive" className="w-fit text-[10px]">
                  {e.state}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {e.integration}
                </span>
                <span className="text-xs text-muted-foreground">
                  {e.last_changed
                    ? new Date(e.last_changed).toLocaleString()
                    : "Unknown"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stale Entities */}
      {data?.stale_entities && data.stale_entities.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium">Stale Entities</h3>
          <div className="rounded-lg border border-border">
            <div className="grid grid-cols-4 gap-4 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>Entity ID</span>
              <span>State</span>
              <span>Integration</span>
              <span>Last Changed</span>
            </div>
            {data.stale_entities.map((e) => (
              <div
                key={e.entity_id}
                className="grid grid-cols-4 gap-4 border-b border-border px-4 py-2 text-sm last:border-0"
              >
                <span className="font-mono text-xs">{e.entity_id}</span>
                <span className="text-xs">{e.state}</span>
                <span className="text-xs text-muted-foreground">
                  {e.integration}
                </span>
                <span className="text-xs text-muted-foreground">
                  {e.last_changed
                    ? new Date(e.last_changed).toLocaleString()
                    : "Unknown"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unhealthy Integrations */}
      {data?.unhealthy_integrations &&
        data.unhealthy_integrations.length > 0 && (
          <div>
            <h3 className="mb-3 text-sm font-medium">
              Unhealthy Integrations
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {data.unhealthy_integrations.map((i) => (
                <Card key={i.entry_id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{i.title}</span>
                      <Badge variant="destructive" className="text-[10px]">
                        {i.state.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {i.domain}
                    </p>
                    {i.reason && (
                      <p className="mt-2 text-xs text-destructive">
                        {i.reason}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

      {/* All healthy */}
      {data &&
        !data.unavailable_entities.length &&
        !data.stale_entities.length &&
        !data.unhealthy_integrations.length && (
          <Card>
            <CardContent className="flex flex-col items-center py-12">
              <CheckCircle2 className="mb-2 h-8 w-8 text-success" />
              <p className="text-sm font-medium text-success">
                All entities and integrations are healthy
              </p>
            </CardContent>
          </Card>
        )}
    </div>
  );
}

// ─── Error Log Tab ──────────────────────────────────────────────────────────

function ErrorLogTab() {
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

// ─── Traces Tab ─────────────────────────────────────────────────────────────

function TracesTab() {
  const { data, isLoading, error } = useRecentTraces(50);

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
          <AlertTriangle className="mb-2 h-8 w-8 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">
            Unable to fetch traces. Is MLflow running?
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          Recent Traces ({data?.total ?? 0})
        </h3>
      </div>

      {data?.traces && data.traces.length > 0 ? (
        <div className="rounded-lg border border-border">
          <div className="grid grid-cols-4 gap-4 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium text-muted-foreground">
            <span>Trace ID</span>
            <span>Status</span>
            <span>Duration</span>
            <span>Time</span>
          </div>
          {data.traces.map((t) => (
            <div
              key={t.trace_id}
              className="grid grid-cols-4 gap-4 border-b border-border px-4 py-2 text-sm last:border-0"
            >
              <span className="font-mono text-xs truncate">
                {t.trace_id}
              </span>
              <Badge
                variant={t.status === "OK" ? "success" : "destructive"}
                className="w-fit text-[10px]"
              >
                {t.status}
              </Badge>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {t.duration_ms != null
                  ? `${(t.duration_ms / 1000).toFixed(1)}s`
                  : "N/A"}
              </span>
              <span className="text-xs text-muted-foreground">
                {new Date(t.timestamp_ms).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <Workflow className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No traces found. Start a conversation to generate traces.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Config Check Tab ───────────────────────────────────────────────────────

function ConfigCheckTab() {
  const { data, isLoading, refetch, isFetching } = useConfigCheck();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Configuration Validation</h3>
          <p className="text-xs text-muted-foreground">
            Check your Home Assistant configuration for errors and warnings.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Shield className="mr-1.5 h-3.5 w-3.5" />
          )}
          Run Check
        </Button>
      </div>

      {isLoading || isFetching ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Result card */}
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-xl",
                  data.valid ? "bg-success/10" : "bg-destructive/10",
                )}
              >
                {data.valid ? (
                  <CheckCircle2 className="h-6 w-6 text-success" />
                ) : (
                  <XCircle className="h-6 w-6 text-destructive" />
                )}
              </div>
              <div>
                <h2 className="text-lg font-semibold">
                  {data.valid
                    ? "Configuration Valid"
                    : "Configuration Issues Found"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {data.errors.length} error{data.errors.length !== 1 ? "s" : ""}
                  , {data.warnings.length} warning
                  {data.warnings.length !== 1 ? "s" : ""}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Errors */}
          {data.errors.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-destructive">
                Errors
              </h4>
              <div className="space-y-1">
                {data.errors.map((err, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2"
                  >
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
                    <span className="text-xs">{err}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-amber-400">
                Warnings
              </h4>
              <div className="space-y-1">
                {data.warnings.map((warn, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2"
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                    <span className="text-xs">{warn}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <Shield className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Click "Run Check" to validate your HA configuration.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
