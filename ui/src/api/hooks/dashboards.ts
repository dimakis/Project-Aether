import { useQuery } from "@tanstack/react-query";
import { dashboards } from "@/api/client/dashboards";
import { queryKeys } from "./queryKeys";

/** Fetch the list of all Lovelace dashboards. */
export function useDashboards() {
  return useQuery({
    queryKey: queryKeys.dashboards.all,
    queryFn: () => dashboards.list(),
  });
}

/** Fetch full Lovelace config for a specific dashboard.
 *
 * @param urlPath - The dashboard's url_path, or "default" for the overview.
 *                  Pass null/undefined to disable the query.
 */
export function useDashboardConfig(urlPath: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.dashboards.config(urlPath ?? ""),
    queryFn: () => dashboards.getConfig(urlPath!),
    enabled: !!urlPath,
  });
}
