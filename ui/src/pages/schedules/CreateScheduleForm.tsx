import { useState } from "react";
import {
  Check,
  X,
  AlertCircle,
  Loader2,
  Timer,
  Webhook,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useCreateInsightSchedule } from "@/api/hooks";
import type { InsightScheduleCreate } from "@/lib/types";
import { ANALYSIS_TYPES, CRON_PRESETS } from "./constants";

export function CreateScheduleForm({ onClose }: { onClose: () => void }) {
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
