import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAgentConfigVersions, useAgentPromptVersions } from "@/api/hooks";
import type { VersionStatusValue } from "@/lib/types";
import { VERSION_STATUS_COLORS } from "./constants";

// ─── History Tab ─────────────────────────────────────────────────────────────

export function HistoryTab({ agentName }: { agentName: string }) {
  const { data: configVersions } = useAgentConfigVersions(agentName);
  const { data: promptVersions } = useAgentPromptVersions(agentName);

  // Merge and sort by created_at descending
  const events: Array<{
    type: "config" | "prompt";
    version_number: number;
    version: string | null;
    status: string;
    summary: string | null;
    created_at: string;
    promoted_at: string | null;
    detail: string;
  }> = [];

  configVersions?.forEach((v) => {
    events.push({
      type: "config",
      version_number: v.version_number,
      version: v.version,
      status: v.status,
      summary: v.change_summary,
      created_at: v.created_at,
      promoted_at: v.promoted_at,
      detail: `${v.model_name ?? "—"} / temp ${v.temperature ?? "—"}`,
    });
  });

  promptVersions?.forEach((v) => {
    events.push({
      type: "prompt",
      version_number: v.version_number,
      version: v.version,
      status: v.status,
      summary: v.change_summary,
      created_at: v.created_at,
      promoted_at: v.promoted_at,
      detail: `${v.prompt_template.length} chars`,
    });
  });

  events.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div className="space-y-2">
      <h3 className="mb-3 text-sm font-medium">Combined History</h3>
      {events.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No version history yet.
        </p>
      ) : (
        <div className="relative space-y-0 pl-4">
          {/* Timeline line */}
          <div className="absolute bottom-0 left-[7px] top-0 w-px bg-border" />

          {events.map((event) => (
            <div key={`${event.type}-${event.version_number}`} className="relative flex gap-3 pb-4">
              {/* Timeline dot */}
              <div
                className={cn(
                  "relative z-10 mt-1.5 h-2.5 w-2.5 rounded-full ring-2 ring-background",
                  event.type === "config"
                    ? "bg-blue-400"
                    : "bg-purple-400",
                )}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium">
                    {event.type === "config" ? "Config" : "Prompt"}{" "}
                    {event.version ? event.version : `v${event.version_number}`}
                  </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-[9px] ring-1",
                      VERSION_STATUS_COLORS[event.status as VersionStatusValue],
                    )}
                  >
                    {event.status}
                  </Badge>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(event.created_at).toLocaleDateString()}{" "}
                    {new Date(event.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {event.detail}
                </p>
                {event.summary && (
                  <p className="mt-0.5 text-xs text-muted-foreground/70">
                    {event.summary}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
