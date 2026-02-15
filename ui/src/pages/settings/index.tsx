import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Save,
  RotateCcw,
  Timer,
  LayoutDashboard,
  FlaskConical,
  Loader2,
  CheckCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppSettings, usePatchSettings, useResetSettings } from "@/api/hooks";

// ─── Field metadata for rendering ───────────────────────────────────────────

interface FieldDef {
  key: string;
  label: string;
  description: string;
  type: "number" | "boolean";
  unit?: string;
  min?: number;
  max?: number;
}

const CHAT_FIELDS: FieldDef[] = [
  {
    key: "stream_timeout_seconds",
    label: "Stream Timeout",
    description: "Maximum time a streaming response can run before being terminated",
    type: "number",
    unit: "seconds",
    min: 60,
    max: 3600,
  },
  {
    key: "tool_timeout_seconds",
    label: "Tool Timeout",
    description: "Timeout for simple tool calls (HA queries, entity lookups)",
    type: "number",
    unit: "seconds",
    min: 5,
    max: 300,
  },
  {
    key: "analysis_tool_timeout_seconds",
    label: "Analysis Tool Timeout",
    description: "Timeout for long-running analysis tools (Data Science team, diagnostics)",
    type: "number",
    unit: "seconds",
    min: 30,
    max: 600,
  },
  {
    key: "max_tool_iterations",
    label: "Max Tool Iterations",
    description: "Maximum number of tool call rounds per conversation turn",
    type: "number",
    min: 1,
    max: 50,
  },
];

const DASHBOARD_FIELDS: FieldDef[] = [
  {
    key: "default_refresh_interval_seconds",
    label: "Default Refresh Interval",
    description: "How often dashboard widgets refresh their data",
    type: "number",
    unit: "seconds",
    min: 10,
    max: 3600,
  },
  {
    key: "max_widgets",
    label: "Max Widgets",
    description: "Maximum number of widgets allowed per dashboard",
    type: "number",
    min: 1,
    max: 100,
  },
];

const DATA_SCIENCE_FIELDS: FieldDef[] = [
  {
    key: "sandbox_enabled",
    label: "Sandbox Enabled",
    description: "Enable gVisor sandbox for script execution (Constitution: Isolation)",
    type: "boolean",
  },
  {
    key: "sandbox_artifacts_enabled",
    label: "Artifacts Enabled",
    description: "Allow sandbox scripts to write artifacts (charts, CSVs) to output",
    type: "boolean",
  },
  {
    key: "sandbox_timeout_quick",
    label: "Quick Analysis Timeout",
    description: "Maximum execution time for quick analysis scripts",
    type: "number",
    unit: "seconds",
    min: 5,
    max: 120,
  },
  {
    key: "sandbox_timeout_standard",
    label: "Standard Analysis Timeout",
    description: "Maximum execution time for standard analysis scripts",
    type: "number",
    unit: "seconds",
    min: 10,
    max: 300,
  },
  {
    key: "sandbox_timeout_deep",
    label: "Deep Analysis Timeout",
    description: "Maximum execution time for deep analysis scripts",
    type: "number",
    unit: "seconds",
    min: 30,
    max: 600,
  },
  {
    key: "sandbox_memory_quick",
    label: "Quick Analysis Memory",
    description: "Memory limit for quick analysis scripts",
    type: "number",
    unit: "MB",
    min: 128,
    max: 2048,
  },
  {
    key: "sandbox_memory_standard",
    label: "Standard Analysis Memory",
    description: "Memory limit for standard analysis scripts",
    type: "number",
    unit: "MB",
    min: 256,
    max: 4096,
  },
  {
    key: "sandbox_memory_deep",
    label: "Deep Analysis Memory",
    description: "Memory limit for deep analysis scripts",
    type: "number",
    unit: "MB",
    min: 512,
    max: 8192,
  },
];

// ─── Section Form Component ─────────────────────────────────────────────────

