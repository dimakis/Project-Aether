import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { zones, type ZoneCreatePayload, type ZoneUpdatePayload } from "@/api/client/zones";
import { queryKeys } from "./queryKeys";

export function useHAZones() {
  return useQuery({
    queryKey: queryKeys.zones.all,
    queryFn: () => zones.list(),
  });
}

export function useCreateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ZoneCreatePayload) => zones.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.zones.all }),
  });
}

export function useUpdateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ZoneUpdatePayload }) =>
      zones.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.zones.all }),
  });
}

export function useDeleteZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => zones.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.zones.all }),
  });
}

export function useSetDefaultZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => zones.setDefault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.zones.all }),
  });
}

export function useTestZone() {
  return useMutation({
    mutationFn: (id: string) => zones.test(id),
  });
}
