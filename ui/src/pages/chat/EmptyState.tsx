import { motion } from "framer-motion";
import { Zap, Lightbulb, BarChart3, Settings, Home, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  {
    icon: Lightbulb,
    title: "Turn on the",
    highlight: "living room lights",
    message: "Turn on the living room lights",
    color: "text-yellow-400",
  },
  {
    icon: BarChart3,
    title: "Analyze my",
    highlight: "energy usage this week",
    message:
      "Analyze my energy consumption over the past week and suggest optimizations",
    color: "text-emerald-400",
  },
  {
    icon: Settings,
    title: "Create an automation for",
    highlight: "morning routine",
    message:
      "Help me create an automation for my morning routine that turns on lights and adjusts the thermostat",
    color: "text-blue-400",
  },
  {
    icon: Zap,
    title: "Which devices",
    highlight: "use the most power?",
    message:
      "Which devices in my home use the most power? Show me the top energy consumers",
    color: "text-orange-400",
  },
  {
    icon: Home,
    title: "Show me all",
    highlight: "devices that are on",
    message: "List all devices and lights that are currently on",
    color: "text-purple-400",
  },
  {
    icon: Sparkles,
    title: "Run diagnostics on",
    highlight: "my automations",
    message:
      "Check the health of my automations and identify any that aren't working correctly",
    color: "text-pink-400",
  },
];

const suggestionVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      delay: i * 0.08,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  }),
};

interface EmptyStateProps {
  onSuggestionClick: (message: string) => void;
}

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8 text-center"
      >
        <motion.div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10"
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Zap className="h-8 w-8 text-primary" />
        </motion.div>
        <h1 className="mb-2 text-2xl font-semibold">
          What can I help you with?
        </h1>
        <p className="text-muted-foreground">
          Ask me anything about your Home Assistant setup
        </p>
      </motion.div>
      <div className="grid max-w-2xl gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={i}
            custom={i}
            initial="hidden"
            animate="visible"
            variants={suggestionVariants}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSuggestionClick(s.message)}
            className="group rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-primary/30 hover:bg-accent"
          >
            <s.icon className={cn("mb-2 h-4 w-4", s.color)} />
            <span className="text-sm text-muted-foreground">
              {s.title}{" "}
            </span>
            <span className="text-sm font-medium">{s.highlight}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
