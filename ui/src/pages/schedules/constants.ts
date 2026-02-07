import {
  Zap,
  Activity,
  AlertCircle,
  Shield,
  Cpu,
  Thermometer,
  CloudSun,
  DollarSign,
  Gauge,
  Sparkles,
} from "lucide-react";

export const SCHEDULE_SYSTEM_CONTEXT = `You are the Architect agent on the Insight Schedules page.
Help the user create, manage, and understand insight schedules.
You have access to the create_insight_schedule tool to create recurring
analysis jobs and the run_custom_analysis tool for ad-hoc analysis.

When the user describes a schedule in natural language, use create_insight_schedule
to create it. Confirm the details with the user in your response.

Available analysis types: energy_optimization, anomaly_detection, usage_patterns,
device_health, behavior_analysis, automation_analysis, automation_gap_detection,
correlation_discovery, cost_optimization, comfort_analysis, security_audit,
weather_correlation, custom.

Available triggers: cron (periodic) and webhook (event-driven from HA).`;

export const SCHEDULE_SUGGESTIONS = [
  "Run energy analysis every morning at 8am",
  "Alert me when any device goes offline",
  "Check HVAC efficiency weekly",
  "Analyze energy costs daily at midnight",
];

export const ANALYSIS_TYPES = [
  {
    value: "energy_optimization",
    label: "Energy Optimization",
    icon: Zap,
    emoji: "⚡",
  },
  {
    value: "behavioral",
    label: "Behavioral Analysis",
    icon: Activity,
    emoji: "🧠",
  },
  {
    value: "anomaly",
    label: "Anomaly Detection",
    icon: AlertCircle,
    emoji: "🔍",
  },
  {
    value: "device_health",
    label: "Device Health",
    icon: Shield,
    emoji: "🛡️",
  },
  {
    value: "automation_gap",
    label: "Automation Gaps",
    icon: Cpu,
    emoji: "🤖",
  },
  {
    value: "comfort_analysis",
    label: "Comfort Analysis",
    icon: Thermometer,
    emoji: "🌡️",
  },
  {
    value: "security_audit",
    label: "Security Audit",
    icon: Shield,
    emoji: "🔒",
  },
  {
    value: "weather_correlation",
    label: "Weather Correlation",
    icon: CloudSun,
    emoji: "🌤️",
  },
  {
    value: "cost_optimization",
    label: "Cost Optimization",
    icon: DollarSign,
    emoji: "💰",
  },
  {
    value: "automation_efficiency",
    label: "Automation Efficiency",
    icon: Gauge,
    emoji: "📊",
  },
  {
    value: "custom",
    label: "Custom Analysis",
    icon: Sparkles,
    emoji: "✨",
  },
];

export const CRON_PRESETS = [
  { label: "Every 30 min", value: "*/30 * * * *" },
  { label: "Hourly", value: "0 * * * *" },
  { label: "Daily at 2am", value: "0 2 * * *" },
  { label: "Daily at 8am", value: "0 8 * * *" },
  { label: "Weekly (Mon 8am)", value: "0 8 * * 1" },
  { label: "Monthly (1st at 2am)", value: "0 2 1 * *" },
];
