import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/api/client/auth";

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

  const checkSetupStatus = useCallback(async () => {
    try {
      const data = await authApi.setupStatus();
      setState((s) => ({ ...s, setupComplete: data.setup_complete }));
    } catch {
      // If we can't reach the backend, assume not set up
      setState((s) => ({ ...s, setupComplete: false }));
    }
  }, []);

  const checkSession = useCallback(async () => {
    try {
      const data = await authApi.me();
      if (data) {
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

  // Check setup status, then session on mount
  useEffect(() => {
    (async () => {
      await checkSetupStatus();
      await checkSession();
    })();
  }, [checkSetupStatus, checkSession]);

  const login = useCallback(async (username: string, password: string) => {
    const data = await authApi.login(username, password);
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
    const options = await authApi.passkeyOptions();

    // 2. Perform browser authentication (triggers Face ID / Touch ID)
    const credential = await startAuthentication({ optionsJSON: options });

    // 3. Verify with server
    const data = await authApi.passkeyVerify(credential);
    setState((s) => ({
      ...s,
      authenticated: true,
      username: data.username,
      loading: false,
      hasPasskeys: true,
    }));
  }, []);

  const loginWithHAToken = useCallback(async (haToken: string) => {
    const data = await authApi.loginWithHAToken(haToken);
    setState((s) => ({
      ...s,
      authenticated: true,
      username: data.username,
      loading: false,
    }));
  }, []);

  const runSetup = useCallback(
    async (haUrl: string, haToken: string, password?: string | null) => {
      await authApi.setup({ ha_url: haUrl, ha_token: haToken, password });
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
    await authApi.logout();
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
