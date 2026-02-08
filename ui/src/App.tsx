import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/error-boundary";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { AppLayout } from "@/layouts/app-layout";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";
import { ChatPage } from "@/pages/chat";
import { ProposalsPage } from "@/pages/proposals";
import { InsightsPage } from "@/pages/insights";
import { EntitiesPage } from "@/pages/entities";
import { RegistryPage } from "@/pages/registry";
import { DiagnosticsPage } from "@/pages/diagnostics";
import { SchedulesPage } from "@/pages/schedules";
import { UsagePage } from "@/pages/usage";
import { AgentsPage } from "@/pages/agents";
import { ArchitecturePage } from "@/pages/architecture";
import { ModelRegistryPage } from "@/pages/model-registry";
import { WebhooksPage } from "@/pages/webhooks";
import { Loader2 } from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

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

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public route */}
              <Route path="login" element={<LoginPage />} />

              {/* Protected routes */}
              <Route element={<RequireAuth />}>
                <Route element={<AppLayout />}>
                  <Route index element={<DashboardPage />} />
                  <Route path="chat" element={<ChatPage />} />
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
                </Route>
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
