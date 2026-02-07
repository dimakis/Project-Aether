import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  Plus,
  Play,
  Pause,
  Trash2,
  Loader2,
  Check,
  X,
  AlertCircle,
  Zap,
  Timer,
  Webhook,
  BarChart3,
  Activity,
  Shield,
  Cpu,
  RefreshCw,
  Thermometer,
  CloudSun,
  Gauge,
  Sparkles,
  DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  useInsightSchedules,
  useCreateInsightSchedule,
  useUpdateInsightSchedule,
  useDeleteInsightSchedule,
  useRunInsightSchedule,
} from "@/api/hooks";
import type { InsightSchedule, InsightScheduleCreate } from "@/lib/types";

const ANALYSIS_TYPES = [
  {
    value: "energy_optimization",
    label: "Energy Optimization",
    icon: Zap,
    emoji: "⚡",
  },
  {
    value: "behavioral",
    label: "Behavioral Analysis",
    icon: Activity,
    emoji: "🧠",
  },
  {
    value: "anomaly",
    label: "Anomaly Detection",
    icon: AlertCircle,
    emoji: "🔍",
  },
  {
    value: "device_health",
    label: "Device Health",
    icon: Shield,
    emoji: "🛡️",
  },
  {
    value: "automation_gap",
    label: "Automation Gaps",
    icon: Cpu,
    emoji: "🤖",
  },
  {
    value: "comfort_analysis",
    label: "Comfort Analysis",
    icon: Thermometer,
    emoji: "🌡️",
  },
  {
    value: "security_audit",
    label: "Security Audit",
    icon: Shield,
    emoji: "🔒",
  },
  {
    value: "weather_correlation",
    label: "Weather Correlation",
    icon: CloudSun,
    emoji: "🌤️",
  },
  {
    value: "cost_optimization",
    label: "Cost Optimization",
    icon: DollarSign,
    emoji: "💰",
  },
  {
    value: "automation_efficiency",
    label: "Automation Efficiency",
    icon: Gauge,
    emoji: "📊",
  },
  {
    value: "custom",
    label: "Custom Analysis",
    icon: Sparkles,
    emoji: "✨",
  },
];

const CRON_PRESETS = [
  { label: "Every 30 min", value: "*/30 * * * *" },
  { label: "Hourly", value: "0 * * * *" },
  { label: "Daily at 2am", value: "0 2 * * *" },
  { label: "Daily at 8am", value: "0 8 * * *" },
  { label: "Weekly (Mon 8am)", value: "0 8 * * 1" },
  { label: "Monthly (1st at 2am)", value: "0 2 1 * *" },
];

