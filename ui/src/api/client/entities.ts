import { request } from "./core";

// ─── Areas ──────────────────────────────────────────────────────────────────

export const areas = {
  list: () =>
    request<import("@/lib/types").AreaList>(`/areas`),
};

// ─── Entities ───────────────────────────────────────────────────────────────

export const entities = {
  list: (domain?: string, areaId?: string) => {
    const params = new URLSearchParams({ limit: "200" });
    if (domain) params.set("domain", domain);
    if (areaId) params.set("area_id", areaId);
    return request<import("@/lib/types").EntityList>(
      `/entities?${params}`,
    );
  },

  get: (id: string) =>
    request<import("@/lib/types").Entity>(`/entities/${id}`),

  query: (query: string) =>
    request<{ entities: import("@/lib/types").Entity[]; query: string }>(
      `/entities/query`,
      { method: "POST", body: JSON.stringify({ query }) },
    ),

  sync: (force = false) =>
    request<import("@/lib/types").EntitySyncResponse>(`/entities/sync`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),

  domainsSummary: async (): Promise<import("@/lib/types").DomainSummary[]> => {
    const raw = await request<Record<string, number>>(
      `/entities/domains/summary`,
    );
    // API returns {sensor: 239, light: 13, ...} — transform to array
    return Object.entries(raw).map(([domain, count]) => ({
      domain,
      count,
    }));
  },
};
