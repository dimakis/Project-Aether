import { request } from "./core";

// ─── Agents (Feature 23) ─────────────────────────────────────────────────────

export const agents = {
  list: () =>
    request<import("@/lib/types").AgentList>(`/agents`),

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

  promoteConfigVersion: (name: string, versionId: string) =>
    request<import("@/lib/types").ConfigVersion>(
      `/agents/${name}/config/versions/${versionId}/promote`,
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

  promotePromptVersion: (name: string, versionId: string) =>
    request<import("@/lib/types").PromptVersion>(
      `/agents/${name}/prompt/versions/${versionId}/promote`,
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

  // Prompt generation
  generatePrompt: (name: string, userInput?: string) =>
    request<{ generated_prompt: string; agent_name: string; agent_role: string }>(
      `/agents/${name}/prompt/generate`,
      { method: "POST", body: JSON.stringify({ user_input: userInput || null }) },
    ),
};
