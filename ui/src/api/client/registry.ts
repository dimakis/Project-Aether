import { request } from "./core";

// ─── HA Registry ────────────────────────────────────────────────────────────

export const registry = {
  automations: () =>
    request<import("@/lib/types").AutomationList>(
      `/registry/automations`,
    ),

  automation: (id: string) =>
    request<import("@/lib/types").Automation>(
      `/registry/automations/${id}`,
    ),

  automationConfig: (id: string) =>
    request<{ automation_id: string; ha_automation_id: string; config: unknown; yaml: string }>(
      `/registry/automations/${id}/config`,
    ),

  scripts: () =>
    request<import("@/lib/types").ScriptList>(
      `/registry/scripts`,
    ),

  script: (id: string) =>
    request<import("@/lib/types").Script>(
      `/registry/scripts/${id}`,
    ),

  scenes: () =>
    request<import("@/lib/types").SceneList>(
      `/registry/scenes`,
    ),

  scene: (id: string) =>
    request<import("@/lib/types").Scene>(
      `/registry/scenes/${id}`,
    ),

  services: (domain?: string) =>
    request<import("@/lib/types").ServiceList>(
      `/registry/services${domain ? `?domain=${domain}` : ""}`,
    ),

  service: (id: string) =>
    request<import("@/lib/types").Service>(
      `/registry/services/${id}`,
    ),

  summary: () =>
    request<import("@/lib/types").HARegistrySummary>(
      `/registry/summary`,
    ),

  seedServices: () =>
    request<{ seeded: number; updated: number }>(
      `/registry/services/seed`,
      { method: "POST" },
    ),

  helpers: () =>
    request<import("@/lib/types").HelperList>(
      `/registry/helpers`,
    ),

  createHelper: (data: import("@/lib/types").HelperCreateRequest) =>
    request<import("@/lib/types").HelperCreateResponse>(
      `/registry/helpers`,
      { method: "POST", body: JSON.stringify(data), headers: { "Content-Type": "application/json" } },
    ),

  deleteHelper: (domain: string, inputId: string) =>
    request<import("@/lib/types").HelperDeleteResponse>(
      `/registry/helpers/${domain}/${inputId}`,
      { method: "DELETE" },
    ),

  sync: () =>
    request<{
      automations_synced: number;
      scripts_synced: number;
      scenes_synced: number;
      duration_seconds: number;
    }>(`/registry/sync`, { method: "POST" }),
};
