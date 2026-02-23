import { env } from "@/lib/env";
import { request, ApiError } from "./core";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SetupStatusResponse {
  setup_complete: boolean;
}

export interface SessionResponse {
  username: string;
  has_passkeys?: boolean;
}

export interface LoginResponse {
  token: string;
  username: string;
  message: string;
}

export interface PasskeyAuthOptions {
  challenge: string;
  [key: string]: unknown;
}

// ─── Auth API ────────────────────────────────────────────────────────────────

export const authApi = {
  /** Check whether initial setup has been completed. */
  setupStatus: () =>
    request<SetupStatusResponse>("/auth/setup-status"),

  /**
   * Check current session. Returns the user profile if authenticated.
   *
   * Unlike other API calls, a 401 here is expected (means "not logged in")
   * rather than an error, so we catch it and return null.
   */
  me: async (): Promise<SessionResponse | null> => {
    try {
      return await request<SessionResponse>("/auth/me");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return null;
      throw err;
    }
  },

  /** Password login. */
  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  /** Login with Home Assistant long-lived token. */
  loginWithHAToken: (haToken: string) =>
    request<LoginResponse>("/auth/login/ha-token", {
      method: "POST",
      body: JSON.stringify({ ha_token: haToken }),
    }),

  /** Get passkey authentication options from server. */
  passkeyOptions: () =>
    request<PasskeyAuthOptions>("/auth/passkey/authenticate/options", {
      method: "POST",
    }),

  /** Verify passkey authentication with server. */
  passkeyVerify: (credential: unknown) =>
    request<LoginResponse>("/auth/passkey/authenticate/verify", {
      method: "POST",
      body: JSON.stringify({ credential }),
    }),

  /** Run initial setup. */
  setup: (data: { ha_url: string; ha_token: string; password?: string | null }) =>
    request<LoginResponse>("/auth/setup", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Logout (invalidates the session cookie). */
  logout: async (): Promise<void> => {
    await fetch(`${env.API_URL}/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  },
};
