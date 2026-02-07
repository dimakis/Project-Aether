import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  agents,
  areas,
  conversations,
  insightSchedules,
  models,
  modelRatings,
  proposals,
  insights,
  entities,
  registry,
  system,
  traces,
  usage,
} from "./client";
import type { ModelRatingCreatePayload } from "./client";

// ─── Keys ───────────────────────────────────────────────────────────────────

export const queryKeys = {
  conversations: ["conversations"] as const,
  conversation: (id: string) => ["conversations", id] as const,
  models: ["models"] as const,
  proposals: ["proposals"] as const,
  proposalsPending: ["proposals", "pending"] as const,
  proposal: (id: string) => ["proposals", id] as const,
  insights: ["insights"] as const,
  insightsPending: ["insights", "pending"] as const,
  insightsSummary: ["insights", "summary"] as const,
  insight: (id: string) => ["insights", id] as const,
  entities: ["entities"] as const,
  entitiesByDomain: (domain: string) => ["entities", "domain", domain] as const,
  domainsSummary: ["entities", "domains"] as const,
  registryAutomations: ["registry", "automations"] as const,
  registrySummary: ["registry", "summary"] as const,
  systemStatus: ["system", "status"] as const,
} as const;

// ─── Conversations ──────────────────────────────────────────────────────────

export function useConversations() {
  return useQuery({
    queryKey: queryKeys.conversations,
    queryFn: () => conversations.list(),
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: queryKeys.conversation(id),
    queryFn: () => conversations.get(id),
    enabled: !!id,
  });
}

// ─── Models ─────────────────────────────────────────────────────────────────

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => models.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes (models don't change often)
  });
}

// ─── Proposals ──────────────────────────────────────────────────────────────

export function useProposals(status?: string) {
  return useQuery({
    queryKey: [...queryKeys.proposals, status],
    queryFn: () => proposals.list(status),
  });
}

export function usePendingProposals() {
  return useQuery({
    queryKey: queryKeys.proposalsPending,
    queryFn: () => proposals.pending(),
    refetchInterval: 30_000, // Poll every 30s for pending approvals
  });
}

export function useProposal(id: string) {
  return useQuery({
    queryKey: queryKeys.proposal(id),
    queryFn: () => proposals.get(id),
    enabled: !!id,
  });
}

export function useApproveProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useRejectProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      proposals.reject(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useDeployProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.deploy(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
      qc.invalidateQueries({ queryKey: queryKeys.proposal(id) });
    },
  });
}

export function useRollbackProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.rollback(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
      qc.invalidateQueries({ queryKey: queryKeys.proposal(id) });
    },
  });
}

export function useDeleteProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useCreateProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name: string;
      trigger?: unknown;
      actions?: unknown;
      description?: string;
      conditions?: unknown;
      mode?: string;
      proposal_type?: string;
      service_call?: Record<string, unknown>;
    }) => proposals.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
    },
  });
}

// ─── Insights ───────────────────────────────────────────────────────────────

export function useInsights(type?: string, status?: string) {
  return useQuery({
    queryKey: [...queryKeys.insights, type, status],
    queryFn: () => insights.list(type, status),
  });
}

export function useInsightsSummary() {
  return useQuery({
    queryKey: queryKeys.insightsSummary,
    queryFn: () => insights.summary(),
  });
}

export function useInsight(id: string) {
  return useQuery({
    queryKey: queryKeys.insight(id),
    queryFn: () => insights.get(id),
    enabled: !!id,
  });
}

export function useReviewInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insights.review(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useDismissInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      insights.dismiss(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useDeleteInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insights.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useRunAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      type,
      hours,
    }: {
      type?: string;
      hours?: number;
    } = {}) => insights.analyze(type, hours),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

// ─── Areas ──────────────────────────────────────────────────────────────────

export function useAreas() {
  return useQuery({
    queryKey: ["areas"],
    queryFn: () => areas.list(),
  });
}

// ─── Entities ───────────────────────────────────────────────────────────────

