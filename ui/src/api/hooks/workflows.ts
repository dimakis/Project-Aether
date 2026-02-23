import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workflows } from "@/api/client";
import { queryKeys } from "./queryKeys";
import type { WorkflowCreatePayload } from "@/api/client/workflows";

// ─── Workflow Preset Hooks ──────────────────────────────────────────────────

export function useWorkflowPresets() {
  return useQuery({
    queryKey: queryKeys.workflows.presets,
    queryFn: () => workflows.listPresets(),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Workflow Definition Hooks (Feature 29) ────────────────────────────────

export function useWorkflowDefinitions() {
  return useQuery({
    queryKey: queryKeys.workflows.definitions,
    queryFn: () => workflows.listDefinitions(),
  });
}

export function useCreateWorkflowDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowCreatePayload) => workflows.createDefinition(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.workflows.definitions });
    },
  });
}

export function useDeleteWorkflowDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workflows.deleteDefinition(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.workflows.definitions });
    },
  });
}
