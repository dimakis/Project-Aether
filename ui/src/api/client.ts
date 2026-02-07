import { env } from "@/lib/env";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${env.API_URL}/v1${path}`;
  const response = await fetch(url, {
    ...options,
    credentials: "include", // Send httpOnly JWT cookie
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  // Redirect to login on 401 (expired session, etc.)
  if (response.status === 401 && !path.startsWith("/auth/")) {
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message =
      body?.error?.message || body?.detail || response.statusText;
    throw new ApiError(response.status, message);
  }

  // 204 No Content has no body to parse
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ─── Conversations ──────────────────────────────────────────────────────────

export const conversations = {
  list: (status?: string) =>
    request<import("@/lib/types").ConversationList>(
      `/conversations?limit=50${status ? `&status=${status}` : ""}`,
    ),

  get: (id: string) =>
    request<import("@/lib/types").ConversationDetail>(
      `/conversations/${id}`,
    ),

  create: (message: string, title?: string) =>
    request<import("@/lib/types").ConversationDetail>(`/conversations`, {
      method: "POST",
      body: JSON.stringify({ initial_message: message, title }),
    }),

  sendMessage: (id: string, message: string) =>
    request<import("@/lib/types").Message>(
      `/conversations/${id}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ role: "user", content: message }),
      },
    ),

  delete: (id: string) =>
    request<void>(`/conversations/${id}`, { method: "DELETE" }),
};

// ─── Chat (OpenAI-compatible, streaming) ────────────────────────────────────

/** A chunk from the SSE stream — text delta, metadata, or real-time trace event */
export type StreamChunk =
  | string
  | {
      type: "metadata";
      trace_id?: string;
      conversation_id?: string;
      /** Tool names the Architect invoked during this turn */
      tool_calls?: string[];
    }
  | {
      type: "trace";
      agent?: string;
      event: string;
      tool?: string;
      ts?: number;
      agents?: string[];
    };

export async function* streamChat(
  model: string,
  messages: import("@/lib/types").ChatMessage[],
): AsyncGenerator<StreamChunk> {
  const url = `${env.API_URL}/v1/chat/completions`;
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages,
      stream: true,
    }),
  });

  if (response.status === 401) {
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith("data: ")) continue;

      const data = trimmed.slice(6);
      if (data === "[DONE]") return;

      try {
        const parsed = JSON.parse(data);
        if (parsed.error) {
          throw new ApiError(500, parsed.error.message);
        }

        // Handle metadata events (trace_id, conversation_id, tool_calls)
        if (parsed.type === "metadata") {
          yield {
            type: "metadata",
            trace_id: parsed.trace_id,
            conversation_id: parsed.conversation_id,
            tool_calls: parsed.tool_calls,
          };
          continue;
        }

        // Handle real-time trace events (agent activity)
        if (parsed.type === "trace") {
          yield {
            type: "trace",
            agent: parsed.agent,
            event: parsed.event,
            tool: parsed.tool,
            ts: parsed.ts,
            agents: parsed.agents,
          };
          continue;
        }

        const content = parsed.choices?.[0]?.delta?.content;
        if (content) yield content;
      } catch (e) {
        if (e instanceof ApiError) throw e;
        // Skip malformed chunks
      }
    }
  }
}

// ─── Feedback ────────────────────────────────────────────────────────────────

export async function submitFeedback(
  traceId: string,
  sentiment: "positive" | "negative",
): Promise<void> {
  const url = `${env.API_URL}/v1/feedback`;
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId, sentiment }),
  });

  if (response.status === 401) {
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }
}

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

// ─── Models ─────────────────────────────────────────────────────────────────

