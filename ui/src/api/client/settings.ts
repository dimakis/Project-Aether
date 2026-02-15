import { request } from "./core";

export interface AppSettingsResponse {
  chat: Record<string, number | boolean>;
  dashboard: Record<string, number | boolean>;
  data_science: Record<string, number | boolean>;
}

export const appSettings = {
  get: () => request<AppSettingsResponse>("/settings"),

  patch: (body: {
    chat?: Record<string, number | boolean>;
    dashboard?: Record<string, number | boolean>;
    data_science?: Record<string, number | boolean>;
  }) =>
    request<AppSettingsResponse>("/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  reset: (section: string) =>
    request<AppSettingsResponse>("/settings/reset", {
      method: "POST",
      body: JSON.stringify({ section }),
    }),
};
