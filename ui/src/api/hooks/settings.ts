import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { AppSettingsResponse } from "../client/settings";
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
    onSuccess: (data: AppSettingsResponse) => {
      qc.setQueryData(queryKeys.appSettings.all, data);
    },
  });
}

export function useResetSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: appSettings.reset,
    onSuccess: (data: AppSettingsResponse) => {
      qc.setQueryData(queryKeys.appSettings.all, data);
    },
  });
}
