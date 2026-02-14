/**
 * Message list sub-component for InlineAssistant.
 */

import { Bot, User, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import type { InlineMessage, DelegationMsg } from "./types";
import type { EntityContext } from "@/lib/types";

export interface AssistantMessagesProps {
  messages: InlineMessage[];
  delegationMsgs: DelegationMsg[];
  suggestions: string[];
  activeAgent: string | null;
  entityContext?: EntityContext | null;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  onSendMessage: (content: string) => void;
}

export function AssistantMessages({
  messages,
  delegationMsgs,
  suggestions,
  activeAgent,
  entityContext,
  scrollContainerRef,
  messagesEndRef,
  onSendMessage,
}: AssistantMessagesProps) {
  return (
    <div ref={scrollContainerRef} className="max-h-80 overflow-y-auto px-4 py-3">
      {messages.length === 0 ? (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Ask the Architect to help you with schedules, analysis, or any
            question about your smart home.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSendMessage(suggestion)}
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
                  <span className="font-medium text-foreground/70">{d.from}</span>
                  <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/40" />
                  <span className="font-medium text-foreground/70">{d.to}</span>
                  <span className="ml-1 truncate">{d.content}</span>
                </div>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}
