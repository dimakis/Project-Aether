import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { models, system, diagnostics, usage, modelRatings } from "../client";
import type { ModelRatingCreatePayload } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Models ─────────────────────────────────────────────────────────────────

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => models.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes (models don't change often)
  });
}

// ─── System ─────────────────────────────────────────────────────────────────

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: () => system.status(),
    refetchInterval: 60_000, // Poll every minute
  });
}

// ─── Usage ──────────────────────────────────────────────────────────────────

export function useUsageSummary(days = 30) {
  return useQuery({
    queryKey: ["usage", "summary", days],
    queryFn: () => usage.summary(days),
    staleTime: 60_000,
  });
}

export function useUsageDaily(days = 30) {
  return useQuery({
    queryKey: ["usage", "daily", days],
    queryFn: () => usage.daily(days),
    staleTime: 60_000,
  });
}

export function useUsageByModel(days = 30) {
  return useQuery({
    queryKey: ["usage", "models", days],
    queryFn: () => usage.models(days),
    staleTime: 60_000,
  });
}

export function useConversationCost(conversationId: string | null) {
  return useQuery({
    queryKey: ["usage", "conversation", conversationId],
    queryFn: () => usage.conversationCost(conversationId!),
    enabled: !!conversationId,
    staleTime: 30_000,
  });
}

// ─── Model Ratings ──────────────────────────────────────────────────────────

export function useModelRatings(modelName?: string, agentRole?: string) {
  return useQuery({
    queryKey: ["model-ratings", modelName, agentRole],
    queryFn: () => modelRatings.list(modelName, agentRole),
  });
}

export function useModelSummary(agentRole?: string) {
  return useQuery({
    queryKey: ["model-summary", agentRole],
    queryFn: () => modelRatings.summary(agentRole),
  });
}

export function useCreateModelRating() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ModelRatingCreatePayload) => modelRatings.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["model-ratings"] });
      qc.invalidateQueries({ queryKey: ["model-summary"] });
    },
  });
}

export function useModelPerformance(agentRole?: string, hours = 168) {
  return useQuery({
    queryKey: ["model-performance", agentRole, hours],
    queryFn: () => modelRatings.performance(agentRole, hours),
    staleTime: 60_000,
  });
}

// ─── Diagnostics ────────────────────────────────────────────────────────────

export function useHAHealth() {
  return useQuery({
    queryKey: ["diagnostics", "ha-health"],
    queryFn: () => diagnostics.haHealth(),
    staleTime: 60_000,
  });
}

export function useErrorLog() {
  return useQuery({
    queryKey: ["diagnostics", "error-log"],
    queryFn: () => diagnostics.errorLog(),
    staleTime: 60_000,
  });
}

export function useConfigCheck() {
  return useQuery({
    queryKey: ["diagnostics", "config-check"],
    queryFn: () => diagnostics.configCheck(),
    staleTime: 60_000,
    enabled: false, // Only fetch on demand
  });
}

export function useRecentTraces(limit = 50) {
  return useQuery({
    queryKey: ["diagnostics", "traces", limit],
    queryFn: () => diagnostics.recentTraces(limit),
    staleTime: 30_000,
  });
}
