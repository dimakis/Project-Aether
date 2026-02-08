import { request } from "./core";

export interface FlowGradePayload {
  conversation_id: string;
  grade: 1 | -1;
  span_id?: string | null;
  comment?: string | null;
  agent_role?: string | null;
}

export interface FlowGradeItem {
  id: string;
  conversation_id: string;
  span_id: string | null;
  grade: number;
  comment: string | null;
  agent_role: string | null;
  created_at: string;
}

export interface FlowGradeSummary {
  conversation_id: string;
  overall: FlowGradeItem | null;
  steps: FlowGradeItem[];
  total_grades: number;
  thumbs_up: number;
  thumbs_down: number;
}

export const flowGrades = {
  submit: (data: FlowGradePayload) =>
    request<FlowGradeItem>(`/flow-grades`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (conversationId: string) =>
    request<FlowGradeSummary>(`/flow-grades/${conversationId}`),

  delete: (gradeId: string) =>
    request<void>(`/flow-grades/${gradeId}`, { method: "DELETE" }),
};
