import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  Trash2,
  Loader2,
  RefreshCw,
  BarChart3,
  Pencil,
  Check,
  X,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ANALYSIS_TYPES, CRON_PRESETS } from "./constants";
import type { InsightSchedule, InsightScheduleCreate } from "@/lib/types";

interface ScheduleCardProps {
  schedule: InsightSchedule;
  isEditing: boolean;
  onToggleEdit: () => void;
  onToggleEnabled: () => void;
  onDelete: () => void;
  onRun: () => void;
  onUpdate: (data: Partial<InsightScheduleCreate>) => void;
  isRunning: boolean;
  isDeleting: boolean;
  isUpdating: boolean;
}

function InlineEditForm({
  schedule,
  onSave,
  onCancel,
  isUpdating,
}: {
  schedule: InsightSchedule;
  onSave: (data: Partial<InsightScheduleCreate>) => void;
  onCancel: () => void;
  isUpdating: boolean;
}) {
  const [name, setName] = useState(schedule.name);
  const [analysisType, setAnalysisType] = useState(schedule.analysis_type);
  const [cronExpression, setCronExpression] = useState(
    schedule.cron_expression ?? "",
  );
  const [webhookEvent, setWebhookEvent] = useState(
    schedule.webhook_event ?? "",
  );
  const [hoursStr, setHoursStr] = useState(String(schedule.hours ?? 24));

  const handleSave = () => {
    const patch: Partial<InsightScheduleCreate> = {};
    if (name !== schedule.name) patch.name = name;
    if (analysisType !== schedule.analysis_type)
      patch.analysis_type = analysisType;
    if (schedule.trigger_type === "cron" && cronExpression !== schedule.cron_expression)
      patch.cron_expression = cronExpression;
    if (schedule.trigger_type === "webhook" && webhookEvent !== schedule.webhook_event)
      patch.webhook_event = webhookEvent;
    const hours = parseInt(hoursStr) || 24;
    if (hours !== schedule.hours) patch.hours = hours;

    // Only submit if something changed
    if (Object.keys(patch).length > 0) {
      onSave(patch);
    } else {
      onCancel();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.15 }}
      className="space-y-3 border-t border-border/50 pt-3"
    >
      {/* Name */}
      <div>
        <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
          Name
        </label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="h-8 text-sm"
        />
      </div>

      {/* Analysis Type */}
      <div>
        <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
          Analysis Type
        </label>
        <div className="flex flex-wrap gap-1">
          {ANALYSIS_TYPES.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setAnalysisType(type.value)}
              className={cn(
                "rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors",
                analysisType === type.value
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground hover:bg-accent",
              )}
            >
              {type.emoji} {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cron / Webhook */}
      {schedule.trigger_type === "cron" ? (
        <div>
          <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
            Cron Expression
          </label>
          <Input
            value={cronExpression}
            onChange={(e) => setCronExpression(e.target.value)}
            placeholder="0 2 * * *"
            className="h-8 font-mono text-sm"
          />
          <div className="mt-1 flex flex-wrap gap-1">
            {CRON_PRESETS.map((preset) => (
              <button
                key={preset.value}
                type="button"
                onClick={() => setCronExpression(preset.value)}
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] transition-colors",
                  cronExpression === preset.value
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground hover:bg-accent",
                )}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div>
          <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
            Webhook Event
          </label>
          <Input
            value={webhookEvent}
            onChange={(e) => setWebhookEvent(e.target.value)}
            placeholder="e.g., device_offline"
            className="h-8 text-sm"
          />
        </div>
      )}

      {/* Hours */}
      <div>
        <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
          Lookback (hours)
        </label>
        <Input
          type="number"
          min={1}
          max={8760}
          value={hoursStr}
          onChange={(e) => setHoursStr(e.target.value)}
          className="h-8 w-24 text-sm"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={onCancel}
          disabled={isUpdating}
        >
          <X className="mr-1 h-3 w-3" />
          Cancel
        </Button>
        <Button
          type="button"
          size="sm"
          className="h-7 text-xs"
          onClick={handleSave}
          disabled={isUpdating || !name.trim()}
        >
          {isUpdating ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : (
            <Check className="mr-1 h-3 w-3" />
          )}
          Save
        </Button>
      </div>
    </motion.div>
  );
}

export function ScheduleCard({
  schedule,
  isEditing,
  onToggleEdit,
  onToggleEnabled,
  onDelete,
  onRun,
  onUpdate,
  isRunning,
  isDeleting,
  isUpdating,
}: ScheduleCardProps) {
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
                onClick={onToggleEdit}
                title="Edit"
              >
                <Pencil className={cn("h-3.5 w-3.5", isEditing && "text-primary")} />
              </Button>
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

          {/* Inline Edit Form */}
          <AnimatePresence>
            {isEditing && (
              <InlineEditForm
                schedule={schedule}
                onSave={onUpdate}
                onCancel={onToggleEdit}
                isUpdating={isUpdating}
              />
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}
