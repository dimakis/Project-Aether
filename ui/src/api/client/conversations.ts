import { env } from "@/lib/env";
import { ApiError, request } from "./core";

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

/** A chunk from the SSE stream — text delta, metadata, trace, or status event */
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
    }
  | {
      type: "status";
      /** Status message (e.g. "Running analyze_energy..."), empty string to clear */
      content: string;
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

        // Handle status events (tool execution progress)
        if (parsed.type === "status") {
          yield {
            type: "status",
            content: parsed.content ?? "",
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
