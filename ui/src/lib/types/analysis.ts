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
  | "behavioral_pattern"
  | "comfort_analysis"
  | "security_audit"
  | "weather_correlation"
  | "automation_efficiency"
  | "custom";

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
  conversation_id?: string;
  task_label?: string;
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

// ─── Analysis Reports (Feature 33: DS Deep Analysis) ────────────────────────

export type AnalysisDepth = "quick" | "standard" | "deep";
export type ExecutionStrategy = "parallel" | "teamwork";
export type ReportStatus = "running" | "completed" | "failed";

export interface CommunicationEntry {
  from_agent: string;
  to_agent: string;
  message_type: string;
  content: string;
  metadata: Record<string, unknown>;
  timestamp: number | string;
}

export interface AnalysisReport {
  id: string;
  title: string;
  analysis_type: string;
  depth: AnalysisDepth;
  strategy: ExecutionStrategy;
  status: ReportStatus;
  summary: string | null;
  insight_ids: string[];
  artifact_paths: string[];
  communication_log: CommunicationEntry[];
  communication_count: number;
  conversation_id: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface AnalysisReportList {
  reports: AnalysisReport[];
  total: number;
}

export interface ReportCommunicationLog {
  report_id: string;
  communication_log: CommunicationEntry[];
  count: number;
}
