import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { models, system, diagnostics, usage, modelRatings } from "../client";
import type { ModelRatingCreatePayload } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Models ─────────────────────────────────────────────────────────────────

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models.all,
    queryFn: () => models.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes (models don't change often)
  });
}

// ─── System ─────────────────────────────────────────────────────────────────

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.system.status,
    queryFn: () => system.status(),
    refetchInterval: 60_000, // Poll every minute
  });
}

// ─── Usage ──────────────────────────────────────────────────────────────────

export function useUsageSummary(days = 30) {
  return useQuery({
    queryKey: queryKeys.usage.summary(days),
    queryFn: () => usage.summary(days),
    staleTime: 60_000,
  });
}

export function useUsageDaily(days = 30) {
  return useQuery({
    queryKey: queryKeys.usage.daily(days),
    queryFn: () => usage.daily(days),
    staleTime: 60_000,
  });
}

export function useUsageByModel(days = 30) {
  return useQuery({
    queryKey: queryKeys.usage.byModel(days),
    queryFn: () => usage.models(days),
    staleTime: 60_000,
  });
}

export function useConversationCost(conversationId: string | null) {
  return useQuery({
    queryKey: queryKeys.usage.conversationCost(conversationId!),
    queryFn: () => usage.conversationCost(conversationId!),
    enabled: !!conversationId,
    staleTime: 30_000,
  });
}

// ─── Model Ratings ──────────────────────────────────────────────────────────

export function useModelRatings(modelName?: string, agentRole?: string) {
  return useQuery({
    queryKey: queryKeys.modelRatings.list(modelName, agentRole),
    queryFn: () => modelRatings.list(modelName, agentRole),
  });
}

export function useModelSummary(agentRole?: string) {
  return useQuery({
    queryKey: queryKeys.modelRatings.summary(agentRole),
    queryFn: () => modelRatings.summary(agentRole),
  });
}

export function useCreateModelRating() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ModelRatingCreatePayload) => modelRatings.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.modelRatings.all });
      qc.invalidateQueries({ queryKey: ["model-summary"] });
    },
  });
}

export function useModelPerformance(agentRole?: string, hours = 168) {
  return useQuery({
    queryKey: queryKeys.modelRatings.performance(agentRole, hours),
    queryFn: () => modelRatings.performance(agentRole, hours),
    staleTime: 60_000,
  });
}

// ─── Diagnostics ────────────────────────────────────────────────────────────

export function useHAHealth() {
  return useQuery({
    queryKey: queryKeys.diagnostics.haHealth,
    queryFn: () => diagnostics.haHealth(),
    staleTime: 60_000,
  });
}

export function useErrorLog() {
  return useQuery({
    queryKey: queryKeys.diagnostics.errorLog,
    queryFn: () => diagnostics.errorLog(),
    staleTime: 60_000,
  });
}

export function useConfigCheck() {
  return useQuery({
    queryKey: queryKeys.diagnostics.configCheck,
    queryFn: () => diagnostics.configCheck(),
    staleTime: 60_000,
    enabled: false, // Only fetch on demand
  });
}

export function useRecentTraces(limit = 50) {
  return useQuery({
    queryKey: queryKeys.diagnostics.recentTraces(limit),
    queryFn: () => diagnostics.recentTraces(limit),
    staleTime: 30_000,
  });
}
