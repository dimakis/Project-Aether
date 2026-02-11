/**
 * InlineAssistant — a collapsible mini-chat panel that can be embedded
 * in any page to provide contextual Architect conversations.
 *
 * Uses the same streamChat SSE API as the main chat page.
 * Accepts a system context message and suggestion chips specific to
 * the page it's embedded in.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Send,
  Loader2,
  Bot,
  User,
  X,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { streamChat } from "@/api/client";
import { queryKeys } from "@/api/hooks/queryKeys";
import type { ChatMessage, EntityContext } from "@/lib/types";
import { handleTraceEvent } from "@/lib/trace-event-handler";
import type { TraceEventChunk } from "@/lib/trace-event-handler";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";

// ─── Types ──────────────────────────────────────────────────────────────────

interface InlineMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

interface DelegationMsg {
  from: string;
  to: string;
  content: string;
  ts: number;
}

export interface InlineAssistantProps {
  /** System context injected as the first message (invisible to user) */
  systemContext: string;
  /** Suggestion chips shown when the chat is empty */
  suggestions: string[];
  /** React Query keys to invalidate when the assistant performs actions */
  invalidateKeys?: readonly (readonly string[])[];
  /** Placeholder text for the input */
  placeholder?: string;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Model to use (defaults to gpt-4o-mini) */
  model?: string;
  /** Entity context injected alongside the system message */
  entityContext?: EntityContext | null;
  /** Callback to clear the entity context */
  onClearEntityContext?: () => void;
  /** Auto-send this message when set (one-shot, clears previous chat) */
  triggerMessage?: string | null;
  /** Called after triggerMessage has been consumed */
  onTriggerConsumed?: () => void;
  /** External messages state (store-driven) — when provided, internal useState is bypassed */
  externalMessages?: InlineMessage[];
  /** External setter for messages — supports both direct value and functional updater */
  onMessagesChange?: (
    action: InlineMessage[] | ((prev: InlineMessage[]) => InlineMessage[]),
  ) => void;
  /** External delegation messages (store-driven) */
  externalDelegationMsgs?: DelegationMsg[];
  /** External setter for delegation messages */
  onDelegationMsgsChange?: (msgs: DelegationMsg[]) => void;
}

// ─── Constants ───────────────────────────────────────────────────────────────

/**
 * Maps tool names returned in stream metadata to the query keys that should be
 * invalidated after the Architect calls them. Defined at module scope so it's
 * created once rather than on every render.
 */
const TOOL_INVALIDATION_MAP: Record<string, readonly (readonly string[])[]> = {
  create_insight_schedule: [queryKeys.schedules.all],
  run_custom_analysis: [queryKeys.insights.all, queryKeys.insights.summary],
  analyze_energy: [queryKeys.insights.all, queryKeys.insights.summary],
  diagnose_issue: [queryKeys.insights.all, queryKeys.insights.summary],
  seek_approval: [
    queryKeys.proposals.all,
    queryKeys.registry.automations,
    queryKeys.registry.scripts,
    queryKeys.registry.scenes,
  ],
};