function SectionForm({
  section,
  fields,
  values,
  onSave,
  onReset,
  isSaving,
  isResetting,
}: {
  section: string;
  fields: FieldDef[];
  values: Record<string, number | boolean>;
  onSave: (section: string, data: Record<string, number | boolean>) => void;
  onReset: (section: string) => void;
  isSaving: boolean;
  isResetting: boolean;
}) {
  const [local, setLocal] = useState<Record<string, number | boolean>>({});
  const [saved, setSaved] = useState(false);

  // Sync local state when server values change
  useEffect(() => {
    setLocal({ ...values });
  }, [values]);

  const hasChanges = fields.some((f) => {
    const cur = local[f.key];
    const orig = values[f.key];
    return cur !== orig;
  });

  const handleSave = () => {
    // Only send changed fields
    const changed: Record<string, number | boolean> = {};
    for (const f of fields) {
      if (local[f.key] !== values[f.key]) {
        changed[f.key] = local[f.key];
      }
    }
    onSave(section, changed);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      {fields.map((f) => (
        <div key={f.key} className="flex items-start justify-between gap-8">
          <div className="flex-1">
            <Label htmlFor={f.key} className="text-sm font-medium">
              {f.label}
              {f.unit && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({f.unit})
                </span>
              )}
            </Label>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {f.description}
            </p>
          </div>
          <div className="w-32 shrink-0">
            {f.type === "boolean" ? (
              <Switch
                id={f.key}
                checked={!!local[f.key]}
                onCheckedChange={(checked) =>
                  setLocal((prev) => ({ ...prev, [f.key]: checked }))
                }
              />
            ) : (
              <Input
                id={f.key}
                type="number"
                min={f.min}
                max={f.max}
                value={local[f.key] as number ?? ""}
                onChange={(e) =>
                  setLocal((prev) => ({
                    ...prev,
                    [f.key]: parseInt(e.target.value, 10) || 0,
                  }))
                }
                className="h-8 text-sm"
              />
            )}
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2 border-t border-border pt-4">
        <Button
          onClick={handleSave}
          disabled={!hasChanges || isSaving}
          size="sm"
        >
          {isSaving ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : saved ? (
            <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
          ) : (
            <Save className="mr-1.5 h-3.5 w-3.5" />
          )}
          {saved ? "Saved" : "Save Changes"}
        </Button>
        <Button
          variant="outline"
          onClick={() => onReset(section)}
          disabled={isResetting}
          size="sm"
        >
          {isResetting ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
          )}
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}

// ─── Settings Page ──────────────────────────────────────────────────────────

export function SettingsPage() {
  const { data, isLoading } = useAppSettings();
  const patchMut = usePatchSettings();
  const resetMut = useResetSettings();

  const handleSave = (
    section: string,
    changed: Record<string, number | boolean>,
  ) => {
    patchMut.mutate({ [section]: changed });
  };

  const handleReset = (section: string) => {
    resetMut.mutate(section);
  };

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <SettingsIcon className="h-6 w-6 text-muted-foreground" />
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure runtime application settings. Changes are saved to the
            database and take effect immediately.
          </p>
        </div>
      </div>

      <Tabs defaultValue="chat">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="chat" className="gap-1.5">
            <Timer className="h-3.5 w-3.5" />
            Chat & Streaming
          </TabsTrigger>
          <TabsTrigger value="dashboard" className="gap-1.5">
            <LayoutDashboard className="h-3.5 w-3.5" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="data_science" className="gap-1.5">
            <FlaskConical className="h-3.5 w-3.5" />
            Data Science
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Chat & Streaming</CardTitle>
            </CardHeader>
            <CardContent>
              <SectionForm
                section="chat"
                fields={CHAT_FIELDS}
                values={data.chat}
                onSave={handleSave}
                onReset={handleReset}
                isSaving={patchMut.isPending}
                isResetting={resetMut.isPending}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dashboard">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Dashboard</CardTitle>
            </CardHeader>
            <CardContent>
              <SectionForm
                section="dashboard"
                fields={DASHBOARD_FIELDS}
                values={data.dashboard}
                onSave={handleSave}
                onReset={handleReset}
                isSaving={patchMut.isPending}
                isResetting={resetMut.isPending}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="data_science">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Data Science</CardTitle>
            </CardHeader>
            <CardContent>
              <SectionForm
                section="data_science"
                fields={DATA_SCIENCE_FIELDS}
                values={data.data_science}
                onSave={handleSave}
                onReset={handleReset}
                isSaving={patchMut.isPending}
                isResetting={resetMut.isPending}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
