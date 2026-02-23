// ─── Agents (Feature 23) ─────────────────────────────────────────────────────

export type AgentStatusValue = "disabled" | "enabled" | "primary";
export type VersionStatusValue = "draft" | "active" | "archived";

export interface ConfigVersion {
  id: string;
  agent_id: string;
  version_number: number;
  version: string | null;
  status: VersionStatusValue;
  model_name: string | null;
  temperature: number | null;
  fallback_model: string | null;
  tools_enabled: string[] | null;
  change_summary: string | null;
  promoted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PromptVersion {
  id: string;
  agent_id: string;
  version_number: number;
  version: string | null;
  status: VersionStatusValue;
  prompt_template: string;
  change_summary: string | null;
  promoted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentDetail {
  id: string;
  name: string;
  description: string;
  version: string;
  status: AgentStatusValue;
  domain?: string | null;
  is_routable?: boolean;
  intent_patterns?: string[];
  capabilities?: string[];
  active_config_version_id: string | null;
  active_prompt_version_id: string | null;
  active_config: ConfigVersion | null;
  active_prompt: PromptVersion | null;
  created_at: string;
  updated_at: string;
}

export interface AgentList {
  agents: AgentDetail[];
  total: number;
}

export type BumpType = "major" | "minor" | "patch";

export interface ConfigVersionCreate {
  model_name?: string;
  temperature?: number;
  fallback_model?: string;
  tools_enabled?: string[];
  change_summary?: string;
  bump_type?: BumpType;
}

export interface PromptVersionCreate {
  prompt_template: string;
  change_summary?: string;
  bump_type?: BumpType;
}

export interface SeedResult {
  agents_seeded: number;
  configs_created: number;
  prompts_created: number;
}
