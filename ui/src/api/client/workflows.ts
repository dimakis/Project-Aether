import { request } from "./core";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface WorkflowPreset {
  id: string;
  name: string;
  description: string;
  agents: string[];
  workflow_key: string;
  icon: string | null;
}

export interface WorkflowPresetsResponse {
  presets: WorkflowPreset[];
  total: number;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  state_type: string;
  version: number;
  status: string;
  config: Record<string, unknown>;
  intent_patterns: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDefinitionListResponse {
  definitions: WorkflowDefinition[];
  total: number;
}

export interface WorkflowCreatePayload {
  name: string;
  description: string;
  state_type: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  conditional_edges?: Record<string, unknown>[];
  intent_patterns?: string[];
}

// ─── API ────────────────────────────────────────────────────────────────────

export const workflows = {
  listPresets: () =>
    request<WorkflowPresetsResponse>("/workflows/presets"),

  listDefinitions: () =>
    request<WorkflowDefinitionListResponse>("/workflows/definitions"),

  getDefinition: (id: string) =>
    request<WorkflowDefinition>(`/workflows/definitions/${id}`),

  createDefinition: (data: WorkflowCreatePayload) =>
    request<WorkflowDefinition>("/workflows/definitions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteDefinition: (id: string) =>
    request<{ status: string; id: string }>(`/workflows/definitions/${id}`, {
      method: "DELETE",
    }),
};
