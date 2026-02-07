import { motion } from "framer-motion";
import {
  Play,
  Pause,
  Trash2,
  Loader2,
  RefreshCw,
  BarChart3,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ANALYSIS_TYPES } from "./constants";
import type { InsightSchedule } from "@/lib/types";

export function ScheduleCard({
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
