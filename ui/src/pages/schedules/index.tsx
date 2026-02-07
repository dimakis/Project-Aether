import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  Plus,
  Loader2,
  Timer,
  Webhook,
  BarChart3,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useInsightSchedules,
  useUpdateInsightSchedule,
  useDeleteInsightSchedule,
  useRunInsightSchedule,
} from "@/api/hooks";
import { InlineAssistant } from "@/components/InlineAssistant";
import type { InsightSchedule } from "@/lib/types";
import { SCHEDULE_SYSTEM_CONTEXT, SCHEDULE_SUGGESTIONS } from "./constants";
import { ScheduleCard } from "./ScheduleCard";
import { CreateScheduleForm } from "./CreateScheduleForm";

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

      {/* Inline Assistant */}
      <InlineAssistant
        systemContext={SCHEDULE_SYSTEM_CONTEXT}
        suggestions={SCHEDULE_SUGGESTIONS}
        invalidateKeys={[["insightSchedules"]]}
        placeholder="Describe a schedule in natural language..."
      />

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
