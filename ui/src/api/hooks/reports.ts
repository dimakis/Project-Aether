import { useQuery } from "@tanstack/react-query";
import { reports } from "@/api/client/reports";
import { queryKeys } from "./queryKeys";

/**
 * Analysis Reports hooks.
 * Feature 33: DS Deep Analysis.
 */

/** Fetch list of analysis reports. */
export function useReports(status?: string) {
  return useQuery({
    queryKey: [...queryKeys.reports.all, status],
    queryFn: () => reports.list(status),
  });
}

/** Fetch a single report by ID. */
export function useReport(id: string) {
  return useQuery({
    queryKey: queryKeys.reports.detail(id),
    queryFn: () => reports.get(id),
    enabled: !!id,
  });
}

/** Fetch the communication log for a report. */
export function useReportCommunication(id: string) {
  return useQuery({
    queryKey: queryKeys.reports.communication(id),
    queryFn: () => reports.communication(id),
    enabled: !!id,
  });
}
