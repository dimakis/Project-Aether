import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { areas, entities } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Areas ──────────────────────────────────────────────────────────────────

export function useAreas() {
  return useQuery({
    queryKey: queryKeys.areas.all,
    queryFn: () => areas.list(),
  });
}

// ─── Entities ───────────────────────────────────────────────────────────────

export function useEntities(domain?: string, areaId?: string) {
  return useQuery({
    queryKey: areaId
      ? queryKeys.entities.byArea(areaId, domain)
      : domain
        ? queryKeys.entities.byDomain(domain)
        : queryKeys.entities.all,
    queryFn: () => entities.list(domain, areaId),
  });
}

export function useDomainsSummary() {
  return useQuery({
    queryKey: queryKeys.entities.domainsSummary,
    queryFn: () => entities.domainsSummary(),
  });
}

export function useSyncEntities() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => entities.sync(force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.entities.all });
      qc.invalidateQueries({ queryKey: queryKeys.entities.domainsSummary });
    },
  });
}
