import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agents } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Agents (Feature 23) ────────────────────────────────────────────────────

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: () => agents.list(),
  });
}

export function useAvailableAgents() {
  return useQuery({
    queryKey: queryKeys.agents.available,
    queryFn: () => agents.listAvailable(),
  });
}

export function useAgent(name: string) {
  return useQuery({
    queryKey: queryKeys.agents.detail(name),
    queryFn: () => agents.get(name),
    enabled: !!name,
  });
}

export function useAgentConfigVersions(name: string) {
  return useQuery({
    queryKey: queryKeys.agents.configVersions(name),
    queryFn: () => agents.listConfigVersions(name),
    enabled: !!name,
  });
}

export function useAgentPromptVersions(name: string) {
  return useQuery({
    queryKey: queryKeys.agents.promptVersions(name),
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
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
    },
  });
}

export function useSeedAgents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => agents.seed(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
    },
  });
}

export function useCloneAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => agents.clone(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
    },
  });
}

export function useQuickModelSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, modelName }: { name: string; modelName: string }) =>
      agents.quickModelSwitch(name, modelName),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
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
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
    },
  });
}

export function usePromoteConfigVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      versionId,
      bumpType = "patch",
    }: {
      name: string;
      versionId: string;
      bumpType?: "major" | "minor" | "patch";
    }) => agents.promoteConfigVersion(name, versionId, bumpType),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
    },
  });
}

export function useRollbackConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => agents.rollbackConfig(name),
    onSuccess: (_data, name) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
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
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.promptVersions(name) });
    },
  });
}

export function usePromotePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      versionId,
      bumpType = "patch",
    }: {
      name: string;
      versionId: string;
      bumpType?: "major" | "minor" | "patch";
    }) => agents.promotePromptVersion(name, versionId, bumpType),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.all });
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.promptVersions(name) });
    },
  });
}

export function useRollbackPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => agents.rollbackPrompt(name),
    onSuccess: (_data, name) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.promptVersions(name) });
    },
  });
}

export function useDeleteConfigVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.deleteConfigVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
    },
  });
}

export function useDeletePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, versionId }: { name: string; versionId: string }) =>
      agents.deletePromptVersion(name, versionId),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.promptVersions(name) });
    },
  });
}

export function usePromoteBoth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      bumpType = "patch",
    }: {
      name: string;
      bumpType?: "major" | "minor" | "patch";
    }) => agents.promoteBoth(name, bumpType),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agents.detail(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.configVersions(name) });
      qc.invalidateQueries({ queryKey: queryKeys.agents.promptVersions(name) });
    },
  });
}

export function useGeneratePrompt() {
  return useMutation({
    mutationFn: ({ name, userInput }: { name: string; userInput?: string }) =>
      agents.generatePrompt(name, userInput),
  });
}
