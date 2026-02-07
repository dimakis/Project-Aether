import { Database, BarChart3, Home } from "lucide-react";

export const COMPONENT_ICONS: Record<string, typeof Database> = {
  database: Database,
  mlflow: BarChart3,
  home_assistant: Home,
};

export const STATUS_COLORS: Record<string, { dot: string; bg: string; text: string }> = {
  healthy: { dot: "bg-emerald-400", bg: "bg-emerald-400/10", text: "text-emerald-400" },
  degraded: { dot: "bg-amber-400", bg: "bg-amber-400/10", text: "text-amber-400" },
  unhealthy: { dot: "bg-red-400", bg: "bg-red-400/10", text: "text-red-400" },
};
