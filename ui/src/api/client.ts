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
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message =
      body?.error?.message || body?.detail || response.statusText;
    throw new ApiError(response.status, message);
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

/** A chunk from the SSE stream — either a text delta or a metadata event */
export type StreamChunk =
  | string
  | { type: "metadata"; trace_id?: string; conversation_id?: string };

export async function* streamChat(
  model: string,
  messages: import("@/lib/types").ChatMessage[],
): AsyncGenerator<StreamChunk> {
  const url = `${env.API_URL}/v1/chat/completions`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages,
      stream: true,
    }),
  });

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

        // Handle metadata events (trace_id, conversation_id)
        if (parsed.type === "metadata") {
          yield { type: "metadata", trace_id: parsed.trace_id, conversation_id: parsed.conversation_id };
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId, sentiment }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }
}

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
};

// ─── Entities ───────────────────────────────────────────────────────────────

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

  summary: () =>
    request<import("@/lib/types").HARegistrySummary>(
      `/registry/summary`,
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

export { ApiError };
