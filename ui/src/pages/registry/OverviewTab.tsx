import { Zap, FileText, Clapperboard, Wrench, ToggleLeft, Clock, AlertCircle, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { HARegistrySummary } from "@/lib/types";

interface OverviewTabProps {
  summary: HARegistrySummary | null;
  isLoading: boolean;
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  detail,
  color,
  bgColor,
}: {
  icon: typeof Activity;
  label: string;
  value: number;
  detail?: string;
  color: string;
  bgColor: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg",
            bgColor,
          )}
        >
          <Icon className={cn("h-5 w-5", color)} />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
          {detail && (
            <p className="text-[10px] text-muted-foreground/70">{detail}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function OverviewTab({ summary, isLoading }: OverviewTabProps) {
  if (isLoading)
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );

  if (!summary) return null;

  return (
    <div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <SummaryCard
          icon={Zap}
          label="Automations"
          value={summary.automations_count}
          detail={`${summary.automations_enabled} enabled`}
          color="text-amber-400"
          bgColor="bg-amber-500/10"
        />
        <SummaryCard
          icon={FileText}
          label="Scripts"
          value={summary.scripts_count}
          color="text-blue-400"
          bgColor="bg-blue-500/10"
        />
        <SummaryCard
          icon={Clapperboard}
          label="Scenes"
          value={summary.scenes_count}
          color="text-purple-400"
          bgColor="bg-purple-500/10"
        />
        <SummaryCard
          icon={Wrench}
          label="Services"
          value={summary.services_count}
          detail={`${summary.services_seeded} seeded`}
          color="text-emerald-400"
          bgColor="bg-emerald-500/10"
        />
        <SummaryCard
          icon={ToggleLeft}
          label="Helpers"
          value={summary.helpers_count ?? 0}
          color="text-green-400"
          bgColor="bg-green-500/10"
        />
      </div>

      {/* Last synced */}
      {summary.last_synced_at && (
        <p className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          Last synced: {formatRelativeTime(summary.last_synced_at)}
        </p>
      )}

      {/* MCP Gaps */}
      {summary.mcp_gaps && summary.mcp_gaps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <AlertCircle className="h-4 w-4 text-amber-400" />
              MCP Capability Gaps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {summary.mcp_gaps.map((gap, i) => {
                const [func, desc] = gap.split(": ");
                return (
                  <div
                    key={i}
                    className="flex items-start gap-2 rounded-lg bg-muted/30 px-3 py-2"
                  >
                    <code className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                      {func}
                    </code>
                    <span className="text-xs text-muted-foreground">
                      {desc}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
