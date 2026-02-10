/**
 * InlineAssistant — a collapsible mini-chat panel that can be embedded
 * in any page to provide contextual Architect conversations.
 *
 * Uses the same streamChat SSE API as the main chat page.
 * Accepts a system context message and suggestion chips specific to
 * the page it's embedded in.
 */

import { useState, useRef, useEffect, useCallback } from "react";
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { streamChat } from "@/api/client";
import type { ChatMessage } from "@/lib/types";
import { handleTraceEvent } from "@/lib/trace-event-handler";
import type { TraceEventChunk } from "@/lib/trace-event-handler";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ─── Types ──────────────────────────────────────────────────────────────────

interface InlineMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export interface InlineAssistantProps {
  /** System context injected as the first message (invisible to user) */
  systemContext: string;
  /** Suggestion chips shown when the chat is empty */
  suggestions: string[];
  /** React Query keys to invalidate when the assistant performs actions */
  invalidateKeys?: string[][];
  /** Placeholder text for the input */
  placeholder?: string;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Model to use (defaults to gpt-4o-mini) */
  model?: string;
}

// ─── Component ──────────────────────────────────────────────────────────────

export function InlineAssistant({
  systemContext,
  suggestions,
  invalidateKeys = [],
  placeholder = "Ask Architect...",
  defaultCollapsed = true,
  model = "gpt-4o-mini",
}: InlineAssistantProps) {
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [messages, setMessages] = useState<InlineMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      const userMsg: InlineMessage = { role: "user", content: content.trim() };
      const assistantMsg: InlineMessage = {
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      // Build full message history with system context
      const chatHistory: ChatMessage[] = [
        { role: "system", content: systemContext },
        ...messages.map((m) => ({
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

        // Invalidate relevant queries so the page data refreshes.
        // Always invalidate the provided keys, plus targeted invalidation
        // based on which tools the Architect actually called.
        for (const key of invalidateKeys) {
          queryClient.invalidateQueries({ queryKey: key });
        }

        // Targeted invalidation based on tool calls
        if (toolCallsUsed.length > 0) {
          const TOOL_INVALIDATION_MAP: Record<string, string[][]> = {
            create_insight_schedule: [["insightSchedules"]],
            run_custom_analysis: [["insights"], ["insightsSummary"]],
            analyze_energy: [["insights"], ["insightsSummary"]],
            diagnose_issue: [["insights"], ["insightsSummary"]],
            seek_approval: [["proposals"]],
          };
          for (const toolName of toolCallsUsed) {
            const keys = TOOL_INVALIDATION_MAP[toolName];
            if (keys) {
              for (const key of keys) {
                queryClient.invalidateQueries({ queryKey: key });
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
    [isStreaming, messages, systemContext, model, invalidateKeys, queryClient],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setInput("");
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card/50 backdrop-blur-sm">
      {/* Header / Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
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
              <div className="max-h-80 overflow-y-auto px-4 py-3">
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
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content || (msg.isStreaming ? "..." : "")}
                              </ReactMarkdown>
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
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

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
                        title="Clear chat"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button
                      size="icon"
                      onClick={() => sendMessage(input)}
                      disabled={!input.trim() || isStreaming}
                      className="h-7 w-7"
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
