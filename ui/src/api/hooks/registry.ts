import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { registry } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Registry ───────────────────────────────────────────────────────────────

export function useSyncRegistry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => registry.sync(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.registry.all });
    },
  });
}

export function useRegistryAutomations(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registry.automations,
    queryFn: () => registry.automations(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistrySummary(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registry.summary,
    queryFn: () => registry.summary(),
    enabled: options?.enabled ?? true,
  });
}

export function useAutomationConfig(automationId: string) {
  return useQuery({
    queryKey: queryKeys.registry.automationConfig(automationId),
    queryFn: () => registry.automationConfig(automationId),
    enabled: !!automationId,
  });
}

export function useRegistryScripts(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registry.scripts,
    queryFn: () => registry.scripts(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistryScenes(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registry.scenes,
    queryFn: () => registry.scenes(),
    enabled: options?.enabled ?? true,
  });
}

export function useRegistryServices(options?: { domain?: string; enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.registry.services(options?.domain),
    queryFn: () => registry.services(options?.domain),
    enabled: options?.enabled ?? true,
  });
}
