import { useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { MessageBubble } from "./MessageBubble";
import { EmptyState } from "./EmptyState";
import type { DisplayMessage } from "@/lib/storage";

interface ChatMessageListProps {
  messages: DisplayMessage[];
  activeSessionId: string | null;
  copiedIdx: number | null;
  /** Live agent status (e.g. "Running discover_entities...") */
  statusMessage?: string;
  onCopy: (content: string, idx: number) => void;
  onRetry: () => void;
  onFeedback: (index: number, sentiment: "positive" | "negative") => void;
  onCreateProposal?: (yamlContent: string) => void;
  onSuggestionClick: (message: string) => void;
}

export function ChatMessageList({
  messages,
  activeSessionId,
  copiedIdx,
  statusMessage,
  onCopy,
  onRetry,
  onFeedback,
  onCreateProposal,
  onSuggestionClick,
}: ChatMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(messages.length);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /** True when the user is already at or near the bottom of the scroll area. */
  const isNearBottom = () => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  };

  useEffect(() => {
    // Always scroll for new messages (user just sent); otherwise only if near bottom
    const isNewMessage = messages.length !== prevMessageCountRef.current;
    prevMessageCountRef.current = messages.length;

    if (isNewMessage || isNearBottom()) {
      scrollToBottom();
    }
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div ref={containerRef} className="flex-1 overflow-auto">
      {isEmpty ? (
        <EmptyState onSuggestionClick={onSuggestionClick} />
      ) : (
        <div className="mx-auto max-w-3xl space-y-1 px-4 py-6">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => (
              <MessageBubble
                key={`${activeSessionId}-${i}`}
                msg={msg}
                index={i}
                isLast={i === messages.length - 1}
                copiedIdx={copiedIdx}
                statusMessage={
                  msg.isStreaming && i === messages.length - 1
                    ? statusMessage
                    : undefined
                }
                onCopy={onCopy}
                onRetry={onRetry}
                onFeedback={onFeedback}
                onCreateProposal={onCreateProposal}
              />
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}
