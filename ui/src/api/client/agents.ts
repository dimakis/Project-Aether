import { request } from "./core";

// ─── Agents (Feature 23) ─────────────────────────────────────────────────────

// ─── Available / Routable Agents (Feature 30) ────────────────────────────────

export interface AvailableAgent {
  name: string;
  description: string;
  domain: string | null;
  is_routable: boolean;
  intent_patterns: string[];
  capabilities: string[];
}

export interface AvailableAgentsResponse {
  agents: AvailableAgent[];
  total: number;
}

export const agents = {
  list: () =>
    request<import("@/lib/types").AgentList>(`/agents`),

  listAvailable: () =>
    request<AvailableAgentsResponse>(`/agents/available`),

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

  clone: (name: string) =>
    request<import("@/lib/types").AgentDetail>(`/agents/${name}/clone`, {
      method: "POST",
    }),

  quickModelSwitch: (name: string, modelName: string) =>
    request<import("@/lib/types").AgentDetail>(`/agents/${name}/model`, {
      method: "PATCH",
      body: JSON.stringify({ model_name: modelName }),
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

  promoteConfigVersion: (name: string, versionId: string, bumpType: string = "patch") =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/versions/${versionId}/promote?bump_type=${bumpType}`,
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

  promotePromptVersion: (name: string, versionId: string, bumpType: string = "patch") =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/versions/${versionId}/promote?bump_type=${bumpType}`,
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

  // Promote both config and prompt drafts in one operation
  promoteBoth: (name: string, bumpType: string = "patch") =>
    request<{
      config: import("@/lib/types").ConfigVersion | null;
      prompt: import("@/lib/types").PromptVersion | null;
      message: string;
    }>(
      `/agents/${name}/promote-all?bump_type=${bumpType}`,
      { method: "POST" },
    ),

  // Prompt generation
  generatePrompt: (name: string, userInput?: string) =>
    request<{ generated_prompt: string; agent_name: string; agent_role: string }>(
      `/agents/${name}/prompt/generate`,
      { method: "POST", body: JSON.stringify({ user_input: userInput || null }) },
    ),
};
