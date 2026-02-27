import { request } from "./core";

export interface OptimizationJob {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  analysis_types: string[];
  hours_analyzed: number;
  insight_count: number;
  suggestion_count: number;
  insights: Record<string, unknown>[];
  suggestions: AutomationSuggestion[];
  recommendations: string[];
  started_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface AutomationSuggestion {
  id: string;
  pattern: string;
  entities: string[];
  proposed_trigger: string;
  proposed_action: string;
  confidence: number;
  source_insight_type: string;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
}

export interface SuggestionList {
  items: AutomationSuggestion[];
  total: number;
}

export interface OptimizationRequest {
  analysis_types?: string[];
  hours?: number;
  entity_ids?: string[];
  focus_areas?: string[];
}

export const optimization = {
  run: (data: OptimizationRequest) =>
    request<OptimizationJob>("/optimize", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  status: (jobId: string) => request<OptimizationJob>(`/optimize/${jobId}`),

  suggestions: () => request<SuggestionList>("/optimize/suggestions/list"),

  acceptSuggestion: (id: string, comment?: string) =>
    request<{ status: string; proposal_id?: string }>(
      `/optimize/suggestions/${id}/accept`,
      {
        method: "POST",
        body: JSON.stringify({ comment }),
      },
    ),

  rejectSuggestion: (id: string, reason?: string) =>
    request<{ status: string }>(
      `/optimize/suggestions/${id}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      },
    ),
};
