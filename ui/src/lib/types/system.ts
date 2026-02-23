// ─── System ──────────────────────────────────────────────────────────────────

export interface HealthCheck {
  status: string;
  timestamp: string;
  version: string;
}

export interface SystemComponent {
  name: string;
  status: string;
  message?: string;
  latency_ms?: number;
}

export interface SystemStatus {
  status: string;
  timestamp: string;
  version: string;
  environment: string;
  components: SystemComponent[];
  uptime_seconds?: number;
  public_url?: string | null;
  deployment_mode?: string;
}

// ─── Usage ───────────────────────────────────────────────────────────────────

export interface UsageModelBreakdown {
  model: string;
  provider: string;
  calls: number;
  tokens: number;
  cost_usd: number;
}

export interface UsageSummary {
  period_days: number;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  by_model: UsageModelBreakdown[];
}

export interface UsageDailyEntry {
  date: string;
  calls: number;
  tokens: number;
  cost_usd: number;
}

export interface UsageDailyResponse {
  days: number;
  data: UsageDailyEntry[];
}

export interface UsageByModelEntry {
  model: string;
  provider: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  tokens: number;
  cost_usd: number;
  avg_latency_ms: number | null;
}

export interface UsageByModelResponse {
  days: number;
  models: UsageByModelEntry[];
}

// ─── Model Performance ───────────────────────────────────────────────────────

export interface ModelPerformanceItem {
  model: string;
  agent_role: string | null;
  call_count: number;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_usd: number | null;
  avg_cost_per_call: number | null;
}
