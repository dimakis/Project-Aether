import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { zones, type ZoneCreatePayload, type ZoneUpdatePayload } from "@/api/client/zones";

const ZONES_KEY = ["zones"] as const;

export function useHAZones() {
  return useQuery({
    queryKey: ZONES_KEY,
    queryFn: () => zones.list(),
  });
}

export function useCreateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ZoneCreatePayload) => zones.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ZONES_KEY }),
  });
}

export function useUpdateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ZoneUpdatePayload }) =>
      zones.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ZONES_KEY }),
  });
}

export function useDeleteZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => zones.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ZONES_KEY }),
  });
}

export function useSetDefaultZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => zones.setDefault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ZONES_KEY }),
  });
}

export function useTestZone() {
  return useMutation({
    mutationFn: (id: string) => zones.test(id),
  });
}
