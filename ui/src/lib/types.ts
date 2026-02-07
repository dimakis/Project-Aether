// ─── Chat / OpenAI compat ────────────────────────────────────────────────────

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  name?: string;
  tool_calls?: unknown;
  tool_call_id?: string;
}

export interface ModelsResponse {
  object: string;
  data: ModelInfo[];
}

export interface ModelInfo {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}

// ─── Conversations ───────────────────────────────────────────────────────────

export interface Conversation {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationList {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_calls?: unknown;
  tool_results?: unknown;
  tokens_used?: number;
  latency_ms?: number;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  pending_approvals?: string[];
}

// ─── Proposals ───────────────────────────────────────────────────────────────

export type ProposalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "deployed"
  | "rolled_back"
  | "failed";

export interface Proposal {
  id: string;
  name: string;
  description?: string;
  status: ProposalStatus;
  conversation_id?: string;
  proposed_at?: string;
  approved_at?: string;
  approved_by?: string;
  deployed_at?: string;
  rolled_back_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface ProposalWithYAML extends Proposal {
  yaml_content?: string;
}

export interface ProposalList {
  items: Proposal[];
  total: number;
  limit: number;
  offset: number;
}

export interface DeploymentResponse {
  success: boolean;
  proposal_id: string;
  ha_automation_id?: string;
  method?: string;
  yaml_content?: string;
  instructions?: string;
  deployed_at?: string;
  error?: string;
}

// ─── Insights ────────────────────────────────────────────────────────────────

export type InsightType =
  | "energy_optimization"
  | "anomaly_detection"
  | "usage_pattern"
  | "cost_saving"
  | "maintenance_prediction"
  | "automation_gap"
  | "automation_inefficiency"
  | "correlation"
  | "device_health"
  | "behavioral_pattern";

export interface Insight {
  id: string;
  type: InsightType;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  confidence: number;
  impact: string;
  entities: string[];
  script_path?: string;
  script_output?: Record<string, unknown>;
  status: string;
  mlflow_run_id?: string;
  created_at: string;
  reviewed_at?: string;
  actioned_at?: string;
}

export interface InsightList {
  items: Insight[];
  total: number;
  limit: number;
  offset: number;
}

export interface InsightSummary {
  total: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  pending_count: number;
  high_impact_count: number;
}

export interface AnalysisJob {
  job_id: string;
  status: string;
  analysis_type: string;
  progress: number;
  started_at: string;
  completed_at?: string;
  mlflow_run_id?: string;
  insight_ids: string[];
  error?: string;
}

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
  state: string;
  alias: string;
}

export interface AutomationList {
  automations: Automation[];
  total: number;
}

export interface HARegistrySummary {
  automations: number;
  scripts: number;
  scenes: number;
  areas: number;
  devices: number;
  entities: number;
}

// ─── Insight Schedules (Feature 10) ──────────────────────────────────────────

export interface InsightSchedule {
  id: string;
  name: string;
  enabled: boolean;
  analysis_type: string;
  trigger_type: "cron" | "webhook";
  entity_ids: string[] | null;
  hours: number;
  options: Record<string, unknown>;
  cron_expression: string | null;
  webhook_event: string | null;
  webhook_filter: Record<string, unknown> | null;
  last_run_at: string | null;
  last_result: string | null;
  last_error: string | null;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface InsightScheduleList {
  items: InsightSchedule[];
  total: number;
}

export interface InsightScheduleCreate {
  name: string;
  analysis_type: string;
  trigger_type: "cron" | "webhook";
  enabled?: boolean;
  entity_ids?: string[];
  hours?: number;
  options?: Record<string, unknown>;
  cron_expression?: string;
  webhook_event?: string;
  webhook_filter?: Record<string, unknown>;
}

// ─── Traces (Feature 11) ─────────────────────────────────────────────────────

export interface SpanNode {
  span_id: string;
  name: string;
  agent: string;
  type: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  status: string;
  attributes: Record<string, unknown>;
  children: SpanNode[];
}

export interface TraceResponse {
  trace_id: string;
  status: string;
  duration_ms: number;
  root_span: SpanNode | null;
  agents_involved: string[];
  span_count: number;
}

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
}
