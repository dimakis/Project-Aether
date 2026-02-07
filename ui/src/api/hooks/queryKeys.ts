// ─── Query Keys ─────────────────────────────────────────────────────────────

export const queryKeys = {
  conversations: ["conversations"] as const,
  conversation: (id: string) => ["conversations", id] as const,
  models: ["models"] as const,
  proposals: ["proposals"] as const,
  proposalsPending: ["proposals", "pending"] as const,
  proposal: (id: string) => ["proposals", id] as const,
  insights: ["insights"] as const,
  insightsPending: ["insights", "pending"] as const,
  insightsSummary: ["insights", "summary"] as const,
  insight: (id: string) => ["insights", id] as const,
  entities: ["entities"] as const,
  entitiesByDomain: (domain: string) => ["entities", "domain", domain] as const,
  domainsSummary: ["entities", "domains"] as const,
  registryAutomations: ["registry", "automations"] as const,
  registrySummary: ["registry", "summary"] as const,
  systemStatus: ["system", "status"] as const,
} as const;
