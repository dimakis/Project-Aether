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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSystemStatus } from "@/api/hooks";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/proposals", icon: FileCheck, label: "Proposals" },
  { to: "/insights", icon: Lightbulb, label: "Insights" },
  { to: "/entities", icon: Cpu, label: "Entities" },
  { to: "/registry", icon: BookOpen, label: "Registry" },
  { to: "/diagnostics", icon: Activity, label: "Diagnostics" },
];

export function AppLayout() {
  const { data: status } = useSystemStatus();
  const isHealthy = status?.status === "healthy";

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
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className="border-t border-border p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                isHealthy ? "bg-success" : "bg-destructive",
              )}
            />
            <span>{isHealthy ? "System Healthy" : "Connecting..."}</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
