import { useState } from "react";
import {
  Activity,
  BarChart3,
  Heart,
  FileWarning,
  Workflow,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { OverviewTab } from "./OverviewTab";
import { HAHealthTab } from "./HAHealthTab";
import { LogsTab } from "./LogsTab";
import { TracingTab } from "./TracingTab";
import { ConfigCheckTab } from "./ConfigCheckTab";
import { EvaluationsTab } from "./EvaluationsTab";

// ─── Types ──────────────────────────────────────────────────────────────────

export type DiagTab =
  | "overview"
  | "ha-health"
  | "error-log"
  | "traces"
  | "config"
  | "evaluations";

const TABS: Array<{ id: DiagTab; label: string; icon: typeof Activity }> = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "ha-health", label: "HA Health", icon: Heart },
  { id: "error-log", label: "Error Log", icon: FileWarning },
  { id: "traces", label: "Agent Traces", icon: Workflow },
  { id: "config", label: "Config Check", icon: Shield },
  { id: "evaluations", label: "Evaluations", icon: BarChart3 },
];

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
      {activeTab === "error-log" && <LogsTab />}
      {activeTab === "traces" && <TracingTab />}
      {activeTab === "config" && <ConfigCheckTab />}
      {activeTab === "evaluations" && <EvaluationsTab />}
    </div>
  );
}
