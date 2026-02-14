import { CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useHAHealth } from "@/api/hooks";

export function HAHealthTab() {
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
