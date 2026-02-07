import { Power, PowerOff, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AgentDetail, AgentStatusValue } from "@/lib/types";

export function OverviewTab({
  agent,
  onStatusChange,
  statusPending,
}: {
  agent: AgentDetail;
  onStatusChange: (status: AgentStatusValue) => void;
  statusPending: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* Status controls */}
      <div>
        <h3 className="mb-2 text-sm font-medium">Status</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={agent.status === "enabled" ? "default" : "outline"}
            onClick={() => onStatusChange("enabled")}
            disabled={statusPending || agent.status === "enabled"}
          >
            <Power className="mr-1.5 h-3.5 w-3.5" />
            Enabled
          </Button>
          <Button
            size="sm"
            variant={agent.status === "disabled" ? "destructive" : "outline"}
            onClick={() => onStatusChange("disabled")}
            disabled={statusPending || agent.status === "disabled"}
          >
            <PowerOff className="mr-1.5 h-3.5 w-3.5" />
            Disabled
          </Button>
          <Button
            size="sm"
            variant={agent.status === "primary" ? "default" : "outline"}
            onClick={() => onStatusChange("primary")}
            disabled={statusPending || agent.status === "primary"}
          >
            <Star className="mr-1.5 h-3.5 w-3.5" />
            Primary
          </Button>
        </div>
      </div>

      {/* Current config summary */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Active Config
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {agent.active_config ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Model</span>
                  <span className="font-mono text-xs">
                    {agent.active_config.model_name ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Temperature</span>
                  <span>{agent.active_config.temperature ?? "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fallback</span>
                  <span className="font-mono text-xs">
                    {agent.active_config.fallback_model ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span>v{agent.active_config.version_number}</span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">No active config</p>
            )}
          </CardContent>
        </Card>

        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Active Prompt
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {agent.active_prompt ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span>v{agent.active_prompt.version_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Length</span>
                  <span>
                    {agent.active_prompt.prompt_template.length} chars
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                  {agent.active_prompt.prompt_template.slice(0, 150)}...
                </p>
              </>
            ) : (
              <p className="text-muted-foreground">No active prompt</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
