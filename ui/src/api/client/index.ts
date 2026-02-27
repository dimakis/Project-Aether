// Barrel re-export — preserves `import { ... } from "@/api/client"` contract
export { ApiError, request } from "./core";
export { conversations, streamChat, submitFeedback } from "./conversations";
export type { StreamChunk } from "./conversations";
export { proposals, insights } from "./proposals";
export { areas, entities } from "./entities";
export { registry } from "./registry";
export { agents } from "./agents";
export { insightSchedules, traces } from "./schedules";
export {
  models,
  system,
  diagnostics,
  usage,
  modelRatings,
} from "./system";
export { authApi } from "./auth";
export { appSettings } from "./settings";
export type { AppSettingsResponse } from "./settings";
export { workflows } from "./workflows";
export { flowGrades } from "./flow-grades";
export { optimization } from "./optimization";
export { evaluations } from "./evaluations";
export { jobs } from "./jobs";
export type { FlowGradePayload, FlowGradeItem, FlowGradeSummary } from "./flow-grades";
export type { WorkflowPreset, WorkflowPresetsResponse } from "./workflows";
export type {
  EntityDiagnosticItem,
  IntegrationHealthItem,
  HAHealthResponse,
  ErrorLogResponse,
  ConfigCheckResponse,
  RecentTracesResponse,
  ModelRatingItem,
  ModelRatingListResponse,
  ModelSummaryItem,
  ModelRatingCreatePayload,
  ModelPerformanceItem,
} from "./system";
