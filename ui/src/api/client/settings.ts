import { request } from "./core";

type SettingsValue = number | boolean | string;

export interface AppSettingsResponse {
  chat: Record<string, SettingsValue>;
  dashboard: Record<string, SettingsValue>;
  data_science: Record<string, SettingsValue>;
  notifications: Record<string, SettingsValue>;
}

export const appSettings = {
  get: () => request<AppSettingsResponse>("/settings"),

  patch: (body: {
    chat?: Record<string, SettingsValue>;
    dashboard?: Record<string, SettingsValue>;
    data_science?: Record<string, SettingsValue>;
    notifications?: Record<string, SettingsValue>;
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
