import { AlertTriangle, Loader2, Clock, Workflow } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRecentTraces } from "@/api/hooks";

export function TracingTab() {
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
