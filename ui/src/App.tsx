import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/error-boundary";
import { AppLayout } from "@/layouts/app-layout";
import { DashboardPage } from "@/pages/dashboard";
import { ChatPage } from "@/pages/chat";
import { ProposalsPage } from "@/pages/proposals";
import { InsightsPage } from "@/pages/insights";
import { EntitiesPage } from "@/pages/entities";
import { RegistryPage } from "@/pages/registry";
import { DiagnosticsPage } from "@/pages/diagnostics";
import { SchedulesPage } from "@/pages/schedules";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="proposals" element={<ProposalsPage />} />
              <Route path="insights" element={<InsightsPage />} />
              <Route path="entities" element={<EntitiesPage />} />
              <Route path="registry" element={<RegistryPage />} />
              <Route path="schedules" element={<SchedulesPage />} />
              <Route path="diagnostics" element={<DiagnosticsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
