import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Save,
  RotateCcw,
  Timer,
  LayoutDashboard,
  FlaskConical,
  Bell,
  Loader2,
  CheckCircle,
  AlertCircle,
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

type SettingsValue = number | boolean | string;

function SectionForm({
  section,
  fields,
  values,
  onSave,
  onReset,
  isSaving,
  isResetting,
  error,
}: {
  section: string;
  fields: FieldDef[];
  values: Record<string, SettingsValue>;
  onSave: (section: string, data: Record<string, SettingsValue>) => void;
  onReset: (section: string) => void;
  isSaving: boolean;
  isResetting: boolean;
  error?: string | null;
}) {
  const [local, setLocal] = useState<Record<string, SettingsValue>>({});
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
    const changed: Record<string, SettingsValue> = {};
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
      <div className="space-y-2 border-t border-border pt-4">
        <div className="flex items-center gap-2">
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
        {error && (
          <p className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Notification Form Component ─────────────────────────────────────────────

const IMPACT_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

function NotificationForm({
  values,
  onSave,
  onReset,
  isSaving,
  isResetting,
  error,
}: {
  values: Record<string, number | boolean>;
  onSave: (section: string, data: Record<string, number | boolean>) => void;
  onReset: (section: string) => void;
  isSaving: boolean;
  isResetting: boolean;
  error?: string | null;
}) {
  const [enabled, setEnabled] = useState(!!values.enabled);
  const [minImpact, setMinImpact] = useState(
    String(values.min_impact || "high"),
  );
  const [quietStart, setQuietStart] = useState(
    String(values.quiet_hours_start || ""),
  );
  const [quietEnd, setQuietEnd] = useState(
    String(values.quiet_hours_end || ""),
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setEnabled(!!values.enabled);
    setMinImpact(String(values.min_impact || "high"));
    setQuietStart(String(values.quiet_hours_start || ""));
    setQuietEnd(String(values.quiet_hours_end || ""));
  }, [values]);

  const hasChanges =
    enabled !== !!values.enabled ||
    minImpact !== String(values.min_impact || "high") ||
    quietStart !== String(values.quiet_hours_start || "") ||
    quietEnd !== String(values.quiet_hours_end || "");

  const handleSave = () => {
    const changed: Record<string, string | boolean> = {};
    if (enabled !== !!values.enabled) changed.enabled = enabled;
    if (minImpact !== String(values.min_impact || "high"))
      changed.min_impact = minImpact;
    if (quietStart !== String(values.quiet_hours_start || ""))
      changed.quiet_hours_start = quietStart || "";
    if (quietEnd !== String(values.quiet_hours_end || ""))
      changed.quiet_hours_end = quietEnd || "";
    onSave("notifications", changed as Record<string, number | boolean>);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-8">
        <div className="flex-1">
          <Label htmlFor="notif-enabled" className="text-sm font-medium">
            Insight Notifications
          </Label>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Send push notifications when scheduled analysis finds actionable
            insights
          </p>
        </div>
        <div className="w-32 shrink-0">
          <Switch
            id="notif-enabled"
            checked={enabled}
            onCheckedChange={setEnabled}
          />
        </div>
      </div>

      <div className="flex items-start justify-between gap-8">
        <div className="flex-1">
          <Label htmlFor="notif-impact" className="text-sm font-medium">
            Minimum Impact
          </Label>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Only notify for insights at or above this impact level
          </p>
        </div>
        <div className="w-32 shrink-0">
          <select
            id="notif-impact"
            value={minImpact}
            onChange={(e) => setMinImpact(e.target.value)}
            className="h-8 w-full rounded-md border bg-background px-2 text-sm"
          >
            {IMPACT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-start justify-between gap-8">
        <div className="flex-1">
          <Label htmlFor="notif-quiet-start" className="text-sm font-medium">
            Quiet Hours Start
          </Label>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Suppress notifications from this time (HH:MM)
          </p>
        </div>
        <div className="w-32 shrink-0">
          <Input
            id="notif-quiet-start"
            type="time"
            value={quietStart}
            onChange={(e) => setQuietStart(e.target.value)}
            className="h-8 text-sm"
          />
        </div>
      </div>

      <div className="flex items-start justify-between gap-8">
        <div className="flex-1">
          <Label htmlFor="notif-quiet-end" className="text-sm font-medium">
            Quiet Hours End
          </Label>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Resume notifications at this time (HH:MM)
          </p>
        </div>
        <div className="w-32 shrink-0">
          <Input
            id="notif-quiet-end"
            type="time"
            value={quietEnd}
            onChange={(e) => setQuietEnd(e.target.value)}
            className="h-8 text-sm"
          />
        </div>
      </div>

      <div className="space-y-2 border-t border-border pt-4">
        <div className="flex items-center gap-2">
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
            onClick={() => onReset("notifications")}
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
        {error && (
          <p className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Settings Page ──────────────────────────────────────────────────────────

export function SettingsPage() {
  const { data, isLoading } = useAppSettings();
  const patchMut = usePatchSettings();
  const resetMut = useResetSettings();

  const mutError =
    (patchMut.error as Error | null)?.message ??
    (resetMut.error as Error | null)?.message ??
    null;

  const handleSave = (
    section: string,
    changed: Record<string, SettingsValue>,
  ) => {
    patchMut.reset();
    patchMut.mutate({ [section]: changed });
  };

  const handleReset = (section: string) => {
    resetMut.reset();
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
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="chat" className="gap-1.5">
            <Timer className="h-3.5 w-3.5" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="dashboard" className="gap-1.5">
            <LayoutDashboard className="h-3.5 w-3.5" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="data_science" className="gap-1.5">
            <FlaskConical className="h-3.5 w-3.5" />
            Data Science
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-1.5">
            <Bell className="h-3.5 w-3.5" />
            Notifications
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
                error={mutError}
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
                error={mutError}
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
                error={mutError}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Insight Notifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <NotificationForm
                values={data.notifications}
                onSave={handleSave}
                onReset={handleReset}
                isSaving={patchMut.isPending}
                isResetting={resetMut.isPending}
                error={mutError}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
