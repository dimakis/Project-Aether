import { request } from "./core";

export interface ScorerResult {
  name: string;
  pass_count: number;
  fail_count: number;
  error_count: number;
  pass_rate: number | null;
  avg_value: number | null;
}

export interface EvaluationSummary {
  run_id: string | null;
  trace_count: number;
  scorer_results: ScorerResult[];
  evaluated_at: string | null;
}

export interface EvaluationTriggerResponse {
  status: string;
  trace_count: number;
  message: string;
}

export interface ScorerInfo {
  name: string;
  description: string;
}

export interface ScorersResponse {
  count: number;
  scorers: ScorerInfo[];
}

export const evaluations = {
  summary: () => request<EvaluationSummary>("/evaluations/summary"),

  run: (maxTraces?: number) =>
    request<EvaluationTriggerResponse>(
      `/evaluations/run${maxTraces ? `?max_traces=${maxTraces}` : ""}`,
      { method: "POST" },
    ),

  scorers: () => request<ScorersResponse>("/evaluations/scorers"),
};
