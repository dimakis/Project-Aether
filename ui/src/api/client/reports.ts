import { request } from "./core";
import type {
  AnalysisReport,
  AnalysisReportList,
  ReportCommunicationLog,
} from "@/lib/types";

/**
 * Analysis Reports API client.
 * Feature 33: DS Deep Analysis.
 */
export const reports = {
  /** List reports with optional status filter. */
  list: (status?: string) => {
    const params = new URLSearchParams({ limit: "50" });
    if (status) params.set("status", status);
    return request<AnalysisReportList>(`/reports?${params}`);
  },

  /** Get a single report by ID. */
  get: (id: string) => request<AnalysisReport>(`/reports/${id}`),

  /** Get the communication log for a report. */
  communication: (id: string) =>
    request<ReportCommunicationLog>(`/reports/${id}/communication`),
};
