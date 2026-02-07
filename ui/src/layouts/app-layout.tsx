import { NavLink, Outlet } from "react-router-dom";
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
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useSystemStatus, useProposals } from "@/api/hooks";
import {
  useAgentActivity,
  useActivityPanel,
  toggleActivityPanel,
} from "@/lib/agent-activity-store";
import { AgentActivityPanel } from "@/components/chat/agent-activity-panel";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/proposals", icon: FileCheck, label: "Proposals" },
  { to: "/insights", icon: Lightbulb, label: "Insights" },
  { to: "/entities", icon: Cpu, label: "Entities" },
  { to: "/registry", icon: BookOpen, label: "Registry" },
  { to: "/schedules", icon: Clock, label: "Schedules" },
  { to: "/usage", icon: BarChart3, label: "LLM Usage" },
  { to: "/diagnostics", icon: Activity, label: "Diagnostics" },
  { to: "/agents", icon: Bot, label: "Agents" },
];

const AGENT_LABELS: Record<string, string> = {
  architect: "Architect",
  data_scientist: "Data Scientist",
  sandbox: "Sandbox",
  librarian: "Librarian",
  developer: "Developer",
};

export function AppLayout() {
  const { username, logout } = useAuth();
  const { data: status } = useSystemStatus();
  const isHealthy = status?.status === "healthy";
  const agentActivity = useAgentActivity();
  const { panelOpen } = useActivityPanel();

  // Fetch pending proposal count for the sidebar badge
  const { data: pendingData } = useProposals("proposed");
  const pendingCount = pendingData?.total ?? 0;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-border bg-card">
        {/* Logo */}
        <div className="flex h-14 items-center gap-2.5 border-b border-border px-4">
          <Zap className="h-5 w-5 text-primary" />
          <span className="text-lg font-semibold tracking-tight">
            Aether
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1">{label}</span>
              {/* Pending proposals badge */}
              {label === "Proposals" && pendingCount > 0 && (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500/15 px-1.5 text-[10px] font-semibold text-amber-400 ring-1 ring-amber-500/30">
                  {pendingCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className="space-y-2 border-t border-border p-4">
          {/* User + Logout */}
          <div className="flex items-center justify-between">
            <span className="truncate text-xs text-muted-foreground">
              {username ?? "user"}
            </span>
            <button
              onClick={logout}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="Sign out"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Activity panel toggle */}
          <button
            onClick={toggleActivityPanel}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors",
              panelOpen
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Activity className="h-3.5 w-3.5" />
            Activity Panel
          </button>

          {/* System status */}
          {agentActivity.isActive ? (
            <div className="flex items-center gap-2 text-xs text-primary">
              <div className="relative h-2 w-2">
                <div className="absolute inset-0 animate-ping rounded-full bg-primary/60" />
                <div className="relative h-2 w-2 rounded-full bg-primary" />
              </div>
              <span className="truncate">
                {agentActivity.activeAgent
                  ? AGENT_LABELS[agentActivity.activeAgent] ?? agentActivity.activeAgent
                  : "Processing"}
                {agentActivity.delegatingTo && (
                  <span className="text-muted-foreground">
                    {" → "}
                    {AGENT_LABELS[agentActivity.delegatingTo] ?? agentActivity.delegatingTo}
                  </span>
                )}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div
                className={cn(
                  "h-2 w-2 rounded-full",
                  isHealthy ? "bg-success" : "bg-destructive",
                )}
              />
              <span>{isHealthy ? "System Healthy" : "Connecting..."}</span>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content + Activity Panel */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-auto">
          <Outlet />
          <footer className="px-6 py-4 text-center text-[11px] text-muted-foreground/50">
            Made with CC (Claude 🤖 &amp; Coffee ☕) 😄
          </footer>
        </main>

        {/* Global Agent Activity Panel */}
        <AgentActivityPanel />
      </div>
    </div>
  );
}
