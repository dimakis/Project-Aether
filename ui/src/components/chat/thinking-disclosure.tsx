import { useState, useRef, useEffect } from "react";
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
 *
 * Shows a compact 5-line scrollable window during streaming that
 * auto-scrolls. After streaming, collapses to a summary bar
 * ("Thought for N words") that expands on click to the same 5-line box.
 */
export function ThinkingDisclosure({
  thinking,
  isActive = false,
  className,
}: ThinkingDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const combinedThinking = thinking.join("\n\n---\n\n");
  const wordCount = combinedThinking.split(/\s+/).filter(Boolean).length;

  // Auto-scroll to bottom when new thinking content arrives during streaming
  useEffect(() => {
    if (isActive && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [combinedThinking, isActive]);

  if (thinking.length === 0 && !isActive) return null;

  // During streaming: always show. After: toggle via click.
  const showContent = isActive || isOpen;

  return (
    <div className={cn("mb-3", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={showContent}
        aria-label={isActive ? "Reasoning in progress" : `Thought for ${wordCount} words`}
        className={cn(
          "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors",
          isActive
            ? "bg-primary/5 text-primary"
            : "bg-muted/50 text-muted-foreground hover:bg-muted",
        )}
      >
        <Brain className={cn("h-3.5 w-3.5", isActive && "animate-pulse")} />
        <span className="font-medium">
          {isActive
            ? "Reasoning..."
            : `Thought for ${wordCount} words`}
        </span>
        <motion.span
          animate={{ rotate: showContent ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="ml-auto"
        >
          <ChevronDown className="h-3 w-3" />
        </motion.span>
      </button>

      <AnimatePresence>
        {showContent && combinedThinking && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div
              ref={scrollRef}
              className="mt-1 max-h-[6rem] overflow-auto rounded-lg border border-border/30 bg-muted/30 px-3 py-2"
            >
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