export function SchedulesPage() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: schedulesData, isLoading } = useInsightSchedules();
  const deleteMut = useDeleteInsightSchedule();
  const updateMut = useUpdateInsightSchedule();
  const runMut = useRunInsightSchedule();

  const schedules = schedulesData?.items ?? [];
  const cronSchedules = schedules.filter((s) => s.trigger_type === "cron");
  const webhookSchedules = schedules.filter(
    (s) => s.trigger_type === "webhook",
  );

  const handleToggleEnabled = (schedule: InsightSchedule) => {
    updateMut.mutate({
      id: schedule.id,
      data: { enabled: !schedule.enabled },
    });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Clock className="h-6 w-6 text-primary" />
            Insight Schedules
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure recurring analysis jobs and event-driven triggers
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          New Schedule
        </Button>
      </div>

      {/* Create Form */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <CreateScheduleForm
              onClose={() => setShowCreateForm(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Timer className="h-8 w-8 text-blue-400" />
              <div>
                <p className="text-2xl font-bold">{cronSchedules.length}</p>
                <p className="text-xs text-muted-foreground">Cron Schedules</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Webhook className="h-8 w-8 text-emerald-400" />
              <div>
                <p className="text-2xl font-bold">{webhookSchedules.length}</p>
                <p className="text-xs text-muted-foreground">
                  Webhook Triggers
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">
                  {schedules.reduce((sum, s) => sum + s.run_count, 0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Total Executions
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Schedule List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : schedules.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Clock className="mb-3 h-10 w-10 text-muted-foreground/20" />
            <p className="text-sm text-muted-foreground">
              No schedules configured yet
            </p>
            <p className="mt-1 text-xs text-muted-foreground/50">
              Create a schedule to automatically run insight analysis
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {/* Cron Schedules */}
          {cronSchedules.length > 0 && (
            <div>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Timer className="h-4 w-4" />
                Cron Schedules
              </h2>
              <div className="space-y-2">
                {cronSchedules.map((schedule) => (
                  <ScheduleCard
                    key={schedule.id}
                    schedule={schedule}
                    isEditing={editingId === schedule.id}
                    onToggleEdit={() =>
                      setEditingId(
                        editingId === schedule.id ? null : schedule.id,
                      )
                    }
                    onToggleEnabled={() => handleToggleEnabled(schedule)}
                    onDelete={() => deleteMut.mutate(schedule.id)}
                    onRun={() => runMut.mutate(schedule.id)}
                    isRunning={runMut.isPending}
                    isDeleting={deleteMut.isPending}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Webhook Triggers */}
          {webhookSchedules.length > 0 && (
            <div>
              <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Webhook className="h-4 w-4" />
                Webhook Triggers
              </h2>
              <div className="space-y-2">
                {webhookSchedules.map((schedule) => (
                  <ScheduleCard
                    key={schedule.id}
                    schedule={schedule}
                    isEditing={editingId === schedule.id}
                    onToggleEdit={() =>
                      setEditingId(
                        editingId === schedule.id ? null : schedule.id,
                      )
                    }
                    onToggleEnabled={() => handleToggleEnabled(schedule)}
                    onDelete={() => deleteMut.mutate(schedule.id)}
                    onRun={() => runMut.mutate(schedule.id)}
                    isRunning={runMut.isPending}
                    isDeleting={deleteMut.isPending}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Schedule Card ───────────────────────────────────────────────────────────

function ScheduleCard({
  schedule,
  isEditing,
  onToggleEdit,
  onToggleEnabled,
  onDelete,
  onRun,
  isRunning,
  isDeleting,
}: {
  schedule: InsightSchedule;
  isEditing: boolean;
  onToggleEdit: () => void;
  onToggleEnabled: () => void;
  onDelete: () => void;
  onRun: () => void;
  isRunning: boolean;
  isDeleting: boolean;
}) {
  const analysisType = ANALYSIS_TYPES.find(
    (t) => t.value === schedule.analysis_type,
  );
  const Icon = analysisType?.icon ?? BarChart3;

  return (
    <motion.div layout>
      <Card
        className={cn(
          "transition-all",
          !schedule.enabled && "opacity-60",
        )}
      >
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                schedule.enabled
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
            </div>

            {/* Info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate font-medium">{schedule.name}</h3>
                <Badge
                  variant={schedule.enabled ? "default" : "secondary"}
                  className="text-[10px]"
                >
                  {schedule.enabled ? "Active" : "Paused"}
                </Badge>
                {schedule.last_result === "failed" && (
                  <Badge variant="destructive" className="text-[10px]">
                    Failed
                  </Badge>
                )}
              </div>

              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span>
                  {analysisType?.emoji ?? "📊"}{" "}
                  {analysisType?.label ?? schedule.analysis_type}
                </span>
                <span className="text-muted-foreground/30">·</span>
                {schedule.trigger_type === "cron" ? (
                  <span className="font-mono text-[10px]">
                    🕐 {schedule.cron_expression}
                  </span>
                ) : (
                  <span>
                    🔔 {schedule.webhook_event}
                  </span>
                )}
                <span className="text-muted-foreground/30">·</span>
                <span>{schedule.hours}h lookback</span>
                {schedule.run_count > 0 && (
                  <>
                    <span className="text-muted-foreground/30">·</span>
                    <span>
                      {schedule.run_count} run
                      {schedule.run_count !== 1 && "s"}
                    </span>
                  </>
                )}
                {schedule.last_run_at && (
                  <>
                    <span className="text-muted-foreground/30">·</span>
                    <span>
                      Last:{" "}
                      {new Date(schedule.last_run_at).toLocaleString(
                        undefined,
                        {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        },
                      )}
                    </span>
                  </>
                )}
              </div>

              {schedule.last_error && (
                <p className="mt-1 truncate text-[10px] text-destructive">
                  ⚠️ {schedule.last_error}
                </p>
              )}

              {schedule.entity_ids && schedule.entity_ids.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {schedule.entity_ids.slice(0, 3).map((eid) => (
                    <Badge
                      key={eid}
                      variant="outline"
                      className="text-[9px]"
                    >
                      {eid}
                    </Badge>
                  ))}
                  {schedule.entity_ids.length > 3 && (
                    <Badge variant="outline" className="text-[9px]">
                      +{schedule.entity_ids.length - 3} more
                    </Badge>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex shrink-0 items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onRun}
                disabled={isRunning}
                title="Run now"
              >
                {isRunning ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onToggleEnabled}
                title={schedule.enabled ? "Pause" : "Enable"}
              >
                {schedule.enabled ? (
                  <Pause className="h-3.5 w-3.5" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive/50 hover:text-destructive"
                onClick={onDelete}
                disabled={isDeleting}
                title="Delete"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ─── Create Form ─────────────────────────────────────────────────────────────

function CreateScheduleForm({ onClose }: { onClose: () => void }) {
  const createMut = useCreateInsightSchedule();
  const [form, setForm] = useState<InsightScheduleCreate>({
    name: "",
    analysis_type: "energy_optimization",
    trigger_type: "cron",
    enabled: true,
    hours: 24,
    cron_expression: "0 2 * * *",
    webhook_event: "",
  });
  // Track hours as a string so the user can freely clear and retype
  const [hoursStr, setHoursStr] = useState("24");
  // Custom analysis prompt (used when analysis_type === "custom")
  const [customPrompt, setCustomPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const hours = parseInt(hoursStr) || 24;
    const options: Record<string, unknown> = { ...form.options };
    if (form.analysis_type === "custom" && customPrompt.trim()) {
      options.custom_query = customPrompt.trim();
    }
    createMut.mutate(
      { ...form, hours, options },
      {
        onSuccess: () => onClose(),
        onError: () => {
          // Error is displayed inline via createMut.error below
        },
      },
    );
  };

  const updateField = <K extends keyof InsightScheduleCreate>(
    key: K,
    value: InsightScheduleCreate[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-sm">
          <span>New Insight Schedule</span>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Name
            </label>
            <Input
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              placeholder="e.g., Daily Energy Report"
              required
            />
          </div>

          {/* Trigger Type */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Trigger Type
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => updateField("trigger_type", "cron")}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all",
                  form.trigger_type === "cron"
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-border hover:border-primary/30 hover:bg-accent",
                )}
              >
                <Timer className="h-4 w-4" />
                Cron Schedule
              </button>
              <button
                type="button"
                onClick={() => updateField("trigger_type", "webhook")}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all",
                  form.trigger_type === "webhook"
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-border hover:border-primary/30 hover:bg-accent",
                )}
              >
                <Webhook className="h-4 w-4" />
                HA Webhook
              </button>
            </div>
          </div>

          {/* Analysis Type */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Analysis Type
            </label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {ANALYSIS_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => updateField("analysis_type", type.value)}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-all",
                    form.analysis_type === type.value
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/30 hover:bg-accent",
                  )}
                >
                  <span>{type.emoji}</span>
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom Analysis Prompt */}
          {form.analysis_type === "custom" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                What should be analyzed?
              </label>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="e.g., Check if my HVAC is cycling on/off too frequently"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                required
              />
              <p className="mt-1 text-[10px] text-muted-foreground/60">
                Describe in natural language what patterns, metrics, or behaviors to look for
              </p>
            </div>
          )}

          {/* Cron Expression */}
          {form.trigger_type === "cron" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Cron Expression
              </label>
              <Input
                value={form.cron_expression ?? ""}
                onChange={(e) =>
                  updateField("cron_expression", e.target.value)
                }
                placeholder="0 2 * * *"
                className="font-mono"
                required
              />
              <div className="mt-1.5 flex flex-wrap gap-1">
                {CRON_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    onClick={() =>
                      updateField("cron_expression", preset.value)
                    }
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] transition-colors",
                      form.cron_expression === preset.value
                        ? "bg-primary/20 text-primary"
                        : "bg-muted text-muted-foreground hover:bg-accent",
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Webhook Event */}
          {form.trigger_type === "webhook" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Webhook Event Label
              </label>
              <Input
                value={form.webhook_event ?? ""}
                onChange={(e) =>
                  updateField("webhook_event", e.target.value)
                }
                placeholder="e.g., device_offline"
                required
              />
              <p className="mt-1 text-[10px] text-muted-foreground/60">
                HA automations will fire this event label via POST /webhooks/ha
              </p>
            </div>
          )}

          {/* Lookback Hours */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Lookback Window (hours)
            </label>
            <Input
              type="number"
              min={1}
              max={8760}
              value={hoursStr}
              onChange={(e) => setHoursStr(e.target.value)}
            />
          </div>

          {/* Error display */}
          {createMut.isError && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                {createMut.error instanceof Error
                  ? createMut.error.message
                  : "Failed to create schedule"}
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createMut.isPending || !form.name}
            >
              {createMut.isPending ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Check className="mr-1.5 h-4 w-4" />
              )}
              Create Schedule
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
