import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { insightSchedules, traces } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Insight Schedules (Feature 10) ──────────────────────────────────────────

export function useInsightSchedules() {
  return useQuery({
    queryKey: queryKeys.schedules.all,
    queryFn: () => insightSchedules.list(),
  });
}

export function useCreateInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: import("@/lib/types").InsightScheduleCreate) =>
      insightSchedules.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.schedules.all }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.schedules.all }),
  });
}

export function useDeleteInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insightSchedules.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.schedules.all }),
  });
}

export function useRunInsightSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insightSchedules.runNow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.schedules.all }),
  });
}

// ─── Traces (Feature 11) ────────────────────────────────────────────────────

export function useTraceSpans(traceId: string | null, isStreaming = false) {
  return useQuery({
    queryKey: queryKeys.traces.detail(traceId!),
    queryFn: () => traces.getSpans(traceId!),
    enabled: !!traceId,
    staleTime: 30_000, // 30s — traces are mostly immutable once complete
    refetchInterval: isStreaming ? 3_000 : false, // Poll every 3s while streaming
  });
}
