import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  optimization,
  type OptimizationRequest,
} from "@/api/client/optimization";
import { queryKeys } from "./queryKeys";

export function useOptimizationJob(jobId: string | null) {
  return useQuery({
    queryKey: queryKeys.optimization.job(jobId ?? ""),
    queryFn: () => optimization.status(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") return 3000;
      return false;
    },
  });
}

export function useSuggestions() {
  return useQuery({
    queryKey: queryKeys.optimization.suggestions,
    queryFn: () => optimization.suggestions(),
  });
}

export function useRunOptimization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OptimizationRequest) => optimization.run(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.optimization.all });
    },
  });
}

export function useAcceptSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) =>
      optimization.acceptSuggestion(id, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.optimization.suggestions });
    },
  });
}

export function useRejectSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      optimization.rejectSuggestion(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.optimization.suggestions });
    },
  });
}
