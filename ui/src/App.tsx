import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppErrorBoundary } from "@/components/app-error-boundary";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { AppLayout } from "@/layouts/app-layout";
import { Loader2 } from "lucide-react";

// ── Lazy-loaded page components ─────────────────────────────────────────────
// Each page is loaded on demand; the browser only fetches the chunk when the
// user navigates to the route.  Named-export pages are wrapped with
// .then(m => ({ default: m.X })) to satisfy React.lazy's default-export
// requirement.

const LoginPage = lazy(() =>
  import("@/pages/login").then((m) => ({ default: m.LoginPage })),
);
const DashboardPage = lazy(() =>
  import("@/pages/dashboard").then((m) => ({ default: m.DashboardPage })),
);
// ChatPage is mounted persistently by AppLayout (not through Routes)
// so that active streams survive page navigation.
const ProposalsPage = lazy(() => import("@/pages/proposals"));
const InsightsPage = lazy(() => import("@/pages/insights"));
const EntitiesPage = lazy(() =>
  import("@/pages/entities").then((m) => ({ default: m.EntitiesPage })),
);
const RegistryPage = lazy(() => import("@/pages/registry"));
const DiagnosticsPage = lazy(() =>
  import("@/pages/diagnostics").then((m) => ({ default: m.DiagnosticsPage })),
);
const SchedulesPage = lazy(() =>
  import("@/pages/schedules").then((m) => ({ default: m.SchedulesPage })),
);
const UsagePage = lazy(() =>
  import("@/pages/usage").then((m) => ({ default: m.UsagePage })),
);
const AgentsPage = lazy(() =>
  import("@/pages/agents").then((m) => ({ default: m.AgentsPage })),
);
const ArchitecturePage = lazy(() =>
  import("@/pages/architecture").then((m) => ({ default: m.ArchitecturePage })),
);
const ModelRegistryPage = lazy(() =>
  import("@/pages/model-registry").then((m) => ({ default: m.ModelRegistryPage })),
);
const WebhooksPage = lazy(() =>
  import("@/pages/webhooks").then((m) => ({ default: m.WebhooksPage })),
);
const ZonesPage = lazy(() =>
  import("@/pages/settings/zones").then((m) => ({ default: m.ZonesPage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/settings").then((m) => ({ default: m.SettingsPage })),
);
const ReportsPage = lazy(() =>
  import("@/pages/reports").then((m) => ({ default: m.ReportsPage })),
);
const ReportDetailPage = lazy(() =>
  import("@/pages/reports/ReportDetail").then((m) => ({ default: m.ReportDetail })),
);
const DashboardEditorPage = lazy(() =>
  import("@/pages/dashboard-editor").then((m) => ({
    default: m.DashboardEditorPage,
  })),
);
const WorkflowDefinitionsPage = lazy(() =>
  import("@/pages/workflows").then((m) => ({
    default: m.WorkflowDefinitionsPage,
  })),
);

// ── Shared loading fallback ────────────────────────────────────────────────

function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

// ── Route-level error boundary ─────────────────────────────────────────────
// Wraps each lazy route so a crash in one page doesn't take down the whole
// app.  The user can navigate away or retry without a full reload.

function RouteShell() {
  return (
    <AppErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </AppErrorBoundary>
  );
}

// ── Query client ───────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ── Auth guard ─────────────────────────────────────────────────────────────

/** Route guard — redirects to /login when unauthenticated. */
function RequireAuth() {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return authenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

// ── Application root ──────────────────────────────────────────────────────

export default function App() {
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public route */}
              <Route
                path="login"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <LoginPage />
                  </Suspense>
                }
              />

              {/* Protected routes */}
              <Route element={<RequireAuth />}>
                <Route element={<AppLayout />}>
                  <Route element={<RouteShell />}>
                    <Route index element={<DashboardPage />} />
                    {/* Chat is rendered by AppLayout (persistent mount); noop route for NavLink matching */}
                    <Route path="chat" element={null} />
                    <Route path="proposals" element={<ProposalsPage />} />
                    <Route path="insights" element={<InsightsPage />} />
                    <Route path="entities" element={<EntitiesPage />} />
                    <Route path="registry" element={<RegistryPage />} />
                    <Route path="schedules" element={<SchedulesPage />} />
                    <Route path="usage" element={<UsagePage />} />
                    <Route path="diagnostics" element={<DiagnosticsPage />} />
                    <Route path="agents" element={<AgentsPage />} />
                    <Route path="architecture" element={<ArchitecturePage />} />
                    <Route path="agents/registry" element={<ModelRegistryPage />} />
                    <Route path="webhooks" element={<WebhooksPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                    <Route path="settings/zones" element={<ZonesPage />} />
                    <Route path="reports" element={<ReportsPage />} />
                    <Route path="reports/:id" element={<ReportDetailPage />} />
                    <Route path="dashboard-editor" element={<DashboardEditorPage />} />
                    <Route path="workflows" element={<WorkflowDefinitionsPage />} />
                  </Route>
                </Route>
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </AppErrorBoundary>
  );
}
