import { useState } from "react";
import {
  BookOpen,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useRegistryAutomations, useRegistrySummary } from "@/api/hooks";

const TABS = ["Automations", "Summary"] as const;

export function RegistryPage() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>(
    "Automations",
  );
  const { data: automations, isLoading: autoLoading } =
    useRegistryAutomations();
  const { data: summary, isLoading: summaryLoading } = useRegistrySummary();

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <BookOpen className="h-6 w-6" />
          HA Registry
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Home Assistant automations, scripts, scenes, and services
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-muted p-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "rounded-md px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Automations" && (
        <div>
          {autoLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (automations?.automations?.length ?? 0) === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center py-16">
                <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  No automations found. Sync the registry first.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              <div className="mb-4 flex gap-3 text-sm text-muted-foreground">
                <span>
                  {automations?.total} total
                </span>
                <span>
                  {automations?.enabled_count} enabled
                </span>
                <span>
                  {automations?.disabled_count} disabled
                </span>
              </div>
              {automations?.automations.map((auto) => (
                <Card key={auto.id}>
                  <CardContent className="flex items-center gap-4 p-4">
                    {auto.state === "on" ? (
                      <ToggleRight className="h-5 w-5 shrink-0 text-success" />
                    ) : (
                      <ToggleLeft className="h-5 w-5 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{auto.alias}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {auto.entity_id}
                        {auto.description && ` — ${auto.description}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[10px]">
                        {auto.mode}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {auto.trigger_count}T / {auto.condition_count}C /{" "}
                        {auto.action_count}A
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "Summary" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summaryLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))
          ) : summary ? (
            <>
              <SummaryCard
                label="Automations"
                value={summary.automations_count}
                detail={`${summary.automations_enabled} enabled`}
              />
              <SummaryCard
                label="Scripts"
                value={summary.scripts_count}
              />
              <SummaryCard
                label="Scenes"
                value={summary.scenes_count}
              />
              <SummaryCard
                label="Services"
                value={summary.services_count}
                detail={`${summary.services_seeded} seeded`}
              />
              {summary.mcp_gaps.length > 0 && (
                <Card className="sm:col-span-2 lg:col-span-3">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <AlertCircle className="h-4 w-4 text-warning" />
                      MCP Capability Gaps
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {summary.mcp_gaps.map((gap, i) => (
                        <li
                          key={i}
                          className="text-xs text-muted-foreground"
                        >
                          {gap}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: number;
  detail?: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
        {detail && (
          <p className="mt-1 text-[10px] text-muted-foreground/70">
            {detail}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
