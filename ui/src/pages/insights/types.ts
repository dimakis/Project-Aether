import {
  Zap,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Wrench,
  GitBranch,
  BarChart3,
  Heart,
  Users,
  Activity,
} from "lucide-react";
import type { InsightType } from "@/lib/types";

export const TYPE_CONFIG: Record<
  InsightType,
  { icon: typeof Zap; label: string; color: string }
> = {
  energy_optimization: { icon: Zap, label: "Energy", color: "text-yellow-400" },
  anomaly_detection: {
    icon: AlertTriangle,
    label: "Anomaly",
    color: "text-red-400",
  },
  usage_pattern: {
    icon: TrendingUp,
    label: "Usage",
    color: "text-cyan-400",
  },
  cost_saving: {
    icon: DollarSign,
    label: "Cost Saving",
    color: "text-green-400",
  },
  maintenance_prediction: {
    icon: Wrench,
    label: "Maintenance",
    color: "text-orange-400",
  },
  automation_gap: {
    icon: GitBranch,
    label: "Automation Gap",
    color: "text-purple-400",
  },
  automation_inefficiency: {
    icon: BarChart3,
    label: "Inefficiency",
    color: "text-amber-400",
  },
  correlation: {
    icon: Activity,
    label: "Correlation",
    color: "text-indigo-400",
  },
  device_health: {
    icon: Heart,
    label: "Device Health",
    color: "text-pink-400",
  },
  behavioral_pattern: {
    icon: Users,
    label: "Behavioral",
    color: "text-teal-400",
  },
};

export const IMPACT_STYLES: Record<string, { bg: string; text: string; ring: string }> = {
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    ring: "ring-red-500/30",
  },
  high: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    ring: "ring-orange-500/30",
  },
  medium: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    ring: "ring-blue-500/30",
  },
  low: {
    bg: "bg-zinc-500/10",
    text: "text-zinc-400",
    ring: "ring-zinc-500/30",
  },
};

export const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "reviewed", label: "Reviewed" },
  { value: "actioned", label: "Actioned" },
  { value: "dismissed", label: "Dismissed" },
];
