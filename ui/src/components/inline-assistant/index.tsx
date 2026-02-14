/**
 * InlineAssistant — a collapsible mini-chat panel that can be embedded
 * in any page to provide contextual Architect conversations.
 *
 * Uses the same streamChat SSE API as the main chat page.
 * Accepts a system context message and suggestion chips specific to
 * the page it's embedded in.
 */

import { useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, ChevronDown, ChevronUp, X } from "lucide-react";
import { useInlineAssistant } from "./useInlineAssistant";
import { AssistantMessages } from "./AssistantMessages";
import { AssistantInput } from "./AssistantInput";
import type { InlineAssistantProps } from "./types";

export type { InlineAssistantProps } from "./types";

export function InlineAssistant({
  systemContext,
  suggestions,
  invalidateKeys = [],
  placeholder = "Ask Architect...",
  defaultCollapsed = true,
  model = "gpt-4o-mini",
  entityContext = null,
  onClearEntityContext,
  triggerMessage = null,
  onTriggerConsumed,
  externalMessages,
  onMessagesChange,
  externalDelegationMsgs,
  onDelegationMsgsChange,
}: InlineAssistantProps) {
  const {
    messages,
    delegationMsgs,
    input,
    setInput,
    isStreaming,
    activeAgent,
    collapsed,
    setCollapsed,
    messagesEndRef,
    scrollContainerRef,
    inputRef,
    sendMessage,
    clearChat,
  } = useInlineAssistant({
    systemContext,
    invalidateKeys,
    model,
    defaultCollapsed,
    entityContext,
    triggerMessage,
    onTriggerConsumed,
    externalMessages,
    onMessagesChange,
    externalDelegationMsgs,
    onDelegationMsgsChange,
  });

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input);
      }
    },
    [input, sendMessage],
  );

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card/50 backdrop-blur-sm">
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        aria-label="Toggle Architect assistant"
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <span className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Ask Architect
          {messages.length > 0 && (
            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
              {messages.length}
            </span>
          )}
        </span>
        {collapsed ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronUp className="h-4 w-4" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-border">
              <AssistantMessages
                messages={messages}
                delegationMsgs={delegationMsgs}
                suggestions={suggestions}
                activeAgent={activeAgent}
                entityContext={entityContext}
                scrollContainerRef={scrollContainerRef}
                messagesEndRef={messagesEndRef}
                onSendMessage={sendMessage}
              />

              {entityContext && (
                <div className="flex items-center gap-2 border-t border-border px-4 py-1.5">
                  <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-medium text-primary">
                    Focused: {entityContext.entityId}
                  </span>
                  {onClearEntityContext && (
                    <button
                      onClick={onClearEntityContext}
                      className="rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                      title="Clear focus"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )}

              <AssistantInput
                input={input}
                onInputChange={setInput}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                isStreaming={isStreaming}
                hasMessages={messages.length > 0}
                inputRef={inputRef}
                onSend={() => sendMessage(input)}
                onClearChat={clearChat}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
