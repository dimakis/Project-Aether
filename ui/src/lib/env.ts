export const env = {
  API_URL: window.__ENV__?.API_URL ?? "/api",
} as const;
