import { request } from "./core";

// ─── Types ───────────────────────────────────────────────────────────────────

export type UrlPreference = "auto" | "local" | "remote";

export interface HAZone {
  id: string;
  name: string;
  slug: string;
  ha_url: string;
  ha_url_remote: string | null;
  is_default: boolean;
  latitude: number | null;
  longitude: number | null;
  icon: string | null;
  url_preference: UrlPreference;
  created_at: string;
  updated_at: string;
}

export interface ZoneCreatePayload {
  name: string;
  ha_url: string;
  ha_url_remote?: string | null;
  ha_token: string;
  is_default?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  icon?: string | null;
  url_preference?: UrlPreference;
}

export interface ZoneUpdatePayload {
  name?: string;
  ha_url?: string;
  ha_url_remote?: string | null;
  ha_token?: string;
  latitude?: number | null;
  longitude?: number | null;
  icon?: string | null;
  url_preference?: UrlPreference;
}

export interface ZoneTestResult {
  local_ok: boolean;
  remote_ok: boolean | null;
  local_version: string | null;
  remote_version: string | null;
  local_error: string | null;
  remote_error: string | null;
}

// ─── Client ──────────────────────────────────────────────────────────────────

export const zones = {
  list: () => request<HAZone[]>("/zones"),

  create: (payload: ZoneCreatePayload) =>
    request<HAZone>("/zones", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  update: (id: string, payload: ZoneUpdatePayload) =>
    request<HAZone>(`/zones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    request<void>(`/zones/${id}`, { method: "DELETE" }),

  setDefault: (id: string) =>
    request<HAZone>(`/zones/${id}/set-default`, { method: "POST" }),

  test: (id: string) =>
    request<ZoneTestResult>(`/zones/${id}/test`, { method: "POST" }),
};
