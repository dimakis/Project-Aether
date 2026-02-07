import { request } from "./core";

// ─── Insight Schedules (Feature 10) ─────────────────────────────────────────

export const insightSchedules = {
  list: (triggerType?: string, enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (triggerType) params.set("trigger_type", triggerType);
    if (enabledOnly) params.set("enabled_only", "true");
    return request<import("@/lib/types").InsightScheduleList>(
      `/insight-schedules?${params}`,
    );
  },

  get: (id: string) =>
    request<import("@/lib/types").InsightSchedule>(
      `/insight-schedules/${id}`,
    ),

  create: (data: import("@/lib/types").InsightScheduleCreate) =>
    request<import("@/lib/types").InsightSchedule>(`/insight-schedules`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<import("@/lib/types").InsightScheduleCreate>) =>
    request<import("@/lib/types").InsightSchedule>(`/insight-schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/insight-schedules/${id}`, { method: "DELETE" }),

  runNow: (id: string) =>
    request<{ status: string; schedule_id: string }>(
      `/insight-schedules/${id}/run`,
      { method: "POST" },
    ),
};

// ─── Traces (Feature 11) ────────────────────────────────────────────────────

export const traces = {
  getSpans: (traceId: string) =>
    request<import("@/lib/types").TraceResponse>(
      `/traces/${traceId}/spans`,
    ),
};
