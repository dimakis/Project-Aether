import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { env } from "@/lib/env";

// =============================================================================
// Types
// =============================================================================

interface AuthState {
  authenticated: boolean;
  username: string | null;
  loading: boolean;
  hasPasskeys: boolean;
  setupComplete: boolean | null; // null = still checking
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  loginWithPasskey: () => Promise<void>;
  loginWithHAToken: (haToken: string) => Promise<void>;
  runSetup: (haUrl: string, haToken: string, password?: string | null) => Promise<void>;
  logout: () => Promise<void>;
  checkSetupStatus: () => Promise<void>;
}

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<AuthContextType | null>(null);

// =============================================================================
// Provider
// =============================================================================

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    authenticated: false,
    username: null,
    loading: true,
    hasPasskeys: false,
    setupComplete: null,
  });

  // Check setup status, then session on mount
  useEffect(() => {
    (async () => {
      await checkSetupStatus();
      await checkSession();
    })();
  }, []);

  const checkSetupStatus = useCallback(async () => {
    try {
      const res = await fetch(`${env.API_URL}/v1/auth/setup-status`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setState((s) => ({ ...s, setupComplete: data.setup_complete }));
      }
    } catch {
      // If we can't reach the backend, assume not set up
      setState((s) => ({ ...s, setupComplete: false }));
    }
  }, []);

  const checkSession = useCallback(async () => {
    try {
      const res = await fetch(`${env.API_URL}/v1/auth/me`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setState((s) => ({
          ...s,
          authenticated: true,
          username: data.username,
          loading: false,
          hasPasskeys: data.has_passkeys ?? false,
        }));
      } else {
        setState((s) => ({
          ...s,
          authenticated: false,
          username: null,
          loading: false,
          hasPasskeys: false,
        }));
      }
    } catch {
      setState((s) => ({
        ...s,
        authenticated: false,
        username: null,
        loading: false,
        hasPasskeys: false,
      }));
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch(`${env.API_URL}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || body?.error?.message || "Login failed");
    }

    const data = await res.json();
    setState((s) => ({
      ...s,
      authenticated: true,
      username: data.username,
      loading: false,
      hasPasskeys: false,
    }));
  }, []);

  const loginWithPasskey = useCallback(async () => {
    const { startAuthentication } = await import("@simplewebauthn/browser");

    // 1. Get authentication options
    const optRes = await fetch(
      `${env.API_URL}/v1/auth/passkey/authenticate/options`,
      { method: "POST", credentials: "include" },
    );
    if (!optRes.ok) throw new Error("Failed to get passkey options");
    const options = await optRes.json();

    // 2. Perform browser authentication (triggers Face ID / Touch ID)
    const credential = await startAuthentication({ optionsJSON: options });

    // 3. Verify with server
    const verifyRes = await fetch(
      `${env.API_URL}/v1/auth/passkey/authenticate/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ credential }),
      },
    );
    if (!verifyRes.ok) {
      const body = await verifyRes.json().catch(() => ({}));
      throw new Error(body?.detail || "Passkey authentication failed");
    }

    const data = await verifyRes.json();
    setState((s) => ({
      ...s,
      authenticated: true,
      username: data.username,
      loading: false,
      hasPasskeys: true,
    }));
  }, []);

  const loginWithHAToken = useCallback(async (haToken: string) => {
    const res = await fetch(`${env.API_URL}/v1/auth/login/ha-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ ha_token: haToken }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || body?.error?.message || "HA token login failed");
    }

    const data = await res.json();
    setState((s) => ({
      ...s,
      authenticated: true,
      username: data.username,
      loading: false,
    }));
  }, []);

  const runSetup = useCallback(
    async (haUrl: string, haToken: string, password?: string | null) => {
      const res = await fetch(`${env.API_URL}/v1/auth/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ ha_url: haUrl, ha_token: haToken, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Setup failed");
      }

      const data = await res.json();
      setState((s) => ({
        ...s,
        authenticated: true,
        username: "admin",
        loading: false,
        setupComplete: true,
      }));
    },
    [],
  );

  const logout = useCallback(async () => {
    await fetch(`${env.API_URL}/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    setState((s) => ({
      ...s,
      authenticated: false,
      username: null,
      loading: false,
      hasPasskeys: false,
    }));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        loginWithPasskey,
        loginWithHAToken,
        runSetup,
        logout,
        checkSetupStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
