import { Sparkles, Zap, Target, Code, Home, LayoutDashboard } from "lucide-react";

export const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; ring: string }
> = {
  draft: {
    label: "Draft",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  proposed: {
    label: "Pending",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    ring: "ring-amber-500/30",
  },
  approved: {
    label: "Approved",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    ring: "ring-blue-500/30",
  },
  rejected: {
    label: "Rejected",
    color: "text-red-400",
    bg: "bg-red-500/10",
    ring: "ring-red-500/30",
  },
  deployed: {
    label: "Deployed",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    ring: "ring-emerald-500/30",
  },
  rolled_back: {
    label: "Rolled Back",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  archived: {
    label: "Archived",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  failed: {
    label: "Failed",
    color: "text-red-400",
    bg: "bg-red-500/10",
    ring: "ring-red-500/30",
  },
};

export const STATUS_STRIP: Record<string, string> = {
  draft: "bg-zinc-500",
  proposed: "bg-amber-500",
  approved: "bg-blue-500",
  rejected: "bg-red-500",
  deployed: "bg-emerald-500",
  rolled_back: "bg-zinc-500",
  archived: "bg-zinc-500",
  failed: "bg-red-500",
};

export const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "proposed", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "deployed", label: "Deployed" },
  { value: "rejected", label: "Rejected" },
  { value: "rolled_back", label: "Rolled Back" },
];

export const TYPE_ICONS: Record<string, typeof Sparkles> = {
  automation: Zap,
  entity_command: Target,
  script: Code,
  scene: Home,
  dashboard: LayoutDashboard,
};
