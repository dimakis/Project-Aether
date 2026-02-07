import type { AgentStatusValue, VersionStatusValue } from "@/lib/types";

export const AGENT_LABELS: Record<string, string> = {
  architect: "Architect",
  data_scientist: "Data Scientist",
  librarian: "Librarian",
  developer: "Developer",
  orchestrator: "Orchestrator",
  categorizer: "Categorizer",
};

export const STATUS_COLORS: Record<AgentStatusValue, string> = {
  disabled: "bg-red-500/15 text-red-400 ring-red-500/30",
  enabled: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
  primary: "bg-amber-500/15 text-amber-400 ring-amber-500/30",
};

export const VERSION_STATUS_COLORS: Record<VersionStatusValue, string> = {
  draft: "bg-blue-500/15 text-blue-400 ring-blue-500/30",
  active: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
  archived: "bg-zinc-500/15 text-zinc-400 ring-zinc-500/30",
};

export type Tab = "overview" | "config" | "prompt" | "history";