export const models = {
  list: () =>
    request<import("@/lib/types").ModelsResponse>(`/models`),
};

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
    request<import("@/lib/types").Proposal>(`/proposals/${id}/rollback`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  create: (data: {
    name: string;
    trigger?: unknown;
    actions?: unknown;
    description?: string;
    conditions?: unknown;
    mode?: string;
    proposal_type?: string;
    service_call?: Record<string, unknown>;
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

// ─── Entities ───────────────────────────────────────────────────────────────

// ─── Areas ──────────────────────────────────────────────────────────────────

export const areas = {
  list: () =>
    request<import("@/lib/types").AreaList>(`/areas`),
};

export const entities = {
  list: (domain?: string, areaId?: string) => {
    const params = new URLSearchParams({ limit: "200" });
    if (domain) params.set("domain", domain);
    if (areaId) params.set("area_id", areaId);
    return request<import("@/lib/types").EntityList>(
      `/entities?${params}`,
    );
  },

  get: (id: string) =>
    request<import("@/lib/types").Entity>(`/entities/${id}`),

  query: (query: string) =>
    request<{ entities: import("@/lib/types").Entity[]; query: string }>(
      `/entities/query`,
      { method: "POST", body: JSON.stringify({ query }) },
    ),

  sync: (force = false) =>
    request<import("@/lib/types").EntitySyncResponse>(`/entities/sync`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),

  domainsSummary: async (): Promise<import("@/lib/types").DomainSummary[]> => {
    const raw = await request<Record<string, number>>(
      `/entities/domains/summary`,
    );
    // API returns {sensor: 239, light: 13, ...} — transform to array
    return Object.entries(raw).map(([domain, count]) => ({
      domain,
      count,
    }));
  },
};

// ─── HA Registry ────────────────────────────────────────────────────────────

export const registry = {
  automations: () =>
    request<import("@/lib/types").AutomationList>(
      `/registry/automations`,
    ),

  automation: (id: string) =>
    request<import("@/lib/types").Automation>(
      `/registry/automations/${id}`,
    ),

  automationConfig: (id: string) =>
    request<{ automation_id: string; ha_automation_id: string; config: unknown; yaml: string }>(
      `/registry/automations/${id}/config`,
    ),

  scripts: () =>
    request<import("@/lib/types").ScriptList>(
      `/registry/scripts`,
    ),

  script: (id: string) =>
    request<import("@/lib/types").Script>(
      `/registry/scripts/${id}`,
    ),

  scenes: () =>
    request<import("@/lib/types").SceneList>(
      `/registry/scenes`,
    ),

  scene: (id: string) =>
    request<import("@/lib/types").Scene>(
      `/registry/scenes/${id}`,
    ),

  services: (domain?: string) =>
    request<import("@/lib/types").ServiceList>(
      `/registry/services${domain ? `?domain=${domain}` : ""}`,
    ),

  service: (id: string) =>
    request<import("@/lib/types").Service>(
      `/registry/services/${id}`,
    ),

  summary: () =>
    request<import("@/lib/types").HARegistrySummary>(
      `/registry/summary`,
    ),

  seedServices: () =>
    request<{ seeded: number; updated: number }>(
      `/registry/services/seed`,
      { method: "POST" },
    ),

  sync: () =>
    request<{
      automations_synced: number;
      scripts_synced: number;
      scenes_synced: number;
      duration_seconds: number;
    }>(`/registry/sync`, { method: "POST" }),
};

// ─── Agents (Feature 23) ─────────────────────────────────────────────────────

export const agents = {
  list: () =>
    request<import("@/lib/types").AgentList>(`/agents`),

  get: (name: string) =>
    request<import("@/lib/types").AgentDetail>(`/agents/${name}`),

  updateStatus: (name: string, status: string) =>
    request<import("@/lib/types").AgentDetail>(`/agents/${name}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  seed: () =>
    request<import("@/lib/types").SeedResult>(`/agents/seed`, {
      method: "POST",
    }),

  // Config versions
  listConfigVersions: (name: string) =>
    request<import("@/lib/types").ConfigVersion[]>(
      `/agents/${name}/config/versions`,
    ),

  createConfigVersion: (name: string, data: import("@/lib/types").ConfigVersionCreate) =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/versions`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  updateConfigVersion: (name: string, versionId: string, data: Partial<import("@/lib/types").ConfigVersionCreate>) =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/versions/${versionId}`,
      { method: "PATCH", body: JSON.stringify(data) },
    ),

  promoteConfigVersion: (name: string, versionId: string) =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/versions/${versionId}/promote`,
      { method: "POST" },
    ),

  rollbackConfig: (name: string) =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/rollback`,
      { method: "POST" },
    ),

  deleteConfigVersion: (name: string, versionId: string) =>
    request<void>(
      `/agents/${name}/config/versions/${versionId}`,
      { method: "DELETE" },
    ),

  // Prompt versions
  listPromptVersions: (name: string) =>
    request<import("@/lib/types").PromptVersion[]>(
      `/agents/${name}/prompt/versions`,
    ),

  createPromptVersion: (name: string, data: import("@/lib/types").PromptVersionCreate) =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/versions`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  updatePromptVersion: (name: string, versionId: string, data: Partial<import("@/lib/types").PromptVersionCreate>) =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/versions/${versionId}`,
      { method: "PATCH", body: JSON.stringify(data) },
    ),

  promotePromptVersion: (name: string, versionId: string) =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/versions/${versionId}/promote`,
      { method: "POST" },
    ),

  rollbackPrompt: (name: string) =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/rollback`,
      { method: "POST" },
    ),

  deletePromptVersion: (name: string, versionId: string) =>
    request<void>(
      `/agents/${name}/prompt/versions/${versionId}`,
      { method: "DELETE" },
    ),

  // Prompt generation
  generatePrompt: (name: string, userInput?: string) =>
    request<{ generated_prompt: string; agent_name: string; agent_role: string }>(
      `/agents/${name}/prompt/generate`,
      { method: "POST", body: JSON.stringify({ user_input: userInput || null }) },
    ),
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

export { ApiError };
