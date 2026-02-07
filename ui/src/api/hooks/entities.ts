import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { areas, entities } from "../client";
import { queryKeys } from "./queryKeys";

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