export function useEntities(domain?: string, areaId?: string) {
  return useQuery({
    queryKey: areaId
      ? ["entities", "area", areaId, domain]
      : domain
        ? queryKeys.entitiesByDomain(domain)
        : queryKeys.entities,
    queryFn: () => entities.list(domain, areaId),
  });
}

export function useDomainsSummary() {
  return useQuery({
    queryKey: queryKeys.domainsSummary,
    queryFn: () => entities.domainsSummary(),
  });
}

export function useSyncEntities() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => entities.sync(force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.entities });
      qc.invalidateQueries({ queryKey: queryKeys.domainsSummary });
    },
  });
}

// ─── Registry ───────────────────────────────────────────────────────────────

export function useSyncRegistry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => registry.sync(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.registryAutomations });
      qc.invalidateQueries({ queryKey: queryKeys.registrySummary });
      qc.invalidateQueries({ queryKey: ["registryScripts"] });
      qc.invalidateQueries({ queryKey: ["registryScenes"] });
      qc.invalidateQueries({ queryKey: ["registryServices"] });
    },
  });
}

export function useRegistryAutomations(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registryAutomations,
    queryFn: () => registry.automations(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistrySummary(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registrySummary,
    queryFn: () => registry.summary(),
    enabled: options?.enabled ?? true,
  });
}

export function useAutomationConfig(automationId: string) {
  return useQuery({
    queryKey: ["automationConfig", automationId],
    queryFn: () => registry.automationConfig(automationId),
    enabled: !!automationId,
  });
}

export function useRegistryScripts(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["registryScripts"],
    queryFn: () => registry.scripts(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistryScenes(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["registryScenes"],
    queryFn: () => registry.scenes(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistryServices(options?: { domain?: string; enabled?: boolean }) {
  return useQuery({
    queryKey: ["registryServices", options?.domain],
    queryFn: () => registry.services(options?.domain),
    enabled: options?.enabled ?? true,
  });
}

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

// ─── Agents (Feature 23) ────────────────────────────────────────────────────

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: () => agents.list(),
  });
}

export function useAgent(name: string) {
  return useQuery({
    queryKey: ["agents", name],
    queryFn: () => agents.get(name),
    enabled: !!name,
  });
}

export function useAgentConfigVersions(name: string) {
  return useQuery({
    queryKey: ["agents", name, "config", "versions"],
    queryFn: () => agents.listConfigVersions(name),
    enabled: !!name,
  });
}

export function useAgentPromptVersions(name: string) {
  return useQuery({
    queryKey: ["agents", name, "prompt", "versions"],
    queryFn: () => agents.listPromptVersions(name),
    enabled: !!name,
  });
}

export function useUpdateAgentStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, status }: { name: string; status: string }) =>
      agents.updateStatus(name, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useSeedAgents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => agents.seed(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useCreateConfigVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      data,
    }: {
      name: string;
      data: import("@/lib/types").ConfigVersionCreate;
    }) => agents.createConfigVersion(name, data),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "config", "versions"] });
    },
  });
}

export function usePromoteConfigVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.promoteConfigVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "config", "versions"] });
    },
  });
}

export function useRollbackConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => agents.rollbackConfig(name),
    onSuccess: (_data, name) => {
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "config", "versions"] });
    },
  });
}

export function useCreatePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      data,
    }: {
      name: string;
      data: import("@/lib/types").PromptVersionCreate;
    }) => agents.createPromptVersion(name, data),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "prompt", "versions"] });
    },
  });
}

export function usePromotePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.promotePromptVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "prompt", "versions"] });
    },
  });
}

export function useRollbackPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => agents.rollbackPrompt(name),
    onSuccess: (_data, name) => {
      qc.invalidateQueries({ queryKey: ["agents", name] });
      qc.invalidateQueries({ queryKey: ["agents", name, "prompt", "versions"] });
    },
  });
}

export function useDeleteConfigVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.deleteConfigVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents", name, "config", "versions"] });
    },
  });
}

export function useDeletePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.deletePromptVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: ["agents", name, "prompt", "versions"] });
    },
  });
}

export function useGeneratePrompt() {
  return useMutation({
    mutationFn: ({ name, userInput }: { name: string; userInput?: string }) =>
      agents.generatePrompt(name, userInput),
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
