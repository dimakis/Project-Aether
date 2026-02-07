import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThinkingDisclosureProps {
  /** The thinking/reasoning content blocks */
  thinking: string[];
  /** Whether the model is currently still thinking (streaming) */
  isActive?: boolean;
  className?: string;
}

/**
 * Collapsible disclosure for model reasoning/thinking content.
 * Shows a summary bar that expands to reveal the full chain-of-thought.
 */
export function ThinkingDisclosure({
  thinking,
  isActive = false,
  className,
}: ThinkingDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (thinking.length === 0 && !isActive) return null;

  const combinedThinking = thinking.join("\n\n---\n\n");
  const wordCount = combinedThinking.split(/\s+/).filter(Boolean).length;

  return (
    <div className={cn("mb-3", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors",
          isActive
            ? "bg-primary/5 text-primary"
            : "bg-muted/50 text-muted-foreground hover:bg-muted",
        )}
      >
        <Brain className={cn("h-3.5 w-3.5", isActive && "animate-pulse")} />
        <span className="font-medium">
          {isActive ? "Reasoning..." : `Thought for ${wordCount} words`}
        </span>
        {!isActive && (
          <motion.span
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="ml-auto"
          >
            <ChevronDown className="h-3 w-3" />
          </motion.span>
        )}
      </button>

      <AnimatePresence>
        {(isOpen || isActive) && combinedThinking && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-1 max-h-64 overflow-auto rounded-lg border border-border/30 bg-muted/30 px-3 py-2">
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-foreground">
                {combinedThinking}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
