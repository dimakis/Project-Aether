import { useMemo } from "react";
import { motion } from "framer-motion";
import { Bot, User, Copy, Check, RotateCw, ThumbsUp, ThumbsDown } from "lucide-react";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { ThinkingIndicator } from "@/components/ui/thinking-indicator";
import { ThinkingDisclosure } from "@/components/chat/thinking-disclosure";
import { parseThinkingContent } from "@/lib/thinking-parser";
import { cn } from "@/lib/utils";
import type { DisplayMessage } from "@/lib/storage";

const messageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

interface MessageBubbleProps {
  msg: DisplayMessage;
  index: number;
  isLast: boolean;
  copiedIdx: number | null;
  onCopy: (content: string, idx: number) => void;
  onRetry: () => void;
  onFeedback: (index: number, sentiment: "positive" | "negative") => void;
  onCreateProposal?: (yamlContent: string) => void;
}

export function MessageBubble({
  msg,
  index,
  isLast,
  copiedIdx,
  onCopy,
  onRetry,
  onFeedback,
  onCreateProposal,
}: MessageBubbleProps) {
  // Parse thinking content for assistant messages
  const parsed = useMemo(() => {
    if (msg.role !== "assistant") return null;
    return parseThinkingContent(msg.content);
  }, [msg.role, msg.content]);

  const visibleContent = parsed?.visible || msg.content;
  const thinkingBlocks = parsed?.thinking ?? [];
  const isModelThinking = parsed?.isThinking ?? false;

  const timestamp = msg.timestamp ? new Date(msg.timestamp) : undefined;

  return (
    <motion.div
      layout
      initial="hidden"
      animate="visible"
      variants={messageVariants}
      className={cn(
        "group relative flex gap-3 rounded-xl px-4 py-4",
        msg.role === "user" ? "bg-accent/30" : "bg-transparent",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          msg.role === "user"
            ? "bg-primary text-primary-foreground"
            : "bg-gradient-to-br from-primary/20 to-purple-500/20 text-primary",
        )}
      >
        {msg.role === "user" ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        {/* Role label + timestamp */}
        <div className="mb-1 flex items-center gap-2">
          <span className="text-xs font-semibold">
            {msg.role === "user" ? "You" : "Aether"}
          </span>
          {timestamp && (
            <span className="text-[10px] text-muted-foreground/50">
              {timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>

        {/* Message body */}
        {msg.role === "assistant" ? (
          <div className="text-sm">
            {/* Thinking disclosure (if model had thinking content) */}
            {(thinkingBlocks.length > 0 ||
              (isModelThinking && msg.isStreaming)) && (
              <ThinkingDisclosure
                thinking={thinkingBlocks}
                isActive={isModelThinking && !!msg.isStreaming}
              />
            )}

            {visibleContent ? (
              <>
                <MarkdownRenderer content={visibleContent} onCreateProposal={onCreateProposal} />
                {msg.isStreaming && !isModelThinking && (
                  <ThinkingIndicator hasContent />
                )}
              </>
            ) : msg.isStreaming ? (
              <ThinkingIndicator />
            ) : null}

            {/* Feedback buttons (thumbs up/down) */}
            {!msg.isStreaming && visibleContent && (
              <div className="mt-2 flex items-center gap-1">
                <button
                  onClick={() => onFeedback(index, "positive")}
                  disabled={!!msg.feedback}
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    msg.feedback === "positive"
                      ? "text-emerald-400 bg-emerald-400/10"
                      : msg.feedback
                        ? "text-muted-foreground/20 cursor-not-allowed"
                        : "text-muted-foreground/40 hover:bg-emerald-400/10 hover:text-emerald-400",
                  )}
                  title="Good response"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onFeedback(index, "negative")}
                  disabled={!!msg.feedback}
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    msg.feedback === "negative"
                      ? "text-red-400 bg-red-400/10"
                      : msg.feedback
                        ? "text-muted-foreground/20 cursor-not-allowed"
                        : "text-muted-foreground/40 hover:bg-red-400/10 hover:text-red-400",
                  )}
                  title="Bad response"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <MarkdownRenderer content={msg.content} className="text-sm" onCreateProposal={msg.role === "assistant" ? onCreateProposal : undefined} />
        )}
      </div>

      {/* Action buttons (visible on hover) */}
      {!msg.isStreaming && msg.content && (
        <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={() => onCopy(visibleContent || msg.content, index)}
            className="rounded-md p-1.5 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
            title="Copy message"
          >
            {copiedIdx === index ? (
              <Check className="h-3.5 w-3.5 text-success" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
          {msg.role === "assistant" && isLast && (
            <button
              onClick={onRetry}
              className="rounded-md p-1.5 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
              title="Retry"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}
