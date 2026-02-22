import { request } from "./core";

// ─── Proposals ──────────────────────────────────────────────────────────────

export const proposals = {
  list: (status?: string) =>
    request<import("@/lib/types").ProposalList>(
      `/proposals?limit=50${status ? `&status=${status}` : ""}`,
    ),

  pending: async (): Promise<import("@/lib/types").Proposal[]> => {
    const data = await request<
      | import("@/lib/types").Proposal[]
      | import("@/lib/types").ProposalList
    >(`/proposals/pending`);
    // API may return paginated list or raw array
    return Array.isArray(data) ? data : data.items;
  },

  get: (id: string) =>
    request<import("@/lib/types").ProposalWithYAML>(`/proposals/${id}`),

  approve: (id: string) =>
    request<import("@/lib/types").Proposal>(`/proposals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: "user" }),
    }),

  reject: (id: string, reason: string) =>
    request<import("@/lib/types").Proposal>(`/proposals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason, rejected_by: "user" }),
    }),

  deploy: (id: string) =>
    request<import("@/lib/types").DeploymentResponse>(
      `/proposals/${id}/deploy`,
      { method: "POST", body: JSON.stringify({}) },
    ),

  rollback: (id: string) =>
    request<import("@/lib/types").RollbackResponse>(`/proposals/${id}/rollback`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  create: (data: {
    name?: string;
    trigger?: unknown;
    actions?: unknown;
    description?: string;
    conditions?: unknown;
    mode?: string;
    proposal_type?: string;
    service_call?: Record<string, unknown>;
    dashboard_config?: Record<string, unknown>;
    yaml_content?: string;
  }) =>
    request<import("@/lib/types").Proposal>(`/proposals`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/proposals/${id}`, { method: "DELETE" }),
};

// ─── Insights ───────────────────────────────────────────────────────────────

export const insights = {
  list: (type?: string, status?: string) => {
    const params = new URLSearchParams({ limit: "50" });
    if (type) params.set("type", type);
    if (status) params.set("status", status);
    return request<import("@/lib/types").InsightList>(
      `/insights?${params}`,
    );
  },

  pending: async (): Promise<import("@/lib/types").Insight[]> => {
    const data = await request<
      | import("@/lib/types").Insight[]
      | import("@/lib/types").InsightList
    >(`/insights/pending`);
    return Array.isArray(data) ? data : data.items;
  },

  summary: () =>
    request<import("@/lib/types").InsightSummary>(`/insights/summary`),

  get: (id: string) =>
    request<import("@/lib/types").Insight>(`/insights/${id}`),

  review: (id: string) =>
    request<import("@/lib/types").Insight>(`/insights/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ reviewed_by: "user" }),
    }),

  action: (id: string, actionTaken?: string) =>
    request<import("@/lib/types").Insight>(`/insights/${id}/action`, {
      method: "POST",
      body: JSON.stringify({
        actioned_by: "user",
        action_taken: actionTaken,
      }),
    }),

  dismiss: (id: string, reason?: string) =>
    request<import("@/lib/types").Insight>(`/insights/${id}/dismiss`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  analyze: (analysisType = "energy", hours = 24) =>
    request<{ job: import("@/lib/types").AnalysisJob }>(
      `/insights/analyze`,
      {
        method: "POST",
        body: JSON.stringify({ analysis_type: analysisType, hours }),
      },
    ),

  delete: (id: string) =>
    request<void>(`/insights/${id}`, { method: "DELETE" }),
};
