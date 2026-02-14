import { request } from "./core";

// ─── Types ───────────────────────────────────────────────────────────────────

/** Metadata for a Lovelace dashboard (from list endpoint). */
export interface Dashboard {
  id: string;
  title: string;
  mode: string;
  url_path: string;
  /** Whether this dashboard requires admin access. */
  require_admin?: boolean;
  /** Whether the sidebar shows this dashboard. */
  show_in_sidebar?: boolean;
  icon?: string | null;
}

/** Full Lovelace configuration for a dashboard. */
export interface DashboardConfig {
  title?: string;
  views: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

// ─── Client ──────────────────────────────────────────────────────────────────

export const dashboards = {
  /** List all Lovelace dashboards. */
  list: () => request<Dashboard[]>("/dashboards"),

  /** Fetch full Lovelace config. Use "default" for the overview dashboard. */
  getConfig: (urlPath: string) =>
    request<DashboardConfig>(`/dashboards/${urlPath}/config`),
};
