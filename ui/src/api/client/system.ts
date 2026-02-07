import { request } from "./core";

// ─── Models ─────────────────────────────────────────────────────────────────

export const models = {
  list: () =>
    request<import("@/lib/types").ModelsResponse>(`/models`),
};

// ─── System ─────────────────────────────────────────────────────────────────

export const system = {
  health: () =>
    request<import("@/lib/types").HealthCheck>("/health").catch(
      () => null,
    ),

  status: () =>
    request<import("@/lib/types").SystemStatus>("/status"),
};

// ─── Diagnostics ────────────────────────────────────────────────────────────

export interface EntityDiagnosticItem {
  entity_id: string;
  state: string;
  available: boolean;
  last_changed: string | null;
  integration: string;
  issues: string[];
}

export interface IntegrationHealthItem {
  entry_id: string;
  domain: string;
  title: string;
  state: string;
  reason: string | null;
  disabled_by: string | null;
}

export interface HAHealthResponse {
  unavailable_entities: EntityDiagnosticItem[];
  stale_entities: EntityDiagnosticItem[];
  unhealthy_integrations: IntegrationHealthItem[];
  summary: {
    unavailable_count: number;
    stale_count: number;
    unhealthy_integration_count: number;
  };
}

export interface ErrorLogResponse {
  summary: {
    total: number;
    errors: number;
    warnings: number;
    by_level: Record<string, number>;
  };
  by_integration: Record<string, Array<{
    timestamp: string;
    level: string;
    logger: string;
    message: string;
    exception: string | null;
  }>>;
  known_patterns: Array<{
    pattern: string;
    severity: string;
    suggestion: string;
    matched_entries: number;
  }>;
  entry_count: number;
}

export interface ConfigCheckResponse {
  valid: boolean;
  result: string;
  errors: string[];
  warnings: string[];
}

export interface RecentTracesResponse {
  traces: Array<{
    trace_id: string;
    status: string;
    timestamp_ms: number;
    duration_ms: number | null;
  }>;
  total: number;
}

export const diagnostics = {
  haHealth: () =>
    request<HAHealthResponse>("/diagnostics/ha-health"),

  errorLog: () =>
    request<ErrorLogResponse>("/diagnostics/error-log"),

  configCheck: () =>
    request<ConfigCheckResponse>("/diagnostics/config-check"),

  recentTraces: (limit = 50) =>
    request<RecentTracesResponse>(`/diagnostics/traces/recent?limit=${limit}`),
};

// ─── Auth / Setup ────────────────────────────────────────────────────────────

export const auth = {
  setupStatus: () =>
    request<{ setup_complete: boolean }>(`/auth/setup-status`),

  setup: (data: { ha_url: string; ha_token: string; password?: string | null }) =>
    request<{ token: string; message: string }>(`/auth/setup`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  loginWithHAToken: (ha_token: string) =>
    request<{ token: string; username: string; message: string }>(
      `/auth/login/ha-token`,
      {
        method: "POST",
        body: JSON.stringify({ ha_token }),
      },
    ),
};

// ─── Usage ──────────────────────────────────────────────────────────────────

export const usage = {
  summary: (days = 30) =>
    request<{
      period_days: number;
      total_calls: number;
      total_input_tokens: number;
      total_output_tokens: number;
      total_tokens: number;
      total_cost_usd: number;
      by_model: Array<{
        model: string;
        provider: string;
        calls: number;
        tokens: number;
        cost_usd: number;
      }>;
    }>(`/usage/summary?days=${days}`),

  daily: (days = 30) =>
    request<{
      days: number;
      data: Array<{
        date: string;
        calls: number;
        tokens: number;
        cost_usd: number;
      }>;
    }>(`/usage/daily?days=${days}`),

  models: (days = 30) =>
    request<{
      days: number;
      models: Array<{
        model: string;
        provider: string;
        calls: number;
        input_tokens: number;
        output_tokens: number;
        tokens: number;
        cost_usd: number;
        avg_latency_ms: number | null;
      }>;
    }>(`/usage/models?days=${days}`),
};

// ─── Model Ratings ──────────────────────────────────────────────────────────

export interface ModelRatingItem {
  id: string;
  model_name: string;
  agent_role: string;
  rating: number;
  notes: string | null;
  config_snapshot: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ModelRatingListResponse {
  items: ModelRatingItem[];
  total: number;
}

export interface ModelSummaryItem {
  model_name: string;
  agent_role: string;
  avg_rating: number;
  rating_count: number;
  latest_config: Record<string, unknown> | null;
}

export interface ModelRatingCreatePayload {
  model_name: string;
  agent_role: string;
  rating: number;
  notes?: string | null;
  config_snapshot?: Record<string, unknown> | null;
}

export const modelRatings = {
  list: (modelName?: string, agentRole?: string) => {
    const params = new URLSearchParams();
    if (modelName) params.set("model_name", modelName);
    if (agentRole) params.set("agent_role", agentRole);
    const qs = params.toString();
    return request<ModelRatingListResponse>(`/models/ratings${qs ? `?${qs}` : ""}`);
  },

  create: (data: ModelRatingCreatePayload) =>
    request<ModelRatingItem>(`/models/ratings`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  summary: (agentRole?: string) => {
    const qs = agentRole ? `?agent_role=${agentRole}` : "";
    return request<ModelSummaryItem[]>(`/models/summary${qs}`);
  },
};
