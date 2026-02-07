import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { Fingerprint, KeyRound, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

export function LoginPage() {
  const { authenticated, loading, login, loginWithPasskey } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"passkey" | "password">("passkey");

  // Already logged in — redirect to dashboard
  if (!loading && authenticated) return <Navigate to="/" replace />;

  // Initial loading state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const handlePasswordLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setError(null);
    setBusy(true);
    try {
      await loginWithPasskey();
    } catch (err: unknown) {
      // User may have cancelled, or no passkey registered
      const msg = err instanceof Error ? err.message : "Passkey login failed";
      if (!msg.includes("ceremony was cancelled")) {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Logo */}
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
            <KeyRound className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">Aether</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to your home automation dashboard
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Passkey mode */}
        {mode === "passkey" && (
          <div className="space-y-4">
            <button
              onClick={handlePasskeyLogin}
              disabled={busy}
              className="flex w-full items-center justify-center gap-3 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Fingerprint className="h-5 w-5" />
              )}
              Sign in with Passkey
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-background px-2 text-muted-foreground">
                  or
                </span>
              </div>
            </div>

            <button
              onClick={() => setMode("password")}
              className="w-full rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              Use password instead
            </button>
          </div>
        )}

        {/* Password mode */}
        {mode === "password" && (
          <form onSubmit={handlePasswordLogin} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="admin"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <button
              type="submit"
              disabled={busy || !username || !password}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Sign in
            </button>

            <button
              type="button"
              onClick={() => setMode("passkey")}
              className="w-full text-center text-xs text-muted-foreground hover:text-foreground"
            >
              Back to passkey login
            </button>
          </form>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          Secured by JWT + WebAuthn
        </p>
      </div>
    </div>
  );
}
