import { motion } from "framer-motion";
import { Bot, Sparkles } from "lucide-react";

const THINKING_MESSAGES = [
  "Analyzing your smart home...",
  "Processing request...",
  "Consulting the knowledge graph...",
  "Evaluating automations...",
  "Crunching the data...",
];

interface ThinkingIndicatorProps {
  /** If content has started streaming, show the streaming cursor instead */
  hasContent?: boolean;
  /** Live status from the agent (e.g. "Running discover_entities...") */
  statusMessage?: string;
}

export function ThinkingIndicator({ hasContent = false, statusMessage }: ThinkingIndicatorProps) {
  if (hasContent) {
    return (
      <motion.span
        className="inline-block h-4 w-1.5 rounded-sm bg-primary"
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="flex items-center gap-3"
    >
      {/* Animated dots */}
      <div className="flex items-center gap-1.5">
        <motion.div
          className="h-2 w-2 rounded-full bg-primary/60"
          animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
        />
        <motion.div
          className="h-2 w-2 rounded-full bg-primary/60"
          animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
        />
        <motion.div
          className="h-2 w-2 rounded-full bg-primary/60"
          animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
        />
      </div>

      {/* Shimmer text */}
      <motion.span
        className="text-sm text-muted-foreground"
        animate={{ opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {statusMessage || "Thinking..."}
      </motion.span>
    </motion.div>
  );
}

/** Skeleton shimmer for the full message area while waiting */
export function MessageSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-3"
    >
      <div className="h-3 w-3/4 animate-pulse rounded bg-muted/50" />
      <div className="h-3 w-1/2 animate-pulse rounded bg-muted/50" />
      <div className="h-3 w-5/6 animate-pulse rounded bg-muted/50" />
    </motion.div>
  );
}
