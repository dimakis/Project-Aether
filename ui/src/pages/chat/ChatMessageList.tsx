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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex-1 overflow-auto">
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
