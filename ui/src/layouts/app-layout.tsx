import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  FileCheck,
  Lightbulb,
  Cpu,
  BookOpen,
  Activity,
  Zap,
  Clock,
  BarChart3,
  Bot,
  Network,
  Star,
  LogOut,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  MapPin,
  FileBarChart,
  PanelLeft,
  Settings,
  Sparkles,
  Workflow,
  Bell,
  ListChecks,
} from "lucide-react";
import { lazy, Suspense, useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { agentLabel } from "@/lib/agent-registry";
import { useAuth } from "@/contexts/auth-context";
import { useSystemStatus, usePendingProposals, useJobs } from "@/api/hooks";
import { useGlobalActivityStream } from "@/lib/useGlobalActivityStream";
import {
  useAgentActivity,
  useActivityPanel,
  toggleActivityPanel,
  hydrateJobs,
} from "@/lib/agent-activity-store";

function useJobHydration() {
  const { data } = useJobs(20);
  useEffect(() => {
    if (data?.jobs) hydrateJobs(data.jobs);
  }, [data]);
}
import { AgentActivityPanel } from "@/components/chat/agent-activity-panel";
import { Loader2 } from "lucide-react";

const ChatPage = lazy(() => import("@/pages/chat"));

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/proposals", icon: FileCheck, label: "Proposals" },
  { to: "/insights", icon: Lightbulb, label: "Insights" },
  { to: "/reports", icon: FileBarChart, label: "Reports" },
  { to: "/optimization", icon: Sparkles, label: "Optimization" },
  { to: "/entities", icon: Cpu, label: "Entities" },
  { to: "/registry", icon: BookOpen, label: "Registry" },
  { to: "/schedules", icon: Clock, label: "Schedules" },
  { to: "/webhooks", icon: Zap, label: "Webhooks" },
  { to: "/usage", icon: BarChart3, label: "LLM Usage" },
  { to: "/diagnostics", icon: Activity, label: "Diagnostics" },
  { to: "/agents", icon: Bot, label: "Agents" },
  { to: "/architecture", icon: Network, label: "Architecture" },
  { to: "/workflows", icon: Workflow, label: "Workflows" },
  { to: "/jobs", icon: ListChecks, label: "Jobs" },
  { to: "/agents/registry", icon: Star, label: "Model Performance" },
  { to: "/dashboard-editor", icon: PanelLeft, label: "Dashboard Editor" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/settings/zones", icon: MapPin, label: "HA Zones" },
  { to: "/settings/hitl", icon: Bell, label: "Push Notifications" },
];

export function AppLayout() {
  const { username, logout } = useAuth();
  const { data: status } = useSystemStatus();
  const isHealthy = status?.status === "healthy";
  const agentActivity = useAgentActivity();
  const { panelOpen } = useActivityPanel();
  const location = useLocation();
  const isOnChat = location.pathname === "/chat";

  // Global SSE subscription for system-wide LLM activity
  useGlobalActivityStream();

  // Hydrate the job registry from MLflow traces so the activity panel
  // shows recent jobs on page load (survives refresh).
  useJobHydration();

  // Fetch pending proposal count for the sidebar badge (polls every 30s)
  const { data: pendingProposals } = usePendingProposals();
  const pendingCount = pendingProposals?.length ?? 0;

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem("aether:sidebarCollapsed") === "true";
    } catch {
      return false;
    }
  });

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("aether:sidebarCollapsed", String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar — collapsible */}
      <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-border bg-card transition-[width] duration-200 ease-out",
          sidebarCollapsed ? "w-[4rem]" : "w-56",
        )}
      >
        {/* Logo + collapse toggle */}
        <div className="flex h-14 items-center border-b border-border px-2">
          <div className="flex min-w-0 flex-1 items-center gap-2.5 px-2">
            <Zap className="h-5 w-5 shrink-0 text-primary" />
            {!sidebarCollapsed && (
              <span className="truncate text-lg font-semibold tracking-tight">
                Aether
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={toggleSidebar}
            className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              title={sidebarCollapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-lg px-2 py-2 text-sm font-medium transition-colors",
                  sidebarCollapsed ? "justify-center" : "gap-3",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!sidebarCollapsed && (
                <>
                  <span className="flex-1 truncate">{label}</span>
                  {/* Pending proposals badge */}
                  {label === "Proposals" && pendingCount > 0 && (
                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500/15 px-1.5 text-[10px] font-semibold text-amber-400 ring-1 ring-amber-500/30">
                      {pendingCount}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className={cn("space-y-2 border-t border-border", sidebarCollapsed ? "p-2" : "p-4")}>
          {/* Activity panel toggle */}
          <button
            onClick={toggleActivityPanel}
            title="Activity Panel"
            className={cn(
              "flex w-full items-center rounded-lg px-2 py-1.5 text-xs font-medium transition-colors",
              sidebarCollapsed ? "justify-center" : "gap-2",
              panelOpen
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Activity className="h-3.5 w-3.5 shrink-0" />
            {!sidebarCollapsed && <span>Activity Panel</span>}
          </button>

          {/* System status */}
          {agentActivity.isActive ? (
            <div className={cn("flex items-center text-xs text-primary", sidebarCollapsed ? "justify-center" : "gap-2")}>
              <div className="relative h-2 w-2 shrink-0">
                <div className="absolute inset-0 animate-ping rounded-full bg-primary/60" />
                <div className="relative h-2 w-2 rounded-full bg-primary" />
              </div>
              {!sidebarCollapsed && (
                <span className="min-w-0 truncate">
                  {agentActivity.activeAgent
                    ? agentLabel(agentActivity.activeAgent)
                    : "Processing"}
                  {agentActivity.delegatingTo && (
                    <span className="text-muted-foreground">
                      {" → "}
                      {agentLabel(agentActivity.delegatingTo)}
                    </span>
                  )}
                </span>
              )}
            </div>
          ) : (
            <div className={cn("flex items-center text-xs text-muted-foreground", sidebarCollapsed ? "justify-center" : "gap-2")}>
              <div
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  isHealthy ? "bg-success" : "bg-destructive",
                )}
              />
              {!sidebarCollapsed && (
                <span>{isHealthy ? "System Healthy" : "Connecting..."}</span>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content + Activity Panel */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header with UserMenu */}
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-card px-6">
          <UserMenu username={username} onLogout={logout} />
        </header>

        <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-hidden">
          {/* ChatPage is always mounted so streams survive navigation.
              Hidden via CSS when on another route. */}
          <div className={cn("h-full", isOnChat ? "" : "hidden")}>
            <Suspense
              fallback={
                <div className="flex min-h-[50vh] items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              }
            >
              <ChatPage />
            </Suspense>
          </div>

          {/* Other routes render via Outlet (hidden when on /chat) */}
          {!isOnChat && (
            <div className="h-full overflow-auto px-6 pt-6 pb-4">
              <Outlet />
              <footer className="mt-6 py-4 text-center text-[11px] text-muted-foreground/50">
                Made with CC (Claude 🤖 &amp; Coffee ☕) 😄
              </footer>
            </div>
          )}
        </main>

        {/* Global Agent Activity Panel */}
        <AgentActivityPanel />
      </div>
      </div>
    </div>
  );
}


/** UserMenu dropdown at top-right of the header. */
function UserMenu({ username, onLogout }: { username: string | null; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const displayName = username ?? "user";
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        {/* Avatar initials */}
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
          {initials}
        </div>
        <span className="hidden sm:inline">{displayName}</span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-lg border border-border bg-card shadow-lg">
          <div className="border-b border-border px-3 py-2">
            <p className="text-sm font-medium">{displayName}</p>
            <p className="text-[11px] text-muted-foreground">Signed in</p>
          </div>
          <button
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
