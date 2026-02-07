import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agents } from "../client";

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
