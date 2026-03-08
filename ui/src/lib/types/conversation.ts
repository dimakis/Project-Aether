// ─── Chat / OpenAI compat ────────────────────────────────────────────────────

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  name?: string;
  tool_calls?: unknown;
  tool_call_id?: string;
}

export interface ModelsResponse {
  object: string;
  data: ModelInfo[];
}

export interface ModelInfo {
  id: string;
  object: string;
  created: number;
  owned_by: string;
  input_cost_per_1m: number | null;
  output_cost_per_1m: number | null;
}

// ─── Conversations ───────────────────────────────────────────────────────────

export interface Conversation {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationList {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_calls?: unknown;
  tool_results?: unknown;
  tokens_used?: number;
  latency_ms?: number;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  pending_approvals?: string[];
}
