import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { appSettings } from "../client";
import { queryKeys } from "./queryKeys";

export function useAppSettings() {
  return useQuery({
    queryKey: queryKeys.appSettings.all,
    queryFn: () => appSettings.get(),
    staleTime: 30_000,
  });
}

export function usePatchSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: appSettings.patch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.appSettings.all });
    },
  });
}

export function useResetSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: appSettings.reset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.appSettings.all });
    },
  });
}
