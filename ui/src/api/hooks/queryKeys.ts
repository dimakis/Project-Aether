// ─── Centralized Query Key Factory ──────────────────────────────────────────
//
// Every React Query key in the app MUST be defined here. This prevents key
// drift between queries and invalidations, and makes cache operations
// type-safe and greppable.
//
// Convention:
//   - Each domain has a namespace object.
//   - `all` is the broadest key for that domain (useful for mass invalidation).
//   - Static keys are `as const` tuples.
//   - Parameterized keys are factory functions returning `as const` tuples.

export const queryKeys = {
  // ── Conversations ───────────────────────────────────────────────────────
  conversations: {
    all: ["conversations"] as const,
    detail: (id: string) => ["conversations", id] as const,
  },

  // ── Models ──────────────────────────────────────────────────────────────
  models: {
    all: ["models"] as const,
  },

  // ── Proposals ───────────────────────────────────────────────────────────
  proposals: {
    all: ["proposals"] as const,
    pending: ["proposals", "pending"] as const,
    detail: (id: string) => ["proposals", id] as const,
  },

  // ── Insights ────────────────────────────────────────────────────────────
  insights: {
    all: ["insights"] as const,
    summary: ["insights", "summary"] as const,
    detail: (id: string) => ["insights", id] as const,
  },

  // ── Entities ────────────────────────────────────────────────────────────
  entities: {
    all: ["entities"] as const,
    byDomain: (domain: string) => ["entities", "domain", domain] as const,
    byArea: (areaId: string, domain?: string) =>
      ["entities", "area", areaId, domain] as const,
    domainsSummary: ["entities", "domains"] as const,
  },

  // ── Areas ───────────────────────────────────────────────────────────────
  areas: {
    all: ["areas"] as const,
  },

  // ── Registry ────────────────────────────────────────────────────────────
  registry: {
    all: ["registry"] as const,
    summary: ["registry", "summary"] as const,
    automations: ["registry", "automations"] as const,
    automationConfig: (id: string) =>
      ["registry", "automationConfig", id] as const,
    scripts: ["registry", "scripts"] as const,
    scenes: ["registry", "scenes"] as const,
    services: (domain?: string) => ["registry", "services", domain] as const,
  },

  // ── Agents ──────────────────────────────────────────────────────────────
  agents: {
    all: ["agents"] as const,
    detail: (name: string) => ["agents", name] as const,
    configVersions: (name: string) =>
      ["agents", name, "config", "versions"] as const,
    promptVersions: (name: string) =>
      ["agents", name, "prompt", "versions"] as const,
  },

  // ── Insight Schedules ───────────────────────────────────────────────────
  schedules: {
    all: ["insightSchedules"] as const,
  },

  // ── Traces ──────────────────────────────────────────────────────────────
  traces: {
    detail: (traceId: string) => ["traces", traceId] as const,
  },

  // ── Usage ───────────────────────────────────────────────────────────────
  usage: {
    all: ["usage"] as const,
    summary: (days: number) => ["usage", "summary", days] as const,
    daily: (days: number) => ["usage", "daily", days] as const,
    byModel: (days: number) => ["usage", "models", days] as const,
    conversationCost: (conversationId: string) =>
      ["usage", "conversation", conversationId] as const,
  },

  // ── Model Ratings / Performance ─────────────────────────────────────────
  modelRatings: {
    all: ["model-ratings"] as const,
    list: (modelName?: string, agentRole?: string) =>
      ["model-ratings", modelName, agentRole] as const,
    summary: (agentRole?: string) => ["model-summary", agentRole] as const,
    performance: (agentRole?: string, hours?: number) =>
      ["model-performance", agentRole, hours] as const,
  },

  // ── Diagnostics ─────────────────────────────────────────────────────────
  diagnostics: {
    all: ["diagnostics"] as const,
    haHealth: ["diagnostics", "ha-health"] as const,
    errorLog: ["diagnostics", "error-log"] as const,
    configCheck: ["diagnostics", "config-check"] as const,
    recentTraces: (limit: number) =>
      ["diagnostics", "traces", limit] as const,
  },

  // ── Flow Grades ─────────────────────────────────────────────────────────
  flowGrades: {
    all: ["flow-grades"] as const,
    detail: (conversationId: string) =>
      ["flow-grades", conversationId] as const,
  },

  // ── Workflow Presets ─────────────────────────────────────────────────────
  workflows: {
    presets: ["workflows", "presets"] as const,
  },

  // ── Zones ───────────────────────────────────────────────────────────────
  zones: {
    all: ["zones"] as const,
  },

  // ── System ──────────────────────────────────────────────────────────────
  system: {
    status: ["system", "status"] as const,
  },
} as const;
