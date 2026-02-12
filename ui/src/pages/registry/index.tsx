import { useState } from "react";
import { BookOpen, Zap, FileText, Clapperboard, Wrench, Activity, Search, X, RefreshCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { queryKeys } from "@/api/hooks/queryKeys";
import {
  useRegistryAutomations,
  useRegistrySummary,
  useRegistryScripts,
  useRegistryScenes,
  useRegistryServices,
  useSyncRegistry,
} from "@/api/hooks";
import { InlineAssistant } from "@/components/InlineAssistant";
import { AutomationTab } from "./AutomationTab";
import { ScriptTab } from "./ScriptTab";
import { SceneTab } from "./SceneTab";
import { ServiceTab } from "./ServiceTab";
import { OverviewTab } from "./OverviewTab";
import { REGISTRY_SYSTEM_CONTEXT, REGISTRY_SUGGESTIONS } from "./constants";

const TABS = [
  { key: "overview", label: "Overview", icon: Activity },
  { key: "automations", label: "Automations", icon: Zap },
  { key: "scripts", label: "Scripts", icon: FileText },
  { key: "scenes", label: "Scenes", icon: Clapperboard },
  { key: "services", label: "Services", icon: Wrench },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export function RegistryPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: summary, isLoading: summaryLoading } = useRegistrySummary({
    enabled: activeTab === "overview",
  });
  const { data: automations, isLoading: autoLoading } =
    useRegistryAutomations({ enabled: activeTab === "automations" });
  const { data: scripts, isLoading: scriptsLoading } = useRegistryScripts({
    enabled: activeTab === "scripts",
  });
  const { data: scenes, isLoading: scenesLoading } = useRegistryScenes({
    enabled: activeTab === "scenes",
  });
  const { data: services, isLoading: servicesLoading } =
    useRegistryServices({ enabled: activeTab === "services" });
  const syncMut = useSyncRegistry();

  // Tab counts from summary (always loaded on first visit) or individual data
  const tabCounts: Record<string, number> = {
    automations: summary?.automations_count ?? automations?.total ?? 0,
    scripts: summary?.scripts_count ?? scripts?.total ?? 0,
    scenes: summary?.scenes_count ?? scenes?.total ?? 0,
    services: summary?.services_count ?? services?.total ?? 0,
    overview: 0,
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <BookOpen className="h-6 w-6" />
            HA Registry
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Home Assistant automations, scripts, scenes, and services
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => syncMut.mutate()}
          disabled={syncMut.isPending}
        >
          <RefreshCw
            className={`mr-2 h-3.5 w-3.5 ${syncMut.isPending ? "animate-spin" : ""}`}
          />
          {syncMut.isPending ? "Syncing..." : "Sync Registry"}
        </Button>
      </div>

      {/* Inline Assistant */}
      <div className="mb-6">
        <InlineAssistant
          systemContext={REGISTRY_SYSTEM_CONTEXT}
          suggestions={REGISTRY_SUGGESTIONS}
          invalidateKeys={[
            queryKeys.registry.automations,
            queryKeys.registry.scripts,
            queryKeys.registry.scenes,
            queryKeys.proposals.all,
          ]}
          placeholder="Ask Architect to optimize, edit, or create automations..."
        />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-muted p-1" role="tablist" aria-label="Registry sections">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                setSearchQuery("");
              }}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
              {tabCounts[tab.key] > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 min-w-5 justify-center px-1.5 py-0 text-[10px] font-medium"
                >
                  {tabCounts[tab.key]}
                </Badge>
              )}
            </button>
          );
        })}
      </div>

      {/* Search (not on overview) */}
      {activeTab !== "overview" && (
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Search ${activeTab}...`}
            className="pl-9"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Tab content */}
      {activeTab === "automations" && (
        <AutomationTab
          automations={automations?.automations ?? []}
          isLoading={autoLoading}
          searchQuery={searchQuery}
          enabledCount={automations?.enabled_count}
          disabledCount={automations?.disabled_count}
          onSync={() => syncMut.mutate()}
          isSyncing={syncMut.isPending}
        />
      )}
      {activeTab === "scripts" && (
        <ScriptTab
          scripts={scripts?.scripts ?? []}
          isLoading={scriptsLoading}
          searchQuery={searchQuery}
          runningCount={scripts?.running_count}
          onSync={() => syncMut.mutate()}
          isSyncing={syncMut.isPending}
        />
      )}
      {activeTab === "scenes" && (
        <SceneTab
          scenes={scenes?.scenes ?? []}
          isLoading={scenesLoading}
          searchQuery={searchQuery}
          onSync={() => syncMut.mutate()}
          isSyncing={syncMut.isPending}
        />
      )}
      {activeTab === "services" && (
        <ServiceTab
          services={services?.services ?? []}
          domains={services?.domains ?? []}
          isLoading={servicesLoading}
          searchQuery={searchQuery}
          onSync={() => syncMut.mutate()}
          isSyncing={syncMut.isPending}
        />
      )}
      {activeTab === "overview" && (
        <OverviewTab summary={summary ?? null} isLoading={summaryLoading} />
      )}
    </div>
  );
}

export default RegistryPage;
