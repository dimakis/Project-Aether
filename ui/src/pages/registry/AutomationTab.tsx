import { useState, useMemo } from "react";
import { ToggleLeft, ToggleRight, ChevronRight, Clock, Code } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { YamlViewer } from "@/components/ui/data-viewer";
import { cn, formatRelativeTime } from "@/lib/utils";
import { useAutomationConfig } from "@/api/hooks";
import type { Automation } from "@/lib/types";
import { EmptyState } from "./EmptyState";
import { StatPill } from "./StatPill";

interface AutomationTabProps {
  automations: Automation[];
  isLoading: boolean;
  searchQuery: string;
  enabledCount?: number;
  disabledCount?: number;
}

function AutomationDetail({ automation }: { automation: Automation }) {
  const { data, isLoading } = useAutomationConfig(
    automation.ha_automation_id || automation.id,
  );

  return (
    <div
      className="mt-4 space-y-3 border-t border-border/50 pt-4"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Description */}
      {automation.description && (
        <p className="text-xs text-muted-foreground">
          {automation.description}
        </p>
      )}

      {/* Metadata */}
      <div className="flex flex-wrap gap-2">
        {automation.trigger_types?.map((t, i) => (
          <Badge key={i} variant="secondary" className="text-[10px]">
            trigger: {t}
          </Badge>
        ))}
        {automation.last_triggered && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <Clock className="h-2.5 w-2.5" />
            Last: {formatRelativeTime(automation.last_triggered)}
          </span>
        )}
      </div>

      {/* YAML Configuration */}
      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Code className="h-3 w-3" />
          Configuration
        </h4>
        {isLoading ? (
          <Skeleton className="h-24" />
        ) : data?.yaml ? (
          <div className="overflow-hidden rounded-lg border border-border/50">
            <YamlViewer content={data.yaml} collapsible maxHeight={400} />
          </div>
        ) : (
          <p className="text-[10px] text-muted-foreground">
            Configuration not available from Home Assistant
          </p>
        )}
      </div>
    </div>
  );
}

export function AutomationTab({
  automations,
  isLoading,
  searchQuery,
  enabledCount,
  disabledCount,
}: AutomationTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!searchQuery) return automations;
    const q = searchQuery.toLowerCase();
    return automations.filter(
      (a) =>
        a.alias.toLowerCase().includes(q) ||
        a.entity_id.toLowerCase().includes(q) ||
        (a.description ?? "").toLowerCase().includes(q),
    );
  }, [automations, searchQuery]);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );

  if (filtered.length === 0) return <EmptyState type="automations" />;

  return (
    <div>
      {/* Stats row */}
      <div className="mb-4 flex gap-3">
        <StatPill
          label="Enabled"
          value={enabledCount ?? 0}
          color="text-emerald-400"
        />
        <StatPill
          label="Disabled"
          value={disabledCount ?? 0}
          color="text-zinc-400"
        />
        <StatPill label="Total" value={automations.length} color="text-primary" />
      </div>

      {searchQuery && filtered.length !== automations.length && (
        <p className="mb-2 text-xs text-muted-foreground">
          Showing {filtered.length} of {automations.length}
        </p>
      )}

      <div className="space-y-2">
        {filtered.map((auto) => (
          <Card
            key={auto.id}
            className={cn(
              "cursor-pointer transition-all hover:shadow-md",
              expandedId === auto.id && "ring-1 ring-primary/30",
            )}
            onClick={() =>
              setExpandedId(expandedId === auto.id ? null : auto.id)
            }
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                {auto.state === "on" ? (
                  <ToggleRight className="h-5 w-5 shrink-0 text-emerald-400" />
                ) : (
                  <ToggleLeft className="h-5 w-5 shrink-0 text-zinc-400" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{auto.alias}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {auto.entity_id}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {auto.mode && (
                    <Badge variant="secondary" className="text-[10px]">
                      {auto.mode}
                    </Badge>
                  )}
                  <span className="text-[10px] text-muted-foreground">
                    {auto.trigger_count ?? 0}T / {auto.condition_count ?? 0}C /{" "}
                    {auto.action_count ?? 0}A
                  </span>
                  <ChevronRight
                    className={cn(
                      "h-3.5 w-3.5 text-muted-foreground transition-transform",
                      expandedId === auto.id && "rotate-90",
                    )}
                  />
                </div>
              </div>

              {/* Expanded detail */}
              {expandedId === auto.id && (
                <AutomationDetail automation={auto} />
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
