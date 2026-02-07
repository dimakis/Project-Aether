import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { insightSchedules, traces } from "../client";

// ─── Insight Schedules (Feature 10) ──────────────────────────────────────────

export function useInsightSchedules() {
  return useQuery({
    queryKey: ["insightSchedules"],
    queryFn: () => insightSchedules.list(),
  });
}

export function useCreateInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: import("@/lib/types").InsightScheduleCreate) =>
      insightSchedules.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insightSchedules"] }),
  });
}

export function useUpdateInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<import("@/lib/types").InsightScheduleCreate>;
    }) => insightSchedules.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insightSchedules"] }),
  });
}

export function useDeleteInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insightSchedules.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insightSchedules"] }),
  });
}

export function useRunInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insightSchedules.runNow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insightSchedules"] }),
  });
}

// ─── Traces (Feature 11) ────────────────────────────────────────────────────

export function useTraceSpans(traceId: string | null) {
  return useQuery({
    queryKey: ["traces", traceId],
    queryFn: () => traces.getSpans(traceId!),
    enabled: !!traceId,
    staleTime: Infinity, // Traces are immutable once complete
  });
}
