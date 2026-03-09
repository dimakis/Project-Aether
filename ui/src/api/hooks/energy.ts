import { useQuery } from "@tanstack/react-query";
import { energy } from "../client/energy";
import { queryKeys } from "./queryKeys";

export function useTariffs() {
  return useQuery({
    queryKey: queryKeys.energy.tariffs,
    queryFn: () => energy.tariffs(),
    refetchInterval: 60_000,
  });
}
