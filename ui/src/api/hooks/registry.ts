import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { registry } from "../client";
import { queryKeys } from "./queryKeys";

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
