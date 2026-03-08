// ─── Areas ──────────────────────────────────────────────────────────────────

export interface Area {
  id: string;
  ha_area_id: string;
  name: string;
  floor_id?: string;
  icon?: string;
  entity_count: number;
  last_synced_at?: string;
}

export interface AreaList {
  areas: Area[];
  total: number;
}

// ─── Entities ────────────────────────────────────────────────────────────────

export interface Entity {
  id: string;
  entity_id: string;
  domain: string;
  name: string;
  state: string | null;
  attributes: Record<string, unknown>;
  area_id?: string;
  device_id?: string;
  device_class?: string;
  unit_of_measurement?: string;
  supported_features?: number;
  icon?: string;
  last_synced_at?: string;
}

export interface EntityList {
  entities: Entity[];
  total: number;
  domain?: string;
}

export interface EntitySyncResponse {
  session_id: string;
  status: string;
  entities_found: number;
  entities_added: number;
  entities_updated: number;
  entities_removed: number;
  duration_seconds: number;
}

export interface DomainSummary {
  domain: string;
  count: number;
}

// ─── Registry ────────────────────────────────────────────────────────────────

export interface Automation {
  id: string;
  entity_id: string;
  ha_automation_id: string;
  alias: string;
  state: string;
  description?: string | null;
  mode?: string;
  trigger_types?: string[] | null;
  trigger_count?: number;
  action_count?: number;
  condition_count?: number;
  last_triggered?: string | null;
  last_synced_at?: string | null;
}

export interface AutomationList {
  automations: Automation[];
  total: number;
  enabled_count?: number;
  disabled_count?: number;
}

export interface Script {
  id: string;
  entity_id: string;
  alias: string;
  state: string;
  description?: string | null;
  mode?: string;
  icon?: string | null;
  last_triggered?: string | null;
  last_synced_at?: string | null;
  sequence?: unknown[] | null;
  fields?: Record<string, unknown> | null;
}

export interface ScriptList {
  scripts: Script[];
  total: number;
  running_count?: number;
}

export interface Scene {
  id: string;
  entity_id: string;
  name: string;
  icon?: string | null;
  last_synced_at?: string | null;
  entity_states?: Record<string, unknown> | null;
}

export interface SceneList {
  scenes: Scene[];
  total: number;
}

export interface Service {
  id: string;
  domain: string;
  service: string;
  name?: string | null;
  description?: string | null;
  fields?: Record<string, unknown> | null;
  target?: Record<string, unknown> | null;
  is_seeded?: boolean;
  last_synced_at?: string | null;
}

export interface ServiceList {
  services: Service[];
  total: number;
  domains?: string[];
  seeded_count?: number;
  discovered_count?: number;
}

export interface HARegistrySummary {
  automations_count: number;
  automations_enabled: number;
  scripts_count: number;
  scenes_count: number;
  services_count: number;
  services_seeded: number;
  helpers_count?: number;
  last_synced_at?: string | null;
  mcp_gaps?: string[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export type HelperType =
  | "input_boolean"
  | "input_number"
  | "input_text"
  | "input_select"
  | "input_datetime"
  | "input_button"
  | "counter"
  | "timer";

export interface Helper {
  entity_id: string;
  domain: string;
  name: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface HelperList {
  helpers: Helper[];
  total: number;
  by_type: Record<string, number>;
}

export interface HelperCreateRequest {
  helper_type: HelperType;
  input_id: string;
  name: string;
  icon?: string;
  config: Record<string, unknown>;
}

export interface HelperCreateResponse {
  success: boolean;
  entity_id?: string;
  input_id: string;
  helper_type: string;
  error?: string;
}

export interface HelperDeleteResponse {
  success: boolean;
  entity_id: string;
  error?: string;
}

// ─── Registry entity context ─────────────────────────────────────────────────

/** Context about a specific entity, passed to InlineAssistant for focused chat. */
export interface EntityContext {
  /** Entity ID, e.g. "automation.kitchen_lights" */
  entityId: string;
  /** Domain type: automation, script, or scene */
  entityType: "automation" | "script" | "scene";
  /** Human-friendly display name */
  label: string;
  /** Original YAML config (if available) */
  configYaml?: string;
  /** User-edited YAML (if the user modified it) */
  editedYaml?: string;
}
