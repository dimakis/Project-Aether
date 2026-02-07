// Barrel re-export — preserves `import { ... } from "@/api/hooks"` contract
export { queryKeys } from "./queryKeys";
export { useConversations, useConversation } from "./conversations";
export {
  useProposals,
  usePendingProposals,
  useProposal,
  useApproveProposal,
  useRejectProposal,
  useDeployProposal,
  useRollbackProposal,
  useDeleteProposal,
  useCreateProposal,
  useInsights,
  useInsightsSummary,
  useInsight,
  useReviewInsight,
  useDismissInsight,
  useDeleteInsight,
  useRunAnalysis,
} from "./proposals";
export { useAreas, useEntities, useDomainsSummary, useSyncEntities } from "./entities";
export {
  useSyncRegistry,
  useRegistryAutomations,
  useRegistrySummary,
  useAutomationConfig,
  useRegistryScripts,
  useRegistryScenes,
  useRegistryServices,
} from "./registry";
export {
  useInsightSchedules,
  useCreateInsightSchedule,
  useUpdateInsightSchedule,
  useDeleteInsightSchedule,
  useRunInsightSchedule,
  useTraceSpans,
} from "./schedules";
export {
  useAgents,
  useAgent,
  useAgentConfigVersions,
  useAgentPromptVersions,
  useUpdateAgentStatus,
  useSeedAgents,
  useCloneAgent,
  useCreateConfigVersion,
  usePromoteConfigVersion,
  useRollbackConfig,
  useCreatePromptVersion,
  usePromotePromptVersion,
  useRollbackPrompt,
  useDeleteConfigVersion,
  useDeletePromptVersion,
  useGeneratePrompt,
} from "./agents";
export { useWorkflowPresets } from "./workflows";
export {
  useModels,
  useSystemStatus,
  useUsageSummary,
  useUsageDaily,
  useUsageByModel,
  useModelRatings,
  useModelSummary,
  useCreateModelRating,
  useHAHealth,
  useErrorLog,
  useConfigCheck,
  useRecentTraces,
} from "./system";
