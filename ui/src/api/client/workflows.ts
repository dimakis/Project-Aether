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

// ─── API ────────────────────────────────────────────────────────────────────

export const workflows = {
  listPresets: () =>
    request<WorkflowPresetsResponse>("/workflows/presets"),
};
