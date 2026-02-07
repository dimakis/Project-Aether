import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  Fingerprint,
  KeyRound,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Server,
  Shield,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

// =============================================================================
// Setup Wizard (shown when setup_complete is false)
// =============================================================================

function SetupWizard() {
  const { runSetup } = useAuth();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [haUrl, setHaUrl] = useState("");
  const [haToken, setHaToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Full setup flow: test connection + create config
  const handleSetup = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (step === 2 && password && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setBusy(true);
    try {
      await runSetup(haUrl, haToken, password || null);
      setStep(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setBusy(false);
    }
  };

  // Passkey registration after setup
  const handleRegisterPasskey = async () => {
    setError(null);
    setBusy(true);
    try {
      const { startRegistration } = await import("@simplewebauthn/browser");
      const apiUrl = import.meta.env.VITE_API_URL || "/api";

      // Get registration options
      const optRes = await fetch(`${apiUrl}/v1/auth/passkey/register/options`, {
        method: "POST",
        credentials: "include",
      });
      if (!optRes.ok) throw new Error("Failed to get passkey options");
      const options = await optRes.json();

      // Trigger Face ID / Touch ID
      const credential = await startRegistration({ optionsJSON: options });

      // Verify with server
      const verifyRes = await fetch(`${apiUrl}/v1/auth/passkey/register/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ credential }),
      });

      if (!verifyRes.ok) {
        const body = await verifyRes.json().catch(() => ({}));
        throw new Error(body?.detail || "Passkey registration failed");
      }

      // Done! Redirect to dashboard
      window.location.href = "/";
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      if (!msg.includes("ceremony was cancelled")) {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
            <Server className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">
            Welcome to Aether
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Let's connect to your Home Assistant instance
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition-colors ${
                  step >= s
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {step > s ? <CheckCircle2 className="h-4 w-4" /> : s}
              </div>
              {s < 3 && (
                <div
                  className={`h-0.5 w-8 transition-colors ${
                    step > s ? "bg-primary" : "bg-muted"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Step 1: HA Connection */}
        {step === 1 && (
          <form onSubmit={handleSetup} className="space-y-4">
            <div>
              <label
                htmlFor="ha-url"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Home Assistant URL
              </label>
              <input
                id="ha-url"
                type="url"
                value={haUrl}
                onChange={(e) => setHaUrl(e.target.value)}
                required
                placeholder="http://homeassistant.local:8123"
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Your HA instance URL (e.g. http://192.168.1.x:8123)
              </p>
            </div>

            <div>
              <label
                htmlFor="ha-token"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Long-Lived Access Token
              </label>
              <input
                id="ha-token"
                type="password"
                value={haToken}
                onChange={(e) => setHaToken(e.target.value)}
                required
                placeholder="eyJ0eX..."
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Create one in HA: Profile &rarr; Security &rarr; Long-Lived Access Tokens
              </p>
            </div>

            <div className="pt-2">
              <label
                htmlFor="setup-password"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Fallback Password{" "}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <input
                id="setup-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Optional recovery password"
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {password && (
              <div>
                <label
                  htmlFor="confirm-password"
                  className="mb-1.5 block text-sm font-medium text-foreground"
                >
                  Confirm Password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required={!!password}
                  className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={busy || !haUrl || !haToken}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              Connect &amp; Set Up
            </button>
          </form>
        )}

        {/* Step 3: Done - Register Passkey */}
        {step === 3 && (
          <div className="space-y-4 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Setup Complete!
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Your Home Assistant is connected. Register a passkey for quick
                biometric login.
              </p>
            </div>

            <button
              onClick={handleRegisterPasskey}
              disabled={busy}
              className="flex w-full items-center justify-center gap-3 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Fingerprint className="h-5 w-5" />
              )}
              Register Passkey (Face ID / Touch ID)
            </button>

            <a
              href="/"
              className="block text-sm text-muted-foreground hover:text-foreground"
            >
              Skip for now &rarr;
            </a>
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          {step === 1 && "Your HA token is encrypted and stored securely."}
          {step === 3 && "You can register more passkeys later in Settings."}
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Login Page (shown when setup is complete)
// =============================================================================

function LoginForm() {
  const { login, loginWithPasskey, loginWithHAToken } = useAuth();

  const [mode, setMode] = useState<"passkey" | "password" | "ha-token">("passkey");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [haToken, setHaToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handlePasskeyLogin = async () => {
    setError(null);
    setBusy(true);
    try {
      await loginWithPasskey();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Passkey login failed";
      if (!msg.includes("ceremony was cancelled")) {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  };

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

  const handleHATokenLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await loginWithHAToken(haToken);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "HA token login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
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

      {/* Passkey mode (primary) */}
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
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setMode("ha-token")}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              <Shield className="h-4 w-4" />
              HA Token
            </button>
            <button
              onClick={() => setMode("password")}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              <KeyRound className="h-4 w-4" />
              Password
            </button>
          </div>
        </div>
      )}

      {/* HA Token mode */}
      {mode === "ha-token" && (
        <form onSubmit={handleHATokenLogin} className="space-y-4">
          <div>
            <label
              htmlFor="ha-token-login"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              Home Assistant Token
            </label>
            <input
              id="ha-token-login"
              type="password"
              value={haToken}
              onChange={(e) => setHaToken(e.target.value)}
              required
              placeholder="Long-lived access token"
              className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={busy || !haToken}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in with HA Token
          </button>

          <button
            type="button"
            onClick={() => setMode("passkey")}
            className="flex w-full items-center justify-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to passkey login
          </button>
        </form>
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
            className="flex w-full items-center justify-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to passkey login
          </button>
        </form>
      )}

      {/* Footer */}
      <p className="text-center text-xs text-muted-foreground">
        Secured by JWT + WebAuthn
      </p>
    </div>
  );
}

// =============================================================================
// Main Login Page
// =============================================================================

export function LoginPage() {
  const { authenticated, loading, setupComplete } = useAuth();

  // Already logged in
  if (!loading && authenticated) return <Navigate to="/" replace />;

  // Initial loading
  if (loading || setupComplete === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Setup wizard (first time)
  if (!setupComplete) {
    return <SetupWizard />;
  }

  // Normal login
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <LoginForm />
    </div>
  );
}
