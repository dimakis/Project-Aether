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
  auth,
  usage,
  modelRatings,
} from "./system";
export { workflows } from "./workflows";
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