// ─── Component ──────────────────────────────────────────────────────────────

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
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [internalMessages, setInternalMessages] = useState<InlineMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [internalDelegationMsgs, setInternalDelegationMsgs] = useState<DelegationMsg[]>([]);

  // Use external state when provided, otherwise fall back to internal
  const messages = externalMessages ?? internalMessages;
  const setMessages = onMessagesChange ?? setInternalMessages;
  const delegationMsgs = externalDelegationMsgs ?? internalDelegationMsgs;
  const setDelegationMsgs = onDelegationMsgsChange ?? setInternalDelegationMsgs;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Refs for values read inside sendMessage so the callback stays stable
  // and doesn't recreate on every messages/isStreaming change.
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const isStreamingRef = useRef(isStreaming);
  isStreamingRef.current = isStreaming;

  // Memoize invalidateKeys identity to avoid unnecessary callback recreation
  const stableInvalidateKeys = useMemo(() => invalidateKeys, [invalidateKeys]);

  // Smart auto-scroll: only scroll if user is near the bottom
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const isNearBottom = distanceFromBottom < 80;

    if (isNearBottom) {
      // During streaming use instant scroll to avoid jitter;
      // for new user messages use smooth scroll.
      const lastMsg = messages[messages.length - 1];
      const behavior = lastMsg?.isStreaming ? "instant" : "smooth";
      messagesEndRef.current?.scrollIntoView({ behavior: behavior as ScrollBehavior });
    }
  }, [messages]);

  // Focus input when expanded
  useEffect(() => {
    if (!collapsed) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [collapsed]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 100) + "px";
    }
  }, [input]);

  // Build effective system context with entity info
  const effectiveSystemContext = useMemo(() => {
    if (!entityContext) return systemContext;

    let ctx = `${systemContext}\n\n--- ENTITY CONTEXT ---\nThe user is viewing: ${entityContext.entityId} ("${entityContext.label}")\nType: ${entityContext.entityType}`;

    if (entityContext.configYaml) {
      ctx += `\n\nCurrent configuration:\n\`\`\`yaml\n${entityContext.configYaml}\n\`\`\``;
    }
    if (entityContext.editedYaml) {
      ctx += `\n\nUser's edited YAML:\n\`\`\`yaml\n${entityContext.editedYaml}\n\`\`\``;
    }

    return ctx;
  }, [systemContext, entityContext]);

  // Handle triggerMessage: auto-expand, clear chat, auto-send
  const triggerMessageRef = useRef(triggerMessage);
  useEffect(() => {
    // Only fire when triggerMessage transitions from null/undefined to a string
    if (
      triggerMessage &&
      triggerMessage !== triggerMessageRef.current &&
      !isStreaming
    ) {
      triggerMessageRef.current = triggerMessage;
      setCollapsed(false);
      setMessages([]);
      setDelegationMsgs([]);
      // Defer send to next tick so state updates settle
      setTimeout(() => {
        sendMessageFn(triggerMessage);
        onTriggerConsumed?.();
      }, 50);
    } else if (!triggerMessage) {
      triggerMessageRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerMessage]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreamingRef.current) return;

      const userMsg: InlineMessage = { role: "user", content: content.trim() };
      const assistantMsg: InlineMessage = {
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      // Build full message history from ref (avoids stale closure) with system + entity context
      const chatHistory: ChatMessage[] = [
        { role: "system", content: effectiveSystemContext },
        ...messagesRef.current.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
        { role: "user", content: content.trim() },
      ];

      try {
        let fullContent = "";
        let toolCallsUsed: string[] = [];

        for await (const chunk of streamChat(model, chatHistory)) {
          if (typeof chunk === "object" && "type" in chunk) {
            if (chunk.type === "metadata") {
              // Capture tool calls from metadata for targeted invalidation
              if (chunk.tool_calls) {
                toolCallsUsed = chunk.tool_calls;
              }
              continue;
            }
            if (chunk.type === "trace") {
              // Update local agent activity indicator
              handleTraceEvent(
                chunk as TraceEventChunk,
                (activity) => {
                  setActiveAgent(activity.activeAgent ?? null);
                },
                {
                  isActive: false,
                  activeAgent: null,
                  agentsSeen: [],
                  agentStates: {},
                  liveTimeline: [],
                  thinkingStream: "",
                  activeEdges: [],
                  delegationMessages: [],
                  completedAt: null,
                },
              );
              continue;
            }
            if (chunk.type === "delegation") {
              // Capture inter-agent delegation messages
              const msg: DelegationMsg = {
                from: (chunk as Record<string, unknown>).from as string,
                to: (chunk as Record<string, unknown>).to as string,
                content: (chunk as Record<string, unknown>).content as string,
                ts: ((chunk as Record<string, unknown>).ts as number) ?? Date.now() / 1000,
              };
              setDelegationMsgs((prev) => [...prev, msg]);
              continue;
            }
          }
          const text = typeof chunk === "string" ? chunk : "";
          fullContent += text;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: fullContent,
              isStreaming: true,
            };
            return updated;
          });
        }

        // Finalize
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: fullContent,
            isStreaming: false,
          };
          return updated;
        });

        // Invalidate relevant queries so the page data refreshes
        for (const key of stableInvalidateKeys) {
          queryClient.invalidateQueries({ queryKey: [...key] });
        }

        // Targeted invalidation based on which tools the Architect called
        if (toolCallsUsed.length > 0) {
          for (const toolName of toolCallsUsed) {
            const keys = TOOL_INVALIDATION_MAP[toolName];
            if (keys) {
              for (const key of keys) {
                queryClient.invalidateQueries({ queryKey: [...key] });
              }
            }
          }
        }
      } catch {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "Sorry, I encountered an error. Please try again.",
            isStreaming: false,
          };
          return updated;
        });
      } finally {
        setIsStreaming(false);
        setActiveAgent(null);
        inputRef.current?.focus();
      }
    },
    [effectiveSystemContext, model, stableInvalidateKeys, queryClient],
  );

  // Stable ref for sendMessage so triggerMessage effect doesn't depend on the callback
  const sendMessageFn = useCallback(
    (msg: string) => sendMessage(msg),
    [sendMessage],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setDelegationMsgs([]);
    setInput("");
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card/50 backdrop-blur-sm">
      {/* Header / Toggle */}
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

      {/* Collapsible body */}
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
              {/* Messages area */}
              <div ref={scrollContainerRef} className="max-h-80 overflow-y-auto px-4 py-3">
                {messages.length === 0 ? (
                  <div className="space-y-3">
                    <p className="text-xs text-muted-foreground">
                      Ask the Architect to help you with schedules, analysis, or
                      any question about your smart home.
                    </p>
                    {/* Suggestion chips */}
                    <div className="flex flex-wrap gap-1.5">
                      {suggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => sendMessage(suggestion)}
                          className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:bg-accent hover:text-foreground"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        className={cn(
                          "flex gap-2",
                          msg.role === "user" ? "justify-end" : "justify-start",
                        )}
                      >
                        {msg.role === "assistant" && (
                          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                            <Bot className="h-3.5 w-3.5 text-primary" />
                          </div>
                        )}
                        <div
                          className={cn(
                            "max-w-[85%] rounded-lg px-3 py-2 text-xs",
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted",
                          )}
                        >
                          {msg.role === "assistant" ? (
                            <div className="prose prose-xs prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                              <MarkdownRenderer
                                content={msg.content || (msg.isStreaming ? "..." : "")}
                                originalYaml={entityContext?.configYaml}
                              />
                              {msg.isStreaming && (
                                <span className="ml-1 inline-flex items-center gap-1">
                                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary/60" />
                                  {activeAgent && activeAgent !== "architect" && (
                                    <span className="text-[10px] text-muted-foreground">
                                      {activeAgent === "data_scientist"
                                        ? "Analyzing..."
                                        : activeAgent === "system"
                                          ? "Processing..."
                                          : activeAgent}
                                    </span>
                                  )}
                                </span>
                              )}
                            </div>
                          ) : (
                            <p>{msg.content}</p>
                          )}
                        </div>
                        {msg.role === "user" && (
                          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted">
                            <User className="h-3.5 w-3.5 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    ))}

                    {/* Delegation activity feed */}
                    {delegationMsgs.length > 0 && (
                      <div className="mt-2 space-y-1 rounded-lg border border-border/50 bg-muted/30 p-2">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                          Agent Activity
                        </p>
                        {delegationMsgs.map((d, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-1 text-[10px] text-muted-foreground"
                          >
                            <span className="font-medium text-foreground/70">
                              {d.from}
                            </span>
                            <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/40" />
                            <span className="font-medium text-foreground/70">
                              {d.to}
                            </span>
                            <span className="ml-1 truncate">{d.content}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* Entity context badge */}
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

              {/* Input area */}
              <div className="border-t border-border px-4 py-2">
                <div className="flex items-end gap-2">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    rows={1}
                    className="flex-1 resize-none border-0 bg-transparent px-1 py-1.5 text-xs placeholder:text-muted-foreground focus:outline-none"
                    disabled={isStreaming}
                  />
                  <div className="flex items-center gap-1">
                    {messages.length > 0 && !isStreaming && (
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={clearChat}
                        className="h-7 w-7"
                        aria-label="Clear chat"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button
                      size="icon"
                      onClick={() => sendMessage(input)}
                      disabled={!input.trim() || isStreaming}
                      className="h-7 w-7"
                      aria-label={isStreaming ? "Sending message" : "Send message"}
                    >
                      {isStreaming ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
